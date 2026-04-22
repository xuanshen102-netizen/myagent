from __future__ import annotations

import argparse
from pathlib import Path

from myagent.agent.loop import AgentKernel
from myagent.config import Settings
from myagent.memory import MemoryManager, MemoryStore
from myagent.observability import EventLogger
from myagent.providers.mock_provider import MockProvider
from myagent.providers.openai_provider import OpenAIProvider
from myagent.prompts import DEFAULT_SYSTEM_PROMPT
from myagent.session.store import SessionStore
from myagent.skills import SkillRegistry
from myagent.skills.loader import discover_skills_with_conflicts
from myagent.tools import ToolRegistry, load_builtin_tools
from myagent.tools.loader import load_mcp_tools


def build_kernel(settings: Settings) -> AgentKernel:
    registry = ToolRegistry()
    for tool in load_builtin_tools(settings.workspace_dir, settings.enabled_builtin_tools):
        registry.register(tool)
    mcp_clients = []
    mcp_servers = settings.resolved_mcp_servers()
    if mcp_servers:
        mcp_tools, mcp_clients = load_mcp_tools(settings.workspace_dir, servers=mcp_servers)
        for tool in mcp_tools:
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
            max_retries=settings.openai_max_retries,
            retry_backoff_seconds=settings.openai_retry_backoff_seconds,
        )
    elif settings.provider == "mock":
        provider = MockProvider(model=settings.model)
    else:
        raise ValueError(f"Unsupported provider: {settings.provider}")

    store = SessionStore(settings.data_dir / "sessions")
    builtin_skill_root = Path(__file__).resolve().parent / "builtin_skills"
    project_skill_root = settings.workspace_dir / ".myagent" / "skills"
    user_skill_roots = settings.skill_dirs
    skill_discovery = discover_skills_with_conflicts(
        builtin_root=builtin_skill_root,
        project_root=project_skill_root,
        user_roots=user_skill_roots,
    )
    skills = SkillRegistry(skill_discovery.manifests)
    memory = MemoryManager(
        MemoryStore(settings.data_dir / "memory"),
        max_recent_messages=settings.max_recent_memory_messages,
        max_facts=settings.memory_max_facts,
        summary_line_limit=settings.memory_summary_line_limit,
        refresh_min_messages=settings.memory_refresh_min_messages,
        prompt_fact_limit=settings.memory_prompt_fact_limit,
        prompt_summary_line_limit=settings.memory_prompt_summary_line_limit,
        task_step_limit=settings.memory_task_step_limit,
    )
    logger = EventLogger(settings.data_dir / "logs") if settings.trace_enabled else None
    if logger is not None:
        for conflict in skill_discovery.conflicts:
            logger.log(
                session_id="system",
                event_type="skill_conflict",
                payload={
                    "skill_name": conflict.name,
                    "replaced_source": conflict.replaced_source,
                    "replacing_source": conflict.replacing_source,
                    "replaced_type": conflict.replaced_type,
                    "replacing_type": conflict.replacing_type,
                },
            )
    return AgentKernel(
        provider=provider,
        tools=registry,
        sessions=store,
        system_prompt=settings.system_prompt or DEFAULT_SYSTEM_PROMPT,
        memory=memory,
        logger=logger,
        skills=skills,
        max_tool_failures_per_turn=settings.max_tool_failures_per_turn,
        max_consecutive_tool_errors=settings.max_consecutive_tool_errors,
        shutdown_callbacks=[client.close for client in mcp_clients],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal agent CLI scaffold.")
    parser.add_argument("prompt", nargs="?", help="One-shot user prompt.")
    parser.add_argument(
        "--session",
        default="default",
        help="Session identifier used for persistence.",
    )
    parser.add_argument(
        "--skill",
        help="Optional skill name, such as repo_explainer, code_debugger, or feature_implementer.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    try:
        kernel = build_kernel(settings)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        if args.prompt:
            print(kernel.run_once(session_id=args.session, user_text=args.prompt, skill_name=args.skill))
            return

        print("myagent interactive mode. Type 'exit' to quit.")
        while True:
            user_text = input("> ").strip()
            if user_text.lower() in {"exit", "quit"}:
                break
            if not user_text:
                continue
            print(kernel.run_once(session_id=args.session, user_text=user_text, skill_name=args.skill))
    finally:
        kernel.close()


if __name__ == "__main__":
    main()
