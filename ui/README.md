# SignalOps UI

UI showcase cho Day 13 Observability. `app.py` chỉ là entrypoint; phần triển khai được chia theo trách nhiệm:

- `settings.py`: đường dẫn, biến môi trường và config runtime.
- `theme.py`: dark theme và responsive CSS.
- `components.py`: KPI cards, panel headers và biểu đồ dùng lại.
- `services.py`: API health, log quality, Langfuse và demo traffic.
- `pages/`: năm màn hình độc lập.

Giao diện gồm năm khu vực:

- **Tổng quan**: trạng thái hệ thống và luồng điều tra Metrics → Traces → Logs.
- **Chat trực tiếp**: gọi `POST /chat` và hiển thị correlation ID, trace ID, latency, token, cost, quality.
- **Metrics**: đúng sáu panel từ `config/dashboard.yaml`, đọc `data/logs.jsonl` và refresh 30 giây.
- **Vận hành**: bật/tắt practice incidents, xem alerts, structured logs và audit trail.
UI showcase cho Day 13 Observability. Giao diện gồm năm khu vực:

- **Overview**: trạng thái hệ thống và luồng điều tra Metrics → Traces → Logs.
- **Live Chat**: gọi `POST /chat` và hiển thị correlation ID, trace ID, latency, token, cost, quality.
- **Metrics**: đúng sáu panel từ `config/dashboard.yaml`, đọc `data/logs.jsonl` và refresh 30 giây.
- **Operations**: bật/tắt practice incidents, xem alerts, structured logs và audit trail.
- **Evidence**: tổng hợp các hạng mục đã hoàn thành và runtime proof.

Chạy toàn bộ demo bằng một lệnh. Script chạy preflight tests/validators, mở API + UI và tự dừng cả hai khi nhấn `Ctrl+C`:

```powershell
conda activate day13
python scripts/run_demo.py
```

Nếu cần mở nhanh và bỏ qua preflight:

```powershell
python scripts/run_demo.py --skip-checks
```

Hoặc chạy API và UI thủ công ở hai terminal:

```powershell
conda activate day13
uvicorn app.main:app --reload --env-file .env
```

```powershell
conda activate day13
streamlit run ui/app.py
```

Mặc định UI mở tại `http://localhost:8501` và gọi API tại `http://127.0.0.1:8000`.
