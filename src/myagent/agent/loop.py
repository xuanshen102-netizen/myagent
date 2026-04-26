from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Callable
from uuid import uuid4

from myagent.memory import MemoryManager
from myagent.observability import EventLogger
from myagent.providers.base import BaseProvider, Message, ModelResponse, ToolResult
from myagent.session.store import SessionStore
from myagent.skills import SkillManifest, SkillRegistry
from myagent.tools.registry import ToolRegistry


@dataclass(slots=True)
class ToolExecutionRecord:
    round_index: int
    tool_call_id: str
    tool_name: str
    arguments: dict[str, object]
    result: ToolResult
    duplicate_count: int


@dataclass(slots=True)
class ReactStep:
    round_index: int
    thought_summary: str
    actions: list[dict[str, object]]
    observations: list[dict[str, object]]


@dataclass(slots=True)
class TurnContext:
    session_id: str
    user_text: str
    active_skill: str | None
    tool_history: dict[str, int]
    executed_tools: list[ToolExecutionRecord]
    react_steps: list[ReactStep]
    trace_id: str
    provider_rounds: int = 0
    tool_failures: int = 0
    consecutive_tool_failures: int = 0


@dataclass(slots=True)
class AgentKernel:
    provider: BaseProvider
    tools: ToolRegistry
    sessions: SessionStore
    max_tool_rounds: int = 4
    system_prompt: str | None = None
    memory: MemoryManager | None = None
    logger: EventLogger | None = None
    skills: SkillRegistry | None = None
    max_duplicate_tool_calls: int = 2
    max_tool_failures_per_turn: int = 2
    max_consecutive_tool_errors: int = 2
    shutdown_callbacks: list[Callable[[], None]] | None = None

    def run_once(self, session_id: str, user_text: str, *, skill_name: str | None = None) -> str:
        active_skill = self._resolve_skill(user_text, skill_name)
        messages = self._load_messages(session_id, user_text, active_skill)
        messages.append(Message(role="user", content=user_text))
        turn = TurnContext(
            session_id=session_id,
            user_text=user_text,
            active_skill=active_skill.name if active_skill else None,
            tool_history={},
            executed_tools=[],
            react_steps=[],
            trace_id=uuid4().hex,
        )
        turn_started_at = time.perf_counter()
        self._log(
            session_id,
            "turn_start",
            {
                "user_text": user_text,
                "message_count": len(messages),
                "system_prompt_enabled": bool(self.system_prompt),
                "active_skill": turn.active_skill,
            },
            trace_id=turn.trace_id,
        )

        for round_index in range(1, self.max_tool_rounds + 1):
            turn.provider_rounds = round_index
            self._log(
                session_id,
                "provider_request",
                {
                    "round": round_index,
                    "message_roles": [message.role for message in messages[-8:]],
                },
                trace_id=turn.trace_id,
            )
            response = self.provider.complete(
                messages=messages,
                tools=self.tools.describe(),
            )
            self._log(
                session_id,
                "provider_response",
                {
                    "round": round_index,
                    "text_preview": response.text[:300],
                    "provider_error": (
                        response.provider_error.to_dict() if response.provider_error else None
                    ),
                    "metadata": response.metadata,
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in response.tool_calls
                    ],
                },
                trace_id=turn.trace_id,
            )
            thought_summary = self._summarize_thought(response)
            if not response.tool_calls:
                assistant_text = response.text.strip() or "(empty response)"
                turn.react_steps.append(
                    ReactStep(
                        round_index=round_index,
                        thought_summary=thought_summary,
                        actions=[],
                        observations=[],
                    )
                )
                messages.append(
                    Message(
                        role="assistant",
                        content=assistant_text,
                        metadata={
                            "react": {
                                "phase": "final_answer",
                                "thought_summary": thought_summary,
                                "round": round_index,
                            }
                        },
                    )
                )
                self.sessions.save(session_id, messages)
                snapshot = self._update_memory(session_id, messages, active_skill=turn.active_skill)
                self._log(
                    session_id,
                    "turn_complete",
                    {
                        "assistant_text": assistant_text,
                        "provider_rounds": turn.provider_rounds,
                        "tool_call_count": len(turn.executed_tools),
                        "tool_failures": turn.tool_failures,
                        "provider_error": (
                            response.provider_error.to_dict()
                            if response.provider_error
                            else None
                        ),
                        "react_steps": [self._react_step_payload(step) for step in turn.react_steps],
                        "memory_summary_present": bool(snapshot and snapshot.summary),
                        "memory_fact_count": len(snapshot.facts) if snapshot else 0,
                        "turn_latency_ms": round((time.perf_counter() - turn_started_at) * 1000, 3),
                        "trace_id": turn.trace_id,
                    },
                    trace_id=turn.trace_id,
                )
                return assistant_text

            messages.append(
                Message(
                    role="assistant",
                    content=response.text or "",
                    tool_calls=response.tool_calls,
                    metadata={
                        "react": {
                            "phase": "thought_action",
                            "thought_summary": thought_summary,
                            "round": round_index,
                            "actions": [
                                {"tool_name": call.name, "arguments": call.arguments}
                                for call in response.tool_calls
                            ],
                        }
                    },
                )
            )
            self._apply_tool_calls(turn, messages, response, round_index, thought_summary)
            if (
                turn.tool_failures >= self.max_tool_failures_per_turn
                or turn.consecutive_tool_failures >= self.max_consecutive_tool_errors
            ):
                break

        fallback = "Tool loop reached the safety limit before producing a final answer."
        messages.append(Message(role="assistant", content=fallback))
        self.sessions.save(session_id, messages)
        snapshot = self._update_memory(session_id, messages, active_skill=turn.active_skill)
        self._log(
            session_id,
            "turn_complete",
            {
                "assistant_text": fallback,
                "provider_rounds": turn.provider_rounds,
                "tool_call_count": len(turn.executed_tools),
                "tool_failures": turn.tool_failures,
                "react_steps": [self._react_step_payload(step) for step in turn.react_steps],
                "memory_summary_present": bool(snapshot and snapshot.summary),
                "memory_fact_count": len(snapshot.facts) if snapshot else 0,
                "turn_latency_ms": round((time.perf_counter() - turn_started_at) * 1000, 3),
                "trace_id": turn.trace_id,
            },
            trace_id=turn.trace_id,
        )
        return fallback

    def _load_messages(
        self,
        session_id: str,
        user_text: str,
        active_skill: SkillManifest | None,
    ) -> list[Message]:
        messages = self.sessions.load(session_id)
        prompt_parts = [
            part
            for part in [
                self.system_prompt,
                self._skill_prompt(active_skill, user_text),
                self._memory_prompt(session_id, user_text),
            ]
            if part
        ]
        if prompt_parts:
            system_message = Message(role="system", content="\n\n".join(prompt_parts))
            if messages and messages[0].role == "system":
                messages[0] = system_message
            else:
                messages.insert(0, system_message)
        return messages

    def _apply_tool_calls(
        self,
        turn: TurnContext,
        messages: list[Message],
        response: ModelResponse,
        round_index: int,
        thought_summary: str,
    ) -> None:
        step = ReactStep(
            round_index=round_index,
            thought_summary=thought_summary,
            actions=[
                {"tool_name": call.name, "arguments": call.arguments}
                for call in response.tool_calls
            ],
            observations=[],
        )
        for call in response.tool_calls:
            tool_started_at = time.perf_counter()
            signature = self._tool_signature(call.name, call.arguments)
            turn.tool_history[signature] = turn.tool_history.get(signature, 0) + 1
            if turn.tool_history[signature] > self.max_duplicate_tool_calls:
                result = ToolResult.failure(
                    (
                        f"Skipped duplicate tool call for {call.name}. "
                        "The same tool arguments were already used repeatedly in this turn."
                    ),
                    error_type="duplicate_tool_call",
                    metadata={"tool_name": call.name},
                )
            else:
                result = self.tools.execute(call.name, call.arguments)
            record = ToolExecutionRecord(
                round_index=round_index,
                tool_call_id=call.id,
                tool_name=call.name,
                arguments=call.arguments,
                result=result,
                duplicate_count=turn.tool_history[signature],
            )
            turn.executed_tools.append(record)
            if result.ok:
                turn.consecutive_tool_failures = 0
            else:
                turn.tool_failures += 1
                turn.consecutive_tool_failures += 1
            observation_summary = self._summarize_observation(call.name, result)
            step.observations.append(
                {
                    "tool_name": call.name,
                    "status": result.status,
                    "summary": observation_summary,
                    "error_type": result.error_type,
                }
            )
            self._log(
                turn.session_id,
                "tool_result",
                {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "result_preview": result.content[:500],
                    "status": result.status,
                    "error_type": result.error_type,
                    "metadata": result.metadata,
                    "observation_summary": observation_summary,
                    "duplicate_count": turn.tool_history[signature],
                    "round": round_index,
                    "tool_latency_ms": round((time.perf_counter() - tool_started_at) * 1000, 3),
                },
                trace_id=turn.trace_id,
            )
            messages.append(
                Message(
                    role="tool",
                    content=result.content,
                    name=call.name,
                    tool_call_id=call.id,
                    tool_result=result,
                    metadata={
                        "react": {
                            "phase": "observation",
                            "round": round_index,
                            "tool_name": call.name,
                            "observation_summary": observation_summary,
                            "status": result.status,
                            "error_type": result.error_type,
                        }
                    },
                )
            )
        turn.react_steps.append(step)
        self._log(
            turn.session_id,
            "react_step",
            self._react_step_payload(step),
            trace_id=turn.trace_id,
        )

    def _tool_signature(self, name: str, arguments: dict[str, object]) -> str:
        return f"{name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True)}"

    def _summarize_thought(self, response: ModelResponse) -> str:
        text = (response.text or "").strip()
        if response.tool_calls:
            if text:
                return text[:240]
            tool_names = ", ".join(call.name for call in response.tool_calls)
            return f"Need external observations before answering; next actions: {tool_names}."
        if text:
            return "Enough information is available to answer directly."
        if response.provider_error is not None:
            return "Provider returned an error instead of a usable answer."
        return "No further action was proposed."

    def _summarize_observation(self, tool_name: str, result: ToolResult) -> str:
        if result.ok:
            preview = result.content.strip().replace("\n", " ")
            if preview:
                return f"{tool_name} succeeded: {preview[:180]}"
            return f"{tool_name} succeeded with an empty textual result."
        preview = result.content.strip().replace("\n", " ")
        if preview:
            return f"{tool_name} failed ({result.error_type or 'error'}): {preview[:180]}"
        return f"{tool_name} failed with error type {result.error_type or 'unknown_error'}."

    def _react_step_payload(self, step: ReactStep) -> dict[str, object]:
        return {
            "round": step.round_index,
            "thought_summary": step.thought_summary,
            "actions": step.actions,
            "observations": step.observations,
        }

    def _memory_prompt(self, session_id: str, user_text: str) -> str | None:
        if self.memory is None:
            return None
        return self.memory.build_memory_prompt(session_id, query=user_text)

    def _update_memory(
        self,
        session_id: str,
        messages: list[Message],
        *,
        active_skill: str | None = None,
    ):
        if self.memory is None:
            return None
        return self.memory.update(session_id, messages, active_skill=active_skill)

    def _resolve_skill(self, user_text: str, skill_name: str | None) -> SkillManifest | None:
        if self.skills is None:
            return None
        if skill_name:
            return self.skills.get(skill_name)
        return self.skills.choose_for_query(user_text)

    def _skill_prompt(self, skill: SkillManifest | None, user_text: str) -> str | None:
        if skill is None:
            return None
        return skill.build_prompt(query=user_text)

    def close(self) -> None:
        if not self.shutdown_callbacks:
            return
        for callback in self.shutdown_callbacks:
            try:
                callback()
            except Exception:
                continue

    def _log(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, object],
        *,
        trace_id: str | None = None,
    ) -> None:
        if self.logger is None:
            return
        self.logger.log(
            session_id=session_id,
            event_type=event_type,
            payload=payload,
            trace_id=trace_id,
        )
