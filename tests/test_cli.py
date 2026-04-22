from pathlib import Path

import pytest

from myagent.cli import build_kernel
from myagent.config import MCPServerConfig, Settings


def test_build_kernel_rejects_missing_openai_key() -> None:
    settings = Settings(
        provider="openai",
        model="gpt-4.1-mini",
        openai_api_key=None,
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY is missing"):
        build_kernel(settings)


def test_build_kernel_rejects_unknown_provider() -> None:
    settings = Settings(
        provider="unknown",
        model="gpt-4.1-mini",
        openai_api_key=None,
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )

    with pytest.raises(ValueError, match="Unsupported provider"):
        build_kernel(settings)


def test_settings_validate_rejects_unknown_api_mode() -> None:
    settings = Settings(
        provider="openai",
        model="gpt-4.1-mini",
        openai_api_key="test-key",
        openai_api_mode="bad-mode",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )

    with pytest.raises(ValueError, match="Unsupported OpenAI API mode"):
        settings.validate()


def test_settings_validate_rejects_invalid_base_url() -> None:
    settings = Settings(
        provider="openai",
        model="gpt-4.1-mini",
        openai_api_key="test-key",
        openai_base_url="example.com/v1",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )

    with pytest.raises(ValueError, match="must start with http:// or https://"):
        settings.validate()


def test_settings_validate_rejects_empty_builtin_tool_set() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        enabled_builtin_tools=(),
    )

    with pytest.raises(ValueError, match="must enable at least one builtin tool"):
        settings.validate()


def test_settings_validate_requires_mcp_command_when_enabled() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        mcp_enabled=True,
        mcp_command=None,
    )

    with pytest.raises(ValueError, match="MYAGENT_MCP_COMMAND is required"):
        settings.validate()


def test_build_kernel_passes_openai_base_url() -> None:
    settings = Settings(
        provider="openai",
        model="gpt-4.1-mini",
        openai_api_key="test-key",
        openai_base_url="https://example.com/v1",
        openai_api_mode="chat",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )
    settings.validate()

    kernel = build_kernel(settings)

    assert kernel.provider.base_url == "https://example.com/v1"
    assert kernel.provider.api_mode == "chat"


def test_build_kernel_respects_enabled_builtin_tools() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        enabled_builtin_tools=("list_dir",),
    )
    settings.validate()

    kernel = build_kernel(settings)

    described = kernel.tools.describe()
    assert [tool["name"] for tool in described] == ["list_dir"]


def test_build_kernel_loads_mcp_tools_when_enabled() -> None:
    fixture = Path("tests") / "fixtures" / "fake_mcp_server.py"
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        enabled_builtin_tools=("list_dir",),
        mcp_enabled=True,
        mcp_command="python",
        mcp_args=(str(fixture),),
    )
    settings.validate()

    kernel = build_kernel(settings)
    try:
        described = kernel.tools.describe()
        names = [tool["name"] for tool in described]
        assert "list_dir" in names
        assert "mcp__default__echo" in names
    finally:
        kernel.close()


def test_settings_validate_supports_multiple_mcp_servers() -> None:
    fixture = Path("tests") / "fixtures" / "fake_mcp_server.py"
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        mcp_servers=(
            MCPServerConfig(name="repo", command="python", args=(str(fixture),), timeout_seconds=20),
            MCPServerConfig(name="browser", command="python", args=(str(fixture),), timeout_seconds=10),
        ),
    )

    settings.validate()
    resolved = settings.resolved_mcp_servers()

    assert [server.name for server in resolved] == ["repo", "browser"]


def test_settings_validate_rejects_duplicate_mcp_server_names() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        mcp_servers=(
            MCPServerConfig(name="dup", command="python"),
            MCPServerConfig(name="dup", command="python"),
        ),
    )

    with pytest.raises(ValueError, match="Duplicate MCP server name"):
        settings.validate()


def test_settings_from_env_parses_mcp_servers_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYAGENT_PROVIDER", "mock")
    monkeypatch.setenv("MYAGENT_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv(
        "MYAGENT_MCP_SERVERS",
        '[{"name":"repo","command":"python","args":["tests/fixtures/fake_mcp_server.py"],"timeout_seconds":15}]',
    )

    settings = Settings.from_env()

    assert settings.mcp_servers == (
        MCPServerConfig(
            name="repo",
            command="python",
            args=("tests/fixtures/fake_mcp_server.py",),
            timeout_seconds=15.0,
        ),
    )


def test_build_kernel_loads_multiple_mcp_servers() -> None:
    fixture = Path("tests") / "fixtures" / "fake_mcp_server.py"
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
        enabled_builtin_tools=("list_dir",),
        mcp_servers=(
            MCPServerConfig(name="repo", command="python", args=(str(fixture),)),
            MCPServerConfig(name="browser", command="python", args=(str(fixture),)),
        ),
    )
    settings.validate()

    kernel = build_kernel(settings)
    try:
        described = kernel.tools.describe()
        names = [tool["name"] for tool in described]
        assert "list_dir" in names
        assert "mcp__repo__echo" in names
        assert "mcp__browser__echo" in names
    finally:
        kernel.close()


def test_build_kernel_initializes_skill_registry() -> None:
    settings = Settings(
        provider="mock",
        model="gpt-4.1-mini",
        data_dir=Path(".data"),
        workspace_dir=Path.cwd(),
    )
    settings.validate()

    kernel = build_kernel(settings)

    assert kernel.skills is not None
    assert "repo_explainer" in kernel.skills.names()


def test_settings_from_env_parses_skill_dirs(monkeypatch: pytest.MonkeyPatch) -> None:
    skill_root = Path(".data") / "test-skill-dirs"
    skill_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MYAGENT_PROVIDER", "mock")
    monkeypatch.setenv("MYAGENT_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("MYAGENT_SKILL_DIRS", str(skill_root))

    settings = Settings.from_env()

    assert settings.skill_dirs == (skill_root.resolve(),)


def test_build_kernel_logs_skill_conflicts() -> None:
    root = Path(".data") / "test-skill-conflict-log"
    skill_dir = Path.cwd() / ".myagent" / "skills" / "repo_explainer"
    skill_dir.mkdir(parents=True, exist_ok=True)
    try:
        (skill_dir / "SKILL.md").write_text(
            """---
name: repo_explainer
description: Override repo explainer.
---

Override.
""",
            encoding="utf-8",
        )
        settings = Settings(
            provider="mock",
            model="gpt-4.1-mini",
            data_dir=root,
            workspace_dir=Path.cwd(),
        )
        settings.validate()

        kernel = build_kernel(settings)
        kernel.close()

        log_text = (root / "logs" / "system.jsonl").read_text(encoding="utf-8")
        assert '"event": "skill_conflict"' in log_text
    finally:
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skill_file.unlink()
        if skill_dir.exists():
            skill_dir.rmdir()
        skills_root = skill_dir.parent
        if skills_root.exists() and not any(skills_root.iterdir()):
            skills_root.rmdir()
        myagent_root = skills_root.parent
        if myagent_root.exists() and not any(myagent_root.iterdir()):
            myagent_root.rmdir()
