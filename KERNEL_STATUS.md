# 内核状态文档

## 文档目的

这份文档用于跟踪 `myagent` 作为“本地优先代码仓库智能助手内核”的底层能力建设情况。

适用范围：

- agent runtime
- provider 抽象
- tool 执行模型
- memory
- MCP
- observability
- 安全策略

不包括：

- 对外产品功能定义
- UI / channel / API 这类上层交付形态

## 当前内核定位

`myagent` 当前是一个可运行的本地 Agent 内核，目标是支撑“代码仓库理解、工作区自动化、MCP 工具扩展、安全执行、可追踪运行时”。

建议对外统一表述：

**本地优先的代码仓库智能助手内核**

## 内核模块总览

| 模块 | 当前状态 | 说明 |
|---|---|---|
| Agent Loop | 已实现 | 支持多轮工具调用、失败预算、重复调用保护 |
| Provider Abstraction | 已实现 | 已有 `mock` 与 OpenAI-compatible provider |
| Provider Retry / Error Model | 已实现 | 结构化 provider error、retry / backoff 已接入 |
| Tool Registry | 已实现 | 支持结构化 `ToolSpec` / `ToolResult` |
| Builtin Tools | 已实现 | `list_dir`、`repo_search`、`read_file`、`run_command` |
| Tool Safety Policy | 已实现 | 有 allow/block 策略与工作区限制 |
| Session Persistence | 已实现 | 会话消息持久化 |
| Memory v2 | 已实现 | 增量摘要、稳定事实提取、task memory、相关性检索、动态注入、最小长期记忆 |
| Runtime Trace | 已实现 | `trace_id`、provider/tool latency、重试信息 |
| MCP Stdio Client | 已实现 | 支持 `initialize`、`tools/list`、`tools/call` |
| Multi MCP Server | 已实现 | 支持多个 MCP server、命名空间与聚合加载 |
| HTTP API Runtime | 已实现 | 已支持最小 HTTP API：health/chat/session |
| Channel Runtime | 未实现 | 尚无 Telegram / Discord / WebSocket 等 |
| Skill Runtime | 已实现 | `SKILL.md` 发现、自动选择、惰性加载、prompt 注入 |
| Plugin / Skill Loading | 已实现（本地） | 支持项目级/用户级 skill 目录加载 |

## 已实现的关键设计

### 1. Agent Runtime

已具备：

- 多轮 provider -> tool -> provider 迭代
- tool failure budget
- consecutive tool error guard
- duplicate tool-call protection
- runtime trace logging

当前实现文件：

- [loop.py](D:/Projects/myagent/src/myagent/agent/loop.py)

### 2. Provider Layer

已具备：

- `BaseProvider`
- `ModelResponse`
- `ProviderError`
- OpenAI-compatible provider
- `responses` / `chat` 双模式
- retry / backoff

当前实现文件：

- [base.py](D:/Projects/myagent/src/myagent/providers/base.py)
- [openai_provider.py](D:/Projects/myagent/src/myagent/providers/openai_provider.py)

### 3. Tool Execution Model

已具备：

- 结构化 `ToolSpec`
- 结构化 `ToolResult`
- 内置工具注册
- 仓库搜索工具 `repo_search`
- 工具命令安全限制
- builtin tool 可配置启用

当前实现文件：

- [base.py](D:/Projects/myagent/src/myagent/tools/base.py)
- [registry.py](D:/Projects/myagent/src/myagent/tools/registry.py)
- [builtin.py](D:/Projects/myagent/src/myagent/tools/builtin.py)
- [loader.py](D:/Projects/myagent/src/myagent/tools/loader.py)

### 4. Memory

已具备：

- session transcript persistence
- memory snapshot persistence
- incremental summary refresh
- stable fact extraction
- task memory
- fact deduplication
- relevance-based retrieval
- dynamic prompt injection
- project-level long-term memory（最小版）

当前实现文件：

- [memory.py](D:/Projects/myagent/src/myagent/memory.py)

### 5. MCP

已具备：

- 多个 `stdio` MCP server 接入
- MCP tools -> `ToolSpec` 包装
- `mcp__<server_name>__<tool_name>` 命名
- kernel 退出时关闭全部 MCP 子进程

当前实现文件：

- [mcp.py](D:/Projects/myagent/src/myagent/mcp.py)
- [loader.py](D:/Projects/myagent/src/myagent/tools/loader.py)

### 6. Observability

已具备：

- session 级 JSONL 日志
- `trace_id`
- provider latency
- tool latency
- provider raw-response dump

当前实现文件：

- [observability.py](D:/Projects/myagent/src/myagent/observability.py)

### 7. Skill Runtime

已具备：

- `SKILL.md` front matter 解析
- `SkillRegistry`
- 显式 skill 指定
- 基于 query 的简单自动选择
- 项目级 / 用户级 skill 目录发现
- skill prompt 注入
- skill 写入 task memory

当前实现文件：

- [registry.py](D:/Projects/myagent/src/myagent/skills/registry.py)
- [loader.py](D:/Projects/myagent/src/myagent/skills/loader.py)
- [loop.py](D:/Projects/myagent/src/myagent/agent/loop.py)

## 还缺的关键内核能力

按优先级排序：

1. **Memory consolidation / long-term retrieval**
   - 当前已有最小长期记忆
   - 还缺更好的压缩策略
   - 还缺更稳定的长期保留策略
   - 还缺更强的长期检索

2. **更完整的 provider telemetry**
   - token usage
   - request id
   - 更统一的失败分类

3. **Skill isolation / richer assets**
   - 当前已有本地目录加载
   - 还缺更强的资源加载、隔离与版本治理

## 当前推荐开发顺序

1. 更完整的 memory consolidation / long-term retrieval
2. 更完整的 provider telemetry
3. 更强的 skill 资源治理 / 后续 channel

## 最近一次状态更新时间

- 时间：2026-04-22
- 状态结论：**内核已经具备 CLI、最小 HTTP API、多 MCP、最小长期记忆与仓库搜索工具，下一步重点应放在更完整的 memory consolidation 和后续协议/治理能力。**
