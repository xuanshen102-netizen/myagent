from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    provider: str = "mock"
    model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_api_mode: str = "responses"
    data_dir: Path = Path(".data")
    workspace_dir: Path = Path.cwd()
    system_prompt: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            provider=os.getenv("MYAGENT_PROVIDER", "mock"),
            model=os.getenv("MYAGENT_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("MYAGENT_OPENAI_BASE_URL"),
            openai_api_mode=os.getenv("MYAGENT_OPENAI_API_MODE", "responses"),
            data_dir=Path(os.getenv("MYAGENT_DATA_DIR", ".data")),
            workspace_dir=Path.cwd(),
            system_prompt=os.getenv("MYAGENT_SYSTEM_PROMPT"),
        )
