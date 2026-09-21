from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event

BUSCAR_EVENTOS_SCHEMA: dict[str, Any] = {
    "name": "buscar_eventos",
    "description": (
        "Busca eventos agendados cuya fecha de inicio cae dentro de un rango "
        "[fecha_inicio, fecha_fin] (ambos inclusive). Usala para saber si hay "
        "algún evento programado en una fecha dada, por ejemplo para decidir "
        "si corresponde avisar por email."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fecha_inicio": {
                "type": "string",
                "format": "date",
                "description": "Fecha de inicio del rango, formato YYYY-MM-DD.",
            },
            "fecha_fin": {
                "type": "string",
                "format": "date",
                "description": "Fecha de fin del rango, formato YYYY-MM-DD.",
            },
        },
        "required": ["fecha_inicio", "fecha_fin"],
    },
}


class BuscarEventosInput(BaseModel):
    fecha_inicio: date
    fecha_fin: date


async def buscar_eventos(session: AsyncSession, raw_input: dict[str, Any]) -> list[dict[str, Any]]:
    """Tool: consulta parametrizada a la tabla `events`.

    El LLM solo puede pasar `fecha_inicio`/`fecha_fin`; nunca genera SQL.
    """
    params = BuscarEventosInput.model_validate(raw_input)
    range_start = datetime.combine(params.fecha_inicio, time.min)
    range_end = datetime.combine(params.fecha_fin, time.max)

    result = await session.execute(
        select(Event)
        .where(Event.starts_at >= range_start, Event.starts_at <= range_end)
        .order_by(Event.starts_at)
    )
    events = result.scalars().all()

    return [
        {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "location": event.location,
            "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat(),
            "is_outdoor": event.is_outdoor,
        }
        for event in events
    ]
