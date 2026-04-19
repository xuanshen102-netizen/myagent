# Codex Handoff

## Read This First

1. `PROJECT_STATUS.md`
2. `ROADMAP.md`
3. `README.md`

## Source Layout

- `src/myagent/agent/loop.py`: turn loop, tool execution, duplicate-call protection
- `src/myagent/providers/openai_provider.py`: OpenAI-compatible provider, error mapping, debug dumps
- `src/myagent/tools/builtin.py`: builtin file/shell tools and safety limits
- `src/myagent/observability.py`: JSONL runtime event logger
- `scripts/debug_openai_compat.py`: inspect raw third-party provider payloads
- `scripts/smoke_agent_tasks.py`: run real-provider smoke scenarios

## Local Expectations

- Python environment: Conda env named `myagent`
- `.env` must exist locally but must never be committed
- Run tests with:

```powershell
python -m pytest tests -p no:cacheprovider
```

## Current Known Risks

- Third-party OpenAI-compatible providers may not fully support `responses`
- `run_command` is intentionally conservative but still needs a stronger allowlist design
- README contains some encoding noise from earlier edits; functional docs live in the handoff files above
