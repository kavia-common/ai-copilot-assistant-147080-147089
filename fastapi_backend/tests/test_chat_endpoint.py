from fastapi.testclient import TestClient

# Ensure import path for app
from src.api.main import app

client = TestClient(app)


def test_chat_with_messages_shape_returns_200():
    payload = {
        "messages": [{"role": "user", "content": "What is water?"}],
        "response_style": "plain",
    }
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "reply" in data and isinstance(data["reply"], str)


def test_chat_with_legacy_message_shape_returns_200():
    payload = {"message": "Give me examples of vegetables"}
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "reply" in data and isinstance(data["reply"], str)


def test_chat_invalid_payload_returns_400_with_clear_message():
    payload = {"messages": [{"role": "invalid", "content": ""}]}  # invalid role and empty content
    resp = client.post("/api/chat", json=payload)
    assert resp.status_code == 400
    detail = resp.json().get("detail")
    # FastAPI wraps our detail object; ensure our keys are present
    assert isinstance(detail, dict)
    assert detail.get("code") == "invalid_payload"
    assert "accepted_shapes" in detail
    assert "validation" in detail
