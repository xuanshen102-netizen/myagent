from __future__ import annotations

from pathlib import Path

from myagent.mcp import StdioMCPClient
from myagent.tools.base import ToolSpec
from myagent.tools.builtin import build_builtin_tools


def load_builtin_tools(workspace_dir: Path, enabled_tools: tuple[str, ...]) -> list[ToolSpec]:
    enabled = set(enabled_tools)
    tools = []
    for tool in build_builtin_tools(workspace_dir):
        if tool.name in enabled:
            tools.append(tool)
    return tools


def load_mcp_tools(
    workspace_dir: Path,
    *,
    command: str | None,
    args: tuple[str, ...],
    timeout_seconds: float,
) -> tuple[list[ToolSpec], StdioMCPClient | None]:
    if not command:
        return [], None

    client = StdioMCPClient(
        command=command,
        args=args,
        cwd=workspace_dir,
        timeout_seconds=timeout_seconds,
    )
    tools: list[ToolSpec] = []
    for definition in client.list_tools():
        tool_name = f"mcp__{definition.name}"
        tools.append(
            ToolSpec(
                name=tool_name,
                description=f"[MCP] {definition.description}",
                parameters=definition.input_schema,
                handler=lambda arguments, *, tool_name=definition.name: client.call_tool(tool_name, arguments),
            )
        )
    return tools, client
