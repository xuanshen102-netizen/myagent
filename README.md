# myagent

`myagent` 是一个面向代码与工作区自动化任务的本地 Agent 内核。

当前重点：

- 可运行的 CLI Agent
- OpenAI 兼容模型接入
- 带安全限制的本地工具调用
- 会话持久化
- memory v1.5
- runtime trace 与调试日志
- 基于 `stdio` 的最小 MCP 工具接入

项目目前仍然是“内核优先、本地优先”的形态，还不是完整的 `nanobot` 风格平台；暂时还没有 channel、HTTP API、插件系统和后台调度。

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
- 根据最近对话生成摘要
- 从对话中提取简单事实
- 对事实去重
- 选择性地把事实注入后续对话上下文

### MCP

- 最小 `stdio` MCP client
- 支持：
  - `initialize`
  - `tools/list`
  - `tools/call`
- MCP 工具会以 `mcp__<tool_name>` 的形式暴露给 Agent

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
│  ├─ memory.py     # memory v1.5
│  └─ mcp.py        # 最小 stdio MCP client
├─ scripts/
├─ tests/
├─ .env.example
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

## MCP 配置

当前已经支持最小的 `stdio` MCP 接入。

在 `.env` 中加入：

```dotenv
MYAGENT_MCP_ENABLED=1
MYAGENT_MCP_COMMAND=python
MYAGENT_MCP_ARGS=path\to\your_mcp_server.py
MYAGENT_MCP_TIMEOUT_SECONDS=20
```

如果你还想保留内置工具，可以继续配置：

```dotenv
MYAGENT_ENABLED_BUILTIN_TOOLS=list_dir,read_file,run_command
```

加载后的 MCP 工具名格式为：

```text
mcp__tool_name
```

当前 MCP 范围：

- 只支持 `stdio` transport
- 只接工具能力
- 还不支持 HTTP/SSE transport
- 还不支持多 MCP server 聚合
- 还不支持 resources / prompts / sampling

## 运行时文件

运行产生的数据都写在 `.data/` 下：

- `.data/sessions/`：会话持久化
- `.data/memory/`：memory 快照
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
myagent "读取 README.md 并总结这个项目"
myagent "执行 python --version 并解释结果"
```

## 当前限制

目前仍未实现：

- HTTP API
- channel 接入
- plugin / skill 系统
- 后台调度与主动执行
- 更高级的 memory 检索与 consolidation
- `mock` 与 OpenAI-compatible 之外的多 provider 生态
- 更完整的 MCP 协议面

## 更多状态信息

另见：

- [PROJECT_STATUS.md](D:/Projects/myagent/PROJECT_STATUS.md)
- [ROADMAP.md](D:/Projects/myagent/ROADMAP.md)
