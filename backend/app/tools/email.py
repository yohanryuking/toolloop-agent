from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SentEmail

ENVIAR_EMAIL_SCHEMA: dict[str, Any] = {
    "name": "enviar_email",
    "description": (
        "Envía un email. Es una simulación: no hay SMTP real, el envío "
        "queda registrado como una fila en la tabla sent_emails. Usala solo "
        "cuando el usuario pida explícitamente avisar o notificar algo por "
        "email, nunca por iniciativa propia."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "destinatario": {
                "type": "string",
                "description": "Dirección de email del destinatario.",
            },
            "asunto": {"type": "string", "description": "Asunto del email."},
            "cuerpo": {
                "type": "string",
                "description": "Cuerpo del email en texto plano.",
            },
        },
        "required": ["destinatario", "asunto", "cuerpo"],
    },
}


class EnviarEmailInput(BaseModel):
    destinatario: str
    asunto: str
    cuerpo: str

    @field_validator("destinatario")
    @classmethod
    def _validar_email(cls, value: str) -> str:
        local, _, domain = value.partition("@")
        if not local or "." not in domain:
            raise ValueError("destinatario debe ser una dirección de email válida")
        return value


async def enviar_email(session: AsyncSession, raw_input: dict[str, Any]) -> dict[str, Any]:
    """Tool: "envío" de email simulado — inserta un row en `sent_emails`."""
    params = EnviarEmailInput.model_validate(raw_input)
    record = SentEmail(
        recipient=params.destinatario, subject=params.asunto, body=params.cuerpo
    )
    session.add(record)
    await session.flush()
    return {"status": "sent", "id": record.id, "recipient": record.recipient}
