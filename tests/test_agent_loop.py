from pathlib import Path
from uuid import uuid4

from myagent.agent.loop import AgentKernel
from myagent.memory import MemoryManager, MemoryStore
from myagent.observability import EventLogger
from myagent.providers.base import BaseProvider, Message, ModelResponse, ProviderError, ToolCall, ToolResult
from myagent.session.store import SessionStore
from myagent.skills import SkillRegistry
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
            handler=lambda arguments: ToolResult.success(f"listed {arguments['path']}"),
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
    assert saved[2].metadata["react"]["phase"] == "thought_action"
    assert saved[2].metadata["react"]["actions"][0]["tool_name"] == "list_dir"
    assert saved[3].role == "tool"
    assert saved[3].content == "listed ."
    assert saved[3].tool_result is not None
    assert saved[3].tool_result.ok
    assert saved[3].metadata["react"]["phase"] == "observation"
    assert "list_dir succeeded" in saved[3].metadata["react"]["observation_summary"]


def test_agent_kernel_injects_explicit_skill_prompt() -> None:
    registry = ToolRegistry()
    provider = ScriptedProvider()
    store_root = Path(".data") / "test-agent-skill-explicit" / str(uuid4())
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(store_root),
        system_prompt="Follow the local agent policy.",
        skills=SkillRegistry(),
    )

    kernel.run_once(session_id="demo", user_text="实现一个新功能", skill_name="feature_implementer")

    assert "Active skill: feature_implementer" in provider.seen_messages[0][0].content


def test_agent_kernel_auto_selects_skill_from_query() -> None:
    registry = ToolRegistry()
    provider = ScriptedProvider()
    store_root = Path(".data") / "test-agent-skill-auto" / str(uuid4())
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(store_root),
        system_prompt="Follow the local agent policy.",
        skills=SkillRegistry(),
    )

    kernel.run_once(session_id="demo", user_text="帮我调试这个报错")

    assert "Active skill: code_debugger" in provider.seen_messages[0][0].content


def test_agent_kernel_skips_excessive_duplicate_tool_calls() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="list_dir",
            description="List files",
            parameters={"type": "object"},
            handler=lambda arguments: ToolResult.success(f"listed {arguments['path']}"),
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
    assert saved[6].tool_result is not None
    assert saved[6].tool_result.error_type == "duplicate_tool_call"


def test_agent_kernel_stops_after_tool_failure_budget() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="run_command",
            description="Run command",
            parameters={"type": "object"},
            handler=lambda arguments: ToolResult.failure(
                f"failed {arguments['command']}",
                error_type="nonzero_exit",
            ),
        )
    )

    class FailingToolProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="failing-tools")

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            tool_messages = [message for message in messages if message.role == "tool"]
            if len(tool_messages) < 2:
                return ModelResponse(
                    text="Try commands.",
                    tool_calls=[
                        ToolCall(id=f"call_{len(tool_messages)+1}", name="run_command", arguments={"command": "python --version"})
                    ],
                )
            return ModelResponse(text="This response should not be reached.")

    store_root = Path(".data") / "test-agent-tool-failure-budget" / str(uuid4())
    kernel = AgentKernel(
        provider=FailingToolProvider(),
        tools=registry,
        sessions=SessionStore(store_root),
        max_tool_failures_per_turn=2,
        max_consecutive_tool_errors=2,
    )

    result = kernel.run_once(session_id="demo", user_text="run commands")

    assert "safety limit" in result


def test_agent_kernel_updates_memory_after_turn() -> None:
    registry = ToolRegistry()

    class AnswerOnlyProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="answer-only")

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            return ModelResponse(text="I will remember that your name is Alice.")

    root = Path(".data") / "test-agent-memory" / str(uuid4())
    kernel = AgentKernel(
        provider=AnswerOnlyProvider(),
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        memory=MemoryManager(MemoryStore(root / "memory")),
    )

    kernel.run_once(session_id="demo", user_text="My name is Alice.")
    snapshot = kernel.memory.store.load("demo")

    assert "user: My name is Alice." in snapshot.summary
    assert any("My name is Alice." in fact for fact in snapshot.facts)


def test_agent_kernel_refreshes_memory_prompt_for_new_query() -> None:
    registry = ToolRegistry()

    class InspectingProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="inspecting")
            self.system_messages: list[str] = []

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            self.system_messages.append(messages[0].content if messages and messages[0].role == "system" else "")
            return ModelResponse(text="ok")

    root = Path(".data") / "test-agent-memory-query" / str(uuid4())
    provider = InspectingProvider()
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        memory=MemoryManager(MemoryStore(root / "memory"), refresh_min_messages=1),
        system_prompt="Follow the local agent policy.",
    )

    kernel.run_once(session_id="demo", user_text="Workspace is D:/Projects/myagent.")
    kernel.run_once(session_id="demo", user_text="What Python version am I using?")

    assert len(provider.system_messages) == 2
    assert "Follow the local agent policy." in provider.system_messages[1]
    assert "Relevant facts" in provider.system_messages[1]
    assert "Workspace is D:/Projects/myagent." in provider.system_messages[1]


def test_agent_kernel_injects_task_memory_into_followup_turn() -> None:
    registry = ToolRegistry()

    class TaskProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="task")
            self.system_messages: list[str] = []

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            self.system_messages.append(messages[0].content if messages and messages[0].role == "system" else "")
            if len(self.system_messages) == 1:
                return ModelResponse(text="已完成配置解析。下一步做测试。")
            return ModelResponse(text="继续执行。")

    root = Path(".data") / "test-agent-task-memory" / str(uuid4())
    provider = TaskProvider()
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        memory=MemoryManager(MemoryStore(root / "memory"), refresh_min_messages=1),
        system_prompt="Follow the local agent policy.",
    )

    kernel.run_once(session_id="demo", user_text="实现多 MCP 支持")
    kernel.run_once(session_id="demo", user_text="继续，把测试补完")

    assert len(provider.system_messages) == 2
    assert "Current task: 实现多 MCP 支持" in provider.system_messages[1]
    assert "Completed steps" in provider.system_messages[1]
    assert "Pending steps" in provider.system_messages[1]


def test_agent_kernel_writes_active_skill_into_task_memory() -> None:
    registry = ToolRegistry()

    class SkillMemoryProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="skill-memory")

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del messages, tools
            return ModelResponse(text="已完成仓库结构说明。")

    root = Path(".data") / "test-agent-skill-memory" / str(uuid4())
    kernel = AgentKernel(
        provider=SkillMemoryProvider(),
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        memory=MemoryManager(MemoryStore(root / "memory"), refresh_min_messages=1),
        skills=SkillRegistry(),
    )

    kernel.run_once(session_id="demo", user_text="总结这个仓库结构", skill_name="repo_explainer")
    snapshot = kernel.memory.store.load("demo")

    assert snapshot.task.active_skill == "repo_explainer"


def test_agent_kernel_logs_provider_error_metadata() -> None:
    registry = ToolRegistry()

    class ErrorProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="erroring")

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del messages, tools
            return ModelResponse(
                text="Authentication failed for the configured API provider.",
                provider_error=ProviderError(
                    error_type="authentication_error",
                    message="Authentication failed for the configured API provider.",
                    retryable=False,
                ),
                metadata={"attempts": 1},
            )

    root = Path(".data") / "test-agent-provider-error" / str(uuid4())
    logger = EventLogger(root / "logs")
    kernel = AgentKernel(
        provider=ErrorProvider(),
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        logger=logger,
    )

    kernel.run_once(session_id="demo", user_text="hello")

    log_text = (root / "logs" / "demo.jsonl").read_text(encoding="utf-8")
    assert '"error_type": "authentication_error"' in log_text


def test_agent_kernel_logs_trace_and_latency_fields() -> None:
    registry = ToolRegistry()

    class TraceProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="trace")

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del messages, tools
            return ModelResponse(text="done", metadata={"provider_latency_ms": 1.23, "attempts": 1})

    root = Path(".data") / "test-agent-trace" / str(uuid4())
    logger = EventLogger(root / "logs")
    kernel = AgentKernel(
        provider=TraceProvider(),
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        logger=logger,
    )

    kernel.run_once(session_id="demo", user_text="hello")

    log_text = (root / "logs" / "demo.jsonl").read_text(encoding="utf-8")
    assert '"trace_id":' in log_text
    assert '"turn_latency_ms":' in log_text
    assert '"provider_latency_ms": 1.23' in log_text


def test_agent_kernel_records_react_steps_in_logs_and_final_message() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="list_dir",
            description="List files",
            parameters={"type": "object"},
            handler=lambda arguments: ToolResult.success(f"listed {arguments['path']}"),
        )
    )
    provider = ScriptedProvider()
    root = Path(".data") / "test-agent-react-trace" / str(uuid4())
    kernel = AgentKernel(
        provider=provider,
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        logger=EventLogger(root / "logs"),
    )

    result = kernel.run_once(session_id="demo", user_text="what is here?")
    saved = kernel.sessions.load("demo")
    log_text = (root / "logs" / "demo.jsonl").read_text(encoding="utf-8")

    assert result == "The workspace inspection is complete."
    assert saved[-1].metadata["react"]["phase"] == "final_answer"
    assert "Enough information is available to answer directly." == saved[-1].metadata["react"]["thought_summary"]
    assert '"event": "react_step"' in log_text
    assert '"thought_summary": "Checking the workspace."' in log_text
    assert '"observation_summary": "list_dir succeeded: listed ."' in log_text


def test_agent_kernel_can_complete_repo_search_read_and_synthesize_flow() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="repo_search",
            description="Search repo",
            parameters={"type": "object"},
            handler=lambda arguments: ToolResult.success(
                "src/app.py | score=10 | filename overlap=1 | snippet=def build_server(): pass",
                structured_content={
                    "matches": [
                        {
                            "path": "src/app.py",
                            "score": 10,
                            "reason": "filename overlap=1",
                            "snippet": "def build_server(): pass",
                        }
                    ]
                },
                metadata={"query": arguments["query"]},
            ),
        )
    )
    registry.register(
        ToolSpec(
            name="read_file",
            description="Read file",
            parameters={"type": "object"},
            handler=lambda arguments: ToolResult.success(
                "def build_server():\n    return 'server'\n",
                metadata={"path": arguments["path"]},
            ),
        )
    )

    class RepoFlowProvider(BaseProvider):
        def __init__(self) -> None:
            super().__init__(model="repo-flow")
            self.calls = 0

        def complete(
            self,
            messages: list[Message],
            tools: list[dict[str, object]],
        ) -> ModelResponse:
            del tools
            self.calls += 1
            if self.calls == 1:
                return ModelResponse(
                    text="I will search the repository first.",
                    tool_calls=[ToolCall(id="call_1", name="repo_search", arguments={"query": "build server"})],
                )
            if self.calls == 2:
                assert any(
                    message.role == "tool" and "src/app.py" in message.content for message in messages
                )
                return ModelResponse(
                    text="I found the likely file and will read it.",
                    tool_calls=[ToolCall(id="call_2", name="read_file", arguments={"path": "src/app.py"})],
                )
            assert any(
                message.role == "tool" and "def build_server()" in message.content for message in messages
            )
            return ModelResponse(
                text="`build_server` is defined in `src/app.py` and returns the string `server`.",
            )

    root = Path(".data") / "test-agent-repo-flow" / str(uuid4())
    kernel = AgentKernel(
        provider=RepoFlowProvider(),
        tools=registry,
        sessions=SessionStore(root / "sessions"),
        system_prompt="Follow repository inspection flow.",
    )

    result = kernel.run_once(session_id="demo", user_text="Where is build_server defined?")
    saved = kernel.sessions.load("demo")

    assert "src/app.py" in result
    assert "returns the string `server`" in result
    assert saved[2].tool_calls[0].name == "repo_search"
    assert saved[4].tool_calls[0].name == "read_file"
