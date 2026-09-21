import json
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


async def run_agent_loop(session: AsyncSession, messages: list[dict[str, Any]]) -> str:
    """Ciclo ReAct: llama al LLM, ejecuta tools si las pide, repite.

    `messages` es el historial en formato de la API de Anthropic. Los pasos
    intermedios (tool_use/tool_result) viven solo en esta función; lo único
    que persiste el caller es el mensaje de usuario y la respuesta final.
    """
    llm = get_llm_client()
    conversation = list(messages)

    for _ in range(MAX_ITERATIONS):
        response = await llm.complete(messages=conversation, tools=tool_schemas())

        if response.stop_reason != "tool_use":
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        conversation.append({"role": "assistant", "content": response.content})
        conversation.append(
            {
                "role": "user",
                "content": [
                    await _execute_tool_use(session, block)
                    for block in response.content
                    if block.type == "tool_use"
                ],
            }
        )

    raise AgentError("Se alcanzó el máximo de iteraciones sin una respuesta final.")


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
