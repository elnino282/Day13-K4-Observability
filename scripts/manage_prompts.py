from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.audit import write_audit
from app.cli import configure_utf8_stdio
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE
from app.tracing import get_langfuse_client


PROMPT_NAME = "day13-chat"
CANDIDATE_PROMPT_TEMPLATE = (
    "You are a concise observability assistant.\n"
    "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\n"
    "Answer in no more than three sentences."
)


def _get_by_label(client: Any, label: str):
    try:
        return client.get_prompt(
            PROMPT_NAME,
            label=label,
            type="text",
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=4,
        )
    except Exception as exc:
        if type(exc).__name__ in {"NotFoundError", "LangfuseNotFoundError"}:
            return None
        raise


def prompt_status(client: Any) -> dict[str, int | None]:
    return {
        label: (int(prompt.version) if prompt is not None else None)
        for label in ("baseline", "candidate", "production")
        for prompt in [_get_by_label(client, label)]
    }


def bootstrap_prompts(client: Any) -> dict[str, int | None]:
    current = prompt_status(client)
    if current["baseline"] is not None and current["candidate"] is not None:
        return current
    if current["baseline"] is not None or current["candidate"] is not None:
        raise RuntimeError(
            "Prompt day13-chat đang ở trạng thái dở dang; không tự tạo thêm version."
        )

    baseline = client.create_prompt(
        name=PROMPT_NAME,
        prompt=DEFAULT_PROMPT_TEMPLATE,
        labels=["baseline", "production"],
        type="text",
        tags=["day13", "observability"],
        commit_message="Create Day 13 baseline prompt",
    )
    candidate = client.create_prompt(
        name=PROMPT_NAME,
        prompt=CANDIDATE_PROMPT_TEMPLATE,
        labels=["candidate"],
        type="text",
        tags=["day13", "observability"],
        commit_message="Create concise candidate prompt",
    )
    write_audit(
        "prompt_bootstrapped",
        actor="prompt-cli",
        details={"name": PROMPT_NAME, "baseline": baseline.version, "candidate": candidate.version},
    )
    return prompt_status(client)


def promote_candidate(client: Any) -> dict[str, int | None]:
    candidate = _get_by_label(client, "candidate")
    if candidate is None:
        raise RuntimeError("Không tìm thấy label candidate; hãy chạy bootstrap trước.")
    client.update_prompt(
        name=PROMPT_NAME,
        version=int(candidate.version),
        new_labels=["candidate", "production"],
    )
    write_audit(
        "prompt_promoted",
        actor="prompt-cli",
        details={"name": PROMPT_NAME, "production_version": candidate.version},
    )
    return prompt_status(client)


def rollback_production(client: Any) -> dict[str, int | None]:
    baseline = _get_by_label(client, "baseline")
    if baseline is None:
        raise RuntimeError("Không tìm thấy label baseline; hãy chạy bootstrap trước.")
    client.update_prompt(
        name=PROMPT_NAME,
        version=int(baseline.version),
        new_labels=["baseline", "production"],
    )
    write_audit(
        "prompt_rolled_back",
        actor="prompt-cli",
        details={"name": PROMPT_NAME, "production_version": baseline.version},
    )
    return prompt_status(client)


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Quản lý prompt Day 13 trên Langfuse")
    parser.add_argument("action", choices=["status", "bootstrap", "promote", "rollback"])
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    client = get_langfuse_client()
    if not client.auth_check():
        print("Langfuse authentication failed.", file=sys.stderr)
        return 1

    actions = {
        "status": prompt_status,
        "bootstrap": bootstrap_prompts,
        "promote": promote_candidate,
        "rollback": rollback_production,
    }
    try:
        status = actions[args.action](client)
    except Exception as exc:
        print(f"Prompt operation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"prompt_name": PROMPT_NAME, "labels": status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
