from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class ToolResult:
    status: Literal["ok", "error"]
    content: str
    structured_content: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @classmethod
    def success(
        cls,
        content: str,
        *,
        structured_content: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            status="ok",
            content=content,
            structured_content=structured_content,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        content: str,
        *,
        error_type: str,
        structured_content: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            status="error",
            content=content,
            structured_content=structured_content,
            metadata=metadata or {},
            error_type=error_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "structured_content": self.structured_content,
            "metadata": self.metadata,
            "error_type": self.error_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolResult":
        return cls(
            status=data["status"],
            content=data.get("content", ""),
            structured_content=data.get("structured_content"),
            metadata=data.get("metadata", {}),
            error_type=data.get("error_type"),
        )


@dataclass(slots=True)
class ProviderError:
    error_type: str
    message: str
    retryable: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "retryable": self.retryable,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderError":
        return cls(
            error_type=data["error_type"],
            message=data["message"],
            retryable=bool(data.get("retryable", False)),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class Message:
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result: ToolResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "name": self.name,
            "tool_call_id": self.tool_call_id,
            "tool_calls": [asdict(item) for item in self.tool_calls],
            "tool_result": self.tool_result.to_dict() if self.tool_result else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data.get("content", ""),
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=[ToolCall(**item) for item in data.get("tool_calls", [])],
            tool_result=(
                ToolResult.from_dict(data["tool_result"])
                if data.get("tool_result") is not None
                else None
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_error: ProviderError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        raise NotImplementedError

