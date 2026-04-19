from pathlib import Path
from uuid import uuid4

from myagent.observability import EventLogger


def test_event_logger_writes_jsonl_entry() -> None:
    root = Path(".data") / "test-logs" / str(uuid4())
    logger = EventLogger(root)

    logger.log("demo", "turn_start", {"value": 1, "items": ["a", "b"]}, trace_id="trace-123")

    path = root / "demo.jsonl"
    content = path.read_text(encoding="utf-8")
    assert '"event": "turn_start"' in content
    assert '"value": 1' in content
    assert '"trace_id": "trace-123"' in content
