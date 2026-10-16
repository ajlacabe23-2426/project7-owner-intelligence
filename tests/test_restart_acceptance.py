"""Verify Project 7's evidence/feedback survives a real loopback API restart.

This is a synthetic operator lab with a disposable SQLite file, never hosted data.
"""
import socket
import threading
import time

import httpx
import uvicorn

from app.main import app
from scripts.demo_operator_feedback import run_lab


def start_local_server():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        until = time.monotonic() + 12
        while not server.started and thread.is_alive() and time.monotonic() < until:
            time.sleep(0.01)
        assert server.started, "Disposable operator API did not start"
    except BaseException:
        server.should_exit = True
        thread.join(timeout=12)
        listener.close()
        raise
    return f"http://127.0.0.1:{port}", server, thread, listener


def stop_local_server(server, thread, listener):
    server.should_exit = True
    thread.join(timeout=12)
    listener.close()
    assert not thread.is_alive(), "Disposable operator API did not shut down"


def test_episode_resolution_and_feedback_survive_actual_server_restart(monkeypatch, tmp_path):
    monkeypatch.setenv("OWNER_INTELLIGENCE_DB_PATH", str(tmp_path / "restart-acceptance.db"))

    base, server, thread, socket_handle = start_local_server()
    try:
        first = run_lab(base)
        assert first["result"] == "PASS"
        episode_id = first["episode_id"]
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            old = client.get("/episodes/" + episode_id + "/feedback")
            assert old.status_code == 200
            prior = old.json()
            assert prior["episode"]["current_status"] == "resolved"
            assert len(prior["dispositions"]) == 1
            assert len(prior["outcomes"]) == 1
    finally:
        stop_local_server(server, thread, socket_handle)

    # Stop uvicorn completely, then start another independent instance using
    # the same local database. The result must not rely on in-memory state.
    next_base, next_server, next_thread, next_socket = start_local_server()
    try:
        with httpx.Client(base_url=next_base, trust_env=False, timeout=5) as client:
            after = client.get("/episodes/" + episode_id + "/feedback")
            assert after.status_code == 200
            restored = after.json()
            assert restored["episode"]["current_status"] == "resolved"
            assert restored["dispositions"] == prior["dispositions"]
            assert restored["outcomes"] == prior["outcomes"]
            assert client.get("/episodes/" + episode_id + "-unknown/feedback").status_code == 404
    finally:
        stop_local_server(next_server, next_thread, next_socket)
