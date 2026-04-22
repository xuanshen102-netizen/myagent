import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from myagent.api import build_server
from myagent.config import Settings


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_settings_validate_rejects_invalid_api_port() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        api_port=70000,
    )

    with pytest.raises(ValueError, match="MYAGENT_API_PORT"):
        settings.validate()


def test_http_api_health_chat_and_session_endpoints() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data") / "test-api",
        workspace_dir=Path.cwd(),
        api_host="127.0.0.1",
        api_port=0,
        trace_enabled=False,
    )
    settings.validate()

    server = build_server(settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        status, health = _request_json(f"http://{host}:{port}/health")
        assert status == 200
        assert health["status"] == "ok"

        status, chat = _request_json(
            f"http://{host}:{port}/chat",
            method="POST",
            payload={"session_id": "demo", "message": "hello", "skill": "repo_explainer"},
        )
        assert status == 200
        assert chat["session_id"] == "demo"
        assert "mock" in chat["answer"]
        assert chat["skill"] == "repo_explainer"

        status, session_payload = _request_json(f"http://{host}:{port}/sessions/demo")
        assert status == 200
        assert session_payload["session_id"] == "demo"
        assert len(session_payload["messages"]) >= 2
        assert session_payload["memory"] is not None
        assert "task" in session_payload["memory"]
    finally:
        server.shutdown()
        server.server_close()
        server.kernel.close()
        thread.join(timeout=5)
