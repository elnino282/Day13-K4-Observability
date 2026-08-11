from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


DASHBOARD_ACTIVITY_EVENTS = frozenset(
    {"request_received", "response_sent", "request_failed"}
)


@dataclass(frozen=True)
class DashboardSnapshot:
    request_count: int
    response_count: int
    error_count: int
    error_rate_pct: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    request_rate_per_minute: float
    total_cost_usd: float
    tokens_in_total: int
    tokens_out_total: int
    quality_avg: float


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read valid JSON objects while tolerating an incomplete final log line."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def records_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["ts", "event"])
    frame = pd.json_normalize(records)
    if "ts" not in frame:
        frame["ts"] = pd.NaT
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True, errors="coerce")
    return frame.dropna(subset=["ts"]).sort_values("ts")


def filter_recent(
    frame: pd.DataFrame,
    minutes: int,
    *,
    anchor: datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    if frame.empty or minutes <= 0:
        return frame.copy()
    if anchor is None:
        anchor_ts = frame["ts"].max()
    else:
        anchor_ts = pd.Timestamp(anchor)
        if anchor_ts.tzinfo is None:
            anchor_ts = anchor_ts.tz_localize(timezone.utc)
        else:
            anchor_ts = anchor_ts.tz_convert(timezone.utc)
    window = pd.to_timedelta(int(minutes), unit="min")
    return frame[frame["ts"] >= anchor_ts - window].copy()


def dashboard_window(frame: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Select a dashboard window anchored to the latest API telemetry.

    Lifecycle events such as ``app_stopped`` can be newer than the last chat
    request. Anchoring to every event would make the dashboard look empty even
    when the log still contains valid request/response telemetry.
    """
    if frame.empty:
        return frame.copy()
    activity = frame[frame.get("event", pd.Series(index=frame.index, dtype=str)).isin(DASHBOARD_ACTIVITY_EVENTS)]
    anchor = activity["ts"].max() if not activity.empty else frame["ts"].max()
    recent = filter_recent(frame, minutes, anchor=anchor)
    return recent[recent["ts"] <= anchor].copy()


def _numeric(frame: pd.DataFrame, field: str) -> pd.Series:
    if field not in frame:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[field], errors="coerce").dropna()


def dashboard_snapshot(frame: pd.DataFrame) -> DashboardSnapshot:
    if "event" not in frame:
        frame = frame.assign(event="")
    requests = frame[frame["event"] == "request_received"]
    responses = frame[frame["event"] == "response_sent"]
    failures = frame[frame["event"] == "request_failed"]
    latencies = _numeric(responses, "latency_ms")
    costs = _numeric(responses, "cost_usd")
    tokens_in = _numeric(responses, "tokens_in")
    tokens_out = _numeric(responses, "tokens_out")
    quality = _numeric(responses, "quality_score")

    if len(requests) > 1:
        elapsed = max(
            1.0,
            (requests["ts"].max() - requests["ts"].min()).total_seconds() / 60,
        )
    else:
        elapsed = 1.0

    def percentile(value: float) -> float:
        return float(latencies.quantile(value)) if not latencies.empty else 0.0

    return DashboardSnapshot(
        request_count=len(requests),
        response_count=len(responses),
        error_count=len(failures),
        error_rate_pct=(len(failures) / len(requests) * 100) if len(requests) else 0.0,
        latency_p50=percentile(0.50),
        latency_p95=percentile(0.95),
        latency_p99=percentile(0.99),
        request_rate_per_minute=len(requests) / elapsed,
        total_cost_usd=float(costs.sum()) if not costs.empty else 0.0,
        tokens_in_total=int(tokens_in.sum()) if not tokens_in.empty else 0,
        tokens_out_total=int(tokens_out.sum()) if not tokens_out.empty else 0,
        quality_avg=float(quality.mean()) if not quality.empty else 0.0,
    )


def minute_series(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    work["minute"] = work["ts"].dt.floor("min")
    rows: list[dict[str, Any]] = []
    for minute, group in work.groupby("minute"):
        snapshot = dashboard_snapshot(group)
        rows.append(
            {
                "minute": minute,
                "requests": snapshot.request_count,
                "errors": snapshot.error_count,
                "error_rate_pct": snapshot.error_rate_pct,
                "latency_p50": snapshot.latency_p50,
                "latency_p95": snapshot.latency_p95,
                "latency_p99": snapshot.latency_p99,
                "cost_usd": snapshot.total_cost_usd,
                "tokens_in": snapshot.tokens_in_total,
                "tokens_out": snapshot.tokens_out_total,
                "quality": snapshot.quality_avg,
            }
        )
    return pd.DataFrame(rows).sort_values("minute")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def latest_event_time(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No events yet"
    latest = frame["ts"].max().to_pydatetime().astimezone(timezone.utc)
    return latest.strftime("%Y-%m-%d %H:%M:%S UTC")
