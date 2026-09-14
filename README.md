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

## Estado actual: Fase 1 (Sprint 0 + Sprint 1)

Lo que funciona hoy: un endpoint de chat (`POST /api/chat`) que mantiene
historial de conversación en SQLite y llama al LLM **sin tool calling
todavía**. Esto valida la base (persistencia, wiring del cliente LLM, CORS,
frontend) antes de sumar herramientas (Sprint 2+, documentado en el roadmap).

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
