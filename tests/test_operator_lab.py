"""Run the operator lab over real HTTP against a disposable local server."""
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from app.main import app
from scripts.demo_operator_feedback import WorkflowError, validate_base_url


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:8000", "http://example.com", "http://localhost:8000",
    "http://127.0.0.1.evil.invalid", "http://user:password@127.0.0.1",
    "http://127.0.0.1:8000/path", "http://127.0.0.1:8000?redirect=remote",
    "http://127.0.0.1:8000#fragment", "http://127.0.0.1:bad",
])
def test_lab_rejects_non_loopback_or_ambiguous_urls(url):
    with pytest.raises(WorkflowError):
        validate_base_url(url)


def test_operator_lab_real_http(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "operator-lab.db"))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started, "Disposable API failed to start"
        root = Path(__file__).resolve().parents[1]
        command = [sys.executable, str(root / "scripts/demo_operator_feedback.py"),
                   "--base-url", f"http://127.0.0.1:{port}"]
        first = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30)
        assert first.returncode == 0, first.stderr
        report = json.loads(first.stdout)
        assert report["result"] == "PASS"
        assert len(report["checks"]) == 7
        assert report["episode_id"]
        # Re-running creates an independent synthetic episode without a DB reset.
        second = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30)
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout)["episode_id"] != report["episode_id"]
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive(), "Disposable API did not stop"
