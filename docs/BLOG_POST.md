# Construí un agente de verdad, no otro chatbot con RAG

*Borrador listo para publicar (LinkedIn, dev.to, blog personal). Ajustá el
tono/longitud según la plataforma — completá los `[...]` con tus datos.*

---

Todo el mundo está mostrando chatbots con RAG. Le metés un vector store, le
pasás el contexto recuperado en el prompt, y el modelo responde. Está bien,
funciona, pero no es lo mismo que construir un **agente**: algo que decide
qué hacer, encadena varias herramientas, evalúa resultados intermedios y
ajusta su plan sobre la marcha.

Quería mostrar esa diferencia con un proyecto concreto, así que construí
**toolloop-agent**: un agente que resuelve una tarea real de varios pasos —
*"revisá el clima de mañana y si tenemos un evento al aire libre ese día en
la agenda, avisá al equipo por email"* — usando tool calling nativo del LLM,
no "prompt engineering a mano" pidiéndole que responda en JSON.

Repo: `[link a tu repo de GitHub]`

## La diferencia que importa: quién decide

En un RAG, el flujo es fijo: pregunta → buscar contexto → responder. En este
proyecto, el LLM ve tres herramientas disponibles y **decide** cuáles usar,
en qué orden, y cuándo ya tiene suficiente información para responder:

```json
{
  "name": "buscar_eventos",
  "description": "Busca eventos agendados en un rango de fechas...",
  "input_schema": {
    "type": "object",
    "properties": {
      "fecha_inicio": { "type": "string", "format": "date" },
      "fecha_fin": { "type": "string", "format": "date" }
    },
    "required": ["fecha_inicio", "fecha_fin"]
  }
}
```

Esto es tool/function calling nativo del proveedor (Anthropic, en este caso):
el modelo devuelve un bloque `tool_use` con el nombre de la herramienta y los
parámetros ya validados contra el schema, no un texto que yo tengo que
parsear con regex y rezar para que venga bien formado.

## El loop ReAct, en código real

El corazón del proyecto es un ciclo *pensar → actuar → observar → repetir*.
Simplificado, así es como se ve:

```python
for _ in range(MAX_ITERATIONS):
    response = await llm.complete(messages=conversation, tools=tool_schemas())

    if response.stop_reason != "tool_use":
        yield {"type": "final", "text": extraer_texto(response)}
        return

    for block in response.content:
        if block.type != "tool_use":
            continue
        yield {"type": "action", "tool": block.name, "input": block.input}
        resultado = await ejecutar_tool(block.name, block.input)
        yield {"type": "observation", "tool": block.name, "output": resultado}

    conversation.append(mensaje_con_los_resultados)
```

Cada iteración es una llamada real al LLM con el historial actualizado,
incluyendo los resultados de las herramientas que ya se ejecutaron. El
modelo ve la observación y decide el siguiente paso — puede llamar a otra
herramienta, volver a llamar a la misma con otros parámetros, o ya responder.
Para la tarea del ejemplo, esto significa tres llamadas encadenadas:
`buscar_web` (clima) → `buscar_eventos` (agenda) → `enviar_email` (aviso),
sin que yo le haya *scripteado* esa secuencia en ningún lado.

## Una decisión de seguridad que cualquier backend dev reconoce

El LLM **nunca** genera SQL. La herramienta de consulta a la base de datos es
una función Python con parámetros tipados (`fecha_inicio`, `fecha_fin`,
validados con Pydantic), no un `ejecutar_query(sql: str)` que le daría al
modelo la posibilidad de construir queries arbitrarias. Es la misma lógica
que aplicás para cualquier input de usuario no confiable: el LLM es, para
efectos de seguridad, un usuario más que no controlás del todo.

## Mostrar el razonamiento, no esconderlo

Cada acción y observación se transmite al frontend en tiempo real por
Server-Sent Events, y se persiste en una tabla `agent_steps` para poder
reconstruir la traza de una ejecución pasada. La UI tiene dos paneles: el
chat de siempre, y al lado un timeline que muestra en vivo qué herramienta
está llamando el agente, con qué parámetros, y qué le respondió. Es la misma
filosofía de transparencia que un buen sistema de RAG debería tener al
mostrar sus fuentes — pero acá aplicada a acciones, no a documentos.

## Y cuando algo falla

Un agente que se cae porque una herramienta tiró una excepción, o que
loopea infinitamente porque nunca llega a una respuesta final, no sirve para
nada en producción. Dos decisiones concretas:

- Si una herramienta falla (parámetros inválidos, lo que sea), el error se
  convierte en una observación (`is_error: true`) que el LLM puede leer y
  decidir cómo seguir — pedir el dato de nuevo, probar otra herramienta,
  avisarle al usuario. Nunca un 500.
- Hay un límite duro de iteraciones. Si se alcanza, el agente responde
  explicando que no pudo completar la tarea, en vez de colgarse.

## Por qué SQLite y no Supabase

El brief original proponía Supabase. Terminé usando SQLite vía SQLAlchemy
async, por la misma razón por la que el email y la búsqueda web están
simulados: quería que el proyecto se pudiera correr y demostrar sin depender
de ninguna cuenta ni credencial externa. SQLAlchemy habla con SQLite y con
Postgres con el mismo código, así que el día que haga falta un Postgres real
(por ejemplo, para el deploy si el hosting no da disco persistente), es un
cambio de config, no de arquitectura.

## Qué sigue

El código completo, la arquitectura y el roadmap sprint por sprint están en
el repo (`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`).
Si te interesa el patrón ReAct o estás armando algo parecido, los comentarios
están abiertos — `[tu contacto / LinkedIn]`.

`[Acá va el video demo — ya grabado, ver demo/README.md en el repo; subilo a
donde vayas a publicar el post y pegá el link/embed acá]`
