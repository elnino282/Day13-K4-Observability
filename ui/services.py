from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pandas as pd

from scripts.manage_prompts import prompt_status
from scripts.validate_logs import ENRICHMENT_FIELDS, PII_DETECTORS
from ui.data import dashboard_snapshot, dashboard_window, minute_series, read_jsonl, records_frame
from ui.settings import API_BASE_URL, LOG_PATH


INCIDENT_PLAYBOOKS = {
    "rag_slow": {
        "metric": "P95 latency vượt ngưỡng SLO 3.000 ms.",
        "trace": "Mở một trace chậm; span rag.retrieve chiếm phần lớn waterfall.",
        "log": "retrieval_completed có cùng correlation ID và latency_ms tăng cao.",
        "root": "Độ trễ retrieval được chèn vào luồng mock vector-store.",
        "fix": "Tắt scenario; áp dụng cache, timeout hoặc retrieval fallback.",
        "prevent": "Cảnh báo tail latency và bổ sung kiểm thử timeout/circuit breaker.",
    },
    "tool_fail": {
        "metric": "Error rate và số lượng request_failed tăng.",
        "trace": "rag.retrieve là span đầu tiên có level ERROR.",
        "log": "retrieval_failed và request_failed dùng chung correlation ID.",
        "root": "Lời gọi vector-store phát sinh timeout exception.",
        "fix": "Tắt tool bị lỗi và trả về fallback response an toàn.",
        "prevent": "Thêm retry budget, circuit breaker và downstream health check.",
    },
    "cost_spike": {
        "metric": "Output token và cost tăng trong khi traffic không đổi.",
        "trace": "llm.generate có usage và total cost bất thường.",
        "log": "response_sent cho thấy tokens_out và cost_usd tăng cao.",
        "root": "Incident nhân số lượng output token được sinh ra.",
        "fix": "Tắt scenario và giới hạn output token.",
        "prevent": "Cảnh báo cost/request và quản lý token limit theo prompt version.",
    },
}

SCENARIO_LABELS = {
    "rag_slow": "RAG chậm",
    "tool_fail": "Tool lỗi",
    "cost_spike": "Cost tăng đột biến",
}


def get_health() -> tuple[bool, dict[str, Any]]:
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=2.0)
        response.raise_for_status()
        return True, response.json()
    except Exception:
        return False, {}


def analyze_log_quality(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_required = 0
    missing_enrichment = 0
    correlation_ids: set[str] = set()
    pii_hits: list[dict[str, Any]] = []
    for record in records:
        if not {"ts", "level", "event"}.issubset(record):
            missing_required += 1
        if record.get("service") == "api":
            correlation_id = record.get("correlation_id")
            if not correlation_id or correlation_id == "MISSING":
                missing_required += 1
            if not ENRICHMENT_FIELDS.issubset(record):
                missing_enrichment += 1
        raw = json.dumps(record, ensure_ascii=False)
        detected = [name for name, detector in PII_DETECTORS.items() if detector.search(raw)]
        if detected:
            pii_hits.append({"event": record.get("event", "unknown"), "types": detected})
        correlation_id = record.get("correlation_id")
        if correlation_id and correlation_id not in {"MISSING", "system"}:
            correlation_ids.add(str(correlation_id))

    score = 100
    if missing_required:
        score -= 30
    if len(correlation_ids) < 2:
        score -= 20
    if missing_enrichment:
        score -= 20
    if pii_hits:
        score -= 30
    return {
        "score": max(0, score),
        "missing_required": missing_required,
        "missing_enrichment": missing_enrichment,
        "correlation_ids": len(correlation_ids),
        "pii_hits": pii_hits,
    }


def fetch_langfuse_snapshot() -> dict[str, Any]:
    from app.tracing import get_langfuse_client

    client = get_langfuse_client()
    if not client.auth_check():
        raise RuntimeError("Langfuse authentication failed")
    labels = prompt_status(client)
    response = client.api.trace.list(limit=20, order_by="timestamp.desc")
    traces = []
    for trace in response.data:
        metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
        traces.append(
            {
                "timestamp": trace.timestamp,
                "trace_id": trace.id,
                "name": trace.name,
                "session_id": trace.session_id,
                "prompt_label": metadata.get("prompt_label"),
                "prompt_version": metadata.get("prompt_version"),
                "correlation_id": metadata.get("correlation_id"),
            }
        )
    return {"labels": labels, "traces": traces, "count": len(traces)}


def run_demo_burst(count: int, scenario: str) -> list[dict[str, Any]]:
    prompts = [
        "Giải thích cách Metrics, Traces và Logs phối hợp với nhau",
        "Kỹ sư nên điều tra tail latency như thế nào",
        "Tóm tắt quy trình observability cho AI API",
        "Nên kiểm tra signal nào sau khi latency tăng",
        "Mô tả cách chứng minh một span chậm là root cause",
        "Đội AI có thể kiểm soát token cost như thế nào",
        "Vì sao correlation ID hữu ích khi xử lý incident",
        "Điều gì làm cho một alert có thể hành động được",
    ]
    results = []
    session_id = f"ui-{scenario}-{uuid.uuid4().hex[:6]}"
    for index in range(count):
        started = pd.Timestamp.now(tz="UTC")
        try:
            response = httpx.post(
                f"{API_BASE_URL}/chat",
                json={
                    "user_id": "ui-incident-demo",
                    "session_id": session_id,
                    "feature": "monitoring",
                    "message": prompts[index % len(prompts)],
                },
                timeout=30.0,
            )
            elapsed_ms = int((pd.Timestamp.now(tz="UTC") - started).total_seconds() * 1000)
            payload = response.json()
            results.append(
                {
                    "request": index + 1,
                    "status": response.status_code,
                    "latency_ms": elapsed_ms,
                    "correlation_id": payload.get("correlation_id") or response.headers.get("x-request-id"),
                    "trace_id": payload.get("trace_id"),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "request": index + 1,
                    "status": "client_error",
                    "latency_ms": None,
                    "correlation_id": None,
                    "trace_id": None,
                    "detail": type(exc).__name__,
                }
            )
    return results


def load_dashboard_data(minutes: int):
    frame = records_frame(read_jsonl(LOG_PATH))
    recent = dashboard_window(frame, minutes)
    return recent, minute_series(recent), dashboard_snapshot(recent)
