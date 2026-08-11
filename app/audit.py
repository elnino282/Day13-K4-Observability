from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pii import scrub_value


AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
_AUDIT_LOCK = threading.Lock()


def write_audit(
    action: str,
    *,
    correlation_id: str = "system",
    actor: str = "system",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = scrub_value(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "audit_event",
            "action": action,
            "actor": actor,
            "correlation_id": correlation_id,
            "details": details or {},
        }
    )
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOCK:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
