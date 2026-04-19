from __future__ import annotations

from dataclasses import dataclass
import json

from myagent.observability import EventLogger
from myagent.providers.base import BaseProvider, Message, ModelResponse
from myagent.session.store import SessionStore
from myagent.tools.registry import ToolRegistry


@dataclass(slots=True)
class AgentKernel:
    provider: BaseProvider
    tools: ToolRegistry
    sessions: SessionStore
    max_tool_rounds: int = 4
    system_prompt: str | None = None
    logger: EventLogger | None = None
    max_duplicate_tool_calls: int = 2

    def run_once(self, session_id: str, user_text: str) -> str:
        messages = self._load_messages(session_id)
        messages.append(Message(role="user", content=user_text))
        self._log(
            session_id,
            "turn_start",
            {
                "user_text": user_text,
                "message_count": len(messages),
                "system_prompt_enabled": bool(self.system_prompt),
            },
        )
        tool_history: dict[str, int] = {}

        for round_index in range(1, self.max_tool_rounds + 1):
            self._log(
                session_id,
                "provider_request",
                {
                    "round": round_index,
                    "message_roles": [message.role for message in messages[-8:]],
                },
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
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in response.tool_calls
                    ],
                },
            )
            if not response.tool_calls:
                assistant_text = response.text.strip() or "(empty response)"
                messages.append(Message(role="assistant", content=assistant_text))
                self.sessions.save(session_id, messages)
                self._log(session_id, "turn_complete", {"assistant_text": assistant_text})
                return assistant_text

            messages.append(
                Message(
                    role="assistant",
                    content=response.text or "",
                    tool_calls=response.tool_calls,
                )
            )
            self._apply_tool_calls(session_id, messages, response, tool_history)

        fallback = "Tool loop reached the safety limit before producing a final answer."
        messages.append(Message(role="assistant", content=fallback))
        self.sessions.save(session_id, messages)
        self._log(session_id, "turn_complete", {"assistant_text": fallback})
        return fallback

    def _load_messages(self, session_id: str) -> list[Message]:
        messages = self.sessions.load(session_id)
        if not messages and self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        return messages

    def _apply_tool_calls(
        self,
        session_id: str,
        messages: list[Message],
        response: ModelResponse,
        tool_history: dict[str, int],
    ) -> None:
        for call in response.tool_calls:
            signature = self._tool_signature(call.name, call.arguments)
            tool_history[signature] = tool_history.get(signature, 0) + 1
            if tool_history[signature] > self.max_duplicate_tool_calls:
                result = (
                    f"Skipped duplicate tool call for {call.name}. "
                    "The same tool arguments were already used repeatedly in this turn."
                )
            else:
                result = self.tools.execute(call.name, call.arguments)
            self._log(
                session_id,
                "tool_result",
                {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "result_preview": result[:500],
                    "duplicate_count": tool_history[signature],
                },
            )
            messages.append(
                Message(
                    role="tool",
                    content=result,
                    name=call.name,
                    tool_call_id=call.id,
                )
            )

    def _tool_signature(self, name: str, arguments: dict[str, object]) -> str:
        return f"{name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True)}"

    def _log(self, session_id: str, event_type: str, payload: dict[str, object]) -> None:
        if self.logger is None:
            return
        self.logger.log(session_id=session_id, event_type=event_type, payload=payload)
