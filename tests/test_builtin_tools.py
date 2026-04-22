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


def test_repo_search_finds_files_by_name_and_content() -> None:
    workspace = Path(".data") / "test-tools-repo-search" / str(uuid4())
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text("This project is a local coding assistant.", encoding="utf-8")
    (workspace / "src" / "memory.py").write_text(
        "class MemoryManager:\n    pass\n# project memory consolidation\n",
        encoding="utf-8",
    )

    registry = ToolRegistry()
    for tool in build_builtin_tools(workspace):
        registry.register(tool)

    filename_match = registry.execute("repo_search", {"query": "memory", "mode": "filename"})
    content_match = registry.execute("repo_search", {"query": "coding assistant", "mode": "content"})

    assert filename_match.ok
    assert "src/memory.py" in filename_match.content
    assert filename_match.structured_content is not None
    assert filename_match.structured_content["matches"][0]["path"] == "src/memory.py"

    assert content_match.ok
    assert "README.md" in content_match.content
    assert "snippet=" in content_match.content
