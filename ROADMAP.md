# Roadmap

## Completed

- Project scaffold and Conda environment setup
- CLI agent kernel
- session persistence
- builtin tools: `list_dir`, `read_file`, `run_command`
- OpenAI provider integration
- custom `base_url` support
- `responses` / `chat` API mode support
- provider compatibility debug script
- runtime logging and raw provider dumps
- smoke script for real-call validation
- regression test suite

## Near Term

1. Run `scripts/smoke_agent_tasks.py` against the real provider and inspect failures.
2. Tune prompt and tool behavior based on real-call logs.
3. Tighten `run_command` policy with a more explicit allow/block model.
4. Improve tool result formatting for large outputs and command failures.
5. Add structured retry / fallback logic for provider failures.

## Later

1. Add richer memory beyond session transcript persistence.
2. Add plugin or skill loading model.
3. Add HTTP API or web UI.
4. Add multi-agent or workflow orchestration only if needed by real tasks.
