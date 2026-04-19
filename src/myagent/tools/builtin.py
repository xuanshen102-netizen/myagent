from __future__ import annotations

import subprocess
from pathlib import Path

from myagent.tools.base import ToolSpec

MAX_FILE_CHARS = 12_000
BLOCKED_COMMAND_PATTERNS = (
    "remove-item",
    "del ",
    "erase ",
    "rd ",
    "rmdir ",
    "rm ",
    "mv ",
    "move-item",
    "rename-item",
    "git reset",
    "git checkout --",
    "format ",
    "shutdown",
    "reboot",
)


def build_builtin_tools(workspace_dir: Path) -> list[ToolSpec]:
    root = workspace_dir.resolve()

    def resolve_in_workspace(relative: str) -> Path:
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Access denied: path escapes workspace root.") from exc
        return target

    def read_file_tool(arguments: dict[str, object]) -> str:
        relative = str(arguments.get("path", ""))
        if not relative:
            return "Missing required argument: path"

        try:
            target = resolve_in_workspace(relative)
        except ValueError as exc:
            return str(exc)

        if not target.exists():
            return f"File not found: {relative}"
        if target.is_dir():
            return f"Expected a file but got a directory: {relative}"

        content = target.read_text(encoding="utf-8")
        if len(content) <= MAX_FILE_CHARS:
            return content
        return (
            content[:MAX_FILE_CHARS]
            + "\n\n[truncated]\n"
            + f"File exceeded {MAX_FILE_CHARS} characters. Narrow the request to a smaller section."
        )

    def list_dir_tool(arguments: dict[str, object]) -> str:
        relative = str(arguments.get("path", "."))
        try:
            target = resolve_in_workspace(relative)
        except ValueError as exc:
            return str(exc)

        if not target.exists():
            return f"Directory not found: {relative}"
        if not target.is_dir():
            return f"Expected a directory but got a file: {relative}"

        items = sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())
        return "\n".join(items) if items else "(empty directory)"

    def run_command_tool(arguments: dict[str, object]) -> str:
        command = str(arguments.get("command", ""))
        if not command:
            return "Missing required argument: command"

        normalized = " ".join(command.lower().split())
        if any(token in normalized for token in BLOCKED_COMMAND_PATTERNS):
            return "Command blocked by safety policy."

        if subprocess.os.name == "nt":
            shell_command = ["powershell", "-Command", command]
        else:
            shell_command = ["/bin/sh", "-lc", command]

        try:
            completed = subprocess.run(
                shell_command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return "Command timed out after 15 seconds."
        output = completed.stdout.strip()
        error = completed.stderr.strip()
        return (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{output or '(empty)'}\n"
            f"stderr:\n{error or '(empty)'}"
        )

    return [
        ToolSpec(
            name="read_file",
            description="Read a UTF-8 text file from the current workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=read_file_tool,
        ),
        ToolSpec(
            name="list_dir",
            description="List files and directories from the current workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
            handler=list_dir_tool,
        ),
        ToolSpec(
            name="run_command",
            description="Run a local shell command inside the current workspace. Destructive commands are blocked.",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            handler=run_command_tool,
        ),
    ]
