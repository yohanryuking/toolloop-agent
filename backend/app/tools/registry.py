from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.email import ENVIAR_EMAIL_SCHEMA, enviar_email
from app.tools.events import BUSCAR_EVENTOS_SCHEMA, buscar_eventos
from app.tools.web_search import BUSCAR_WEB_SCHEMA, buscar_web

ToolHandler = Callable[[AsyncSession, dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    schema: dict[str, Any]
    handler: ToolHandler


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "buscar_eventos": ToolSpec(schema=BUSCAR_EVENTOS_SCHEMA, handler=buscar_eventos),
    "buscar_web": ToolSpec(schema=BUSCAR_WEB_SCHEMA, handler=buscar_web),
    "enviar_email": ToolSpec(schema=ENVIAR_EMAIL_SCHEMA, handler=enviar_email),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [spec.schema for spec in TOOL_REGISTRY.values()]
