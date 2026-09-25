import json
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import get_llm_client
from app.tools.registry import TOOL_REGISTRY, tool_schemas

# Salvaguarda mínima contra loops infinitos. El manejo robusto de errores de
# herramientas y de este límite (respuesta explicativa al usuario, logging,
# etc.) es el alcance de Sprint 5 — ver docs/ROADMAP.md.
MAX_ITERATIONS = 6


class AgentError(Exception):
    pass


async def run_agent_stream(
    session: AsyncSession, messages: list[dict[str, Any]]
) -> AsyncIterator[dict[str, Any]]:
    """Ciclo ReAct como generador: yield-ea un dict por cada paso.

    Tipos de paso emitidos:
      - {"type": "action", "tool": str, "input": dict}
      - {"type": "observation", "tool": str, "output": Any, "is_error": bool}
      - {"type": "final", "text": str}

    `messages` es el historial en formato de la API de Anthropic. Los pasos
    intermedios (tool_use/tool_result) viven solo en el loop local; lo único
    que persiste el caller (además de los pasos que quiera guardar del
    generador) es el mensaje de usuario y la respuesta final.
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

            result_block = await _execute_tool_use(session, block)
            tool_results.append(result_block)
            yield {
                "type": "observation",
                "tool": block.name,
                "output": result_block["content"],
                "is_error": result_block.get("is_error", False),
            }

        conversation.append({"role": "user", "content": tool_results})

    raise AgentError("Se alcanzó el máximo de iteraciones sin una respuesta final.")


async def run_agent_loop(session: AsyncSession, messages: list[dict[str, Any]]) -> str:
    """Variante no-streaming: consume `run_agent_stream` y devuelve solo el
    texto final. Usada por el endpoint simple `POST /api/chat`."""
    async for step in run_agent_stream(session, messages):
        if step["type"] == "final":
            return step["text"]
    raise AgentError("El generador del agente terminó sin una respuesta final.")


async def _execute_tool_use(session: AsyncSession, block: Any) -> dict[str, Any]:
    spec = TOOL_REGISTRY.get(block.name)
    if spec is None:
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": f"Herramienta desconocida: {block.name}",
            "is_error": True,
        }

    result = await spec.handler(session, block.input)
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result, default=str),
    }
