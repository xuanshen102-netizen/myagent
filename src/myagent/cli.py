from __future__ import annotations

import argparse

from myagent.agent.loop import AgentKernel
from myagent.config import Settings
from myagent.observability import EventLogger
from myagent.providers.mock_provider import MockProvider
from myagent.providers.openai_provider import OpenAIProvider
from myagent.prompts import DEFAULT_SYSTEM_PROMPT
from myagent.session.store import SessionStore
from myagent.tools.builtin import build_builtin_tools
from myagent.tools.registry import ToolRegistry


def build_kernel(settings: Settings) -> AgentKernel:
    registry = ToolRegistry()
    for tool in build_builtin_tools(settings.workspace_dir):
        registry.register(tool)

    if settings.provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "MYAGENT_PROVIDER is set to 'openai' but OPENAI_API_KEY is missing."
            )
        provider = OpenAIProvider(
            model=settings.model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            api_mode=settings.openai_api_mode,
            debug_dir=settings.data_dir / "provider-debug",
        )
    elif settings.provider == "mock":
        provider = MockProvider(model=settings.model)
    else:
        raise ValueError(f"Unsupported provider: {settings.provider}")

    store = SessionStore(settings.data_dir / "sessions")
    return AgentKernel(
        provider=provider,
        tools=registry,
        sessions=store,
        system_prompt=settings.system_prompt or DEFAULT_SYSTEM_PROMPT,
        logger=EventLogger(settings.data_dir / "logs"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal agent CLI scaffold.")
    parser.add_argument("prompt", nargs="?", help="One-shot user prompt.")
    parser.add_argument(
        "--session",
        default="default",
        help="Session identifier used for persistence.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    try:
        kernel = build_kernel(settings)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.prompt:
        print(kernel.run_once(session_id=args.session, user_text=args.prompt))
        return

    print("myagent interactive mode. Type 'exit' to quit.")
    while True:
        user_text = input("> ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            continue
        print(kernel.run_once(session_id=args.session, user_text=user_text))


if __name__ == "__main__":
    main()
