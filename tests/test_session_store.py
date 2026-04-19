from pathlib import Path
from uuid import uuid4

from myagent.providers.base import Message, ToolResult
from myagent.session.store import SessionStore


def test_session_store_roundtrip() -> None:
    root = Path(".data") / "test-session-store" / str(uuid4())
    root.mkdir(parents=True, exist_ok=True)
    store = SessionStore(root)
    messages = [
        Message(role="user", content="hello"),
        Message(
            role="tool",
            content="ok",
            tool_call_id="call_1",
            tool_result=ToolResult.success("ok", metadata={"path": "README.md"}),
        ),
    ]
    store.save("demo", messages)

    loaded = store.load("demo")
    assert len(loaded) == 2
    assert loaded[0].role == "user"
    assert loaded[0].content == "hello"
    assert loaded[1].tool_result is not None
    assert loaded[1].tool_result.metadata["path"] == "README.md"
