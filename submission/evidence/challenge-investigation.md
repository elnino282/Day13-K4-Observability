# Challenge `day13-k4-observability-v1`

Số liệu dưới đây lấy từ run cuối cùng, khớp với `data/logs.jsonl` đang nộp (validator 100/100 trên 49 record). Run điều tra trước đó giữ ở mục cuối để đối chiếu.

## Metrics

- Baseline (10 request `qa`/`summary`): P50 158 ms, P95 671 ms, P99 988 ms, error 0, quality trung bình 0,88.
- Sau 5 request `rag_slow` chính thức (feature `monitoring`): P50/P95/P99 = 2.654 ms, error 0, quality trung bình 0,84.
- P95 vượt ngưỡng chính thức 2.000 ms trong `config/challenge.json`. Error rate và quality không xấu đi, nên triệu chứng khu trú ở latency.

## Trace

- Trace ID: `6420376f132f9b69b7a87e59b867e756`
- Prompt metadata: `day13-chat`, label `production`, version 1, source `langfuse`.
- `agent.run`: 2.654 ms (bằng `latency_ms` của log `response_sent` cùng correlation ID).
- `rag.retrieve`: `tool_name=mock_rag.retrieve`, tool latency đo được 2.500 ms.
- Phần còn lại (~154 ms) là `llm.generate` cộng overhead, khớp dải P50 158 ms của baseline.

Span retrieval chiếm khoảng 94% root span và là span bất thường.

## Logs

```json
{"event":"request_received","correlation_id":"req-e8cf46ee","feature":"monitoring","model":"claude-sonnet-4-5"}
{"event":"retrieval_completed","correlation_id":"req-e8cf46ee","tool_name":"mock_rag.retrieve","latency_ms":2500}
{"event":"response_sent","correlation_id":"req-e8cf46ee","latency_ms":2654,"trace_id":"6420376f132f9b69b7a87e59b867e756"}
```

## Conclusion and action

- Root cause: incident `rag_slow` thêm delay 2,5 giây trong retrieval. Metrics, thời lượng trace và log nối theo correlation ID đều chỉ về cùng một span.
- Immediate mitigation: tắt `rag_slow` (`python scripts/inject_incident.py --disable`); audit log ghi cả hành động bật và tắt.
- Production fix: đặt timeout cho retrieval, cache kết quả an toàn và dùng circuit breaker/fallback khi vector store vượt latency budget.
- Prevention: alert khi P95 vượt ngưỡng kéo dài, giữ span theo từng tool, và bắt buộc quy trình Metrics → Traces → Logs trong runbook.

## Run điều tra trước đó (đối chiếu)

Cùng kịch bản, chạy trước khi regenerate log sạch. Log của run này không còn trong `data/logs.jsonl`.

- Metrics: P50 1.353 ms, P95/P99 1.373 ms trước incident; P50 2.655 ms, P95/P99 2.657 ms sau incident.
- Trace `b4d029792a4e68cd0758851eab3a163b`: `agent.run` 2.657 ms, `rag.retrieve` 2.503 ms, `llm.generate` 150 ms.
- Correlation ID `req-a5553348` với `retrieval_completed`, `tool_name=mock_rag.retrieve`, `latency_ms=2500`.
- Kết luận giống hệt run cuối: retrieval là bottleneck.
