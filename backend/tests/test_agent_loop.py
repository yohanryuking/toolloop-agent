from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.loop import MAX_ITERATIONS, run_agent_loop, run_agent_stream
from app.db.models import Base, Event, SentEmail
import app.agent.loop as loop_module
from sqlalchemy import select


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


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s


@pytest.mark.asyncio
async def test_agent_loop_executes_tool_and_returns_final_answer(monkeypatch, session):
    tomorrow = datetime.utcnow() + timedelta(days=1)
    session.add(
        Event(
            title="Feria al aire libre",
            starts_at=tomorrow,
            ends_at=tomorrow + timedelta(hours=2),
            is_outdoor=True,
        )
    )
    await session.commit()

    calls = {"count": 0}

    class FakeLLMClient:
        async def complete(self, messages, tools=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeResponse(
                    content=[
                        FakeToolUseBlock(
                            id="tool_1",
                            name="buscar_eventos",
                            input={
                                "fecha_inicio": tomorrow.date().isoformat(),
                                "fecha_fin": tomorrow.date().isoformat(),
                            },
                        )
                    ],
                    stop_reason="tool_use",
                )
            return FakeResponse(
                content=[FakeTextBlock(text="Sí, hay un evento al aire libre mañana.")],
                stop_reason="end_turn",
            )

    monkeypatch.setattr(loop_module, "get_llm_client", lambda: FakeLLMClient())

    reply = await run_agent_loop(session, [{"role": "user", "content": "¿hay eventos mañana?"}])

    assert "aire libre" in reply
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_agent_loop_max_iterations_devuelve_mensaje_explicativo(monkeypatch, session):
    calls = {"count": 0}

    class AlwaysToolUseLLMClient:
        async def complete(self, messages, tools=None):
            calls["count"] += 1
            return FakeResponse(
                content=[
                    FakeToolUseBlock(
                        id="tool_x",
                        name="buscar_eventos",
                        input={"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-02"},
                    )
                ],
                stop_reason="tool_use",
            )

    monkeypatch.setattr(loop_module, "get_llm_client", lambda: AlwaysToolUseLLMClient())

    # No debe levantar ninguna excepción: el límite se resuelve con una
    # respuesta explicativa, no con un crash del request.
    reply = await run_agent_loop(session, [{"role": "user", "content": "loop infinito"}])

    assert "no pude completar" in reply.lower()
    assert calls["count"] == MAX_ITERATIONS


@pytest.mark.asyncio
async def test_agent_loop_tool_error_se_convierte_en_observacion(monkeypatch, session):
    """Si una tool falla (ej. parámetros inválidos), el loop no debe
    propagar la excepción: la convierte en una observación de error y sigue,
    dejando que el LLM decida cómo continuar."""
    calls = {"count": 0}

    class FailingThenRecoveringLLMClient:
        async def complete(self, messages, tools=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeResponse(
                    content=[
                        FakeToolUseBlock(
                            id="tool_bad",
                            name="buscar_eventos",
                            input={"fecha_inicio": "no-es-una-fecha", "fecha_fin": "2026-01-02"},
                        )
                    ],
                    stop_reason="tool_use",
                )
            return FakeResponse(
                content=[FakeTextBlock(text="No pude leer esas fechas, ¿me las repetís?")],
                stop_reason="end_turn",
            )

    monkeypatch.setattr(loop_module, "get_llm_client", lambda: FailingThenRecoveringLLMClient())

    events = [
        step
        async for step in run_agent_stream(
            session, [{"role": "user", "content": "eventos en no-es-una-fecha"}]
        )
    ]

    observation = next(e for e in events if e["type"] == "observation")
    assert observation["is_error"] is True

    final = next(e for e in events if e["type"] == "final")
    assert "repetís" in final["text"]


@pytest.mark.asyncio
async def test_agent_loop_encadena_web_eventos_y_email(monkeypatch, session):
    """Reproduce el escenario del brief: clima + evento al aire libre + aviso
    por email, encadenando las tres herramientas en un solo turno."""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    session.add(
        Event(
            title="Feria al aire libre",
            starts_at=tomorrow,
            ends_at=tomorrow + timedelta(hours=2),
            is_outdoor=True,
        )
    )
    await session.commit()

    steps = [
        FakeResponse(
            content=[
                FakeToolUseBlock(
                    id="t1", name="buscar_web", input={"query": "clima mañana"}
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(
            content=[
                FakeToolUseBlock(
                    id="t2",
                    name="buscar_eventos",
                    input={
                        "fecha_inicio": tomorrow.date().isoformat(),
                        "fecha_fin": tomorrow.date().isoformat(),
                    },
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(
            content=[
                FakeToolUseBlock(
                    id="t3",
                    name="enviar_email",
                    input={
                        "destinatario": "equipo@empresa.com",
                        "asunto": "Evento al aire libre mañana",
                        "cuerpo": "Va a estar soleado, no cancelen la feria.",
                    },
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(
            content=[FakeTextBlock(text="Listo, avisé al equipo por email.")],
            stop_reason="end_turn",
        ),
    ]

    class ScriptedLLMClient:
        def __init__(self) -> None:
            self._index = 0

        async def complete(self, messages, tools=None):
            response = steps[self._index]
            self._index += 1
            return response

    monkeypatch.setattr(loop_module, "get_llm_client", lambda: ScriptedLLMClient())

    reply = await run_agent_loop(
        session,
        [{"role": "user", "content": "revisa el clima y si hay evento al aire libre avisa por mail"}],
    )

    assert "avisé" in reply
    sent = (await session.execute(select(SentEmail))).scalars().all()
    assert len(sent) == 1
    assert sent[0].recipient == "equipo@empresa.com"
