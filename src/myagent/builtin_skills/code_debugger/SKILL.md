---
name: code_debugger
description: Debug command failures, errors, and broken code paths.
triggers: [debug, error, bug, 失败, 报错, 调试, 测试失败]
preferred-tools: [read_file, run_command]
response-style: Return symptom, likely cause, evidence, and next step.
---

Focus on reproducing and localizing the failure.
Explain observed errors, possible causes, and next validation steps.
Prefer direct evidence from files and command output.
