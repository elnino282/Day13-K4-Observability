from __future__ import annotations

from collections import Counter

from app import metrics


def _reset_metrics(monkeypatch) -> None:
    monkeypatch.setattr(metrics, "TRAFFIC", 0)
    monkeypatch.setattr(metrics, "ERRORS", Counter())
    monkeypatch.setattr(metrics, "REQUEST_LATENCIES", [])
    monkeypatch.setattr(metrics, "REQUEST_COSTS", [])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_IN", [])
    monkeypatch.setattr(metrics, "REQUEST_TOKENS_OUT", [])
    monkeypatch.setattr(metrics, "QUALITY_SCORES", [])


def test_snapshot_has_zero_error_rate_without_requests(monkeypatch) -> None:
    _reset_metrics(monkeypatch)

    result = metrics.snapshot()

    assert result["traffic"] == 0
    assert result["error_rate_pct"] == 0.0
    assert result["error_breakdown"] == {}


def test_snapshot_calculates_errors_over_successes_and_errors(monkeypatch) -> None:
    _reset_metrics(monkeypatch)
    for _ in range(3):
        metrics.record_request(
            latency_ms=100,
            cost_usd=0.001,
            tokens_in=10,
            tokens_out=20,
            quality_score=0.8,
        )
    metrics.record_error("RuntimeError")

    result = metrics.snapshot()

    assert result["traffic"] == 3
    assert result["error_rate_pct"] == 25.0
    assert result["error_breakdown"] == {"RuntimeError": 1}
