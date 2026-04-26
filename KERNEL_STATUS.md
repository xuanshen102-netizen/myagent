# 内核状态文档

## 文档目的

这份文档用于跟踪 `myagent` 作为本地优先 Agent Runtime 的内核能力建设情况。

关注范围：

- agent runtime
- provider 抽象
- tool 执行模型
- memory
- MCP
- observability
- 安全策略

不包含：

- UI / channel 等上层产品形态
- 商业化或平台化规划

## 当前内核定位

`myagent` 当前可以定义为：

**一个本地优先、面向代码仓库场景、具备显式 ReAct 运行轨迹的工具型 Agent Runtime。**

这里的“显式 ReAct 运行轨迹”指的是：

- 有 `Thought` 的结构化摘要 `thought_summary`
- 有明确的 `Action`，即结构化 tool calls
- 有明确的 `Observation`，即工具结果和 observation summary
- 每一轮都会记录 `react_step`

它还不是完整的 Coding Agent，因为还没有代码编辑、测试验证和编码状态机。

## 内核模块总览

| 模块 | 当前状态 | 说明 |
|---|---|---|
| Agent Loop | 已实现 | 支持多轮工具调用、失败预算、重复调用保护、ReAct step 记录 |
| ReAct Trace | 已实现 | 记录 `thought_summary -> actions -> observations` |
| Provider Abstraction | 已实现 | 已有 `mock` 与 OpenAI-compatible provider |
| Provider Retry / Error Model | 已实现 | 支持 retry / backoff 与结构化 provider error |
| Tool Registry | 已实现 | 支持统一 `ToolSpec` / `ToolResult` |
| Builtin Tools | 已实现 | `list_dir`、`repo_search`、`read_file`、`run_command` |
| Tool Safety Policy | 已实现 | 工作区限制与 shell allow/block 策略 |
| Session Persistence | 已实现 | 会话消息持久化 |
| Memory v2 | 已实现 | summary、facts、task memory、最小长期记忆 |
| Runtime Trace | 已实现 | `trace_id`、provider/tool latency、provider dump |
| MCP Stdio Client | 已实现 | 支持 `initialize`、`tools/list`、`tools/call` |
| Multi MCP Server | 已实现 | 支持多 server 聚合与命名空间隔离 |
| HTTP API Runtime | 已实现 | 最小 HTTP API |
| Skill Runtime | 已实现 | `SKILL.md` 发现、自动选择、prompt 注入 |
| Coding Task State Machine | 未实现 | 尚无 `inspect/edit/verify/done` 阶段控制 |
| File Mutation Tools | 未实现 | 尚无安全写文件 / patch 能力 |
| Validation Tools | 未实现 | 尚无 `run_tests` / `run_lint` / `run_typecheck` |

## 已实现的关键设计

### 1. Agent Runtime

当前已具备：

- provider -> tool -> provider 的多轮闭环
- tool failure budget
- consecutive tool error guard
- duplicate tool-call protection
- runtime trace logging
- ReAct step 结构化记录

ReAct 轨迹当前落在两层：

- 消息元数据 `message.metadata["react"]`
- 日志事件 `react_step`

核心实现文件：

- [loop.py](D:\project\myagent\src\myagent\agent\loop.py)

### 2. Provider Layer

当前已具备：

- `BaseProvider`
- `ModelResponse`
- `ProviderError`
- OpenAI-compatible provider
- `responses` / `chat` 双模式
- retry / backoff

核心实现文件：

- [base.py](D:\project\myagent\src\myagent\providers\base.py)
- [openai_provider.py](D:\project\myagent\src\myagent\providers\openai_provider.py)

### 3. Tool Execution Model

当前已具备：

- 结构化 `ToolSpec`
- 结构化 `ToolResult`
- 内置工具注册
- `repo_search` 仓库搜索
- shell 安全限制

核心实现文件：

- [base.py](D:\project\myagent\src\myagent\tools\base.py)
- [registry.py](D:\project\myagent\src\myagent\tools\registry.py)
- [builtin.py](D:\project\myagent\src\myagent\tools\builtin.py)
- [loader.py](D:\project\myagent\src\myagent\tools\loader.py)

### 4. Memory

当前已具备：

- session transcript persistence
- memory snapshot persistence
- incremental summary refresh
- stable fact extraction
- task memory
- relevance-based retrieval
- dynamic prompt injection
- project-level minimal long-term memory

核心实现文件：

- [memory.py](D:\project\myagent\src\myagent\memory.py)

### 5. MCP

当前已具备：

- 多个 `stdio` MCP server 接入
- MCP tools -> `ToolSpec` 包装
- `mcp__<server_name>__<tool_name>` 命名
- kernel 退出时关闭 MCP 子进程

核心实现文件：

- [mcp.py](D:\project\myagent\src\myagent\mcp.py)
- [loader.py](D:\project\myagent\src\myagent\tools\loader.py)

### 6. Observability

当前已具备：

- session 级 JSONL 日志
- `trace_id`
- provider latency
- tool latency
- provider raw-response dump
- ReAct step 日志

核心实现文件：

- [observability.py](D:\project\myagent\src\myagent\observability.py)

## 当前内核仍缺的关键能力

按优先级排序：

1. Coding task state machine
2. Safe file mutation tools
3. Structured validation tools
4. Git awareness
5. 更强的 coding memory

## 推荐下一步

严格按这个顺序推进：

1. `inspect / edit / verify / done` 任务阶段
2. 文件编辑工具
3. 测试 / lint / typecheck 工具
4. Git 只读工具
5. coding-oriented delivery 输出

## 最近一次状态更新时间

- 时间：2026-04-26
- 状态结论：**内核已完成 ReAct 第一阶段落地，当前最重要的不是继续扩展聊天能力，而是把 ReAct loop 演化成面向编码任务的执行状态机。**
