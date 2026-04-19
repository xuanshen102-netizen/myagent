# Project Status

## Current State

`myagent` is now a working local agent kernel with a hardened core, not just a scaffold.

Implemented today:

- CLI entrypoint with interactive and one-shot modes
- session persistence
- structured tool registry and builtin tools
- OpenAI-compatible provider with `responses` and `chat` modes
- structured provider errors
- bounded provider retry and backoff
- structured tool results
- stronger shell command policy
- per-session JSONL logs
- provider raw-response debug dumps
- memory v1 with summary and fact persistence
- smoke scripts for compatibility and end-to-end validation
- regression test suite

## Core Capabilities

### Agent Kernel

- multi-round tool loop
- duplicate tool-call protection
- per-turn tool failure budget
- consecutive tool-error guard
- structured tool execution records in runtime logs

### Provider Layer

- `mock` provider for local validation
- OpenAI-compatible provider
- configurable `responses` / `chat` API mode
- structured provider error classification
- retry for retryable provider failures
- raw payload debug dump for compatibility debugging

### Tool Layer

- builtin tools: `list_dir`, `read_file`, `run_command`
- workspace path enforcement for file access
- command allow/block policy for shell execution
- structured tool result object with:
  - `status`
  - `content`
  - `error_type`
  - `metadata`
  - optional structured payload

### Memory

- session transcript persistence
- memory v1 snapshot persistence under `.data/memory/`
- summary built from recent conversational turns
- simple fact extraction from user/assistant content
- memory prompt injection on future turns for the same session

### Observability

- per-session JSONL event logs under `.data/logs/`
- tool result status and error metadata in logs
- provider error metadata in logs
- provider raw-response dumps under `.data/provider-debug/`

## Important Runtime Files

- `.env` is local-only and ignored by Git
- `.data/sessions/` stores persisted session transcripts
- `.data/memory/` stores memory v1 snapshots
- `.data/logs/` stores per-session runtime logs
- `.data/provider-debug/` stores the latest raw provider response
- `.data/debug-openai-response.json` is produced by the compatibility debug script

## Current Limitations

The project is still a kernel-first local agent, not a full `nanobot`-style platform yet.

Still missing:

- MCP integration
- extensible external tool loading
- HTTP API
- channel integrations
- advanced memory retrieval and consolidation
- multi-provider ecosystem beyond `mock` + OpenAI-compatible endpoints
- scheduled/background agent execution
- plugin or skill loading model

## Key Commands

```powershell
conda activate myagent
python scripts\debug_openai_compat.py
python scripts\smoke_agent_tasks.py
python -m pytest tests -p no:cacheprovider
myagent "列出当前目录并说明项目结构"
myagent "读取 README.md 并总结这个项目"
```

## Tested Coverage

The current test suite covers:

- agent loop behavior
- duplicate tool-call protection
- per-turn tool failure budget
- builtin tool safety behavior
- CLI/provider configuration validation
- provider response parsing
- provider retry behavior
- structured provider error behavior
- observability logging
- session persistence
- memory summary and fact persistence

Current passing status:

- `28` tests passing in the local `myagent` Conda environment

## Recommended Next Work

1. Add runtime trace and metrics: latency, token usage, request ids.
2. Improve memory from v1 to explicit retrieval and compaction.
3. Add extensible tool loading before introducing MCP.
4. Introduce MCP after tool loading and trace are stable.
5. Add HTTP API and only then consider channels or UI.
