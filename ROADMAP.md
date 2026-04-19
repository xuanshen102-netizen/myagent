# Roadmap

## Completed

- project scaffold and Conda environment setup
- CLI agent kernel
- session persistence
- builtin tools: `list_dir`, `read_file`, `run_command`
- structured tool result model
- stronger shell command safety policy
- OpenAI provider integration
- custom `base_url` support
- `responses` / `chat` API mode support
- structured provider error model
- bounded provider retry and backoff
- runtime logging and raw provider dumps
- memory v1 with summary and fact persistence
- provider compatibility debug script
- smoke script for real-call validation
- regression test suite

## Near Term

1. Add runtime trace and metrics:
   - provider latency
   - tool latency
   - token usage
   - turn ids / request ids
2. Improve memory from v1 to v1.5:
   - fact deduplication
   - more selective memory injection
   - better summary refresh policy
3. Add extensible tool loading:
   - builtin vs external tools
   - configuration-driven enable/disable
   - tool namespaces
4. Run `scripts/smoke_agent_tasks.py` against the real provider and inspect failures.
5. Tune prompts and tool behavior using real logs.

## Later

1. Add MCP support after extensible tool loading is stable.
2. Add HTTP API before UI or channel integrations.
3. Add richer memory retrieval and consolidation beyond v1.
4. Add plugin or skill loading model.
5. Add channel integrations only after API and MCP are stable.
6. Add multi-agent or workflow orchestration only if real tasks justify it.
