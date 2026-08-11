# Evidence screenshot checklist

Machine-verifiable evidence and exact IDs are already stored in this directory. Before submission, add these UI screenshots without editing or fabricating their contents:

- `langfuse-trace-list.png`: Langfuse trace list showing at least 10 traces from `trace-index.md`.
- `langfuse-prompt-versions.png`: prompt `day13-chat` versions 1 and 2 with baseline/candidate labels.
- `langfuse-prompt-rollback.png`: final production label on version 1; `prompt-lifecycle.txt` records the promote/rollback values.
- `langfuse-rag-slow-waterfall.png`: trace `b4d029792a4e68cd0758851eab3a163b` with `rag.retrieve` and `llm.generate` visible.
- `dashboard-runtime.png`: merged dashboard showing all six panels, 60-minute range, units and thresholds.

After adding the dashboard screenshot, replace the pending note in `submission/REPORT.md` with its relative path. Team identity, repository URL, final commit SHA and per-member commit/PR attribution must also be filled by the team.
