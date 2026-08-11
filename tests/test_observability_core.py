from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app import logging_config
from app.main import app


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_request_context_propagates_and_pii_is_scrubbed(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            headers={"x-request-id": "req-DEADBEEF"},
            json={
                "user_id": "student@vinuni.edu.vn",
                "session_id": "session-0901234567",
                "feature": "monitoring",
                "message": "Contact 090 123 4567 or student@vinuni.edu.vn",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-deadbeef"
    assert re.fullmatch(r"\d+\.\d", response.headers["x-response-time-ms"])
    assert response.json()["correlation_id"] == "req-deadbeef"

    api_records = [record for record in _records(log_path) if record["service"] == "api"]
    assert {record["event"] for record in api_records} >= {
        "request_received",
        "retrieval_completed",
        "response_sent",
    }
    for record in api_records:
        assert record["correlation_id"] == "req-deadbeef"
        assert {"user_id_hash", "session_id", "feature", "model", "env"} <= record.keys()

    rendered = json.dumps(api_records, ensure_ascii=False)
    assert "student@vinuni.edu.vn" not in rendered
    assert "090 123 4567" not in rendered
    assert "0901234567" not in rendered
    assert "REDACTED" in rendered


def test_invalid_request_id_is_replaced(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs.jsonl")
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "not-safe"})

    assert response.status_code == 200
    assert re.fullmatch(r"req-[0-9a-f]{8}", response.headers["x-request-id"])
