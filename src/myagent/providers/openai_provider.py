from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from myagent.providers.base import BaseProvider, Message, ModelResponse, ProviderError
from myagent.providers.base import ToolCall


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        api_key: str | None,
        base_url: str | None = None,
        api_mode: str = "responses",
        debug_dir: Path | None = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        super().__init__(model=model)
        self.api_key = api_key
        self.base_url = base_url
        self.api_mode = api_mode
        self.debug_dir = debug_dir
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        attempts = 0
        started_at = time.perf_counter()
        while True:
            attempts += 1
            try:
                response = self._perform_request(messages, tools)
                response.metadata.setdefault("attempts", attempts)
                response.metadata.setdefault(
                    "provider_latency_ms",
                    round((time.perf_counter() - started_at) * 1000, 3),
                )
                response.metadata.setdefault("api_mode", self.api_mode)
                return response
            except Exception as exc:
                provider_error = self._map_exception(exc, attempts)
                if provider_error.retryable and attempts <= self.max_retries:
                    time.sleep(self.retry_backoff_seconds * attempts)
                    continue
                return ModelResponse(
                    text=provider_error.message,
                    provider_error=provider_error,
                    metadata={
                        "attempts": attempts,
                        "provider_latency_ms": round((time.perf_counter() - started_at) * 1000, 3),
                        "api_mode": self.api_mode,
                    },
                )

    def _perform_request(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        if self.api_mode == "responses":
            response = self.client.responses.create(
                model=self.model,
                input=self._build_input(messages),
                tools=self._build_tools(tools),
            )
            self._write_debug_dump("responses", response)
            return self._parse_response(response)

        if self.api_mode == "chat":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_chat_messages(messages),
                tools=self._build_chat_tools(tools),
            )
            self._write_debug_dump("chat", response)
            return self._parse_chat_response(response)

        raise ValueError(f"Unsupported OpenAI API mode: {self.api_mode}")

    def _map_exception(self, exc: Exception, attempts: int) -> ProviderError:
        if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
            return ProviderError(
                error_type="authentication_error",
                message=(
                    "Authentication failed for the configured API provider. "
                    "Check OPENAI_API_KEY and provider account permissions."
                ),
                retryable=False,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, RateLimitError):
            return ProviderError(
                error_type="rate_limit",
                message=(
                    "The API request was rate-limited or rejected for quota reasons. "
                    "Check provider quota, billing, or retry later."
                ),
                retryable=True,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, (BadRequestError, UnprocessableEntityError)):
            return ProviderError(
                error_type="invalid_request",
                message=f"The API rejected the request as invalid: {exc}",
                retryable=False,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, NotFoundError):
            return ProviderError(
                error_type="not_found",
                message=(
                    f"The configured model or endpoint was not found: {exc}. "
                    "Check MYAGENT_MODEL and MYAGENT_OPENAI_BASE_URL."
                ),
                retryable=False,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, (APIConnectionError, APITimeoutError)):
            return ProviderError(
                error_type="connection_error",
                message=(
                    "The API request could not reach the provider or timed out. "
                    "Check network access and MYAGENT_OPENAI_BASE_URL."
                ),
                retryable=True,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, APIStatusError):
            return ProviderError(
                error_type="api_status_error",
                message=f"The provider returned an API error: {exc}",
                retryable=False,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, json.JSONDecodeError):
            return ProviderError(
                error_type="invalid_tool_arguments",
                message=(
                    "The model returned tool arguments that were not valid JSON. "
                    f"Raw parser error: {exc}"
                ),
                retryable=False,
                metadata={"attempts": attempts},
            )
        if isinstance(exc, ValueError):
            return ProviderError(
                error_type="configuration_error",
                message=str(exc),
                retryable=False,
                metadata={"attempts": attempts},
            )
        return ProviderError(
            error_type="unknown_provider_error",
            message=f"Unexpected provider error: {exc}",
            retryable=False,
            metadata={"attempts": attempts},
        )

    def _build_input(self, messages: list[Message]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "tool":
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id,
                        "output": message.content,
                    }
                )
                continue

            if message.role == "assistant" and message.content:
                items.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "input_text", "text": message.content}],
                    }
                )

            if message.role == "assistant":
                for tool_call in message.tool_calls:
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": tool_call.id,
                            "name": tool_call.name,
                            "arguments": json.dumps(tool_call.arguments),
                        }
                    )
                continue

            items.append(
                {
                    "role": message.role,
                    "content": [{"type": "input_text", "text": message.content}],
                }
            )

        return items

    def _build_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
                "strict": False,
            }
            for tool in tools
        ]

    def _build_chat_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "assistant":
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content,
                }
                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments),
                            },
                        }
                        for tool_call in message.tool_calls
                    ]
                items.append(assistant_message)
                continue

            if message.role == "tool":
                items.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.tool_call_id,
                        "content": message.content,
                    }
                )
                continue

            items.append({"role": message.role, "content": message.content})

        return items

    def _build_chat_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

    def _parse_response(self, response: Any) -> ModelResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for item in getattr(response, "output", []):
            item_type = getattr(item, "type", None)
            if item_type == "message":
                text = getattr(item, "text", None)
                if text:
                    text_parts.append(text)
                    continue

                for content in getattr(item, "content", []):
                    if getattr(content, "type", None) == "output_text":
                        text_value = getattr(content, "text", "")
                        if text_value:
                            text_parts.append(text_value)
            elif item_type == "function_call":
                raw_arguments = getattr(item, "arguments", "{}") or "{}"
                tool_calls.append(
                    ToolCall(
                        id=getattr(item, "call_id"),
                        name=getattr(item, "name"),
                        arguments=json.loads(raw_arguments),
                    )
                )

        output_text = getattr(response, "output_text", "")
        if output_text and not text_parts:
            text_parts.append(output_text)

        if not text_parts:
            text_parts.extend(self._extract_text_fallback(response))

        final_text = "\n".join(part for part in text_parts if part).strip()
        if not final_text and not tool_calls:
            final_text = (
                "The API call succeeded but returned no assistant text or tool calls. "
                "This usually means the configured model/base_url is not fully compatible "
                "with the Responses API format expected by this project."
            )

        return ModelResponse(
            text=final_text,
            tool_calls=tool_calls,
            metadata={},
        )

    def _parse_chat_response(self, response: Any) -> ModelResponse:
        if isinstance(response, str):
            return ModelResponse(
                text=(
                    "The API returned a raw string instead of a standard chat completion object. "
                    "This usually means the configured base_url is only partially OpenAI-compatible. "
                    "Run scripts/debug_openai_compat.py to inspect the raw payload."
                )
            )

        if not hasattr(response, "choices"):
            payload = self._to_plain_data(response)
            return ModelResponse(
                text=(
                    "The API returned a nonstandard chat response object without 'choices'. "
                    f"Raw payload preview: {json.dumps(payload, ensure_ascii=False)[:500]}"
                )
            )

        choice = response.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        for tool_call in getattr(message, "tool_calls", []) or []:
            raw_arguments = getattr(tool_call.function, "arguments", "{}") or "{}"
            tool_calls.append(
                ToolCall(
                    id=getattr(tool_call, "id"),
                    name=getattr(tool_call.function, "name"),
                    arguments=json.loads(raw_arguments),
                )
            )

        text = getattr(message, "content", "") or ""
        final_text = text.strip()
        if not final_text and not tool_calls:
            final_text = (
                "The API call succeeded but returned no assistant text or tool calls. "
                "This usually means the configured model/base_url is not fully compatible "
                "with the selected API mode."
            )

        return ModelResponse(text=final_text, tool_calls=tool_calls, metadata={})

    def _extract_text_fallback(self, response: Any) -> list[str]:
        payload = self._to_plain_data(response)
        if payload is None:
            return []

        parts: list[str] = []
        self._collect_text_fragments(payload, parts)
        return parts

    def _to_plain_data(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [self._to_plain_data(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_plain_data(item) for key, item in value.items()}
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        namespace_dict = getattr(value, "__dict__", None)
        if isinstance(namespace_dict, dict):
            return {key: self._to_plain_data(item) for key, item in namespace_dict.items()}
        return None

    def _collect_text_fragments(self, value: Any, parts: list[str]) -> None:
        if isinstance(value, str):
            return

        if isinstance(value, list):
            for item in value:
                self._collect_text_fragments(item, parts)
            return

        if not isinstance(value, dict):
            return

        item_type = value.get("type")
        text_value = value.get("text")
        if item_type in {"output_text", "text"} and isinstance(text_value, str) and text_value.strip():
            parts.append(text_value.strip())

        output_text = value.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            parts.append(output_text.strip())

        message_content = value.get("content")
        if isinstance(message_content, str) and value.get("role") == "assistant" and message_content.strip():
            parts.append(message_content.strip())

        for nested in value.values():
            self._collect_text_fragments(nested, parts)

    def _write_debug_dump(self, label: str, response: Any) -> None:
        if self.debug_dir is None:
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        path = self.debug_dir / f"{label}-last.json"
        payload = self._to_plain_data(response)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
