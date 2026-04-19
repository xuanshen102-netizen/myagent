from pathlib import Path
from uuid import uuid4

from myagent.agent.loop import AgentKernel
from myagent.observability import EventLogger
from myagent.providers.base import BaseProvider, Message, ModelResponse, ToolCall
from myagent.session.store import SessionStore
from myagent.tools.base import ToolSpec
from myagent.tools.registry import ToolRegistry


class ScriptedProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(model="scripted")
        self.calls = 0
        self.seen_messages: list[list[Message]] = []

    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        del tools
        self.calls += 1
        self.seen_messages.append(list(messages))
        if self.calls == 1:
            return ModelResponse(
                text="Checking the workspace.",
                tool_calls=[ToolCall(id="call_1", name="list_dir", arguments={"path": "."})],
            )
        return ModelResponse(text="The workspace inspection is complete.")


def test_agent_kernel_injects_system_prompt_and_executes_tool_loop() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="list_dir",
            description="List files",
            parameters={"type": "object"},
            handler=lambda arguments: f"listed {arguments['path']}",
        )
    )
    provider = ScriptedProvider()
    store_root = Path(".data") / "test-agent-loop" / str(uuid4())
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(store_root),
        system_prompt="Follow the local agent policy.",
    )

    result = kernel.run_once(session_id="demo", user_text="what is here?")

    assert result == "The workspace inspection is complete."
    assert provider.calls == 2
    assert provider.seen_messages[0][0].role == "system"
    assert provider.seen_messages[0][0].content == "Follow the local agent policy."
    saved = kernel.sessions.load("demo")
    assert saved[2].role == "assistant"
    assert saved[2].tool_calls[0].name == "list_dir"
    assert saved[3].role == "tool"
    assert saved[3].content == "listed ."


def test_agent_kernel_skips_excessive_duplicate_tool_calls() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="list_dir",
            description="List files",
            parameters={"type": "object"},
            handler=lambda arguments: f"listed {arguments['path']}",
        )
    )

    class DuplicateProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="duplicate")
            self.calls = 0

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            self.calls += 1
            if self.calls < 4:
                return ModelResponse(
                    text="Trying the same tool.",
                    tool_calls=[ToolCall(id=f"call_{self.calls}", name="list_dir", arguments={"path": "."})],
                )
            return ModelResponse(text="Done.")

    store_root = Path(".data") / "test-agent-duplicate-loop" / str(uuid4())
    kernel = AgentKernel(
        provider=DuplicateProvider(),
        tools=registry,
        sessions=SessionStore(store_root),
        logger=EventLogger(store_root / "logs"),
    )

    kernel.run_once(session_id="demo", user_text="repeat")
    saved = kernel.sessions.load("demo")
    assert "Skipped duplicate tool call" in saved[6].content
