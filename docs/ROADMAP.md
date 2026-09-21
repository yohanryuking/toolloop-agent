# Roadmap — toolloop-agent

Estado: **Sprints 0, 1 y 2 implementados.** Sprints 3-6 documentados a
continuación como guía de continuación (diseño técnico, no solo la idea
general del sprint).

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

## ⬜ Sprint 3 — Segunda y tercera herramienta

- **Búsqueda web** (`buscar_web(query: str)`): mock por defecto (respuestas
  fijas o basadas en un pequeño dataset local en `app/tools/mock_web_data.py`),
  con posibilidad de swap a una API real (ej. Brave Search, Tavily, SerpAPI) si
  hay una API key configurada — el mismo patrón que Stripe en el proyecto
  anterior: **interfaz igual, implementación real opcional**.
- **Email simulado** (`enviar_email(destinatario: str, asunto: str, cuerpo: str)`):
  inserta un row en `sent_emails`. No hay SMTP real. El schema del tool no
  permite adjuntar HTML arbitrario sin sanitizar si en algún momento se
  renderiza en el frontend (ver Sprint 5, XSS).
- Registrar ambas en `TOOL_REGISTRY` junto a `buscar_eventos`.
- Actualizar el system prompt del agente para explicar cuándo usar cada
  herramienta (ej. "usa `buscar_web` para clima, usa `buscar_eventos` para la
  agenda interna, usa `enviar_email` solo cuando el usuario lo pida
  explícitamente").

## ⬜ Sprint 4 — Streaming + panel de traza

- Cambiar `POST /api/chat` a un endpoint SSE (`GET /api/chat/stream` o
  `POST` con `text/event-stream`) que emite un evento por cada paso del loop:
  `{"type": "thought" | "action" | "observation" | "final", ...}`.
- El loop del agente (Sprint 2) debe convertirse en un generador/async
  generator que yield-ea cada paso en vez de solo devolver el resultado final.
- Persistir también cada paso en una tabla `agent_steps` (nueva) para poder
  reconstruir la traza de ejecuciones pasadas, no solo verla en vivo.
- Frontend: dos paneles lado a lado — chat (igual que Sprint 1) y una traza
  tipo timeline (pensamiento → acción → observación) que se actualiza en
  tiempo real vía `EventSource`.

## ⬜ Sprint 5 — Robustez

- **Límite de iteraciones**: constante `MAX_AGENT_ITERATIONS` (ej. 8); si se
  alcanza, el agente responde indicando que no pudo completar la tarea en el
  límite de pasos, en vez de loopear indefinidamente.
- **Errores de herramientas**: si una función de tool lanza una excepción, se
  captura y se devuelve como `tool_result` con `is_error: true` y un mensaje
  descriptivo, para que el LLM decida cómo continuar (reintentar con otros
  parámetros, usar otra herramienta, o informar al usuario del fallo) en vez
  de que el proceso backend se caiga.
- **Logging estructurado** de cada ejecución (conversation_id, tool usado,
  parámetros, duración, resultado/error) para debug — un logger dedicado
  (`app/observability/logger.py`) o integración con algo como `structlog`.
- **Validación de límites de entrada**: mensajes de usuario con longitud
  máxima, rate limiting básico si se expone públicamente.

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
