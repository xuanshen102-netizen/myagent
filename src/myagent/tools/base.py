from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from myagent.providers.base import ToolResult

ToolHandler = Callable[[dict[str, Any]], ToolResult]


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

