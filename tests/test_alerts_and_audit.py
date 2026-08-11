from __future__ import annotations

import json
from pathlib import Path

import yaml

from app import audit


def test_alert_rules_are_actionable_and_have_runbooks() -> None:
    payload = yaml.safe_load(Path("config/alert_rules.yaml").read_text(encoding="utf-8"))
    rules = payload["alerts"]

    assert len(rules) == 3
    assert all(rule["severity"] in {"warning", "critical"} for rule in rules)
    assert all(rule["duration"] and rule["owner"] and rule["runbook"] for rule in rules)
    assert "TODO" not in json.dumps(payload)

    runbook = Path("docs/alerts.md").read_text(encoding="utf-8")
    assert all(f"## Alert {index}" in runbook for index in range(1, 4))


def test_audit_log_is_separate_and_scrubbed(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_LOG_PATH", audit_path)

    audit.write_audit(
        "incident_enabled",
        correlation_id="req-deadbeef",
        details={"contact": "student@vinuni.edu.vn"},
    )

    record = json.loads(audit_path.read_text(encoding="utf-8"))
    assert record["event"] == "audit_event"
    assert record["correlation_id"] == "req-deadbeef"
    assert "student@" not in json.dumps(record)
