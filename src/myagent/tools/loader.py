from __future__ import annotations

from pathlib import Path

from myagent.config import MCPServerConfig
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
    servers: tuple[MCPServerConfig, ...],
) -> tuple[list[ToolSpec], list[StdioMCPClient]]:
    tools: list[ToolSpec] = []
    clients: list[StdioMCPClient] = []
    seen_tool_names: set[str] = set()
    for server in servers:
        client = StdioMCPClient(
            command=server.command,
            args=server.args,
            cwd=workspace_dir,
            timeout_seconds=server.timeout_seconds,
        )
        clients.append(client)
        for definition in client.list_tools():
            tool_name = f"mcp__{server.name}__{definition.name}"
            if tool_name in seen_tool_names:
                raise ValueError(f"Duplicate MCP tool name: {tool_name}")
            seen_tool_names.add(tool_name)
            tools.append(
                ToolSpec(
                    name=tool_name,
                    description=f"[MCP:{server.name}] {definition.description}",
                    parameters=definition.input_schema,
                    handler=lambda arguments, *, client=client, tool_name=definition.name: client.call_tool(
                        tool_name, arguments
                    ),
                )
            )
    return tools, clients
