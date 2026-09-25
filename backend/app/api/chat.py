import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.loop import AgentError, run_agent_loop, run_agent_stream
from app.db.database import SessionLocal, get_session
from app.db.models import AgentStep, Conversation, Message
from app.schemas import AgentStepOut, ChatRequest, ChatResponse, MessageOut

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Endpoint simple, sin streaming: llama al agente y devuelve la
    respuesta final de una vez. Los pasos intermedios no se persisten acá —
    para eso está `POST /api/chat/stream`."""
    conversation = await _get_or_create_conversation(session, payload.conversation_id)

    user_message = Message(
        conversation_id=conversation.id, role="user", content=payload.message
    )
    session.add(user_message)
    await session.flush()

    history = await _load_history(session, conversation.id)

    reply_text = await run_agent_loop(
        session,
        messages=[{"role": m.role, "content": m.content} for m in history],
    )

    assistant_message = Message(
        conversation_id=conversation.id, role="assistant", content=reply_text
    )
    session.add(assistant_message)
    await session.commit()

    full_history = await _load_history(session, conversation.id)

    return ChatResponse(
        conversation_id=conversation.id,
        reply=reply_text,
        history=[MessageOut.model_validate(m) for m in full_history],
    )


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """Igual que `/chat`, pero transmite cada paso del ciclo ReAct (acción,
    observación, respuesta final) como Server-Sent Events a medida que
    ocurren, y persiste cada paso en `agent_steps` para poder reconstruir la
    traza más adelante.

    Nota de implementación: no usa `Depends(get_session)` porque FastAPI
    cierra las dependencias con `yield` apenas la función del endpoint
    retorna — que para un `StreamingResponse` es *antes* de que el
    generador se empiece a consumir. Acá se abre y cierra la sesión a mano
    dentro del propio generador para que siga viva durante todo el stream.
    """
    return StreamingResponse(
        _stream_events(payload),
        media_type="text/event-stream",
    )


async def _stream_events(payload: ChatRequest) -> AsyncIterator[str]:
    async with SessionLocal() as session:
        try:
            conversation = await _get_or_create_conversation(
                session, payload.conversation_id
            )
        except HTTPException as exc:
            yield _sse({"type": "error", "message": exc.detail})
            return

        user_message = Message(
            conversation_id=conversation.id, role="user", content=payload.message
        )
        session.add(user_message)
        await session.commit()

        history = await _load_history(session, conversation.id)
        api_messages = [{"role": m.role, "content": m.content} for m in history]

        yield _sse({"type": "conversation_id", "conversation_id": conversation.id})

        final_text = ""
        step_index = 0
        try:
            async for step in run_agent_stream(session, api_messages):
                if step["type"] == "final":
                    final_text = step["text"]
                    yield _sse(step)
                    break

                session.add(
                    AgentStep(
                        conversation_id=conversation.id,
                        step_index=step_index,
                        step_type=step["type"],
                        tool_name=step.get("tool"),
                        payload=json.dumps(step, default=str),
                    )
                )
                step_index += 1
                yield _sse(step)
        except AgentError as exc:
            final_text = str(exc)
            yield _sse({"type": "error", "message": final_text})

        assistant_message = Message(
            conversation_id=conversation.id, role="assistant", content=final_text
        )
        session.add(assistant_message)
        await session.commit()

    yield _sse({"type": "done"})


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


@router.get("/conversations/{conversation_id}/steps", response_model=list[AgentStepOut])
async def get_agent_steps(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[AgentStep]:
    """Traza persistida de una conversación (solo cubre turnos hechos a
    través de `/chat/stream`)."""
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    result = await session.execute(
        select(AgentStep)
        .where(AgentStep.conversation_id == conversation_id)
        .order_by(AgentStep.created_at, AgentStep.step_index)
    )
    return list(result.scalars().all())


async def _get_or_create_conversation(
    session: AsyncSession, conversation_id: str | None
) -> Conversation:
    if conversation_id is None:
        conversation = Conversation()
        session.add(conversation)
        await session.flush()
        return conversation

    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversation


async def _load_history(session: AsyncSession, conversation_id: str) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())
