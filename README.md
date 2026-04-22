# myagent

`myagent` 是一个面向代码与工作区自动化任务的本地 Agent 内核。

当前重点：

- 可运行的 CLI Agent
- OpenAI 兼容模型接入
- 带安全限制的本地工具调用
- 会话持久化
- memory v2 + 最小长期记忆
- `SKILL.md` skill runtime
- runtime trace 与调试日志
- 基于 `stdio` 的最小 MCP 工具接入
- 最小 HTTP API

项目目前仍然是“内核优先、本地优先”的形态，还不是完整的 `nanobot` 风格平台；暂时还没有 channel、插件系统和后台调度。

## 当前能力

### Agent 内核

- 单次调用与交互式 CLI
- 多轮工具调用循环
- 重复工具调用保护
- 单轮工具失败预算
- 结构化工具错误与 provider 错误

### Provider 层

- 用于本地验证的 `mock` provider
- OpenAI 兼容 provider
- 支持 `responses` 和 `chat` 两种 API 模式
- 对可重试错误支持 retry / backoff
- 记录原始 provider 响应，便于兼容性排查

### 工具层

- 内置工具：
  - `list_dir`
  - `repo_search`
  - `read_file`
  - `run_command`
- 文件访问限定在当前工作区
- 命令执行有 allow/block 安全策略
- 工具结果使用结构化 `ToolResult`，包含：
  - `status`
  - `content`
  - `error_type`
  - `metadata`
  - 可选结构化返回内容

### Memory

- 会话消息持久化
- 在 `.data/memory/` 下保存 memory 快照
- 增量更新对话摘要
- 从对话中提取稳定事实
- 维护 task memory：当前任务、已完成步骤、待办与阻塞
- 对事实去重
- 按当前用户问题做相关性检索
- 动态注入相关摘要与事实到后续对话上下文
- 项目级长期记忆：跨 session 共享稳定事实与任务结论

### 仓库问答闭环

- `repo_search`：按文件名和文件内容搜索候选文件
- `read_file`：精读候选文件
- Agent prompt 明确约束“search -> read -> synthesize”
- 适合做仓库结构理解、入口定位、模块解释与实现问答

### Skill

- 内置 `repo_explainer`、`code_debugger`、`feature_implementer`
- 支持显式指定 skill
- 支持基于 query 的简单自动选择
- skill 通过 `SKILL.md` 定义任务策略、工具偏好与输出风格
- 支持内置 skill 目录与项目级 `.myagent/skills/`
- 支持通过 `MYAGENT_SKILL_DIRS` 追加用户级 skill 目录

### MCP

- 最小 `stdio` MCP client
- 支持多个 MCP server 配置与聚合加载
- 支持：
  - `initialize`
  - `tools/list`
  - `tools/call`
- MCP 工具会以 `mcp__<server_name>__<tool_name>` 的形式暴露给 Agent

### HTTP API

- `GET /health`
- `POST /chat`
- `GET /sessions/{id}`
- 复用现有 kernel、memory 与 session

### 可观测性

- 每个 session 的 JSONL 日志
- runtime event 带 `trace_id`
- 记录 provider 延迟与重试信息
- 记录工具调用延迟
- 保存 provider 原始响应 dump

## 项目结构

```text
.
├─ src/myagent/
│  ├─ agent/        # agent 主循环与运行时控制
│  ├─ providers/    # 模型 provider 适配层
│  ├─ session/      # 会话持久化
│  ├─ tools/        # 内置工具与工具加载
│  ├─ cli.py        # 命令行入口
│  ├─ config.py     # 环境变量配置
│  ├─ memory.py     # memory v2
│  └─ mcp.py        # 最小 stdio MCP client
├─ scripts/
├─ tests/
├─ .env.example
├─ USER_MANUAL.md
└─ pyproject.toml
```

## 快速开始

### 1. 创建环境

Windows 下推荐：

```powershell
conda create -n myagent python=3.11 -y
conda activate myagent
pip install -e .
pip install pytest
```

### 2. 生成本地配置

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`。

如果只是本地验证内核，可先用 `mock`：

```dotenv
MYAGENT_PROVIDER=mock
MYAGENT_MODEL=gpt-4.1-mini
MYAGENT_DATA_DIR=.data
```

如果要接 OpenAI：

```dotenv
OPENAI_API_KEY=your_key_here
MYAGENT_OPENAI_BASE_URL=
MYAGENT_OPENAI_API_MODE=responses
MYAGENT_MODEL=gpt-4.1-mini
MYAGENT_PROVIDER=openai
MYAGENT_DATA_DIR=.data
MYAGENT_SYSTEM_PROMPT=
```

### 3. 运行 CLI

单次调用：

```powershell
myagent "读取 README.md 并总结这个项目"
```

交互模式：

```powershell
myagent
```

### 4. 运行 HTTP API

```powershell
myagent-api
```

默认监听：

```text
http://127.0.0.1:8000
```

## MCP 配置

当前已经支持最小的 `stdio` MCP 接入，并支持多 MCP server 聚合。

推荐使用多 MCP 配置：

```dotenv
MYAGENT_MCP_SERVERS=[{"name":"repo","command":"python","args":["path\\to\\repo_mcp.py"],"timeout_seconds":20},{"name":"browser","command":"python","args":["path\\to\\browser_mcp.py"],"timeout_seconds":20}]
```

如果你只想继续使用兼容的单 MCP 配置，也可以保留：

```dotenv
MYAGENT_MCP_ENABLED=1
MYAGENT_MCP_COMMAND=python
MYAGENT_MCP_ARGS=path\to\your_mcp_server.py
MYAGENT_MCP_TIMEOUT_SECONDS=20
```

如果你还想保留内置工具，可以继续配置：

```dotenv
MYAGENT_ENABLED_BUILTIN_TOOLS=list_dir,repo_search,read_file,run_command
```

加载后的 MCP 工具名格式为：

```text
mcp__server_name__tool_name
```

当前 MCP 范围：

- 只支持 `stdio` transport
- 只接工具能力
- 还不支持 HTTP/SSE transport
- 还不支持 resources / prompts / sampling

## Skill 配置

内置 skill 使用 `SKILL.md` 目录结构定义，运行时会做发现和惰性加载。

默认查找位置：

- 内置：`src/myagent/builtin_skills/`
- 项目级：`.myagent/skills/`
- 用户级：`MYAGENT_SKILL_DIRS`

项目级 skill 结构示例：

```text
.myagent/
└─ skills/
   └─ repo_explainer/
      └─ SKILL.md
```

`SKILL.md` 示例：

```md
---
name: repo_explainer
description: Explain repository structure.
triggers: [repo, 仓库]
preferred-tools: [list_dir, read_file]
response-style: Return a concise overview.
---

Inspect the repository before concluding.
Summarize the layout, entrypoints, and key modules.
```

如果你要追加用户级 skill 目录，可以在 `.env` 里配置：

```dotenv
MYAGENT_SKILL_DIRS=D:\skills;D:\team-skills
```

## HTTP API

当前 API 为最小可用版本。

接口：

- `GET /health`
- `POST /chat`
- `GET /sessions/{id}`

示例：

```powershell
curl http://127.0.0.1:8000/health
```

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"demo\",\"message\":\"读取 README.md 并总结这个项目\"}"
```

## 运行时文件

运行产生的数据都写在 `.data/` 下：

- `.data/sessions/`：会话持久化
- `.data/memory/`：session memory 快照与项目级长期记忆
- `.data/logs/`：每个 session 的 JSONL 事件日志
- `.data/provider-debug/`：最近一次 provider 原始响应
- `.data/debug-openai-response.json`：兼容性调试脚本输出

## 调试与验证

运行完整测试：

```powershell
python -m pytest tests -p no:cacheprovider
```

调试 OpenAI / OpenAI-compatible 接口：

```powershell
python scripts\debug_openai_compat.py
```

运行 smoke 场景：

```powershell
python scripts\smoke_agent_tasks.py
```

推荐直接执行的 CLI 检查：

```powershell
myagent "列出当前目录并说明项目结构"
myagent "搜索 build_server 在哪里定义，并总结实现"
myagent "读取 README.md 并总结这个项目"
myagent "执行 python --version 并解释结果"
```

## 当前限制

目前仍未实现：

- channel 接入
- 更强的 skill 资源加载、隔离与版本治理
- 后台调度与主动执行
- 更完整的 memory consolidation
- `mock` 与 OpenAI-compatible 之外的多 provider 生态
- 更完整的 MCP 协议面

## 更多状态信息

另见：

- [PROJECT_STATUS.md](D:/Projects/myagent/PROJECT_STATUS.md)
- [ROADMAP.md](D:/Projects/myagent/ROADMAP.md)
- [KERNEL_STATUS.md](D:/Projects/myagent/KERNEL_STATUS.md)
- [FEATURE_STATUS.md](D:/Projects/myagent/FEATURE_STATUS.md)
- [DEVELOPMENT_TRACKER.md](D:/Projects/myagent/DEVELOPMENT_TRACKER.md)
- [USER_MANUAL.md](D:/Projects/myagent/USER_MANUAL.md)
