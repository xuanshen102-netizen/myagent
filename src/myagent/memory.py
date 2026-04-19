from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from myagent.providers.base import Message


@dataclass(slots=True)
class MemorySnapshot:
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    message_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "facts": self.facts,
            "message_count": self.message_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MemorySnapshot":
        return cls(
            summary=str(data.get("summary", "")),
            facts=[str(item) for item in data.get("facts", [])],
            message_count=int(data.get("message_count", 0)),
        )


class MemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self, session_id: str) -> MemorySnapshot:
        path = self._path_for(session_id)
        if not path.exists():
            return MemorySnapshot()
        data = json.loads(path.read_text(encoding="utf-8"))
        return MemorySnapshot.from_dict(data)

    def save(self, session_id: str, snapshot: MemorySnapshot) -> None:
        path = self._path_for(session_id)
        path.write_text(
            json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _path_for(self, session_id: str) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in session_id)
        return self.root / f"{safe_name}.json"


class MemoryManager:
    def __init__(
        self,
        store: MemoryStore,
        max_recent_messages: int = 8,
        *,
        max_facts: int = 8,
        summary_line_limit: int = 6,
        refresh_min_messages: int = 2,
    ) -> None:
        self.store = store
        self.max_recent_messages = max_recent_messages
        self.max_facts = max_facts
        self.summary_line_limit = summary_line_limit
        self.refresh_min_messages = refresh_min_messages

    def build_memory_prompt(self, session_id: str) -> str | None:
        snapshot = self.store.load(session_id)
        if not snapshot.summary and not snapshot.facts:
            return None

        parts: list[str] = []
        if snapshot.summary:
            parts.append(f"Conversation summary:\n{snapshot.summary}")
        if snapshot.facts:
            selected_facts = self._select_facts_for_prompt(snapshot.facts)
            if selected_facts:
                parts.append("Important facts:\n" + "\n".join(f"- {fact}" for fact in selected_facts))
        return "\n\n".join(parts)

    def update(self, session_id: str, messages: list[Message]) -> MemorySnapshot:
        snapshot = self.store.load(session_id)
        conversational = [message for message in messages if message.role in {"user", "assistant"}]
        if len(conversational) < self.refresh_min_messages:
            return snapshot
        recent = conversational[-self.max_recent_messages :]
        summary_lines = [
            f"{message.role}: {message.content.strip()}"
            for message in recent
            if message.content.strip()
        ]
        facts = self._dedupe_facts(self._extract_facts(conversational))
        updated = MemorySnapshot(
            summary="\n".join(summary_lines[-self.summary_line_limit :]),
            facts=facts[-self.max_facts :],
            message_count=len(conversational),
        )
        if (
            updated.summary != snapshot.summary
            or updated.facts != snapshot.facts
            or updated.message_count != snapshot.message_count
        ):
            self.store.save(session_id, updated)
        return updated

    def _extract_facts(self, messages: list[Message]) -> list[str]:
        facts: list[str] = []
        for message in messages:
            content = " ".join(message.content.split())
            if not content:
                continue
            lowered = content.lower()
            if any(marker in lowered for marker in ("my name is", "i am ", "i'm ", "remember ", "project is", "workspace is")):
                facts.append(content[:240])
        return facts

    def _dedupe_facts(self, facts: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for fact in facts:
            normalized = fact.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(fact.strip())
        return unique

    def _select_facts_for_prompt(self, facts: list[str]) -> list[str]:
        if len(facts) <= 4:
            return facts
        return facts[-4:]
