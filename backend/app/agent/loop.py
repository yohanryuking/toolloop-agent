import json
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import get_llm_client
from app.observability.logger import get_logger
from app.tools.registry import TOOL_REGISTRY, tool_schemas

# Salvaguarda contra loops infinitos: si se llega a este límite de llamadas
# al LLM sin una respuesta final, el agente responde explicándolo en vez de
# loopear indefinidamente (ver `_MAX_ITERATIONS_MESSAGE` más abajo).
MAX_ITERATIONS = 6

_MAX_ITERATIONS_MESSAGE = (
    "No pude completar la tarea en los pasos disponibles "
    f"({MAX_ITERATIONS} llamadas al modelo). Probá reformular el pedido o "
    "dividirlo en pasos más chicos."
)

logger = get_logger(__name__)


async def run_agent_stream(
    session: AsyncSession,
    messages: list[dict[str, Any]],
    *,
    conversation_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Ciclo ReAct como generador: yield-ea un dict por cada paso.

    Tipos de paso emitidos:
      - {"type": "action", "tool": str, "input": dict}
      - {"type": "observation", "tool": str, "output": Any, "is_error": bool}
      - {"type": "final", "text": str, "max_iterations_reached"?: bool}

    `messages` es el historial en formato de la API de Anthropic. Los pasos
    intermedios (tool_use/tool_result) viven solo en el loop local; lo único
    que persiste el caller (además de los pasos que quiera guardar del
    generador) es el mensaje de usuario y la respuesta final.

    Nunca propaga una excepción por un fallo de herramienta ni por alcanzar
    el límite de iteraciones: ambos casos terminan en un paso `final`
    explicativo, para que el caller (endpoint HTTP) no tenga que lidiar con
    excepciones a mitad de una respuesta que ya empezó a transmitirse.
    """
    llm = get_llm_client()
    conversation = list(messages)

    for _ in range(MAX_ITERATIONS):
        response = await llm.complete(messages=conversation, tools=tool_schemas())

        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            yield {"type": "final", "text": final_text}
            return

        conversation.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            yield {"type": "action", "tool": block.name, "input": block.input}

            result_block = await _execute_tool_use(session, block, conversation_id)
            tool_results.append(result_block)
            yield {
                "type": "observation",
                "tool": block.name,
                "output": result_block["content"],
                "is_error": result_block.get("is_error", False),
            }

        conversation.append({"role": "user", "content": tool_results})

    logger.warning(
        "agent_max_iterations_reached conversation_id=%s max_iterations=%d",
        conversation_id,
        MAX_ITERATIONS,
    )
    yield {
        "type": "final",
        "text": _MAX_ITERATIONS_MESSAGE,
        "max_iterations_reached": True,
    }


async def run_agent_loop(
    session: AsyncSession,
    messages: list[dict[str, Any]],
    *,
    conversation_id: str | None = None,
) -> str:
    """Variante no-streaming: consume `run_agent_stream` y devuelve solo el
    texto final. Usada por el endpoint simple `POST /api/chat`."""
    async for step in run_agent_stream(session, messages, conversation_id=conversation_id):
        if step["type"] == "final":
            return step["text"]
    # Inalcanzable en la práctica: run_agent_stream siempre termina con un
    # paso "final" (respuesta del modelo o mensaje de límite de iteraciones).
    return _MAX_ITERATIONS_MESSAGE


async def _execute_tool_use(
    session: AsyncSession, block: Any, conversation_id: str | None
) -> dict[str, Any]:
    spec = TOOL_REGISTRY.get(block.name)
    if spec is None:
        logger.warning(
            "agent_unknown_tool conversation_id=%s tool=%s",
            conversation_id,
            block.name,
        )
        return _tool_error(block.id, f"Herramienta desconocida: {block.name}")

    started = time.monotonic()
    try:
        result = await spec.handler(session, block.input)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de tool se
        # convierte en una observación de error para que el LLM decida cómo
        # seguir, en vez de tumbar el request con un 500.
        duration_ms = (time.monotonic() - started) * 1000
        logger.warning(
            "agent_tool_error conversation_id=%s tool=%s input=%s duration_ms=%.1f error=%s",
            conversation_id,
            block.name,
            block.input,
            duration_ms,
            exc,
        )
        return _tool_error(block.id, f"La herramienta '{block.name}' falló: {exc}")

    duration_ms = (time.monotonic() - started) * 1000
    logger.info(
        "agent_tool_ok conversation_id=%s tool=%s duration_ms=%.1f",
        conversation_id,
        block.name,
        duration_ms,
    )
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result, default=str),
    }


def _tool_error(tool_use_id: str, message: str) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": message,
        "is_error": True,
    }
