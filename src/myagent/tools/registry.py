from __future__ import annotations

from myagent.providers.base import ToolResult
from myagent.tools.base import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def describe(self) -> list[dict[str, object]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, object]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failure(
                f"Unknown tool: {name}",
                error_type="unknown_tool",
                metadata={"tool_name": name},
            )
        try:
            return tool.handler(arguments)
        except Exception as exc:
            return ToolResult.failure(
                f"Tool execution failed for {name}: {exc}",
                error_type="execution_exception",
                metadata={"tool_name": name},
            )
