from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from myagent.providers.base import ToolResult
from myagent.tools.base import ToolSpec

MAX_FILE_CHARS = 12_000
MAX_COMMAND_OUTPUT_CHARS = 8_000
MAX_SEARCH_RESULTS = 20
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

    def repo_search_tool(arguments: dict[str, object]) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        path = str(arguments.get("path", ".") or ".")
        mode = str(arguments.get("mode", "hybrid") or "hybrid").strip().lower()
        file_glob = str(arguments.get("file_glob", "") or "").strip()

        if not query:
            return ToolResult.failure(
                "Missing required argument: query",
                error_type="invalid_arguments",
            )
        if mode not in {"hybrid", "filename", "content"}:
            return ToolResult.failure(
                "Invalid mode. Expected one of: hybrid, filename, content",
                error_type="invalid_arguments",
                metadata={"mode": mode},
            )
        try:
            target = resolve_in_workspace(path)
        except ValueError as exc:
            return ToolResult.failure(
                str(exc),
                error_type="access_denied",
                metadata={"path": path},
            )
        if not target.exists():
            return ToolResult.failure(
                f"Search path not found: {path}",
                error_type="not_found",
                metadata={"path": path},
            )
        if not target.is_dir():
            return ToolResult.failure(
                f"Expected a directory but got a file: {path}",
                error_type="invalid_target",
                metadata={"path": path},
            )

        query_tokens = _tokenize_search_text(query)
        matches: list[dict[str, object]] = []
        for candidate in target.rglob("*"):
            if not candidate.is_file():
                continue
            relative_path = candidate.relative_to(root).as_posix()
            if file_glob and not fnmatch.fnmatch(relative_path, file_glob):
                continue
            score = 0
            reason_parts: list[str] = []
            path_tokens = _tokenize_search_text(relative_path)
            path_overlap = len(query_tokens & path_tokens)
            if mode in {"hybrid", "filename"} and path_overlap:
                score += path_overlap * 5
                reason_parts.append(f"filename overlap={path_overlap}")

            snippet = ""
            if mode in {"hybrid", "content"}:
                try:
                    content = candidate.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    content = ""
                content_score, snippet = _score_content_match(content, query, query_tokens)
                if content_score:
                    score += content_score
                    reason_parts.append("content match")

            if score <= 0:
                continue
            matches.append(
                {
                    "path": relative_path,
                    "score": score,
                    "reason": ", ".join(reason_parts) or "matched",
                    "snippet": snippet,
                }
            )

        matches.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
        matches = matches[:MAX_SEARCH_RESULTS]
        if not matches:
            return ToolResult.success(
                "No repository matches found.",
                structured_content={"matches": []},
                metadata={"query": query, "path": path, "mode": mode, "count": 0},
            )

        rendered = "\n".join(
            f"{item['path']} | score={item['score']} | {item['reason']}"
            + (f" | snippet={item['snippet']}" if item["snippet"] else "")
            for item in matches
        )
        return ToolResult.success(
            rendered,
            structured_content={"matches": matches},
            metadata={"query": query, "path": path, "mode": mode, "count": len(matches)},
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
            name="repo_search",
            description=(
                "Search the repository for relevant files by filename and file content. "
                "Use this before reading files when the exact path is unknown."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "path": {"type": "string"},
                    "mode": {"type": "string", "enum": ["hybrid", "filename", "content"]},
                    "file_glob": {"type": "string"},
                },
                "required": ["query"],
            },
            handler=repo_search_tool,
        ),
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


def _tokenize_search_text(text: str) -> set[str]:
    tokens: set[str] = set()
    current: list[str] = []
    for ch in text.lower():
        if ch.isalnum() or ch in {"_", "-"}:
            current.append(ch)
            continue
        if len(current) >= 2:
            tokens.add("".join(current))
        current = []
    if len(current) >= 2:
        tokens.add("".join(current))
    return tokens


def _score_content_match(content: str, query: str, query_tokens: set[str]) -> tuple[int, str]:
    if not content:
        return 0, ""
    lowered = content.lower()
    score = 0
    snippet = ""
    query_lower = query.lower().strip()
    if query_lower and query_lower in lowered:
        score += 8
        snippet = _build_snippet(content, lowered.index(query_lower), len(query))
    token_overlap = [token for token in query_tokens if token in lowered]
    if token_overlap:
        score += len(token_overlap) * 2
        if not snippet:
            first = token_overlap[0]
            snippet = _build_snippet(content, lowered.index(first), len(first))
    return score, snippet


def _build_snippet(content: str, start: int, length: int) -> str:
    snippet_start = max(0, start - 40)
    snippet_end = min(len(content), start + length + 80)
    snippet = " ".join(content[snippet_start:snippet_end].split())
    return snippet[:180]
