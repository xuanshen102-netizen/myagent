from pathlib import Path
from uuid import uuid4

from myagent.providers.base import Message
from myagent.session.store import SessionStore


def test_session_store_roundtrip() -> None:
    root = Path(".data") / "test-session-store" / str(uuid4())
    root.mkdir(parents=True, exist_ok=True)
    store = SessionStore(root)
    messages = [Message(role="user", content="hello")]
    store.save("demo", messages)

    loaded = store.load("demo")
    assert len(loaded) == 1
    assert loaded[0].role == "user"
    assert loaded[0].content == "hello"
