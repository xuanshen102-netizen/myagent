from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from myagent.config import Settings
from myagent.providers.base import Message
from myagent.providers.openai_provider import OpenAIProvider
from myagent.tools.builtin import build_builtin_tools
from myagent.tools.registry import ToolRegistry


def to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_data(item) for key, item in value.items()}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    namespace_dict = getattr(value, "__dict__", None)
    if isinstance(namespace_dict, dict):
        return {key: to_plain_data(item) for key, item in namespace_dict.items()}
    return repr(value)


def print_section(title: str, payload: Any) -> None:
    print(f"===== {title} =====")
    if isinstance(payload, str):
        print(payload)
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    settings = Settings.from_env()
    if settings.provider != "openai":
        raise SystemExit("MYAGENT_PROVIDER must be set to 'openai' for this debug script.")
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is missing.")

    registry = ToolRegistry()
    for tool in build_builtin_tools(settings.workspace_dir):
        registry.register(tool)

    provider = OpenAIProvider(
        model=settings.model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        api_mode=settings.openai_api_mode,
    )
    messages = [
        Message(role="system", content="You are a local assistant. Inspect the workspace when useful."),
        Message(role="user", content="列出当前目录并说明项目结构"),
    ]

    print(f"provider={settings.provider}")
    print(f"model={settings.model}")
    print(f"base_url={settings.openai_base_url!r}")
    print(f"api_mode={settings.openai_api_mode}")

    if settings.openai_api_mode == "responses":
        raw = provider.client.responses.create(
            model=settings.model,
            input=provider._build_input(messages),
            tools=provider._build_tools(registry.describe()),
        )
    elif settings.openai_api_mode == "chat":
        raw = provider.client.chat.completions.create(
            model=settings.model,
            messages=provider._build_chat_messages(messages),
            tools=provider._build_chat_tools(registry.describe()),
        )
    else:
        raise SystemExit(f"Unsupported MYAGENT_OPENAI_API_MODE: {settings.openai_api_mode}")

    plain = to_plain_data(raw)
    dump_path = Path(".data") / "debug-openai-response.json"
    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        json.dumps(plain, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_section("Response Type", type(raw).__name__)
    print_section("Raw Response", plain)
    print(f"Saved raw response to {dump_path}")


if __name__ == "__main__":
    main()
