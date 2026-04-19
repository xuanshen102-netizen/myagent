from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any

from myagent.providers.base import ToolResult

MCP_PROTOCOL_VERSION = "2025-03-26"


@dataclass(slots=True)
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


class StdioMCPClient:
    def __init__(
        self,
        command: str,
        args: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.command = command
        self.args = args
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self._request_ids = count(1)
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def connect(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            [self.command, *self.args],
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "myagent", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized")

    def list_tools(self) -> list[MCPToolDefinition]:
        self.connect()
        tools: list[MCPToolDefinition] = []
        cursor: str | None = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            result = self._request("tools/list", params)
            for item in result.get("tools", []):
                tools.append(
                    MCPToolDefinition(
                        name=item["name"],
                        description=item.get("description") or item.get("title") or item["name"],
                        input_schema=item.get("inputSchema") or {"type": "object", "properties": {}},
                    )
                )
            cursor = result.get("nextCursor")
            if not cursor:
                break
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        self.connect()
        try:
            result = self._request("tools/call", {"name": name, "arguments": arguments})
        except TimeoutError as exc:
            return ToolResult.failure(
                f"MCP tool call timed out for {name}: {exc}",
                error_type="mcp_timeout",
                metadata={"tool_name": name},
            )
        except RuntimeError as exc:
            return ToolResult.failure(
                f"MCP tool call failed for {name}: {exc}",
                error_type="mcp_execution_error",
                metadata={"tool_name": name},
            )

        rendered = self._render_content(result.get("content", []))
        is_error = bool(result.get("isError"))
        if is_error:
            return ToolResult.failure(
                rendered or f"MCP tool returned an error: {name}",
                error_type="mcp_tool_error",
                structured_content={"content": result.get("content", [])},
                metadata={"tool_name": name},
            )
        return ToolResult.success(
            rendered or "(empty MCP tool response)",
            structured_content={"content": result.get("content", [])},
            metadata={"tool_name": name},
        )

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        self._process = None
        if process.stdin:
            process.stdin.close()
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._write_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            }
        )

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        process = self._require_process()
        request_id = next(self._request_ids)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        with self._lock:
            self._write_message(payload)
            while True:
                line = self._readline(process)
                message = json.loads(line)
                if "id" not in message:
                    continue
                if message["id"] != request_id:
                    continue
                if "error" in message:
                    error = message["error"]
                    raise RuntimeError(error.get("message", "Unknown MCP error"))
                return message.get("result", {})

    def _write_message(self, payload: dict[str, Any]) -> None:
        process = self._require_process()
        if process.stdin is None:
            raise RuntimeError("MCP stdin is unavailable.")
        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def _readline(self, process: subprocess.Popen[str]) -> str:
        if process.stdout is None:
            raise RuntimeError("MCP stdout is unavailable.")
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly.")
        return line

    def _require_process(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise RuntimeError("MCP client is not connected.")
        return self._process

    def _render_content(self, content: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for item in content:
            item_type = item.get("type")
            if item_type == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
                    continue
            parts.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(parts)
