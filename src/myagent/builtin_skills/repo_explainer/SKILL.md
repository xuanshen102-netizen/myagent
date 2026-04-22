---
name: repo_explainer
description: Explain repository structure, entrypoints, and key modules.
triggers: [repo, repository, 项目结构, 仓库, readme, 目录结构]
preferred-tools: [list_dir, read_file]
disallowed-tools: [run_command]
response-style: Return a concise repository overview with likely entrypoints and key files.
---

Inspect the repository before concluding. Prefer structure-first explanations.
Summarize the project layout, likely entrypoints, and key modules.
