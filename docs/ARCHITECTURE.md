# Arquitectura — toolloop-agent

## Objetivo del sistema

Un agente ReAct (Reason → Act → Observe) expuesto vía API HTTP, que:

1. Recibe una pregunta/tarea del usuario.
2. En cada iteración llama al LLM con un set de *tool schemas* disponibles.
3. Si el LLM responde con `tool_use`, el backend ejecuta la función correspondiente
   (nunca código arbitrario generado por el modelo) y devuelve el resultado como
   `tool_result`.
4. Repite hasta que el modelo devuelve una respuesta final en texto, o hasta un
   límite máximo de iteraciones (ver Sprint 5 en `ROADMAP.md`).
5. Cada paso (pensamiento / acción / observación) se puede transmitir al frontend
   en tiempo real vía SSE (ver Sprint 4).

```
Usuario ──pregunta──▶ Agente (FastAPI + LLM tool calling)
                          │        ▲
                        acción  observación
                          ▼        │
                       Herramientas (web, BD, email)
                          │
                          ▼
                       Interfaz (chat + traza)
```

## Stack

| Capa       | Tecnología                                             |
|------------|---------------------------------------------------------|
| Backend    | Python 3.11+, FastAPI, Uvicorn                          |
| LLM        | Anthropic API (`anthropic` SDK), tool/function calling nativo |
| Persistencia | SQLAlchemy 2.0 (async) + SQLite (`aiosqlite`)          |
| Frontend   | React + TypeScript + Vite                                |
| Empaquetado| Docker (backend), `docker-compose` para levantar todo junto |

## Por qué SQLite + SQLAlchemy en vez de Supabase

El proyecto original proponía Supabase (Postgres administrado + API REST/Auth
integrada). Para esta implementación se sustituyó por **SQLite accedido vía
SQLAlchemy async**, por las siguientes razones:

- **Cero dependencias externas para correr/demostrar el proyecto.** Igual que la
  búsqueda web y el email son simulados para no depender de credenciales de
  terceros, la base de datos tampoco debería requerir una cuenta ni una clave de
  servicio: `sqlite` es un archivo local, funciona igual en tu laptop, en CI o en
  un contenedor efímero.
- **Encaja con el stack.** FastAPI + SQLAlchemy es la combinación estándar en el
  ecosistema Python; no hace falta un cliente HTTP adicional (`supabase-py`) ni
  gestionar Row Level Security para un proyecto donde el propio backend ya
  controla el acceso (el LLM nunca toca la BD directamente, solo llama
  funciones tipadas — ver más abajo).
- **Camino de migración simple.** SQLAlchemy habla con SQLite y con Postgres con
  el mismo código de modelos/queries. El día que el proyecto necesite un
  Postgres real (por ejemplo para producción multi-usuario), el cambio es de
  configuración (`DATABASE_URL`) y de driver (`asyncpg` en vez de `aiosqlite`),
  no de arquitectura. Se documenta como ítem abierto en `ROADMAP.md`.
- **Sin Row Level Security ni Auth de Supabase** porque este proyecto no tiene
  multi-tenant ni login: es una demo de patrón de agente, no un producto con
  usuarios. Si se necesitara eso en el futuro, es una capa que se agrega sobre
  FastAPI (JWT/OAuth2), no algo atado a la elección de base de datos.

## Regla de seguridad: sin SQL libre para el LLM

El modelo **nunca** genera ni ejecuta SQL. Las herramientas de base de datos son
funciones Python con parámetros tipados y validados (Pydantic), por ejemplo:

```python
def buscar_eventos(fecha_inicio: date, fecha_fin: date) -> list[Event]: ...
```

El *tool schema* que se expone al LLM describe únicamente esos parámetros. El
backend arma la query parametrizada (SQLAlchemy Core/ORM, sin f-strings ni
concatenación de strings), la ejecuta, y devuelve el resultado ya serializado
como observación. Esto elimina la clase de vulnerabilidad de inyección SQL por
diseño, no por sanitización.

## Modelo de datos (Sprint 0)

Tablas creadas desde el arranque del proyecto (aunque las herramientas que las
usan se conectan recién en Sprints 2 y 3):

- **`events`**: eventos con `id`, `title`, `description`, `location`,
  `starts_at`, `ends_at`, `is_outdoor`. Usada por la tool `buscar_eventos`.
- **`sent_emails`**: registro de "envíos" simulados con `id`, `recipient`,
  `subject`, `body`, `created_at`. Usada por la tool `enviar_email` (Sprint 3).
- **`conversations`** / **`messages`**: historial de conversación del agente
  (Sprint 1), para poder mantener contexto entre turnos y, más adelante,
  reconstruir la traza completa de una ejecución.

Ver `backend/app/db/models.py` para el detalle de columnas.

## Estructura de carpetas

```
backend/
  app/
    main.py           # FastAPI app, wiring de routers
    config.py         # Settings (pydantic-settings), lee variables de entorno
    schemas.py        # Modelos Pydantic de request/response de la API
    db/
      database.py      # engine, session factory, init_db()
      models.py         # Event, SentEmail, Conversation, Message
    llm/
      client.py         # Wrapper del cliente Anthropic (acepta tools opcionales)
    tools/
      events.py          # Tool `buscar_eventos`: schema + handler parametrizado
      registry.py         # TOOL_REGISTRY: name -> ToolSpec(schema, handler)
    agent/
      loop.py             # Ciclo ReAct: llama al LLM, ejecuta tools, repite
    api/
      chat.py            # POST /api/chat — arma el historial y llama a run_agent_loop
  tests/
    test_chat.py
    test_agent_loop.py
  scripts/
    seed_events.py     # Carga eventos de ejemplo para probar buscar_eventos
  requirements.txt
  Dockerfile
  .env.example
frontend/
  src/
    App.tsx             # UI de chat mínima
    api.ts               # cliente HTTP hacia el backend
  ...
docs/
  ARCHITECTURE.md (este archivo)
  ROADMAP.md
  DECISIONS.md
docker-compose.yml
```

## Alcance implementado hasta ahora

Se implementaron **Sprint 0 (setup)**, **Sprint 1 (loop básico sin
herramientas)** y **Sprint 2 (primera herramienta: consulta a BD)** del
roadmap original:

- Scaffolding de FastAPI (backend) y React+Vite (frontend).
- Cliente LLM (Anthropic) configurado y probado con un endpoint de chat real.
- Tablas `events`, `sent_emails`, `conversations`, `messages` creadas en SQLite
  vía SQLAlchemy.
- Endpoint `POST /api/chat` que mantiene historial de mensajes por conversación
  y llama al ciclo del agente (`run_agent_loop`).
- **Tool calling real:** el agente puede llamar a `buscar_eventos` (parámetros
  tipados, sin SQL libre) cuando lo necesita, vía el ciclo ReAct implementado
  en `app/agent/loop.py`, con un registro de herramientas declarativo
  (`app/tools/registry.py`) pensado para sumar `buscar_web` y `enviar_email`
  en Sprint 3 sin tocar el loop.
- Frontend mínimo que consume el endpoint de chat y muestra la conversación
  (todavía no muestra la traza de tool calling — eso es Sprint 4).
- `Dockerfile` + `docker-compose.yml` para correr el stack completo localmente
  (pipeline de "deploy" local, ver `ROADMAP.md` para deploy real en Sprint 6).

Los Sprints 3 a 6 (búsqueda web + email, streaming/traza, robustez, deploy
final) **no están implementados** todavía; quedan completamente documentados
en `ROADMAP.md` con su diseño técnico para que cualquier desarrollador pueda
continuarlos sin tener que re-derivar decisiones.
