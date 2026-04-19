# 项目状态

## 当前状态

`myagent` 现在已经不是单纯的项目骨架，而是一个具备强化内核的本地 Agent。

目前已经实现：

- CLI 入口，支持单次调用和交互模式
- 会话持久化
- 结构化工具注册与内置工具
- OpenAI 兼容 provider，支持 `responses` 和 `chat`
- 结构化 provider 错误
- 有界 retry / backoff
- 结构化工具结果
- 更严格的 shell 命令策略
- 每个 session 的 JSONL 运行日志
- provider 原始响应 dump
- memory v1.5：摘要、事实、去重与选择性注入
- 基于 `stdio` 的最小 MCP 工具接入
- smoke 脚本与回归测试

## 核心能力

### Agent 内核

- 多轮工具调用循环
- 重复工具调用保护
- 单轮工具失败预算
- 连续工具失败保护
- 运行时日志中记录结构化工具执行信息

### Provider 层

- `mock` provider 用于本地验证
- OpenAI-compatible provider
- 可配置 `responses` / `chat` API 模式
- provider 错误结构化分类
- 对可重试错误做 retry
- 原始 payload dump 便于兼容性排查

### 工具层

- 内置工具：`list_dir`、`read_file`、`run_command`
- 文件访问受工作区限制
- 命令执行有 allow/block 策略
- 结构化工具结果对象，包含：
  - `status`
  - `content`
  - `error_type`
  - `metadata`
  - 可选 structured payload

### Memory

- 会话消息持久化
- `.data/memory/` 下保存 memory 快照
- 根据最近对话生成摘要
- 从 user / assistant 内容中提取简单事实
- 对事实做去重
- 在后续对话中选择性注入 memory prompt

### MCP

- 最小 `stdio` MCP client
- 支持 `initialize`
- 支持 `tools/list`
- 支持 `tools/call`
- MCP 工具被包装为现有 `ToolSpec`
- 暴露给模型时使用 `mcp__<tool_name>` 命名

### 可观测性

- `.data/logs/` 下每个 session 的 JSONL 事件日志
- 日志中带 `trace_id`
- 记录 tool result 的状态和错误元数据
- 记录 provider 错误元数据
- 记录 provider latency / retry 信息
- `.data/provider-debug/` 下保存最近一次 provider 原始响应

## 重要运行时文件

- `.env`：本地配置，已加入 Git ignore
- `.data/sessions/`：session transcript
- `.data/memory/`：memory 快照
- `.data/logs/`：运行日志
- `.data/provider-debug/`：provider 原始响应
- `.data/debug-openai-response.json`：兼容性调试脚本输出

## 当前限制

项目目前仍然是“内核优先”的本地 Agent，还不是完整的 `nanobot` 风格平台。

仍未完成：

- HTTP API
- channel 集成
- 高级 memory 检索与 consolidation
- `mock` + OpenAI-compatible 之外的多 provider 生态
- 后台调度与主动执行
- plugin / skill 加载模型
- 更完整的 MCP 协议面

## 常用命令

```powershell
conda activate myagent
python scripts\debug_openai_compat.py
python scripts\smoke_agent_tasks.py
python -m pytest tests -p no:cacheprovider
myagent "列出当前目录并说明项目结构"
myagent "读取 README.md 并总结这个项目"
```

## 测试覆盖

当前测试覆盖：

- agent loop 行为
- 重复工具调用保护
- 单轮工具失败预算
- 内置工具安全行为
- CLI / provider 配置校验
- provider 响应解析
- provider retry 行为
- 结构化 provider error 行为
- observability 日志
- session 持久化
- memory 摘要与事实持久化
- MCP 工具发现与调用

当前本地验证状态：

- `36` 个测试在本地 `myagent` Conda 环境下全部通过

## 下一步建议

1. 先做 HTTP API，给 CLI 之外一个稳定入口。
2. 在 MCP 基础上扩展多 server 支持。
3. 把 memory 从 v1.5 提升到显式检索与压缩策略。
4. 再考虑 channel、skill、plugin。
