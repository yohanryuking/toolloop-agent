import json
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

import app.agent.loop as loop_module
from app.main import app


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list[Any]
    stop_reason: str = "end_turn"


class FakeLLMClient:
    async def complete(self, messages, tools=None):
        last_user = messages[-1]["content"]
        return FakeResponse(content=[FakeTextBlock(text=f"echo: {last_user}")])


def _parse_sse(body: str) -> list[dict[str, Any]]:
    events = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for line in chunk.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


def test_chat_creates_conversation_and_persists_history(monkeypatch):
    monkeypatch.setattr(loop_module, "get_llm_client", lambda: FakeLLMClient())

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
    monkeypatch.setattr(loop_module, "get_llm_client", lambda: FakeLLMClient())

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "hola", "conversation_id": "does-not-exist"},
        )
        assert response.status_code == 404


def test_chat_stream_emite_pasos_y_persiste_traza(monkeypatch):
    calls = {"count": 0}

    class ScriptedLLMClient:
        async def complete(self, messages, tools=None):
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeResponse(
                    content=[
                        FakeToolUseBlock(
                            id="t1",
                            name="buscar_eventos",
                            input={
                                "fecha_inicio": "2026-01-01",
                                "fecha_fin": "2026-01-02",
                            },
                        )
                    ],
                    stop_reason="tool_use",
                )
            return FakeResponse(
                content=[FakeTextBlock(text="No encontré eventos en ese rango.")],
                stop_reason="end_turn",
            )

    monkeypatch.setattr(loop_module, "get_llm_client", lambda: ScriptedLLMClient())

    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"message": "¿hay eventos?"})
        assert response.status_code == 200

        events = _parse_sse(response.text)
        types = [event["type"] for event in events]
        assert types == [
            "conversation_id",
            "action",
            "observation",
            "final",
            "done",
        ]
        assert events[1]["tool"] == "buscar_eventos"
        assert events[3]["text"] == "No encontré eventos en ese rango."

        conversation_id = events[0]["conversation_id"]

        steps_response = client.get(f"/api/conversations/{conversation_id}/steps")
        assert steps_response.status_code == 200
        steps = steps_response.json()
        assert [s["step_type"] for s in steps] == ["action", "observation"]
        assert steps[0]["tool_name"] == "buscar_eventos"
