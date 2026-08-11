from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def wait_for_url(url: str, timeout_seconds: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def run_check(label: str, command: list[str]) -> tuple[bool, str]:
    print(f"\n--- {label} ---")
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    print(output)
    return completed.returncode == 0, output


def terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Day 13 FastAPI + SignalOps demo UI")
    parser.add_argument("--skip-checks", action="store_true", help="Skip tests and validators before launch")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the UI in the default browser")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-port", type=int, default=8501)
    args = parser.parse_args()

    for port in (args.api_port, args.ui_port):
        if port_is_open(port):
            print(f"Port {port} is already in use. Stop the existing service or choose another port.")
            return 1

    environment = dict(os.environ)
    environment["UI_API_BASE_URL"] = f"http://127.0.0.1:{args.api_port}"
    if not args.skip_checks:
        tests_ok, tests_output = run_check(
            "Test suite",
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        )
        match = re.search(r"(\d+) passed", tests_output)
        environment["UI_TEST_SUMMARY"] = f"{match.group(1)} passed" if tests_ok and match else "Failed"
        run_check("Log validator", [sys.executable, "scripts/validate_logs.py"])
        run_check("Dashboard validator", [sys.executable, "scripts/validate_dashboard.py"])
    else:
        environment["UI_TEST_SUMMARY"] = "Checks skipped"

    api_process: subprocess.Popen | None = None
    ui_process: subprocess.Popen | None = None
    try:
        print("\nStarting FastAPI…")
        api_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.api_port),
                "--env-file",
                ".env",
            ],
            cwd=REPO_ROOT,
            env=environment,
        )
        if not wait_for_url(f"http://127.0.0.1:{args.api_port}/health"):
            print("FastAPI did not become healthy within 20 seconds.")
            return 1

        print("Starting SignalOps UI…")
        ui_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "ui/app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(args.ui_port),
                "--server.headless",
                "true",
            ],
            cwd=REPO_ROOT,
            env=environment,
        )
        ui_url = f"http://127.0.0.1:{args.ui_port}"
        if not wait_for_url(f"{ui_url}/_stcore/health"):
            print("Streamlit did not become healthy within 20 seconds.")
            return 1

        print(f"\nDemo ready: {ui_url}")
        print("Press Ctrl+C to stop both services cleanly.")
        if not args.no_browser:
            webbrowser.open(ui_url)
        return ui_process.wait()
    except KeyboardInterrupt:
        print("\nStopping demo…")
        return 0
    finally:
        terminate(ui_process)
        terminate(api_process)


if __name__ == "__main__":
    raise SystemExit(main())
