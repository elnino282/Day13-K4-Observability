# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: C5-3
- Repository URL: https://github.com/elnino282/Day13-K4-Observability
- Commit SHA cuối: **Điền sau khi push commit cuối.**
- Thành viên và vai trò:

| Thành viên | MSSV | Git author | Vai trò |
|---|---|---|---|
| Hồ Ngọc Quỳnh | 2A202601684 | `elnino282` | Logging, PII, metrics và tracing core |
| Nguyễn Duy Bách | 2A202601844 | `Nayumi.DEV` | Dashboard UI, SLO/alert và script demo |
| Hoàng Văn Huy | 2A202601356 | `hoanghuy06072004gtc-sketch` | Contract test cho logging và observability |
| Chu Quang Hiếu | 2A202601344 | `quanghieu4438` | Report, evidence và điều tra challenge |
| Nguyễn Đình Liên Thành | 2A202601790 | **chưa có commit** | **Tự khai phần việc và tạo commit tương ứng** |

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 trên 49 record, 18 correlation ID — [evidence](evidence/validate-logs-final.txt) (baseline 30/100 tại [đây](evidence/validate-logs-baseline.txt)).
- Tổng số traces: 31 trace trong [trace index](evidence/trace-index.md); 15 trace thuộc run cuối khớp đúng `data/logs.jsonl` đang nộp.
- Số PII leak còn lại: 0/49 log records.
- Link/đường dẫn dashboard: contract 6/6 tại [evidence](evidence/validate-dashboard.txt); bổ sung ảnh runtime sau khi merge giao diện dashboard.

## 3. Logging và tracing

- Evidence correlation ID: `req-e8cf46ee` nối `request_received`, `retrieval_completed` và `response_sent` tới trace `6420376f132f9b69b7a87e59b867e756`; xem [challenge investigation](evidence/challenge-investigation.md).
- Evidence PII redaction: [pii-redaction.jsonl](evidence/pii-redaction.jsonl) chứa email, điện thoại và thẻ đã che; validator xác nhận 0 leak.
- Evidence trace waterfall: trace `6420376f132f9b69b7a87e59b867e756`, gồm `agent.run` → `rag.retrieve` + `llm.generate`.
- Giải thích một span đáng chú ý: `rag.retrieve` chiếm 2.500 ms trong tổng 2.654 ms của `agent.run` (khoảng 94%), phần còn lại ~154 ms là generate cộng overhead, khớp dải P50 158 ms của baseline. Log cùng correlation ID đo `tool_name=mock_rag.retrieve` latency 2.500 ms nên retrieval là bottleneck.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Version/label baseline: version 1, labels `baseline` và `production` sau rollback.
- Version/label candidate: version 2, label `candidate`.
- Trace ID của mỗi version: baseline `f00edc1a5e8a6457936c6e0f5cb31a56`; candidate `28041073697b681ca61de79bd5a25ab5`.
- Bằng chứng đổi label hoặc rollback: [prompt-lifecycle.txt](evidence/prompt-lifecycle.txt) và [audit-log.jsonl](evidence/audit-log.jsonl) chứng minh production chuyển sang v2 rồi về v1.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel` — [evidence](evidence/validate-dashboard.txt).
- Evidence dashboard: **Bổ sung ảnh runtime sau khi merge giao diện của thành viên phụ trách dashboard.**
- SLO đã chọn và lý do: P95 ≤ 2.000 ms (99,5%), error rate ≤ 2% (99%), daily cost ≤ 2,5 USD và quality trung bình ≥ 0,75. Ngưỡng latency hạ từ 3.000 xuống 2.000 ms cho khớp `latency_threshold_ms` của challenge: với 3.000 ms thì sự cố `rag_slow` (P95 2.654 ms) vẫn nằm dưới ngưỡng và alert không bao giờ bắn dù người dùng đã chờ gấp 4 lần baseline. Các ngưỡng còn lại khớp dashboard contract và đo trực tiếp trải nghiệm/chi phí.
- Alert rules và runbook: ba alert latency, error và cost có severity, duration, owner và mitigation tại `config/alert_rules.yaml` và `docs/alerts.md`.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1` (`rag_slow`, feature `monitoring`).
- Triệu chứng từ metrics: P95 tăng từ 671 ms (10 request baseline) lên 2.654 ms (5 request challenge), vượt ngưỡng challenge 2.000 ms; error breakdown rỗng và quality chỉ đổi 0,88 → 0,84.
- Trace ID liên quan: `6420376f132f9b69b7a87e59b867e756`.
- Log line/correlation ID liên quan: `req-e8cf46ee`, `retrieval_completed`, `tool_name=mock_rag.retrieve`, `latency_ms=2500`.
- Root cause: incident tạo delay 2,5 giây trong retrieval; span này chiếm khoảng 94% thời gian agent.
- Fix action: tắt incident; trong production áp retrieval timeout, cache và circuit breaker/fallback.
- Preventive measure: alert P95 duy trì 5 phút, giữ per-tool span và dùng runbook Metrics → Traces → Logs. Evidence đầy đủ tại [challenge-investigation.md](evidence/challenge-investigation.md).

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Hồ Ngọc Quỳnh | `app/main.py`, `app/middleware.py`, `app/pii.py`, `app/metrics.py`, test core và evidence đầu tiên | `06c7ac1`, `c775ae7` | **Tự điền** |
| Nguyễn Duy Bách | Dashboard Streamlit `ui/app.py`, `ui/data.py`, `scripts/run_demo.py`, kịch bản demo | `5ec33b8` | Qua repo này, tôi đã học được cách xây dựng hệ thống observability hoàn chỉnh cho ứng dụng AI: ghi log JSON có cấu trúc với correlation ID và loại bỏ PII, gắn trace để theo dõi latency/token/cost bằng Langfuse kèm prompt versioning (label, rollback), và quan trọng nhất là luồng điều tra incident từ Metrics → Traces → Logs để xác định root cause. |
| Hoàng Văn Huy | `tests/test_logging_contract.py`: correlation ID, enrichment, PII và log lỗi | `0a3023c` | **Tự điền** |
| Chu Quang Hiếu | Regenerate log sạch đạt 100/100, cập nhật evidence và toàn bộ report | **Điền SHA commit report sau khi push** | Baseline P95 mới là sự cố, mean thì k: với cả 15 requests, mean chỉ 863 ms < 2000 ms, chỉ p95 = 2654 ms mới vượt ngưỡng. Nên đặt SLO trên percentile đuôi thay vì trên mean. |
| Nguyễn Đình Liên Thành | **Tự khai** | **Chưa có commit** | **Tự điền** |
