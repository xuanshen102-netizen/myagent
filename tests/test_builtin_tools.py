from pathlib import Path
from uuid import uuid4

from myagent.tools.builtin import MAX_FILE_CHARS, build_builtin_tools
from myagent.tools.registry import ToolRegistry


def test_builtin_tools_enforce_workspace_and_command_policy() -> None:
    workspace = Path(".data") / "test-tools" / str(uuid4())
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "hello.txt").write_text("hello world", encoding="utf-8")
    (workspace / "large.txt").write_text("a" * (MAX_FILE_CHARS + 10), encoding="utf-8")

    registry = ToolRegistry()
    for tool in build_builtin_tools(workspace):
        registry.register(tool)

    assert registry.execute("read_file", {"path": "hello.txt"}) == "hello world"
    assert "[truncated]" in registry.execute("read_file", {"path": "large.txt"})
    assert "Access denied" in registry.execute("read_file", {"path": "../outside.txt"})
    assert "Command blocked by safety policy." == registry.execute(
        "run_command",
        {"command": "Remove-Item hello.txt"},
    )
