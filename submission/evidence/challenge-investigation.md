# Challenge `day13-k4-observability-v1`

## Metrics

- Before incident: traffic 5, P50 1.353 ms, P95/P99 1.373 ms, errors 0, quality 0,84.
- After five official `rag_slow` requests: traffic 10, P50 2.655 ms, P95/P99 2.657 ms, errors 0, quality 0,84.
- P95 increased 1.284 ms and exceeded the official challenge threshold of 2.000 ms. Error rate and quality did not degrade, localizing the symptom to latency.

## Trace

- Trace ID: `b4d029792a4e68cd0758851eab3a163b`
- Prompt metadata: `day13-chat`, label `production`, version 1, source `langfuse`.
- `agent.run`: 2.657 ms.
- `rag.retrieve`: 2.503 ms; metadata `tool_name=mock_rag.retrieve`, measured tool latency 2.500 ms.
- `llm.generate`: 150 ms.

The retrieval span accounts for approximately 94% of the root span and is the abnormal span.

## Logs

```json
{"event":"request_received","correlation_id":"req-a5553348","feature":"monitoring","model":"claude-sonnet-4-5"}
{"event":"retrieval_completed","correlation_id":"req-a5553348","tool_name":"mock_rag.retrieve","latency_ms":2500}
{"event":"response_sent","correlation_id":"req-a5553348","latency_ms":2655,"trace_id":"b4d029792a4e68cd0758851eab3a163b"}
```

## Conclusion and action

- Root cause: the `rag_slow` incident adds a 2,5-second delay in retrieval. Metrics, trace duration and the correlation-linked log line agree.
- Immediate mitigation: disable `rag_slow`; the audit log records both enable and disable actions.
- Production fix: enforce a retrieval timeout, cache safe results and use a circuit breaker/fallback when the vector store exceeds its latency budget.
- Prevention: alert on sustained P95 latency, retain per-tool spans, and require a Metrics → Traces → Logs check in the runbook.
