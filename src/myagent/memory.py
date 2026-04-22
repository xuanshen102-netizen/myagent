from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from myagent.providers.base import Message


@dataclass(slots=True)
class TaskMemory:
    title: str = ""
    goal: str = ""
    status: str = "idle"
    active_skill: str = ""
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    last_user_request: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "goal": self.goal,
            "status": self.status,
            "active_skill": self.active_skill,
            "completed_steps": self.completed_steps,
            "pending_steps": self.pending_steps,
            "blockers": self.blockers,
            "last_user_request": self.last_user_request,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "TaskMemory":
        return cls(
            title=str(data.get("title", "")),
            goal=str(data.get("goal", "")),
            status=str(data.get("status", "idle")),
            active_skill=str(data.get("active_skill", "")),
            completed_steps=[str(item) for item in data.get("completed_steps", [])],
            pending_steps=[str(item) for item in data.get("pending_steps", [])],
            blockers=[str(item) for item in data.get("blockers", [])],
            last_user_request=str(data.get("last_user_request", "")),
        )


@dataclass(slots=True)
class MemorySnapshot:
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    message_count: int = 0
    task: TaskMemory = field(default_factory=TaskMemory)

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "facts": self.facts,
            "message_count": self.message_count,
            "task": self.task.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MemorySnapshot":
        return cls(
            summary=str(data.get("summary", "")),
            facts=[str(item) for item in data.get("facts", [])],
            message_count=int(data.get("message_count", 0)),
            task=TaskMemory.from_dict(data.get("task", {})),
        )


@dataclass(slots=True)
class LongTermMemorySnapshot:
    facts: list[str] = field(default_factory=list)
    task_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "facts": self.facts,
            "task_notes": self.task_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LongTermMemorySnapshot":
        return cls(
            facts=[str(item) for item in data.get("facts", [])],
            task_notes=[str(item) for item in data.get("task_notes", [])],
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

    def load_long_term(self) -> LongTermMemorySnapshot:
        path = self.root / "_long_term.json"
        if not path.exists():
            return LongTermMemorySnapshot()
        data = json.loads(path.read_text(encoding="utf-8"))
        return LongTermMemorySnapshot.from_dict(data)

    def save_long_term(self, snapshot: LongTermMemorySnapshot) -> None:
        path = self.root / "_long_term.json"
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
        prompt_fact_limit: int = 4,
        prompt_summary_line_limit: int = 4,
        task_step_limit: int = 3,
        long_term_fact_limit: int = 12,
        long_term_note_limit: int = 12,
        prompt_long_term_limit: int = 4,
    ) -> None:
        self.store = store
        self.max_recent_messages = max_recent_messages
        self.max_facts = max_facts
        self.summary_line_limit = summary_line_limit
        self.refresh_min_messages = refresh_min_messages
        self.prompt_fact_limit = prompt_fact_limit
        self.prompt_summary_line_limit = prompt_summary_line_limit
        self.task_step_limit = task_step_limit
        self.long_term_fact_limit = long_term_fact_limit
        self.long_term_note_limit = long_term_note_limit
        self.prompt_long_term_limit = prompt_long_term_limit

    def build_memory_prompt(self, session_id: str, query: str = "") -> str | None:
        snapshot = self.store.load(session_id)
        long_term = self.store.load_long_term()
        if (
            not snapshot.summary
            and not snapshot.facts
            and not snapshot.task.title
            and not long_term.facts
            and not long_term.task_notes
        ):
            return None

        parts: list[str] = []
        task_prompt = self._build_task_prompt(snapshot.task, query)
        if task_prompt:
            parts.append(task_prompt)
        selected_summary = self._select_summary_lines(snapshot.summary, query)
        if selected_summary:
            parts.append("Relevant conversation summary:\n" + "\n".join(selected_summary))
        if snapshot.facts:
            selected_facts = self._select_facts_for_prompt(snapshot.facts, query)
            if selected_facts:
                parts.append("Relevant facts:\n" + "\n".join(f"- {fact}" for fact in selected_facts))
        long_term_prompt = self._build_long_term_prompt(
            long_term,
            query,
            exclude={*snapshot.facts, *snapshot.task.completed_steps, *snapshot.task.pending_steps},
        )
        if long_term_prompt:
            parts.append(long_term_prompt)
        return "\n\n".join(parts)

    def update(
        self,
        session_id: str,
        messages: list[Message],
        *,
        active_skill: str | None = None,
    ) -> MemorySnapshot:
        snapshot = self.store.load(session_id)
        conversational = [message for message in messages if message.role in {"user", "assistant"}]
        if len(conversational) < self.refresh_min_messages:
            return snapshot
        if len(conversational) - snapshot.message_count < self.refresh_min_messages:
            return snapshot
        recent = conversational[-self.max_recent_messages :]
        summary = self._build_summary(snapshot.summary, recent)
        facts = self._dedupe_facts(self._extract_facts(conversational))
        task = self._update_task_memory(snapshot.task, conversational, active_skill=active_skill)
        updated = MemorySnapshot(
            summary=summary,
            facts=facts[-self.max_facts :],
            message_count=len(conversational),
            task=task,
        )
        long_term = self._update_long_term_memory(updated)
        if (
            updated.summary != snapshot.summary
            or updated.facts != snapshot.facts
            or updated.message_count != snapshot.message_count
            or updated.task != snapshot.task
        ):
            self.store.save(session_id, updated)
        self._save_long_term_if_changed(long_term)
        return updated

    def _extract_facts(self, messages: list[Message]) -> list[str]:
        facts: list[str] = []
        for message in messages:
            content = " ".join(message.content.split())
            if not content:
                continue
            fact = self._extract_fact_from_text(content)
            if fact:
                facts.append(fact[:240])
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

    def _build_summary(self, previous_summary: str, recent_messages: list[Message]) -> str:
        preserved = [
            line.strip()
            for line in previous_summary.splitlines()
            if line.strip()
        ][-max(1, self.summary_line_limit // 2) :]
        recent_lines = [
            f"{message.role}: {message.content.strip()}"
            for message in recent_messages
            if message.content.strip()
        ]
        merged: list[str] = []
        seen: set[str] = set()
        for line in [*preserved, *recent_lines]:
            normalized = line.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(line)
        return "\n".join(merged[-self.summary_line_limit :])

    def _extract_fact_from_text(self, content: str) -> str | None:
        lowered = content.lower()
        english_markers = (
            "my name is",
            "i am ",
            "i'm ",
            "remember ",
            "project is",
            "workspace is",
            "we are building",
            "goal is",
            "i use ",
            "please use ",
            "use chinese",
            "prefer ",
            "always ",
            "never ",
        )
        chinese_markers = (
            "我叫",
            "我是",
            "记住",
            "项目是",
            "工作区是",
            "我们在做",
            "目标是",
            "我用",
            "偏好",
            "请用中文",
            "用中文回复",
        )
        if any(marker in lowered for marker in english_markers) or any(
            marker in content for marker in chinese_markers
        ):
            return content
        return None

    def _select_summary_lines(self, summary: str, query: str) -> list[str]:
        lines = [line.strip() for line in summary.splitlines() if line.strip()]
        if len(lines) <= self.prompt_summary_line_limit:
            return lines
        ranked = sorted(
            enumerate(lines),
            key=lambda item: (
                self._score_text_relevance(query, item[1]),
                item[0],
            ),
            reverse=True,
        )
        selected = sorted(
            ranked[: self.prompt_summary_line_limit],
            key=lambda item: item[0],
        )
        return [line for _, line in selected]

    def _select_facts_for_prompt(self, facts: list[str], query: str) -> list[str]:
        if len(facts) <= self.prompt_fact_limit:
            return facts
        ranked = sorted(
            enumerate(facts),
            key=lambda item: (
                self._score_text_relevance(query, item[1]) + self._fact_priority_bonus(item[1]),
                item[0],
            ),
            reverse=True,
        )
        selected = sorted(
            ranked[: self.prompt_fact_limit],
            key=lambda item: item[0],
        )
        return [fact for _, fact in selected]

    def _select_long_term_items(
        self,
        items: list[str],
        query: str,
        *,
        limit: int,
        exclude: set[str],
    ) -> list[str]:
        filtered = [item for item in items if item not in exclude]
        if len(filtered) <= limit:
            return filtered
        ranked = sorted(
            enumerate(filtered),
            key=lambda item: (
                self._score_text_relevance(query, item[1]) + self._fact_priority_bonus(item[1]),
                item[0],
            ),
            reverse=True,
        )
        selected = sorted(ranked[:limit], key=lambda item: item[0])
        return [item for _, item in selected]

    def _score_text_relevance(self, query: str, text: str) -> int:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0
        text_tokens = self._tokenize(text)
        overlap = len(query_tokens & text_tokens)
        phrase_bonus = 2 if query and query.strip() and query.strip().lower() in text.lower() else 0
        return overlap * 3 + phrase_bonus

    def _fact_priority_bonus(self, fact: str) -> int:
        lowered = fact.lower()
        stable_markers = (
            "my name is",
            "workspace is",
            "project is",
            "i use ",
            "please use ",
            "use chinese",
            "prefer ",
            "请用中文",
            "用中文回复",
            "工作区是",
            "项目是",
            "偏好",
        )
        if any(marker in lowered for marker in stable_markers) or any(
            marker in fact for marker in ("请用中文", "用中文回复", "工作区是", "项目是", "偏好")
        ):
            return 2
        return 0

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[A-Za-z0-9_/\-:.]+|[\u4e00-\u9fff]{2,}", text.lower())
            if len(token) >= 2
        }

    def _update_task_memory(
        self,
        previous: TaskMemory,
        messages: list[Message],
        *,
        active_skill: str | None = None,
    ) -> TaskMemory:
        latest_user_request = self._latest_message_content(messages, "user")
        task_title = self._infer_task_title(messages, previous)
        goal = self._infer_task_goal(messages, previous)
        completed_steps = self._merge_items(
            previous.completed_steps,
            self._extract_task_items(messages, kind="completed"),
        )
        pending_steps = self._merge_items(
            previous.pending_steps,
            self._extract_task_items(messages, kind="pending"),
        )
        blockers = self._merge_items(
            previous.blockers,
            self._extract_task_items(messages, kind="blocker"),
        )
        if completed_steps and pending_steps:
            status = "active"
        elif blockers:
            status = "blocked"
        elif completed_steps:
            status = "active"
        elif latest_user_request:
            status = "active"
        else:
            status = previous.status
        return TaskMemory(
            title=task_title,
            goal=goal,
            status=status or "idle",
            active_skill=active_skill or previous.active_skill,
            completed_steps=completed_steps[-6:],
            pending_steps=pending_steps[-6:],
            blockers=blockers[-4:],
            last_user_request=latest_user_request,
        )

    def _build_task_prompt(self, task: TaskMemory, query: str) -> str | None:
        if not task.title and not task.completed_steps and not task.pending_steps and not task.blockers:
            return None
        parts = [f"Current task: {task.title or task.last_user_request}"]
        if task.goal:
            parts.append(f"Goal: {task.goal}")
        if task.status:
            parts.append(f"Status: {task.status}")
        if task.active_skill:
            parts.append(f"Active skill: {task.active_skill}")
        completed = self._select_task_items(task.completed_steps, query)
        pending = self._select_task_items(task.pending_steps, query)
        blockers = self._select_task_items(task.blockers, query)
        if completed:
            parts.append("Completed steps:\n" + "\n".join(f"- {item}" for item in completed))
        if pending:
            parts.append("Pending steps:\n" + "\n".join(f"- {item}" for item in pending))
        if blockers:
            parts.append("Blockers:\n" + "\n".join(f"- {item}" for item in blockers))
        return "\n".join(parts)

    def _select_task_items(self, items: list[str], query: str) -> list[str]:
        if len(items) <= self.task_step_limit:
            return items
        ranked = sorted(
            enumerate(items),
            key=lambda item: (
                self._score_text_relevance(query, item[1]),
                item[0],
            ),
            reverse=True,
        )
        selected = sorted(ranked[: self.task_step_limit], key=lambda item: item[0])
        return [item for _, item in selected]

    def _latest_message_content(self, messages: list[Message], role: str) -> str:
        for message in reversed(messages):
            if message.role == role and message.content.strip():
                return " ".join(message.content.split())[:240]
        return ""

    def _infer_task_title(self, messages: list[Message], previous: TaskMemory) -> str:
        task_markers = (
            "implement",
            "build",
            "optimize",
            "add",
            "fix",
            "improve",
            "做",
            "实现",
            "优化",
            "补",
            "完善",
            "开发",
            "支持",
        )
        for message in reversed(messages):
            content = " ".join(message.content.split())
            lowered = content.lower()
            if message.role == "user" and any(marker in lowered for marker in task_markers):
                return content[:120]
            if message.role == "user" and any(marker in content for marker in task_markers):
                return content[:120]
        return previous.title or self._latest_message_content(messages, "user")

    def _infer_task_goal(self, messages: list[Message], previous: TaskMemory) -> str:
        goal_markers = (
            "goal is",
            "we are building",
            "need to",
            "目标是",
            "我们在做",
            "需要",
            "要做",
        )
        for message in reversed(messages):
            content = " ".join(message.content.split())
            lowered = content.lower()
            if any(marker in lowered for marker in goal_markers) or any(
                marker in content for marker in goal_markers
            ):
                return content[:180]
        return previous.goal or previous.title

    def _extract_task_items(self, messages: list[Message], *, kind: str) -> list[str]:
        extracted: list[str] = []
        for message in messages:
            content = " ".join(message.content.split())
            if not content:
                continue
            if kind == "completed" and self._looks_completed(content):
                extracted.append(content[:180])
            elif kind == "pending" and self._looks_pending(content):
                extracted.append(content[:180])
            elif kind == "blocker" and self._looks_blocker(content):
                extracted.append(content[:180])
        return extracted

    def _looks_completed(self, content: str) -> bool:
        lowered = content.lower()
        return any(
            marker in lowered
            for marker in ("done", "completed", "implemented", "added", "updated", "fixed", "passed")
        ) or any(
            marker in content
            for marker in ("已完成", "完成了", "已实现", "已支持", "更新了", "修复了", "通过了")
        )

    def _looks_pending(self, content: str) -> bool:
        lowered = content.lower()
        return any(
            marker in lowered
            for marker in ("next", "todo", "pending", "need to", "remaining", "still need")
        ) or any(
            marker in content
            for marker in ("下一步", "待做", "未完成", "还要", "需要", "还缺", "接下来")
        )

    def _looks_blocker(self, content: str) -> bool:
        lowered = content.lower()
        return any(
            marker in lowered
            for marker in ("blocker", "blocked", "error", "failed", "risk", "issue")
        ) or any(
            marker in content
            for marker in ("阻塞", "卡住", "报错", "失败", "风险", "问题")
        )

    def _merge_items(self, previous: list[str], current: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for item in [*previous, *current]:
            normalized = item.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(item.strip())
        return merged

    def _update_long_term_memory(self, snapshot: MemorySnapshot) -> LongTermMemorySnapshot:
        previous = self.store.load_long_term()
        task_notes = self._merge_items(
            previous.task_notes,
            self._build_long_term_task_notes(snapshot.task),
        )
        return LongTermMemorySnapshot(
            facts=self._merge_items(previous.facts, snapshot.facts)[-self.long_term_fact_limit :],
            task_notes=task_notes[-self.long_term_note_limit :],
        )

    def _build_long_term_task_notes(self, task: TaskMemory) -> list[str]:
        notes: list[str] = []
        if task.goal:
            notes.append(f"Project goal: {task.goal}")
        if task.completed_steps:
            notes.extend(f"Completed task note: {item}" for item in task.completed_steps[-2:])
        if task.blockers:
            notes.extend(f"Known blocker: {item}" for item in task.blockers[-2:])
        return notes

    def _build_long_term_prompt(
        self,
        snapshot: LongTermMemorySnapshot,
        query: str,
        *,
        exclude: set[str],
    ) -> str | None:
        selected_facts = self._select_long_term_items(
            snapshot.facts,
            query,
            limit=self.prompt_long_term_limit,
            exclude=exclude,
        )
        selected_notes = self._select_long_term_items(
            snapshot.task_notes,
            query,
            limit=self.prompt_long_term_limit,
            exclude=exclude,
        )
        parts: list[str] = []
        if selected_facts:
            parts.append("Relevant long-term project facts:\n" + "\n".join(f"- {fact}" for fact in selected_facts))
        if selected_notes:
            parts.append("Relevant long-term project notes:\n" + "\n".join(f"- {item}" for item in selected_notes))
        return "\n\n".join(parts) if parts else None

    def _save_long_term_if_changed(self, updated: LongTermMemorySnapshot) -> None:
        existing = self.store.load_long_term()
        if updated.facts != existing.facts or updated.task_notes != existing.task_notes:
            self.store.save_long_term(updated)
