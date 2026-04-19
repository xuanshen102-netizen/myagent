from pathlib import Path

import pytest

from myagent.cli import build_kernel
from myagent.config import Settings


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
        assert "mcp__echo" in names
    finally:
        kernel.close()
