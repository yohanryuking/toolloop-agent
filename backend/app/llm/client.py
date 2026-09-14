from typing import Any

from anthropic import AsyncAnthropic

from app.config import get_settings

SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a organizar tareas relacionadas a eventos, "
    "clima y notificaciones por email. Respondé siempre en español, de forma "
    "breve y concreta."
)


class LLMClient:
    """Wrapper fino sobre el SDK de Anthropic.

    En Fase 1 (Sprint 1) se usa sin `tools`. La firma ya acepta un parámetro
    `tools` opcional para que Sprint 2 pueda sumar tool calling sin tener que
    tocar este wrapper.
    """

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
