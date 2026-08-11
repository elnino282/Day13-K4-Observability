# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: **Nhóm điền sau khi thống nhất thông tin nộp bài.**
- Repository URL: **Nhóm điền sau.**
- Commit SHA cuối: **Điền sau khi merge dashboard và tạo commit cuối.**
- Thành viên và vai trò: **Từng thành viên tự khai đúng commit/PR ở mục 7.**

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 — [evidence](evidence/validate-logs-final.txt) (baseline 30/100 tại [đây](evidence/validate-logs-baseline.txt)).
- Tổng số traces: ít nhất 16 trace đã kiểm chứng — [trace index](evidence/trace-index.md).
- Số PII leak còn lại: 0/70 log records.
- Link/đường dẫn dashboard: contract 6/6 tại [evidence](evidence/validate-dashboard.txt); bổ sung ảnh runtime sau khi merge giao diện dashboard.

## 3. Logging và tracing

- Evidence correlation ID: `req-a5553348` nối request, retrieval và response tới trace `b4d029792a4e68cd0758851eab3a163b`; xem [challenge investigation](evidence/challenge-investigation.md).
- Evidence PII redaction: [pii-redaction.jsonl](evidence/pii-redaction.jsonl) chứa email, điện thoại và thẻ đã che; validator xác nhận 0 leak.
- Evidence trace waterfall: trace `b4d029792a4e68cd0758851eab3a163b`, gồm `agent.run` → `rag.retrieve` + `llm.generate`.
- Giải thích một span đáng chú ý: `rag.retrieve` mất 2.503 ms trong tổng 2.657 ms (khoảng 94%), trong khi `llm.generate` chỉ mất 150 ms. Log cùng correlation đo tool latency 2.500 ms nên retrieval là bottleneck.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: version 1, labels `baseline` và `production` sau rollback.
- Version/label candidate: version 2, label `candidate`.
- Trace ID của mỗi version: baseline `f00edc1a5e8a6457936c6e0f5cb31a56`; candidate `28041073697b681ca61de79bd5a25ab5`.
- Bằng chứng đổi label hoặc rollback: [prompt-lifecycle.txt](evidence/prompt-lifecycle.txt) và [audit-log.jsonl](evidence/audit-log.jsonl) chứng minh production chuyển sang v2 rồi về v1.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel` — [evidence](evidence/validate-dashboard.txt).
- Evidence dashboard: **Bổ sung ảnh runtime sau khi merge giao diện của thành viên phụ trách dashboard.**
- SLO đã chọn và lý do: P95 ≤ 3.000 ms (99,5%), error rate ≤ 2% (99%), daily cost ≤ 2,5 USD và quality trung bình ≥ 0,75. Các ngưỡng khớp dashboard contract và đo trực tiếp trải nghiệm/chi phí.
- Alert rules và runbook: ba alert latency, error và cost có severity, duration, owner và mitigation tại `config/alert_rules.yaml` và `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1` (`rag_slow`, feature `monitoring`).
- Triệu chứng từ metrics: P95 tăng từ 1.373 ms lên 2.657 ms, vượt ngưỡng challenge 2.000 ms; error breakdown rỗng và quality giữ 0,84.
- Trace ID liên quan: `b4d029792a4e68cd0758851eab3a163b`.
- Log line/correlation ID liên quan: `req-a5553348`, `retrieval_completed`, `tool_name=mock_rag.retrieve`, `latency_ms=2500`.
- Root cause: incident tạo delay 2,5 giây trong retrieval; span này chiếm khoảng 94% thời gian agent.
- Fix action: tắt incident; trong production áp retrieval timeout, cache và circuit breaker/fallback.
- Preventive measure: alert P95 duy trì 5 phút, giữ per-tool span và dùng runbook Metrics → Traces → Logs. Evidence đầy đủ tại [challenge-investigation.md](evidence/challenge-investigation.md).

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| **Tự điền** | **Khai đúng phần đã thực hiện** | **Commit/PR tương ứng** | **Bài học cá nhân** |
