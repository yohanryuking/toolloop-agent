"""Levanta el backend real con un LLM *simulado* que sigue el guion del
brief (clima -> evento -> email), para poder grabar un demo o probar la app
sin gastar una API key de Anthropic real. Las herramientas (`buscar_web`,
`buscar_eventos`, `enviar_email`) corren de verdad contra una base SQLite
real — lo único simulado es la respuesta del modelo.

Uso:
    cd backend
    python -m scripts.demo_server

Con el frontend corriendo aparte apuntando a este puerto
(`VITE_API_URL=http://localhost:8010 npm run dev`), se puede probar el flujo
completo end-to-end tal como lo haría un usuario real.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Variables de entorno para esta corrida (no pisa tu .env real: solo aplica
# si no están seteadas ya en el proceso).
os.environ.setdefault("ANTHROPIC_API_KEY", "demo-key-no-se-usa")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./demo_toolloop.db")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")

import app.agent.loop as loop_module  # noqa: E402
from app.db.database import SessionLocal, init_db  # noqa: E402
from app.db.models import Event  # noqa: E402

DEMO_PORT = int(os.environ.get("DEMO_PORT", "8010"))


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list[Any]
    stop_reason: str


class ScriptedDemoLLMClient:
    """Sigue el guion del brief: clima -> evento -> email -> respuesta final.

    Cada instancia arranca en el paso 0 — como `get_llm_client()` se llama
    una vez por request, cada conversación nueva repite el mismo guion desde
    el principio, sin importar cuántas veces se corra la demo.
    """

    def __init__(self) -> None:
        self._index = 0

    async def complete(self, messages, tools=None):
        # Delay artificial para que la traza se vea aparecer paso a paso en
        # un video/demo en vivo, como pasaría con la latencia real de una
        # API de LLM.
        await asyncio.sleep(1.3)

        tomorrow = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
        script = [
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="demo_1", name="buscar_web", input={"query": "clima mañana"}
                    )
                ],
                stop_reason="tool_use",
            ),
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="demo_2",
                        name="buscar_eventos",
                        input={"fecha_inicio": tomorrow, "fecha_fin": tomorrow},
                    )
                ],
                stop_reason="tool_use",
            ),
            FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="demo_3",
                        name="enviar_email",
                        input={
                            "destinatario": "equipo@empresa.com",
                            "asunto": "Feria de comida al aire libre - confirmado para mañana",
                            "cuerpo": (
                                "Hola equipo,\n\nRevisé el pronóstico de mañana: va a estar "
                                "soleado (27°C, 10% de probabilidad de lluvia), así que la "
                                "Feria de comida al aire libre en la Plaza Central sigue en "
                                "pie sin cambios.\n\nSaludos,\nEl agente"
                            ),
                        },
                    )
                ],
                stop_reason="tool_use",
            ),
            FakeResponse(
                content=[
                    FakeTextBlock(
                        text=(
                            "Listo. Mañana va a estar soleado (27°C), así que la Feria de "
                            "comida al aire libre en la Plaza Central sigue en pie. Ya le "
                            "avisé al equipo por email confirmando que no hace falta cambiar "
                            "nada."
                        )
                    )
                ],
                stop_reason="end_turn",
            ),
        ]
        response = script[min(self._index, len(script) - 1)]
        self._index += 1
        return response


async def _seed_demo_event() -> None:
    await init_db()
    tomorrow = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    async with SessionLocal() as session:
        session.add(
            Event(
                title="Feria de comida al aire libre",
                description="Feria de food trucks en la plaza central.",
                location="Plaza Central",
                starts_at=tomorrow,
                ends_at=tomorrow + timedelta(hours=4),
                is_outdoor=True,
            )
        )
        await session.commit()


def main() -> None:
    loop_module.get_llm_client = lambda: ScriptedDemoLLMClient()

    asyncio.run(_seed_demo_event())

    import uvicorn
    from app.main import app

    print(f"Backend demo (LLM simulado) en http://localhost:{DEMO_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=DEMO_PORT, log_level="info")


if __name__ == "__main__":
    main()
