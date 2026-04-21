from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ping_returns_pong() -> None:
    response = TestClient(app).get("/ping")

    assert response.status_code == 200
    assert response.text == "pong"


def test_llm_health_returns_json_shape() -> None:
    response = TestClient(app).get("/health/llm")

    assert response.status_code in (200, 503)
    payload = response.json()
    assert payload["provider"] == "ollama"
    assert "ready" in payload
    assert "reason" in payload
