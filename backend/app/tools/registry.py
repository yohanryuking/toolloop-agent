from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.events import BUSCAR_EVENTOS_SCHEMA, buscar_eventos

ToolHandler = Callable[[AsyncSession, dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    schema: dict[str, Any]
    handler: ToolHandler


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "buscar_eventos": ToolSpec(schema=BUSCAR_EVENTOS_SCHEMA, handler=buscar_eventos),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [spec.schema for spec in TOOL_REGISTRY.values()]
