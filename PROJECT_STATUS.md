# 项目状态

## 当前状态

`myagent` 现在已经不是简单的本地问答脚手架，而是一个可运行的本地 Agent 系统。

当前更准确的定位是：

**本地优先、面向代码仓库场景、具备显式 ReAct 运行轨迹的工具型 Agent。**

## 当前已实现

- CLI 入口，支持单次调用和交互模式
- session 持久化
- 结构化工具注册与内置工具
- OpenAI-compatible provider，支持 `responses` 和 `chat`
- provider error 结构化建模
- retry / backoff
- runtime JSONL 日志
- provider 原始响应 dump
- memory v2：summary、facts、task memory、最小长期记忆
- skill runtime：`SKILL.md` 发现、自动选择、prompt 注入
- 基于 `stdio` 的 MCP 工具接入
- 多 MCP server 聚合
- 最小 HTTP API
- ReAct-style runtime trace：`thought_summary / actions / observations / react_step`
- 回归测试

## 核心能力

### Agent 内核

- 多轮工具调用循环
- 重复工具调用保护
- 单轮工具失败预算
- 连续工具失败保护
- ReAct step 记录
- 运行时日志记录工具和 provider 执行轨迹

### Provider 层

- `mock` provider
- OpenAI-compatible provider
- `responses` / `chat` API 模式切换
- provider 错误分类
- retry
- 原始 payload dump

### 工具层

- builtin tools：`list_dir`、`repo_search`、`read_file`、`run_command`
- 文件访问受工作区限制
- shell allow/block 策略
- `ToolResult` 结构化返回

### Memory

- 会话消息持久化
- memory snapshot
- 增量 summary
- facts 提取
- task memory
- query 相关性注入
- project-level 最小长期记忆

### 可观测性

- `.data/logs/` 下的 JSONL 日志
- `trace_id`
- tool/provider latency
- provider error metadata
- `react_step` 事件

## 当前是否实现了 ReAct

是，但要准确描述为：

**已经实现了 ReAct 的第一阶段工程化版本。**

目前具备：

- `Thought`：用 `thought_summary` 记录当前轮意图
- `Action`：结构化 tool calls
- `Observation`：tool result + observation summary
- 每轮日志化 `react_step`

目前还不具备：

- 显式对外展示完整 chain-of-thought
- 编码任务状态机
- 失败反思 / reflection 机制

## 当前限制

项目当前仍然不是完整的 Coding Agent。

尚未完成：

- 文件写入 / patch 工具
- 测试 / lint / typecheck 验证工具
- Git 感知
- `inspect -> edit -> verify -> done` 任务状态机
- 更强的长程 coding memory
- channel / UI / multi-agent

## 当前测试状态

本地 `myagent` 环境下已验证：

- agent loop
- ReAct 轨迹记录
- provider 解析
- session 持久化
- API 行为

最近一次针对 ReAct 改造的回归结果：

- `28 passed`

## 下一步建议

不要继续停留在“仓库问答助手”的层面。

下一步应该直接进入 Coding Agent 演化：

1. 建立编码任务阶段
2. 增加文件编辑工具
3. 增加验证工具
4. 增加 Git 只读能力

## 最近一次状态更新时间

- 时间：2026-04-26
- 结论：**ReAct 第一阶段已落地，项目下一阶段目标应切换为 coding ReAct agent。**
