from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app


def _read_events(log_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _chat_payload(message: str = "Explain observability") -> dict[str, str]:
    return {
        "user_id": "student-01",
        "session_id": "session-01",
        "feature": "qa",
        "message": message,
    }


def test_request_id_is_propagated_to_response_and_chat_body() -> None:
    request_id = "req-1234abcd"

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": request_id},
            json=_chat_payload(),
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    assert response.json()["correlation_id"] == request_id
    response_time_ms = float(response.headers["x-response-time-ms"])
    assert response_time_ms >= 0


def test_missing_request_id_generates_expected_correlation_id() -> None:
    with TestClient(app) as client:
        response = client.post("/chat", json=_chat_payload())

    assert response.status_code == 200
    correlation_id = response.json()["correlation_id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.headers["x-request-id"] == correlation_id


def test_api_logs_include_context_metadata_and_correlation_id(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    request_id = "req-a1b2c3d4"

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": request_id},
            json=_chat_payload(),
        )

    assert response.status_code == 200
    api_events = [event for event in _read_events(log_path) if event.get("service") == "api"]
    assert api_events
    for event in api_events:
        assert event["correlation_id"] == request_id
        assert event["env"] == "dev"
        assert event["user_id_hash"] == "2a2006df8771"
        assert event["session_id"] == "session-01"
        assert event["feature"] == "qa"
        assert event["model"] == "claude-sonnet-4-5"


def test_api_logs_redact_pii_from_request_and_response_payloads(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    message = "Contact student@example.com or 090 123 4567"

    with TestClient(app) as client:
        response = client.post("/chat", json=_chat_payload(message))

    assert response.status_code == 200
    rendered_logs = log_path.read_text(encoding="utf-8")
    assert "student@example.com" not in rendered_logs
    assert "090 123 4567" not in rendered_logs
    assert "REDACTED_EMAIL" in rendered_logs
    assert "REDACTED_PHONE_VN" in rendered_logs


def test_failed_request_keeps_correlation_id_in_error_log(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    request_id = "req-deadbeef"

    with TestClient(app) as client:
        enabled = client.post("/incidents/tool_fail/enable")
        try:
            response = client.post(
                "/chat",
                headers={"x-request-id": request_id},
                json=_chat_payload("Explain monitoring"),
            )
        finally:
            client.post("/incidents/tool_fail/disable")

    assert enabled.status_code == 200
    assert response.status_code == 500
    failed_events = [
        event for event in _read_events(log_path) if event.get("event") == "request_failed"
    ]
    assert failed_events
    assert failed_events[-1]["correlation_id"] == request_id
