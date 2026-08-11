# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `user_latency_slo_breach`
- Severity: Critical.
- SLI/SLO liên quan: P95 latency ≤ 2.000 ms, mục tiêu 99,5% trong 28 ngày.
- Điều kiện và thời gian duy trì: P95 > 2.000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: phản hồi AI chậm ở phần đuôi phân phối.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận P50/P95/P99 và traffic trong cùng cửa sổ 5 phút.
  2. Mở trace chậm, so sánh duration của `rag.retrieve` và `llm.generate`.
  3. Tìm log theo `correlation_id`, kiểm tra `tool_name`, `latency_ms` và incident audit.
- Mitigation tạm thời: rollback thay đổi gần nhất; bật cache hoặc timeout/circuit breaker cho retrieval chậm.
- Owner: `observability-on-call`.

## Alert 2

- Tên: `request_error_slo_breach`
- Severity: Critical.
- SLI/SLO liên quan: error rate ≤ 2%, mục tiêu 99% trong 28 ngày.
- Điều kiện và thời gian duy trì: error rate > 2% liên tục 5 phút.
- Ảnh hưởng tới người dùng: request không nhận được câu trả lời hợp lệ.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra breakdown `error_type` và xác nhận traffic denominator.
  2. Mở trace lỗi phổ biến nhất, tìm span đầu tiên có level `ERROR`.
  3. Tìm `request_failed` và `retrieval_failed` theo correlation ID trong log.
- Mitigation tạm thời: tắt tool lỗi, dùng fallback an toàn và giảm concurrency nếu downstream quá tải.
- Owner: `api-on-call`.

## Alert 3

- Tên: `daily_cost_budget_at_risk`
- Severity: Warning.
- SLI/SLO liên quan: projected daily cost ≤ 2,5 USD.
- Điều kiện và thời gian duy trì: dự báo chi phí ngày > 2,5 USD liên tục 15 phút.
- Ảnh hưởng tới người dùng: ngân sách có nguy cơ cạn và dịch vụ phải bị giới hạn.
- Ba bước kiểm tra đầu tiên:
  1. So sánh cost, traffic và token output trên cùng cửa sổ.
  2. Lọc trace theo model/prompt version, tìm generation có token hoặc cost bất thường.
  3. Dùng correlation ID kiểm tra request và audit log thay đổi prompt/incident gần nhất.
- Mitigation tạm thời: rollback prompt gây output dài, áp token cap và chuyển traffic phù hợp sang model rẻ hơn.
- Owner: `ai-platform-owner`.
