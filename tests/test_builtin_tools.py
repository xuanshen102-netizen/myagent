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

    read_ok = registry.execute("read_file", {"path": "hello.txt"})
    assert read_ok.ok
    assert read_ok.content == "hello world"

    large = registry.execute("read_file", {"path": "large.txt"})
    assert large.ok
    assert "[truncated]" in large.content
    assert large.metadata["truncated"] is True

    denied = registry.execute("read_file", {"path": "../outside.txt"})
    assert denied.status == "error"
    assert denied.error_type == "access_denied"
    assert "Access denied" in denied.content

    blocked = registry.execute(
        "run_command",
        {"command": "Remove-Item hello.txt"},
    )
    assert blocked.status == "error"
    assert blocked.error_type == "command_blocked"
    assert blocked.content == "Command blocked by safety policy."


def test_run_command_allows_safe_readonly_commands() -> None:
    workspace = Path(".data") / "test-tools-safe-command" / str(uuid4())
    workspace.mkdir(parents=True, exist_ok=True)

    registry = ToolRegistry()
    for tool in build_builtin_tools(workspace):
        registry.register(tool)

    result = registry.execute("run_command", {"command": "python --version"})

    assert result.ok
    assert "exit_code=0" in result.content
