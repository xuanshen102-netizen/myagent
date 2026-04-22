# 使用手册

## 1. 项目定位

`myagent` 当前是一套“本地优先的代码仓库智能助手”第一版实现，适合做：

- 仓库结构理解
- 代码文件搜索与解释
- 本地只读命令辅助
- 多轮会话与项目记忆
- 通过 MCP 扩展外部工具

当前不包含：

- Web 前端
- Telegram / Discord 等 channel
- 完整 MCP 协议面
- 多 agent 编排

## 2. 环境准备

推荐在 Windows 下使用 Conda：

```powershell
conda create -n myagent python=3.11 -y
conda activate myagent
pip install -e .
pip install pytest
```

## 3. 配置 `.env`

先复制模板：

```powershell
Copy-Item .env.example .env
```

### 3.1 只做本地验证

```dotenv
MYAGENT_PROVIDER=mock
MYAGENT_MODEL=gpt-4.1-mini
MYAGENT_DATA_DIR=.data
MYAGENT_ENABLED_BUILTIN_TOOLS=list_dir,repo_search,read_file,run_command
```

### 3.2 接 OpenAI-compatible provider

```dotenv
OPENAI_API_KEY=your_key_here
MYAGENT_PROVIDER=openai
MYAGENT_MODEL=gpt-4.1-mini
MYAGENT_OPENAI_API_MODE=responses
MYAGENT_OPENAI_BASE_URL=
MYAGENT_DATA_DIR=.data
MYAGENT_ENABLED_BUILTIN_TOOLS=list_dir,repo_search,read_file,run_command
```

## 4. 启动方式

### 4.1 CLI 单次调用

```powershell
myagent "读取 README.md 并总结这个项目"
```

### 4.2 CLI 交互模式

```powershell
myagent
```

退出：

```text
exit
```

### 4.3 指定 session

```powershell
myagent --session demo "总结这个仓库结构"
```

### 4.4 指定 skill

```powershell
myagent --skill repo_explainer "总结这个仓库结构"
```

## 5. 现有能力怎么用

### 5.1 仓库问答

推荐提问方式：

- “总结这个仓库结构”
- “搜索 `build_server` 在哪里定义，并解释实现”
- “这个项目的 memory 是怎么实现的”

当前仓库问答闭环是：

1. `repo_search` 搜候选文件
2. `read_file` 精读相关文件
3. Agent 汇总回答

### 5.2 本地命令辅助

示例：

```powershell
myagent "执行 python --version 并解释结果"
myagent "执行 git status 并说明当前工作区状态"
```

说明：

- 只允许受控只读命令
- 危险命令会被策略阻止

### 5.3 记忆与跨 session 复用

如果你在一个 session 中说：

- “项目是本地代码仓库助手”
- “请用中文回复”

后续 session 里再次提相关问题时，系统会从长期记忆里按 query 注入这些信息。

说明：

- session 级记忆保存在 `.data/memory/<session>.json`
- 项目级长期记忆保存在 `.data/memory/_long_term.json`

### 5.4 MCP 工具扩展

如果你要挂多个 MCP server：

```dotenv
MYAGENT_MCP_SERVERS=[{"name":"repo","command":"python","args":["path\\to\\repo_mcp.py"],"timeout_seconds":20},{"name":"browser","command":"python","args":["path\\to\\browser_mcp.py"],"timeout_seconds":20}]
```

MCP 工具暴露格式：

```text
mcp__<server_name>__<tool_name>
```

当前仅支持：

- `stdio`
- `initialize`
- `tools/list`
- `tools/call`

## 6. HTTP API 用法

启动：

```powershell
myagent-api
```

默认地址：

```text
http://127.0.0.1:8000
```

### 6.1 健康检查

```powershell
curl http://127.0.0.1:8000/health
```

### 6.2 发起对话

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"demo\",\"message\":\"搜索 memory 是怎么实现的\"}"
```

### 6.3 查看 session

```powershell
curl http://127.0.0.1:8000/sessions/demo
```

## 7. Skill 用法

Skill 默认查找位置：

- 内置：`src/myagent/builtin_skills/`
- 项目级：`.myagent/skills/`
- 用户级：`MYAGENT_SKILL_DIRS`

项目级 skill 结构：

```text
.myagent/
└─ skills/
   └─ repo_explainer/
      └─ SKILL.md
```

最小 `SKILL.md` 示例：

```md
---
name: repo_explainer
description: Explain repository structure.
triggers: [repo, 仓库]
preferred-tools: [repo_search, read_file]
response-style: Return a concise overview.
---

Inspect the repository before concluding.
Summarize the layout, entrypoints, and key modules.
```

## 8. 运行数据说明

运行时数据位于 `.data/`：

- `.data/sessions/`：session transcript
- `.data/memory/`：session memory 与长期记忆
- `.data/logs/`：JSONL 运行日志
- `.data/provider-debug/`：provider 原始响应 dump

## 9. 测试与验证

### 9.1 全量测试

```powershell
python -m pytest tests -p no:cacheprovider
```

当前状态：

- `65 passed`

### 9.2 Provider 兼容性调试

```powershell
python scripts\debug_openai_compat.py
```

### 9.3 Smoke 场景

```powershell
python scripts\smoke_agent_tasks.py
```

### 9.4 推荐手动验证

```powershell
myagent "列出当前目录并说明项目结构"
myagent "搜索 build_server 在哪里定义，并总结实现"
myagent "执行 python --version 并解释结果"
myagent --session demo "项目是本地代码仓库助手，请用中文回复"
myagent --session demo "总结一下我们现在在做什么"
```

## 10. 当前已实现与未实现

### 已实现

- CLI
- 最小 HTTP API
- OpenAI-compatible provider
- 多轮 tool loop
- `repo_search` 仓库搜索
- `read_file` / `list_dir` / `run_command`
- session memory
- task memory
- 最小长期记忆
- 多 MCP server
- `SKILL.md` skill runtime

### 仍未实现

- channel 接入
- 更完整的 memory consolidation
- 更完整的 MCP 协议面
- 更广的 provider 生态
- 后台调度与主动执行
- 更强的 skill 资源隔离与版本治理
