from pathlib import Path

import pytest

from myagent.config import MCPServerConfig
from myagent.mcp import StdioMCPClient
from myagent.tools.loader import load_mcp_tools


def _fake_server_args() -> tuple[str, tuple[str, ...]]:
    fixture = Path("tests") / "fixtures" / "fake_mcp_server.py"
    return "python", (str(fixture),)


def _fake_server_config(name: str) -> MCPServerConfig:
    command, args = _fake_server_args()
    return MCPServerConfig(name=name, command=command, args=args, timeout_seconds=20)


def test_stdio_mcp_client_lists_and_calls_tools() -> None:
    command, args = _fake_server_args()
    client = StdioMCPClient(command=command, args=args, cwd=Path.cwd())
    try:
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo"

        result = client.call_tool("echo", {"text": "hello"})
        assert result.ok
        assert result.content == "echo:hello"
    finally:
        client.close()


def test_load_mcp_tools_wraps_mcp_tool_as_toolspec() -> None:
    tools, clients = load_mcp_tools(Path.cwd(), servers=(_fake_server_config("default"),))
    try:
        assert len(tools) == 1
        assert tools[0].name == "mcp__default__echo"

        result = tools[0].handler({"text": "world"})
        assert result.ok
        assert result.content == "echo:world"
    finally:
        for client in clients:
            client.close()


def test_load_mcp_tools_supports_multiple_servers() -> None:
    tools, clients = load_mcp_tools(
        Path.cwd(),
        servers=(_fake_server_config("repo"), _fake_server_config("browser")),
    )
    try:
        assert [tool.name for tool in tools] == [
            "mcp__repo__echo",
            "mcp__browser__echo",
        ]
        assert tools[0].handler({"text": "a"}).content == "echo:a"
        assert tools[1].handler({"text": "b"}).content == "echo:b"
    finally:
        for client in clients:
            client.close()


def test_load_mcp_tools_rejects_duplicate_namespaced_tools() -> None:
    with pytest.raises(ValueError, match="Duplicate MCP tool name"):
        load_mcp_tools(
            Path.cwd(),
            servers=(_fake_server_config("dup"), _fake_server_config("dup")),
        )
