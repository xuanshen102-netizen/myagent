from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from myagent.cli import build_kernel
from myagent.config import Settings


class MyAgentHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], kernel) -> None:
        super().__init__(server_address, MyAgentAPIHandler)
        self.kernel = kernel


class MyAgentAPIHandler(BaseHTTPRequestHandler):
    server: MyAgentHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json_response(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": "myagent-api",
                },
            )
            return

        if parsed.path.startswith("/sessions/"):
            session_id = parsed.path.removeprefix("/sessions/").strip()
            if not session_id:
                self._json_response(HTTPStatus.BAD_REQUEST, {"error": "Missing session id."})
                return
            messages = self.server.kernel.sessions.load(session_id)
            memory_snapshot = (
                self.server.kernel.memory.store.load(session_id)
                if self.server.kernel.memory is not None
                else None
            )
            self._json_response(
                HTTPStatus.OK,
                {
                    "session_id": session_id,
                    "messages": [message.to_dict() for message in messages],
                    "memory": memory_snapshot.to_dict() if memory_snapshot is not None else None,
                },
            )
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/chat":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        message = str(payload.get("message", "")).strip()
        session_id = str(payload.get("session_id", "default")).strip() or "default"
        skill = str(payload.get("skill", "")).strip() or None
        if not message:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "Field 'message' is required."})
            return

        answer = self.server.kernel.run_once(session_id=session_id, user_text=message, skill_name=skill)
        self._json_response(
            HTTPStatus.OK,
            {
                "session_id": session_id,
                "answer": answer,
                "skill": skill,
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def _read_json(self) -> dict[str, Any]:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("Missing Content-Length header.")
        try:
            length = int(content_length)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header.") from exc
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(settings: Settings) -> MyAgentHTTPServer:
    kernel = build_kernel(settings)
    return MyAgentHTTPServer((settings.api_host, settings.api_port), kernel)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="myagent HTTP API server.")
    parser.add_argument("--host", help="Override bind host.")
    parser.add_argument("--port", type=int, help="Override bind port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    if args.host:
        settings.api_host = args.host
    if args.port is not None:
        settings.api_port = args.port
    settings.validate()

    server = build_server(settings)
    try:
        print(f"myagent API listening on http://{settings.api_host}:{settings.api_port}")
        server.serve_forever()
    finally:
        server.server_close()
        server.kernel.close()


if __name__ == "__main__":
    main()
