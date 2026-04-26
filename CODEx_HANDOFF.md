# Codex Handoff

## Read This First

1. `PROJECT_STATUS.md`
2. `KERNEL_STATUS.md`
3. `DEVELOPMENT_TRACKER.md`
4. `README.md`

## Current Project Position

`myagent` is no longer just a minimal local tool-calling assistant.

Current accurate positioning:

- local-first
- repository-oriented
- tool-based agent runtime
- explicit ReAct execution trace

What “explicit ReAct execution trace” means in this repo:

- each round can produce a `thought_summary`
- tool calls are recorded as structured `actions`
- tool results are summarized as structured `observations`
- logs include `react_step` events

The project is still **not** a full coding agent yet.
It does not yet have file mutation, validation, git awareness, or a coding-task state machine.

## Source Layout

- `src/myagent/agent/loop.py`: turn loop, tool execution, duplicate-call protection, ReAct trace
- `src/myagent/providers/openai_provider.py`: OpenAI-compatible provider, error mapping, debug dumps
- `src/myagent/providers/base.py`: message / tool / provider protocol objects
- `src/myagent/tools/builtin.py`: builtin file/shell tools and safety limits
- `src/myagent/observability.py`: JSONL runtime event logger
- `scripts/debug_openai_compat.py`: inspect raw third-party provider payloads
- `scripts/smoke_agent_tasks.py`: run real-provider smoke scenarios

## What Changed Most Recently

Latest meaningful runtime change:

- the loop was upgraded from an implicit tool loop to a first-stage ReAct runtime

Implemented:

- prompt-level ReAct guidance
- `thought_summary`
- action / observation trace metadata
- `react_step` logs
- tests that verify ReAct trace behavior

## Local Expectations

- Python environment: Conda env named `myagent`
- `.env` must exist locally but must never be committed
- preferred test command:

```powershell
$env:PYTHONPATH='src'
D:\anaconda\envs\myagent\python.exe -m pytest tests -p no:cacheprovider
```

## Current Known Risks

- third-party OpenAI-compatible providers may not fully support `responses`
- `run_command` is intentionally conservative but still needs stronger task-aware guardrails
- README still contains legacy encoding noise and is not the most reliable status source
- ReAct is implemented at runtime-trace level, but coding-task execution phases are not implemented yet

## Recommended Next Step

Do not spend the next iteration on more general chat capabilities.

Move directly into coding-agent evolution:

1. add coding task phases: `inspect / edit / verify / done`
2. add safe file mutation tools
3. add structured validation tools
4. add git read-only tools
