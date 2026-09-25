from datetime import datetime

from pydantic import BaseModel, Field

# Límite generoso para un mensaje de chat; evita que un payload gigante
# infle innecesariamente el contexto que se le manda al LLM en cada turno.
MAX_MESSAGE_LENGTH = 4000


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
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
