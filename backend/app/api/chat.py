from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.models import Conversation, Message
from app.llm.client import get_llm_client
from app.schemas import ChatRequest, ChatResponse, MessageOut

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    conversation = await _get_or_create_conversation(session, payload.conversation_id)

    user_message = Message(
        conversation_id=conversation.id, role="user", content=payload.message
    )
    session.add(user_message)
    await session.flush()

    history = await _load_history(session, conversation.id)

    llm = get_llm_client()
    response = await llm.complete(
        messages=[{"role": m.role, "content": m.content} for m in history]
    )
    reply_text = "".join(
        block.text for block in response.content if block.type == "text"
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
