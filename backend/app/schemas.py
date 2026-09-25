from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    history: list[MessageOut]


class AgentStepOut(BaseModel):
    step_index: int
    step_type: str
    tool_name: str | None
    payload: str
    created_at: datetime

    model_config = {"from_attributes": True}
