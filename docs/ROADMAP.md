# Roadmap — toolloop-agent

Estado: **Sprints 0 a 5 implementados.** Sprint 6 documentado a continuación
como guía de continuación (diseño técnico, no solo la idea general del
sprint).

---

## ✅ Sprint 0 — Setup (implementado)

- [x] Scaffolding FastAPI (`backend/`) y React+Vite (`frontend/`).
- [x] Acceso a LLM con tool calling nativo (Anthropic SDK) configurado vía
      `ANTHROPIC_API_KEY` en `.env`.
- [x] Tablas `events` y `sent_emails` en SQLite (vía SQLAlchemy), más
      `conversations`/`messages` para el historial del agente.
- [x] `Dockerfile` + `docker-compose.yml` como pipeline de build/run local.

## ✅ Sprint 1 — Loop básico sin herramientas (implementado)

- [x] `POST /api/chat`: recibe `{conversation_id?, message}`, persiste el
      mensaje del usuario, arma el historial completo de la conversación,
      llama al LLM (sin tools) y persiste + devuelve la respuesta.
- [x] Manejo de historial en `conversations` / `messages` (no en memoria del
      proceso, para que sobreviva reinicios y sea la base de la traza futura).
- [x] Frontend mínimo que muestra la conversación y permite mandar mensajes.

---

## ✅ Sprint 2 — Primera herramienta: consulta a BD (implementado)

El agente ahora puede decidir consultar eventos en la BD.

- [x] Tool schema `buscar_eventos` (formato Anthropic `tools=[...]`) en
      `app/tools/events.py`, con `fecha_inicio`/`fecha_fin` como únicos
      parámetros (tipos primitivos, nunca un "query" libre).
- [x] `app/tools/events.py::buscar_eventos(session, raw_input)` valida los
      parámetros con Pydantic (`BuscarEventosInput`) y ejecuta una query
      parametrizada contra `events` con SQLAlchemy — nunca SQL crudo.
- [x] `app/agent/loop.py::run_agent_loop()` reemplaza la llamada directa y
      simple de Sprint 1: llama al LLM con `tools=tool_schemas()`, y si
      `stop_reason == "tool_use"` ejecuta la(s) función(es) Python
      correspondientes, arma los `tool_result` y vuelve a llamar al LLM;
      si `stop_reason == "end_turn"` devuelve la respuesta final. Incluye un
      límite duro de iteraciones (`MAX_ITERATIONS`) como salvaguarda mínima
      contra loops infinitos — el manejo robusto (respuesta explicativa al
      usuario en vez de excepción, logging) queda para Sprint 5.
- [x] Registro de herramientas declarativo: `app/tools/registry.py::TOOL_REGISTRY`
      mapea `name -> ToolSpec(schema, handler)`. Agregar una herramienta nueva
      (Sprint 3) es agregar una entrada al dict.
- [x] Tests (`tests/test_agent_loop.py`): mockean la respuesta del LLM en dos
      turnos (uno con `tool_use`, otro con la respuesta final) y verifican que
      se ejecuta `buscar_eventos` con los parámetros correctos contra una BD
      SQLite en memoria; también cubren el corte por `MAX_ITERATIONS`.
- [x] `backend/scripts/seed_events.py`: inserta un par de eventos de ejemplo
      (uno al aire libre) para poder probar la tool sin cargar datos a mano.

**Nota de diseño (se mantiene):** el LLM nunca pasa un string SQL como
parámetro. Los parámetros del schema son siempre tipos primitivos (fechas),
nunca "query" o "filter" libres.

## ✅ Sprint 3 — Segunda y tercera herramienta (implementado)

- [x] **Búsqueda web** (`app/tools/web_search.py::buscar_web(query: str)`):
      mock por defecto, con datos fijos en `app/tools/mock_web_data.py`
      (respuesta de clima si la query menciona "clima"/"weather", resultado
      genérico en cualquier otro caso). Si hay `TAVILY_API_KEY` configurada,
      usa la API real de Tavily en su lugar vía `httpx` — mismo patrón que
      Stripe en el proyecto anterior: **interfaz igual, implementación real
      opcional**.
- [x] **Email simulado** (`app/tools/email.py::enviar_email(destinatario,
      asunto, cuerpo)`): valida el formato del destinatario con Pydantic e
      inserta un row en `sent_emails`. No hay SMTP real.
- [x] Ambas registradas en `TOOL_REGISTRY` junto a `buscar_eventos`
      (`app/tools/registry.py`).
- [x] System prompt actualizado (`app/llm/client.py`) explicando cuándo usar
      cada herramienta, y en particular que `enviar_email` solo se usa si el
      usuario lo pidió explícitamente, nunca por iniciativa propia del
      agente.
- [x] Tests: `tests/test_tools.py` (mock de `buscar_web`, inserción y
      validación de `enviar_email`) y un test de integración en
      `tests/test_agent_loop.py` que reproduce el escenario completo del
      brief — clima → evento al aire libre → aviso por email — encadenando
      las tres herramientas en un solo turno del agente.

**Pendiente / fuera de alcance de este sprint:** sanitizar el `cuerpo` del
email si en algún momento se renderiza como HTML en el frontend (hoy se
persiste y se muestra como texto plano) — ver Sprint 5.

## ✅ Sprint 4 — Streaming + panel de traza (implementado)

- [x] Nuevo endpoint `POST /api/chat/stream` (SSE, `text/event-stream`) que
      emite un evento por cada paso del loop: `{"type": "action" |
      "observation" | "final" | "error" | "conversation_id" | "done", ...}`.
      `POST /api/chat` (Sprint 1) se mantiene sin cambios para clientes que
      solo quieren la respuesta final de una sola vez (y lo siguen usando los
      tests existentes).
- [x] `app/agent/loop.py::run_agent_stream()` es ahora un async generator que
      yield-ea cada paso (`action`/`observation`/`final`); `run_agent_loop()`
      quedó como wrapper delgado sobre ese generador para no duplicar lógica.
- [x] Tabla `agent_steps` (nueva, en `app/db/models.py`) donde se persiste
      cada paso emitido por `/chat/stream`, y `GET
      /api/conversations/{id}/steps` para reconstruir la traza de una
      ejecución pasada.
- [x] Frontend: layout de dos paneles (`frontend/src/App.tsx`) — chat a la
      izquierda, timeline de traza a la derecha — que se actualiza en vivo
      paso a paso.

**Nota de implementación (desvío del diseño original):** el endpoint es
`POST` (necesita mandar el mensaje en el body), así que el frontend no usa
`EventSource` nativo del browser (que solo soporta `GET`) — en cambio
`frontend/src/api.ts::streamMessage()` usa `fetch` + `ReadableStream` y
parsea manualmente los bloques `data: ...\n\n`. Mismo resultado (streaming
en vivo), mecanismo distinto al que sugería el brief original.

**Gotcha de FastAPI que vale la pena documentar:** `Depends(get_session)` no
sirve para un `StreamingResponse` — FastAPI cierra las dependencias con
`yield` apenas la función del endpoint retorna, lo cual pasa *antes* de que
el generador del stream se empiece a consumir. `chat_stream()` abre y cierra
su propia sesión (`async with SessionLocal() as session`) dentro del
generador para que la transacción siga viva durante todo el stream.

## ✅ Sprint 5 — Robustez (implementado)

- [x] **Límite de iteraciones**: `MAX_ITERATIONS` (6) en `app/agent/loop.py`.
      Al alcanzarlo, `run_agent_stream()` ya no lanza una excepción — emite un
      paso `final` explicando que no se pudo completar la tarea en los pasos
      disponibles, y lo loguea como warning. Tanto `/chat` como `/chat/stream`
      terminan con una respuesta normal (200), nunca con un 500.
- [x] **Errores de herramientas**: `_execute_tool_use()` envuelve la llamada al
      handler en un `try/except Exception` — cualquier fallo (parámetros
      inválidos, error de la tool, lo que sea) se convierte en un
      `tool_result` con `is_error: true` y un mensaje descriptivo, y el ciclo
      sigue: el LLM ve el error como observación y decide cómo continuar
      (pedir los datos de nuevo, probar otra herramienta, avisarle al
      usuario). Nunca tumba el request con un 500.
- [x] **Logging estructurado**: `app/observability/logger.py` (logging
      estándar de Python, sin dependencias nuevas) + líneas `clave=valor`
      (`conversation_id`, `tool`, `duration_ms`, `error`) en cada ejecución de
      herramienta y en cada corte por límite de iteraciones — fáciles de
      grepear o de alimentar a un colector de logs más adelante.
- [x] **Validación de límites de entrada**: `ChatRequest.message` tiene
      `min_length=1` y `max_length=4000` (`app/schemas.py`); un mensaje vacío
      o demasiado largo devuelve `422` automáticamente (validación de
      Pydantic), antes de siquiera tocar el LLM.

**Fuera de alcance de este sprint (decisión consciente):** rate limiting a
nivel de API. Es un proyecto de demo de un solo usuario sin autenticación;
agregar throttling ahora sería resolver un problema que no existe todavía. Si
el proyecto se expone públicamente sin login, la opción más simple es
middleware tipo `slowapi` (basado en `limits`) por IP sobre `/api/chat*`, o
delegarlo a un reverse proxy (nginx, Cloudflare) — no requiere cambios en la
lógica del agente.

## ⬜ Sprint 6 — Deploy y presentación

- Deploy del backend (ej. Fly.io, Render, Railway) y frontend (ej. Vercel,
  Netlify) o ambos en el mismo contenedor detrás de un reverse proxy.
- Si se migra de SQLite a Postgres para este deploy (recomendado si el deploy
  no tiene disco persistente, como muchos PaaS "serverless"): cambiar
  `DATABASE_URL` a una URL `postgresql+asyncpg://...` — el código de modelos y
  queries no cambia gracias a SQLAlchemy.
- README con arquitectura y decisiones (ya cubierto por `docs/ARCHITECTURE.md`
  y `docs/DECISIONS.md`, enlazarlos desde el README principal).
- Video demo con una tarea real multi-paso, por ejemplo la del enunciado
  original: *"revisa el clima de mañana y si tenemos un evento al aire libre
  ese día en la BD, redacta un aviso por email."*
- Post explicando el patrón ReAct y por qué se construyó así (puede basarse
  directamente en la sección "Por qué cada decisión" del brief original y en
  `docs/DECISIONS.md`).

---

## Ítems abiertos / deuda técnica conocida

- No hay autenticación de usuarios (fuera de alcance del proyecto, es una demo
  de patrón de agente, no un producto multi-tenant).
- No hay migraciones formales (Alembic). Para el alcance actual, `init_db()`
  con `create_all()` es suficiente; si el esquema empieza a cambiar con
  frecuencia en Sprints 2+, vale la pena introducir Alembic.
- El cliente LLM está atado al SDK de Anthropic. Si se quisiera soportar
  múltiples proveedores, convendría una interfaz `LLMClient` abstracta antes
  de Sprint 2 (hoy es una sola clase concreta, ver `app/llm/client.py`).
