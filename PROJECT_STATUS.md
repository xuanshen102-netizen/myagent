# Project Status

## Current State

`myagent` is a minimal local agent kernel with:

- CLI entrypoint
- session persistence
- tool registry and builtin tools
- mock provider
- OpenAI-compatible provider with `responses` and `chat` modes
- basic safety limits for file and shell tools
- per-session JSONL logs
- provider raw-response debug dumps
- smoke scripts for compatibility and end-to-end validation

## Important Runtime Files

- `.env` is local-only and ignored by Git
- `.data/logs/` stores per-session runtime logs
- `.data/provider-debug/` stores the latest raw provider response
- `.data/debug-openai-response.json` is produced by the compatibility debug script

## Current Provider Notes

- Official OpenAI should prefer `MYAGENT_OPENAI_API_MODE=responses`
- Some third-party OpenAI-compatible providers only work with `MYAGENT_OPENAI_API_MODE=chat`
- If a provider returns HTML or a raw string, the `base_url` is likely pointing at a website instead of an API endpoint

## Key Commands

```powershell
conda activate myagent
python scripts\debug_openai_compat.py
python scripts\smoke_agent_tasks.py
python -m pytest tests -p no:cacheprovider
myagent "列出当前目录并说明项目结构"
```

## Tested Coverage

The current test suite covers:

- agent loop behavior
- duplicate tool-call protection
- builtin tool safety behavior
- CLI/provider configuration validation
- provider response parsing
- observability logging
- session persistence
