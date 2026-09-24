from typing import Any

import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.tools.mock_web_data import mock_search

BUSCAR_WEB_SCHEMA: dict[str, Any] = {
    "name": "buscar_web",
    "description": (
        "Busca información actualizada en la web, por ejemplo el clima o "
        "noticias. Devuelve una lista breve de resultados (título, resumen, "
        "url). Usala para datos externos que no están en la BD interna de "
        "eventos."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Términos de búsqueda, ej. 'clima mañana en Curitiba'.",
            }
        },
        "required": ["query"],
    },
}


class BuscarWebInput(BaseModel):
    query: str


async def buscar_web(_session: AsyncSession, raw_input: dict[str, Any]) -> list[dict[str, str]]:
    """Tool: búsqueda web. Usa una API real si hay `TAVILY_API_KEY`
    configurada; si no, devuelve resultados mockeados (`mock_web_data.py`)
    para poder demostrar el proyecto sin depender de credenciales externas.
    """
    params = BuscarWebInput.model_validate(raw_input)
    settings = get_settings()

    if not settings.tavily_api_key:
        return mock_search(params.query)

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": params.query,
                "max_results": 3,
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "title": item.get("title", ""),
            "snippet": item.get("content", ""),
            "url": item.get("url", ""),
        }
        for item in data.get("results", [])
    ]
