from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

import app.api.chat as chat_module
from app.main import app


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list[Any]


class FakeLLMClient:
    async def complete(self, messages, tools=None):
        last_user = messages[-1]["content"]
        return FakeResponse(content=[FakeTextBlock(text=f"echo: {last_user}")])


def test_chat_creates_conversation_and_persists_history(monkeypatch):
    monkeypatch.setattr(chat_module, "get_llm_client", lambda: FakeLLMClient())

    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "hola"})
        assert response.status_code == 200
        data = response.json()
        assert data["reply"] == "echo: hola"
        assert len(data["history"]) == 2
        assert data["history"][0]["role"] == "user"
        assert data["history"][1]["role"] == "assistant"

        conversation_id = data["conversation_id"]
        response2 = client.post(
            "/api/chat",
            json={"message": "de nuevo", "conversation_id": conversation_id},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["conversation_id"] == conversation_id
        assert len(data2["history"]) == 4


def test_chat_with_unknown_conversation_id_returns_404(monkeypatch):
    monkeypatch.setattr(chat_module, "get_llm_client", lambda: FakeLLMClient())

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "hola", "conversation_id": "does-not-exist"},
        )
        assert response.status_code == 404
