from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SUPPORTED_PROVIDERS = {"mock", "openai"}
SUPPORTED_OPENAI_API_MODES = {"responses", "chat"}


@dataclass(slots=True, frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: tuple[str, ...] = ()
    timeout_seconds: float = 20.0


@dataclass(slots=True)
class Settings:
    provider: str = "mock"
    model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_api_mode: str = "responses"
    openai_max_retries: int = 2
    openai_retry_backoff_seconds: float = 0.5
    data_dir: Path = Path(".data")
    workspace_dir: Path = Path.cwd()
    system_prompt: str | None = None
    max_tool_failures_per_turn: int = 2
    max_consecutive_tool_errors: int = 2
    max_recent_memory_messages: int = 8
    memory_max_facts: int = 8
    memory_summary_line_limit: int = 6
    memory_refresh_min_messages: int = 2
    memory_prompt_fact_limit: int = 4
    memory_prompt_summary_line_limit: int = 4
    memory_task_step_limit: int = 3
    skill_dirs: tuple[Path, ...] = ()
    enabled_builtin_tools: tuple[str, ...] = ("list_dir", "repo_search", "read_file", "run_command")
    mcp_enabled: bool = False
    mcp_command: str | None = None
    mcp_args: tuple[str, ...] = ()
    mcp_timeout_seconds: float = 20.0
    mcp_servers: tuple[MCPServerConfig, ...] = ()
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    trace_enabled: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        enabled_tools_raw = os.getenv(
            "MYAGENT_ENABLED_BUILTIN_TOOLS",
            "list_dir,repo_search,read_file,run_command",
        )
        mcp_args_raw = os.getenv("MYAGENT_MCP_ARGS", "")
        skill_dirs_raw = os.getenv("MYAGENT_SKILL_DIRS", "")
        settings = cls(
            provider=os.getenv("MYAGENT_PROVIDER", "mock"),
            model=os.getenv("MYAGENT_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("MYAGENT_OPENAI_BASE_URL"),
            openai_api_mode=os.getenv("MYAGENT_OPENAI_API_MODE", "responses"),
            openai_max_retries=int(os.getenv("MYAGENT_OPENAI_MAX_RETRIES", "2")),
            openai_retry_backoff_seconds=float(
                os.getenv("MYAGENT_OPENAI_RETRY_BACKOFF_SECONDS", "0.5")
            ),
            data_dir=Path(os.getenv("MYAGENT_DATA_DIR", ".data")).resolve(),
            workspace_dir=Path.cwd(),
            system_prompt=os.getenv("MYAGENT_SYSTEM_PROMPT"),
            max_tool_failures_per_turn=int(os.getenv("MYAGENT_MAX_TOOL_FAILURES_PER_TURN", "2")),
            max_consecutive_tool_errors=int(os.getenv("MYAGENT_MAX_CONSECUTIVE_TOOL_ERRORS", "2")),
            max_recent_memory_messages=int(os.getenv("MYAGENT_MAX_RECENT_MEMORY_MESSAGES", "8")),
            memory_max_facts=int(os.getenv("MYAGENT_MEMORY_MAX_FACTS", "8")),
            memory_summary_line_limit=int(os.getenv("MYAGENT_MEMORY_SUMMARY_LINE_LIMIT", "6")),
            memory_refresh_min_messages=int(os.getenv("MYAGENT_MEMORY_REFRESH_MIN_MESSAGES", "2")),
            memory_prompt_fact_limit=int(os.getenv("MYAGENT_MEMORY_PROMPT_FACT_LIMIT", "4")),
            memory_prompt_summary_line_limit=int(
                os.getenv("MYAGENT_MEMORY_PROMPT_SUMMARY_LINE_LIMIT", "4")
            ),
            memory_task_step_limit=int(os.getenv("MYAGENT_MEMORY_TASK_STEP_LIMIT", "3")),
            skill_dirs=tuple(
                Path(item.strip()).resolve()
                for item in skill_dirs_raw.split(os.pathsep)
                if item.strip()
            ),
            enabled_builtin_tools=tuple(
                item.strip() for item in enabled_tools_raw.split(",") if item.strip()
            ),
            mcp_enabled=os.getenv("MYAGENT_MCP_ENABLED", "0").strip().lower() in {"1", "true", "yes"},
            mcp_command=os.getenv("MYAGENT_MCP_COMMAND") or None,
            mcp_args=tuple(item.strip() for item in mcp_args_raw.split(",") if item.strip()),
            mcp_timeout_seconds=float(os.getenv("MYAGENT_MCP_TIMEOUT_SECONDS", "20")),
            mcp_servers=cls._parse_mcp_servers(os.getenv("MYAGENT_MCP_SERVERS", "")),
            api_host=os.getenv("MYAGENT_API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("MYAGENT_API_PORT", "8000")),
            trace_enabled=os.getenv("MYAGENT_TRACE_ENABLED", "1").strip().lower() not in {"0", "false", "no"},
        )
        settings.validate()
        return settings

    @staticmethod
    def _parse_mcp_servers(raw: str) -> tuple[MCPServerConfig, ...]:
        raw = raw.strip()
        if not raw:
            return ()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("MYAGENT_MCP_SERVERS must be valid JSON.") from exc
        if not isinstance(payload, list):
            raise ValueError("MYAGENT_MCP_SERVERS must be a JSON array.")

        servers: list[MCPServerConfig] = []
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"MYAGENT_MCP_SERVERS item #{index} must be a JSON object."
                )
            name = str(item.get("name", "")).strip()
            command = str(item.get("command", "")).strip()
            args_raw = item.get("args", [])
            if not isinstance(args_raw, list) or any(not isinstance(arg, str) for arg in args_raw):
                raise ValueError(
                    f"MYAGENT_MCP_SERVERS item #{index} field 'args' must be a string array."
                )
            timeout_raw = item.get("timeout_seconds", 20.0)
            try:
                timeout_seconds = float(timeout_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"MYAGENT_MCP_SERVERS item #{index} field 'timeout_seconds' must be numeric."
                ) from exc
            servers.append(
                MCPServerConfig(
                    name=name,
                    command=command,
                    args=tuple(arg.strip() for arg in args_raw if arg.strip()),
                    timeout_seconds=timeout_seconds,
                )
            )
        return tuple(servers)

    def resolved_mcp_servers(self) -> tuple[MCPServerConfig, ...]:
        if self.mcp_servers:
            return self.mcp_servers
        if not self.mcp_enabled:
            return ()
        return (
            MCPServerConfig(
                name="default",
                command=self.mcp_command or "",
                args=self.mcp_args,
                timeout_seconds=self.mcp_timeout_seconds,
            ),
        )

    def validate(self) -> None:
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
            )
        if self.openai_api_mode not in SUPPORTED_OPENAI_API_MODES:
            raise ValueError(
                f"Unsupported OpenAI API mode: {self.openai_api_mode}. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_OPENAI_API_MODES))}."
            )
        if not self.model.strip():
            raise ValueError("MYAGENT_MODEL must not be empty.")
        if not self.workspace_dir.exists():
            raise ValueError(f"Workspace directory does not exist: {self.workspace_dir}")
        if not self.workspace_dir.is_dir():
            raise ValueError(f"Workspace path is not a directory: {self.workspace_dir}")
        if self.openai_max_retries < 0:
            raise ValueError("MYAGENT_OPENAI_MAX_RETRIES must be >= 0.")
        if self.openai_retry_backoff_seconds < 0:
            raise ValueError("MYAGENT_OPENAI_RETRY_BACKOFF_SECONDS must be >= 0.")
        if self.max_tool_failures_per_turn < 1:
            raise ValueError("MYAGENT_MAX_TOOL_FAILURES_PER_TURN must be >= 1.")
        if self.max_consecutive_tool_errors < 1:
            raise ValueError("MYAGENT_MAX_CONSECUTIVE_TOOL_ERRORS must be >= 1.")
        if self.max_recent_memory_messages < 1:
            raise ValueError("MYAGENT_MAX_RECENT_MEMORY_MESSAGES must be >= 1.")
        if self.memory_max_facts < 1:
            raise ValueError("MYAGENT_MEMORY_MAX_FACTS must be >= 1.")
        if self.memory_summary_line_limit < 1:
            raise ValueError("MYAGENT_MEMORY_SUMMARY_LINE_LIMIT must be >= 1.")
        if self.memory_refresh_min_messages < 1:
            raise ValueError("MYAGENT_MEMORY_REFRESH_MIN_MESSAGES must be >= 1.")
        if self.memory_prompt_fact_limit < 1:
            raise ValueError("MYAGENT_MEMORY_PROMPT_FACT_LIMIT must be >= 1.")
        if self.memory_prompt_summary_line_limit < 1:
            raise ValueError("MYAGENT_MEMORY_PROMPT_SUMMARY_LINE_LIMIT must be >= 1.")
        if self.memory_task_step_limit < 1:
            raise ValueError("MYAGENT_MEMORY_TASK_STEP_LIMIT must be >= 1.")
        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                raise ValueError(f"Skill directory does not exist: {skill_dir}")
            if not skill_dir.is_dir():
                raise ValueError(f"Skill path is not a directory: {skill_dir}")
        if not self.enabled_builtin_tools:
            raise ValueError("MYAGENT_ENABLED_BUILTIN_TOOLS must enable at least one builtin tool.")
        if self.mcp_timeout_seconds <= 0:
            raise ValueError("MYAGENT_MCP_TIMEOUT_SECONDS must be > 0.")
        if self.mcp_enabled and not self.mcp_servers and not self.mcp_command:
            raise ValueError("MYAGENT_MCP_COMMAND is required when MYAGENT_MCP_ENABLED is enabled.")
        resolved_mcp_servers = self.resolved_mcp_servers()
        seen_server_names: set[str] = set()
        for server in resolved_mcp_servers:
            if not server.name.strip():
                raise ValueError("Each MCP server must have a non-empty name.")
            if server.name in seen_server_names:
                raise ValueError(f"Duplicate MCP server name: {server.name}")
            seen_server_names.add(server.name)
            if not server.command.strip():
                raise ValueError(f"MCP server '{server.name}' must define a command.")
            if server.timeout_seconds <= 0:
                raise ValueError(
                    f"MCP server '{server.name}' timeout_seconds must be > 0."
                )
        if not self.api_host.strip():
            raise ValueError("MYAGENT_API_HOST must not be empty.")
        if not (0 <= self.api_port <= 65535):
            raise ValueError("MYAGENT_API_PORT must be between 0 and 65535.")
        if self.provider == "openai" and self.openai_base_url:
            normalized = self.openai_base_url.strip()
            if not normalized.startswith(("http://", "https://")):
                raise ValueError(
                    "MYAGENT_OPENAI_BASE_URL must start with http:// or https:// when provided."
                )
