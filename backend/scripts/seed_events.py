"""Inserta eventos de ejemplo para poder probar `buscar_eventos` sin tener
que cargar datos a mano.

Uso:
    cd backend && python -m scripts.seed_events
"""

import asyncio
from datetime import datetime, timedelta

from app.db.database import SessionLocal, init_db
from app.db.models import Event


def _sample_events() -> list[Event]:
    tomorrow = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return [
        Event(
            title="Feria de comida al aire libre",
            description="Feria de food trucks en la plaza central.",
            location="Plaza Central",
            starts_at=tomorrow,
            ends_at=tomorrow + timedelta(hours=4),
            is_outdoor=True,
        ),
        Event(
            title="Reunión de equipo",
            description="Sync semanal del equipo de producto.",
            location="Sala de reuniones 2",
            starts_at=tomorrow + timedelta(days=1, hours=1),
            ends_at=tomorrow + timedelta(days=1, hours=2),
            is_outdoor=False,
        ),
    ]


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        for event in _sample_events():
            session.add(event)
        await session.commit()
    print("Eventos de ejemplo insertados.")


if __name__ == "__main__":
    asyncio.run(main())
