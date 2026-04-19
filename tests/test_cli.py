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

    kernel = build_kernel(settings)

    assert kernel.provider.base_url == "https://example.com/v1"
    assert kernel.provider.api_mode == "chat"
