# Decisiones de diseño (ADR corto)

## 1. SQLite + SQLAlchemy en vez de Supabase

**Contexto:** el brief original proponía Supabase para las tablas `events` y
`sent_emails`.

**Decisión:** usar SQLite accedido vía SQLAlchemy async (`aiosqlite`), con
`DATABASE_URL` configurable para poder apuntar a Postgres sin cambiar código.

**Razón:** ver `ARCHITECTURE.md#por-qué-sqlite--sqlalchemy-en-vez-de-supabase`.
En resumen: cero dependencias externas para demostrar el proyecto, encaja con
el stack Python/FastAPI, y la migración a Postgres el día de mañana es un
cambio de configuración, no de arquitectura.

## 2. Historial de conversación persistido desde Sprint 1, no en memoria

**Contexto:** Sprint 1 solo necesita "un endpoint de chat simple sin tools
para validar que la base funciona".

**Decisión:** aun así, el historial se persiste en SQLite (`conversations` /
`messages`) desde el principio, en vez de guardarlo en un diccionario en
memoria del proceso.

**Razón:** el historial en memoria se pierde en cada restart y no escala a
más de un worker; además, Sprint 4 necesita poder reconstruir la traza de
ejecuciones pasadas, y tener el historial ya modelado en BD evita una
migración de datos a mitad de proyecto. El costo extra (dos tablas, un par de
queries) es mínimo comparado con ese beneficio.

## 3. Sin tool calling en Fase 1

**Contexto:** el brief pide explícitamente que Sprint 1 sea "sin tools
todavía".

**Decisión:** el endpoint `/api/chat` de esta entrega llama al LLM sin pasar
`tools=[...]`. El wrapper `LLMClient` sí queda preparado para aceptarlos (el
parámetro existe en la firma) pero no hay ninguna herramienta implementada
ni registrada.

**Razón:** validar primero que el loop de mensajes, la persistencia y el
streaming (bases del proyecto) funcionan antes de sumar la complejidad de
tool calling, parsing de `tool_use` y ejecución de funciones — eso es
exactamente lo que pide Sprint 2.

## 4. `requirements.txt` en vez de Poetry/PDM

**Decisión:** dependencias del backend en un `requirements.txt` plano.

**Razón:** para un proyecto de este tamaño (una demo técnica, no un paquete
publicado), un `requirements.txt` + `venv` es más simple de levantar para
cualquier desarrollador nuevo que un gestor de proyecto adicional. Si el
proyecto crece, migrar a Poetry/PDM es sencillo.
