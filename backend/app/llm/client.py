from typing import Any

from anthropic import AsyncAnthropic

from app.config import get_settings

SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a organizar tareas relacionadas a eventos, "
    "clima y notificaciones por email. Respondé siempre en español, de forma "
    "breve y concreta. Cuando necesites saber si hay eventos agendados en una "
    "fecha o rango de fechas, usá la herramienta `buscar_eventos` en vez de "
    "inventar la respuesta."
)


class LLMClient:
    """Wrapper fino sobre el SDK de Anthropic. `tools` es opcional: el loop
    del agente (`app/agent/loop.py`) lo pasa siempre; otros callers pueden
    omitirlo para una llamada simple sin tool calling."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        return await self._client.messages.create(**kwargs)


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
