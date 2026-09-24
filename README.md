# toolloop-agent

Agente autónomo con function calling que encadena búsqueda web, consultas a
base de datos y envío de emails (simulado), mostrando paso a paso su ciclo de
pensamiento → acción → observación. Stack: FastAPI · React · LLM con tool
calling (Anthropic).

📄 **Documentación completa:**
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura, stack, modelo
  de datos y por qué se eligió SQLite/SQLAlchemy en vez de Supabase.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — qué está implementado (Sprints 0 a 3)
  y el diseño técnico detallado de los sprints restantes (4 a 6) para que
  cualquier desarrollador pueda continuarlos.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decisiones de diseño puntuales.

## Estado actual: Sprints 0, 1, 2 y 3

Lo que funciona hoy: un endpoint de chat (`POST /api/chat`) que mantiene
historial de conversación en SQLite y que puede encadenar tres herramientas
vía tool calling nativo del LLM:

- `buscar_eventos`: consulta la agenda interna (parámetros tipados, sin SQL
  libre).
- `buscar_web`: búsqueda web mockeada por defecto (ej. clima), o real si se
  configura `TAVILY_API_KEY`.
- `enviar_email`: "envía" un email insertando un row en `sent_emails` (sin
  SMTP real), solo cuando el usuario lo pide explícitamente.

Streaming de la traza paso a paso queda para el Sprint 4 (ver
`docs/ROADMAP.md`).

Para probar con datos de ejemplo:

```bash
cd backend && python -m scripts.seed_events
```

Y luego preguntarle al agente algo como *"revisá el clima de mañana y si
tenemos un evento al aire libre ese día, avisá al equipo por email"*.

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
