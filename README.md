# toolloop-agent

Agente autónomo con function calling que encadena búsqueda web, consultas a
base de datos y envío de emails (simulado), mostrando paso a paso su ciclo de
pensamiento → acción → observación. Stack: FastAPI · React · LLM con tool
calling (Anthropic).

📄 **Documentación completa:**
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura, stack, modelo
  de datos y por qué se eligió SQLite/SQLAlchemy en vez de Supabase.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — qué está implementado (Sprint 0 y 1)
  y el diseño técnico detallado de los sprints restantes (2 a 6) para que
  cualquier desarrollador pueda continuarlos.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones de diseño puntuales.

## Estado actual: Sprints 0, 1 y 2

Lo que funciona hoy: un endpoint de chat (`POST /api/chat`) que mantiene
historial de conversación en SQLite y que puede decidir consultar la agenda
de eventos vía tool calling nativo del LLM (`buscar_eventos`, con parámetros
tipados y sin SQL libre). Búsqueda web y email simulado quedan para el
Sprint 3 (ver `docs/ROADMAP.md`).

Para probar la herramienta de eventos con datos de ejemplo:

```bash
cd backend && python -m scripts.seed_events
```

Y luego preguntarle al agente algo como *"¿hay algún evento agendado
mañana?"*.

## Cómo correrlo

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # y completar ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Corre en `http://localhost:8000`. Docs interactivas en `/docs`.

Tests:

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Corre en `http://localhost:5173`.

### Con Docker

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build
```

## Estructura

```
backend/    # FastAPI + SQLAlchemy (SQLite) + cliente Anthropic
frontend/   # React + Vite + TypeScript
docs/       # Arquitectura, roadmap y decisiones de diseño
```
