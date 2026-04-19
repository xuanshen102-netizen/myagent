from __future__ import annotations

import json
from pathlib import Path

from myagent.providers.base import Message


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self, session_id: str) -> list[Message]:
        path = self._path_for(session_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Message.from_dict(item) for item in data]

    def save(self, session_id: str, messages: list[Message]) -> None:
        path = self._path_for(session_id)
        payload = [message.to_dict() for message in messages]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _path_for(self, session_id: str) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in session_id)
        return self.root / f"{safe_name}.json"

