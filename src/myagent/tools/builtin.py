from __future__ import annotations

import subprocess
from pathlib import Path

from myagent.providers.base import ToolResult
from myagent.tools.base import ToolSpec

MAX_FILE_CHARS = 12_000
MAX_COMMAND_OUTPUT_CHARS = 8_000
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
    "copy-item",
    "cp ",
    "git reset",
    "git checkout --",
    "git clean",
    "format ",
    "shutdown",
    "reboot",
)
BLOCKED_COMMAND_OPERATORS = (";", "&&", "||", "|", ">", ">>", "<")
ALLOWED_COMMAND_PREFIXES = (
    "python ",
    "python.exe ",
    "py ",
    "git status",
    "git diff",
    "git log",
    "dir",
    "ls",
    "pwd",
    "where ",
    "Get-ChildItem",
    "Get-Location",
    "Get-Content ",
    "Select-String ",
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

    def read_file_tool(arguments: dict[str, object]) -> ToolResult:
        relative = str(arguments.get("path", ""))
        if not relative:
            return ToolResult.failure(
                "Missing required argument: path",
                error_type="invalid_arguments",
            )

        try:
            target = resolve_in_workspace(relative)
        except ValueError as exc:
            return ToolResult.failure(
                str(exc),
                error_type="access_denied",
                metadata={"path": relative},
            )

        if not target.exists():
            return ToolResult.failure(
                f"File not found: {relative}",
                error_type="not_found",
                metadata={"path": relative},
            )
        if target.is_dir():
            return ToolResult.failure(
                f"Expected a file but got a directory: {relative}",
                error_type="invalid_target",
                metadata={"path": relative},
            )

        content = target.read_text(encoding="utf-8")
        if len(content) <= MAX_FILE_CHARS:
            return ToolResult.success(
                content,
                metadata={"path": relative, "truncated": False},
            )
        truncated = (
            content[:MAX_FILE_CHARS]
            + "\n\n[truncated]\n"
            + f"File exceeded {MAX_FILE_CHARS} characters. Narrow the request to a smaller section."
        )
        return ToolResult.success(
            truncated,
            metadata={"path": relative, "truncated": True},
        )

    def list_dir_tool(arguments: dict[str, object]) -> ToolResult:
        relative = str(arguments.get("path", "."))
        try:
            target = resolve_in_workspace(relative)
        except ValueError as exc:
            return ToolResult.failure(
                str(exc),
                error_type="access_denied",
                metadata={"path": relative},
            )

        if not target.exists():
            return ToolResult.failure(
                f"Directory not found: {relative}",
                error_type="not_found",
                metadata={"path": relative},
            )
        if not target.is_dir():
            return ToolResult.failure(
                f"Expected a directory but got a file: {relative}",
                error_type="invalid_target",
                metadata={"path": relative},
            )

        items = sorted(item.name + ("/" if item.is_dir() else "") for item in target.iterdir())
        return ToolResult.success(
            "\n".join(items) if items else "(empty directory)",
            structured_content={"items": items},
            metadata={"path": relative, "count": len(items)},
        )

    def run_command_tool(arguments: dict[str, object]) -> ToolResult:
        command = str(arguments.get("command", ""))
        if not command:
            return ToolResult.failure(
                "Missing required argument: command",
                error_type="invalid_arguments",
            )

        stripped = command.strip()
        normalized = " ".join(stripped.lower().split())
        if any(token in normalized for token in BLOCKED_COMMAND_PATTERNS):
            return ToolResult.failure(
                "Command blocked by safety policy.",
                error_type="command_blocked",
                metadata={"reason": "blocked_pattern"},
            )
        if any(operator in stripped for operator in BLOCKED_COMMAND_OPERATORS):
            return ToolResult.failure(
                "Command blocked by safety policy.",
                error_type="command_blocked",
                metadata={"reason": "blocked_operator"},
            )
        if not any(
            normalized == prefix or normalized.startswith(prefix)
            for prefix in ALLOWED_COMMAND_PREFIXES
        ):
            return ToolResult.failure(
                "Command blocked by safety policy.",
                error_type="command_blocked",
                metadata={"reason": "not_in_allowlist"},
            )

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
            return ToolResult.failure(
                "Command timed out after 15 seconds.",
                error_type="timeout",
                metadata={"command": command},
            )
        output = completed.stdout.strip()
        error = completed.stderr.strip()
        rendered = (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{_truncate_output(output) or '(empty)'}\n"
            f"stderr:\n{_truncate_output(error) or '(empty)'}"
        )
        status = "ok" if completed.returncode == 0 else "error"
        if status == "ok":
            return ToolResult.success(
                rendered,
                structured_content={
                    "exit_code": completed.returncode,
                    "stdout": output,
                    "stderr": error,
                },
                metadata={"command": command},
            )
        return ToolResult.failure(
            rendered,
            error_type="nonzero_exit",
            structured_content={
                "exit_code": completed.returncode,
                "stdout": output,
                "stderr": error,
            },
            metadata={"command": command},
        )

    def _truncate_output(value: str) -> str:
        if len(value) <= MAX_COMMAND_OUTPUT_CHARS:
            return value
        return (
            value[:MAX_COMMAND_OUTPUT_CHARS]
            + "\n\n[truncated]\n"
            + f"Output exceeded {MAX_COMMAND_OUTPUT_CHARS} characters."
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
