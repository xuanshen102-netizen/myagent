import json
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

import httpx

from myagent.providers.base import Message, ToolCall
from myagent.providers.openai_provider import OpenAIProvider
from openai import APIConnectionError


def test_build_input_maps_messages_and_tool_outputs() -> None:
    provider = object.__new__(OpenAIProvider)
    messages = [
        Message(role="user", content="read README"),
        Message(
            role="assistant",
            content="I will inspect the file.",
            tool_calls=[ToolCall(id="call_1", name="read_file", arguments={"path": "README.md"})],
        ),
        Message(role="tool", content="file content", name="read_file", tool_call_id="call_1"),
    ]

    items = provider._build_input(messages)

    assert items[0] == {
        "role": "user",
        "content": [{"type": "input_text", "text": "read README"}],
    }
    assert items[1] == {
        "role": "assistant",
        "content": [{"type": "input_text", "text": "I will inspect the file."}],
    }
    assert items[2] == {
        "type": "function_call",
        "call_id": "call_1",
        "name": "read_file",
        "arguments": json.dumps({"path": "README.md"}),
    }
    assert items[3] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": "file content",
    }


def test_parse_response_extracts_text_and_tool_calls() -> None:
    provider = object.__new__(OpenAIProvider)
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text="Need a tool first.")],
            ),
            SimpleNamespace(
                type="function_call",
                call_id="call_1",
                name="list_dir",
                arguments='{"path":"."}',
            ),
        ],
        output_text="",
    )

    parsed = provider._parse_response(response)

    assert parsed.text == "Need a tool first."
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0].id == "call_1"
    assert parsed.tool_calls[0].name == "list_dir"
    assert parsed.tool_calls[0].arguments == {"path": "."}


def test_openai_provider_stores_base_url() -> None:
    provider = OpenAIProvider(
        model="gpt-4.1-mini",
        api_key="test-key",
        base_url="https://example.com/v1",
        api_mode="chat",
    )

    assert provider.base_url == "https://example.com/v1"
    assert provider.api_mode == "chat"


def test_openai_provider_writes_debug_dump() -> None:
    debug_dir = Path(".data") / "provider-debug-tests" / str(uuid4())
    provider = OpenAIProvider(
        model="gpt-4.1-mini",
        api_key="test-key",
        debug_dir=debug_dir,
    )

    provider._write_debug_dump("responses", {"hello": "world"})

    payload = (debug_dir / "responses-last.json").read_text(encoding="utf-8")
    assert '"hello": "world"' in payload


def test_parse_response_falls_back_for_compatible_nonstandard_payloads() -> None:
    provider = object.__new__(OpenAIProvider)
    response = SimpleNamespace(
        output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="text", text="Fallback text")])],
        output_text="",
    )

    parsed = provider._parse_response(response)

    assert parsed.text == "Fallback text"


def test_parse_response_returns_diagnostic_when_payload_has_no_text() -> None:
    provider = object.__new__(OpenAIProvider)
    response = SimpleNamespace(output=[], output_text="")

    parsed = provider._parse_response(response)

    assert "returned no assistant text or tool calls" in parsed.text


def test_build_chat_messages_maps_tool_history() -> None:
    provider = object.__new__(OpenAIProvider)
    messages = [
        Message(role="system", content="policy"),
        Message(role="user", content="list files"),
        Message(
            role="assistant",
            content="I will inspect the directory.",
            tool_calls=[ToolCall(id="call_1", name="list_dir", arguments={"path": "."})],
        ),
        Message(role="tool", content="README.md", tool_call_id="call_1"),
    ]

    items = provider._build_chat_messages(messages)

    assert items[0] == {"role": "system", "content": "policy"}
    assert items[1] == {"role": "user", "content": "list files"}
    assert items[2]["role"] == "assistant"
    assert items[2]["tool_calls"][0]["function"]["name"] == "list_dir"
    assert items[3] == {"role": "tool", "tool_call_id": "call_1", "content": "README.md"}


def test_parse_chat_response_extracts_text_and_tool_calls() -> None:
    provider = object.__new__(OpenAIProvider)
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Need a tool first.",
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            function=SimpleNamespace(name="list_dir", arguments='{\"path\":\".\"}'),
                        )
                    ],
                )
            )
        ]
    )

    parsed = provider._parse_chat_response(response)

    assert parsed.text == "Need a tool first."
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0].name == "list_dir"
    assert parsed.tool_calls[0].arguments == {"path": "."}


def test_parse_chat_response_handles_raw_string_payload() -> None:
    provider = object.__new__(OpenAIProvider)

    parsed = provider._parse_chat_response("plain string response")

    assert "returned a raw string" in parsed.text


def test_parse_chat_response_handles_missing_choices_object() -> None:
    provider = object.__new__(OpenAIProvider)

    parsed = provider._parse_chat_response(SimpleNamespace(message="bad shape"))

    assert "without 'choices'" in parsed.text


def test_openai_provider_retries_retryable_errors() -> None:
    provider = object.__new__(OpenAIProvider)
    provider.model = "gpt-4.1-mini"
    provider.api_mode = "responses"
    provider.max_retries = 2
    provider.retry_backoff_seconds = 0
    provider._build_input = lambda messages: messages
    provider._build_tools = lambda tools: tools
    provider._parse_response = lambda response: response
    provider._write_debug_dump = lambda label, response: None

    request = httpx.Request("POST", "https://example.com/v1/responses")
    attempts = {"count": 0}

    class StubResponses:
        def create(self, **kwargs):
            del kwargs
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise APIConnectionError(request=request)
            return provider._parse_response(SimpleNamespace(text="ok", tool_calls=[], metadata={}))

    provider.client = SimpleNamespace(responses=StubResponses())

    result = provider.complete(messages=[], tools=[])

    assert result.text == "ok"
    assert result.metadata["attempts"] == 3


def test_openai_provider_returns_structured_error_after_retry_exhaustion() -> None:
    provider = object.__new__(OpenAIProvider)
    provider.model = "gpt-4.1-mini"
    provider.api_mode = "responses"
    provider.max_retries = 1
    provider.retry_backoff_seconds = 0
    provider._build_input = lambda messages: messages
    provider._build_tools = lambda tools: tools
    provider._write_debug_dump = lambda label, response: None
    request = httpx.Request("POST", "https://example.com/v1/responses")

    class StubResponses:
        def create(self, **kwargs):
            del kwargs
            raise APIConnectionError(request=request)

    provider.client = SimpleNamespace(responses=StubResponses())

    result = provider.complete(messages=[], tools=[])

    assert result.provider_error is not None
    assert result.provider_error.retryable is True
    assert result.provider_error.error_type == "connection_error"
    assert result.metadata["attempts"] == 2
