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

    prompt = manager.build_memory_prompt("demo")

    assert prompt is not None
    assert "Conversation summary" in prompt
    assert "Important facts" in prompt


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
    prompt = manager.build_memory_prompt("demo")

    assert len(snapshot.facts) == len(set(fact.lower() for fact in snapshot.facts))
    assert prompt is not None
    assert prompt.count("- ") <= 4
