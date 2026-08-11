from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ui.data import load_yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

API_BASE_URL = os.getenv("UI_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
LOG_PATH = REPO_ROOT / os.getenv("LOG_PATH", "data/logs.jsonl")
AUDIT_PATH = REPO_ROOT / os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl")
DASHBOARD_CONFIG = load_yaml(REPO_ROOT / "config" / "dashboard.yaml")
SLO_CONFIG = load_yaml(REPO_ROOT / "config" / "slo.yaml")
ALERT_CONFIG = load_yaml(REPO_ROOT / "config" / "alert_rules.yaml")
