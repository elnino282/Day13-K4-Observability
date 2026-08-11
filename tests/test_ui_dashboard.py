from __future__ import annotations

from pathlib import Path

from ui.data import dashboard_snapshot, filter_recent, read_jsonl, records_frame


def test_dashboard_snapshot_matches_log_contract(tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-08-11T08:00:00Z","event":"request_received"}',
                '{"ts":"2026-08-11T08:00:01Z","event":"response_sent","latency_ms":100,"cost_usd":0.1,"tokens_in":10,"tokens_out":20,"quality_score":0.8}',
                '{"ts":"2026-08-11T08:01:00Z","event":"request_received"}',
                '{"ts":"2026-08-11T08:01:01Z","event":"request_failed","error_type":"TimeoutError"}',
                "{invalid final line",
            ]
        ),
        encoding="utf-8",
    )

    frame = records_frame(read_jsonl(log_path))
    snapshot = dashboard_snapshot(frame)

    assert snapshot.request_count == 2
    assert snapshot.response_count == 1
    assert snapshot.error_count == 1
    assert snapshot.error_rate_pct == 50.0
    assert snapshot.latency_p95 == 100.0
    assert snapshot.total_cost_usd == 0.1
    assert snapshot.tokens_in_total == 10
    assert snapshot.tokens_out_total == 20
    assert snapshot.quality_avg == 0.8


def test_filter_recent_anchors_to_latest_event() -> None:
    frame = records_frame(
        [
            {"ts": "2026-08-11T06:00:00Z", "event": "request_received"},
            {"ts": "2026-08-11T08:00:00Z", "event": "request_received"},
        ]
    )

    recent = filter_recent(frame, 60)

    assert len(recent) == 1
