from pathlib import Path

from myagent.mcp import StdioMCPClient
from myagent.tools.loader import load_mcp_tools


def _fake_server_args() -> tuple[str, tuple[str, ...]]:
    fixture = Path("tests") / "fixtures" / "fake_mcp_server.py"
    return "python", (str(fixture),)


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
    command, args = _fake_server_args()
    tools, client = load_mcp_tools(
        Path.cwd(),
        command=command,
        args=args,
        timeout_seconds=20,
    )
    try:
        assert len(tools) == 1
        assert tools[0].name == "mcp__echo"

        result = tools[0].handler({"text": "world"})
        assert result.ok
        assert result.content == "echo:world"
    finally:
        if client is not None:
            client.close()
