from pathlib import Path
from uuid import uuid4

from myagent.memory import MemoryManager, MemoryStore
from myagent.providers.base import Message


def test_memory_manager_updates_summary_and_facts() -> None:
    root = Path(".data") / "test-memory" / str(uuid4())
    manager = MemoryManager(MemoryStore(root), max_recent_messages=6)
    messages = [
        Message(role="user", content="My name is Alice."),
        Message(role="assistant", content="I will remember that."),
        Message(role="user", content="The project is a local coding assistant."),
    ]

    snapshot = manager.update("demo", messages)

    assert "user: My name is Alice." in snapshot.summary
    assert any("My name is Alice." in fact for fact in snapshot.facts)
    assert any("The project is a local coding assistant." in fact for fact in snapshot.facts)


def test_memory_prompt_is_built_from_snapshot() -> None:
    root = Path(".data") / "test-memory-prompt" / str(uuid4())
    store = MemoryStore(root)
    manager = MemoryManager(store)
    store.save(
        "demo",
        manager.update(
            "demo",
            [
                Message(role="user", content="Remember workspace is D:/Projects/myagent."),
                Message(role="assistant", content="Stored."),
            ],
        ),
    )

    prompt = manager.build_memory_prompt("demo", query="workspace")

    assert prompt is not None
    assert "Relevant conversation summary" in prompt
    assert "Relevant facts" in prompt


def test_memory_manager_dedupes_facts_and_limits_prompt_selection() -> None:
    root = Path(".data") / "test-memory-dedupe" / str(uuid4())
    manager = MemoryManager(
        MemoryStore(root),
        max_recent_messages=8,
        max_facts=8,
        summary_line_limit=6,
        refresh_min_messages=1,
    )
    messages = [
        Message(role="user", content="My name is Alice."),
        Message(role="assistant", content="My name is Alice."),
        Message(role="user", content="Workspace is D:/Projects/myagent."),
        Message(role="assistant", content="Project is myagent."),
        Message(role="user", content="Remember I use Python 3.11."),
        Message(role="assistant", content="Remember I use pytest."),
    ]

    snapshot = manager.update("demo", messages)
    prompt = manager.build_memory_prompt("demo", query="python workspace")

    assert len(snapshot.facts) == len(set(fact.lower() for fact in snapshot.facts))
    assert prompt is not None
    assert prompt.count("- ") <= 4


def test_memory_prompt_prefers_query_relevant_facts() -> None:
    root = Path(".data") / "test-memory-retrieval" / str(uuid4())
    manager = MemoryManager(MemoryStore(root), refresh_min_messages=1)
    messages = [
        Message(role="user", content="Workspace is D:/Projects/myagent."),
        Message(role="assistant", content="Stored."),
        Message(role="user", content="I use Python 3.11 and pytest."),
        Message(role="assistant", content="Stored."),
        Message(role="user", content="Please use Chinese in later replies."),
        Message(role="assistant", content="Stored."),
    ]

    manager.update("demo", messages)
    prompt = manager.build_memory_prompt("demo", query="python test environment")

    assert prompt is not None
    assert "Python 3.11" in prompt
    assert "Workspace is D:/Projects/myagent." not in prompt or prompt.index("Python 3.11") > -1


def test_memory_manager_refreshes_summary_incrementally() -> None:
    root = Path(".data") / "test-memory-refresh" / str(uuid4())
    manager = MemoryManager(
        MemoryStore(root),
        max_recent_messages=6,
        summary_line_limit=4,
        refresh_min_messages=2,
    )
    first_messages = [
        Message(role="user", content="My name is Alice."),
        Message(role="assistant", content="Stored."),
    ]
    second_messages = [
        *first_messages,
        Message(role="user", content="The project is a local coding assistant."),
        Message(role="assistant", content="Stored again."),
    ]

    first = manager.update("demo", first_messages)
    second = manager.update("demo", second_messages)

    assert "user: My name is Alice." in first.summary
    assert "user: My name is Alice." in second.summary
    assert "user: The project is a local coding assistant." in second.summary


def test_memory_manager_builds_task_memory() -> None:
    root = Path(".data") / "test-memory-task" / str(uuid4())
    manager = MemoryManager(MemoryStore(root), refresh_min_messages=1)
    messages = [
        Message(role="user", content="实现多 MCP 支持。"),
        Message(role="assistant", content="已完成配置解析。"),
        Message(role="assistant", content="下一步做 tool loader 和测试。"),
        Message(role="assistant", content="当前阻塞是 Windows 环境报错。"),
    ]

    snapshot = manager.update("demo", messages)
    prompt = manager.build_memory_prompt("demo", query="测试和loader")

    assert snapshot.task.title == "实现多 MCP 支持。"
    assert snapshot.task.status == "active"
    assert any("已完成配置解析" in item for item in snapshot.task.completed_steps)
    assert any("下一步做 tool loader 和测试" in item for item in snapshot.task.pending_steps)
    assert any("Windows 环境报错" in item for item in snapshot.task.blockers)
    assert prompt is not None
    assert "Current task" in prompt
    assert "Pending steps" in prompt


def test_long_term_memory_is_shared_across_sessions() -> None:
    root = Path(".data") / "test-memory-long-term-shared" / str(uuid4())
    manager = MemoryManager(MemoryStore(root), refresh_min_messages=1)

    manager.update(
        "session-a",
        [
            Message(role="user", content="Project is a local repository assistant."),
            Message(role="assistant", content="Stored."),
            Message(role="user", content="Please use Chinese in later replies."),
            Message(role="assistant", content="Stored."),
        ],
    )

    prompt = manager.build_memory_prompt("session-b", query="中文 repository project")

    assert prompt is not None
    assert "Relevant long-term project facts" in prompt
    assert "Project is a local repository assistant." in prompt
    assert "Please use Chinese in later replies." in prompt


def test_long_term_memory_keeps_task_notes_for_new_sessions() -> None:
    root = Path(".data") / "test-memory-long-term-task-notes" / str(uuid4())
    manager = MemoryManager(MemoryStore(root), refresh_min_messages=1)

    manager.update(
        "session-a",
        [
            Message(role="user", content="实现长期记忆最小版。"),
            Message(role="assistant", content="已完成 memory store 扩展。"),
            Message(role="assistant", content="下一步做跨 session 检索注入。"),
            Message(role="assistant", content="当前阻塞是测试覆盖不足。"),
        ],
    )

    prompt = manager.build_memory_prompt("session-b", query="memory 测试 阻塞")

    assert prompt is not None
    assert "Relevant long-term project notes" in prompt
    assert "Completed task note: 已完成 memory store 扩展。" in prompt
    assert "Known blocker: 当前阻塞是测试覆盖不足。" in prompt
