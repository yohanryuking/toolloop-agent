# Roadmap — toolloop-agent

Estado: **Sprint 0 y Sprint 1 implementados.** Sprints 2-6 documentados a
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

## ⬜ Sprint 2 — Primera herramienta: consulta a BD

**Objetivo:** el agente puede decidir consultar eventos en la BD.

Diseño:

1. Definir el tool schema para el LLM (formato Anthropic `tools=[...]`):
   ```json
   {
     "name": "buscar_eventos",
     "description": "Busca eventos programados en un rango de fechas.",
     "input_schema": {
       "type": "object",
       "properties": {
         "fecha_inicio": {"type": "string", "format": "date"},
         "fecha_fin": {"type": "string", "format": "date"}
       },
       "required": ["fecha_inicio", "fecha_fin"]
     }
   }
   ```
2. Implementar `app/tools/events.py::buscar_eventos(fecha_inicio, fecha_fin)`
   que valida los parámetros (Pydantic) y ejecuta una query parametrizada
   contra `events` con SQLAlchemy (nunca SQL crudo con f-strings).
3. En `app/agent/loop.py` (nuevo módulo — reemplaza la llamada directa y simple
   de Sprint 1), extender el loop:
   - Llamar al LLM con `tools=[buscar_eventos_schema]`.
   - Si `stop_reason == "tool_use"`: parsear el `tool_use` block, ejecutar la
     función Python correspondiente, construir un mensaje `tool_result` y
     volver a llamar al LLM con el historial actualizado.
   - Si `stop_reason == "end_turn"`: devolver la respuesta final.
4. Un **registro de herramientas** (`TOOL_REGISTRY: dict[str, ToolSpec]`) que
   mapea `name -> (schema, función Python, modelo Pydantic de input)` para que
   agregar herramientas nuevas (Sprint 3) sea declarativo.
5. Tests: mockear la respuesta del LLM (dos turnos: uno con `tool_use`, otro
   con la respuesta final) y verificar que se ejecuta la función correcta con
   los parámetros correctos.

**Nota de diseño:** el LLM nunca debe poder pasar un string SQL como parámetro.
Los parámetros del schema son siempre tipos primitivos (fechas, strings,
enums), nunca "query" o "filter" libres.

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
