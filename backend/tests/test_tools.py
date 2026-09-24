import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, SentEmail
from app.tools.email import enviar_email
from app.tools.web_search import buscar_web


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s


@pytest.mark.asyncio
async def test_buscar_web_devuelve_mock_de_clima_sin_api_key(session, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        results = await buscar_web(session, {"query": "clima mañana en Curitiba"})
        assert results
        assert "soleado" in results[0]["snippet"]
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_enviar_email_inserta_registro_en_sent_emails(session):
    result = await enviar_email(
        session,
        {
            "destinatario": "equipo@empresa.com",
            "asunto": "Aviso de evento",
            "cuerpo": "Mañana hay un evento al aire libre.",
        },
    )

    assert result["status"] == "sent"

    rows = (await session.execute(select(SentEmail))).scalars().all()
    assert len(rows) == 1
    assert rows[0].recipient == "equipo@empresa.com"
    assert rows[0].subject == "Aviso de evento"


@pytest.mark.asyncio
async def test_enviar_email_rechaza_destinatario_invalido(session):
    with pytest.raises(ValueError):
        await enviar_email(
            session,
            {"destinatario": "no-es-un-email", "asunto": "x", "cuerpo": "y"},
        )
