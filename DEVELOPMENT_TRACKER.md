# 开发跟踪文档

## 文档目的

这份文档用于持续跟踪 `myagent` 从本地 Agent Runtime 演化到 Coding Agent 的进度。

建议每完成一个明确阶段后更新：

- 当前阶段
- 已完成项
- 风险 / 阻塞
- 下一步

## 项目总目标

做出一个能够写进简历、具备清晰技术深度、并且可以持续演化为 Coding Agent 的项目。

当前统一定位：

**本地优先、面向代码仓库的 ReAct 风格 Agent Runtime。**

## 里程碑

### Milestone 0：最小内核

状态：**已完成**

完成内容：

- CLI
- provider abstraction
- builtin tools
- session persistence
- 基础 agent loop

### Milestone 1：强化内核

状态：**已完成**

完成内容：

- provider error model
- retry / backoff
- structured tool result
- tool failure budget
- runtime trace
- memory v2
- 最小 MCP 接入

### Milestone 2：仓库助手可用版

状态：**已完成**

完成内容：

- 最小 HTTP API
- 多 MCP server 支持
- 最小长期记忆
- `repo_search -> read_file -> synthesize`
- `SKILL.md` skill runtime

### Milestone 3：ReAct 第一阶段

状态：**已完成**

完成内容：

- prompt 层加入 ReAct-style 执行约束
- runtime 层增加 `thought_summary`
- assistant / tool / final answer 写入 `react` 元数据
- 日志层新增 `react_step`
- 回归测试覆盖 ReAct 轨迹

验收结论：

- 当前已不是“隐式工具循环”
- 已成为“具备显式 ReAct 运行轨迹的工具型 Agent Runtime”

### Milestone 4：Coding Agent 演化

状态：**未开始**

目标：

- `inspect / edit / verify / done` 状态机
- 文件编辑工具
- 验证工具
- Git 感知
- coding delivery output

## 当前阶段判断

当前所处阶段：

**Milestone 3：ReAct 第一阶段已完成**

当前结论：

- 内核能力已经足够支撑“仓库理解助手”
- 现在不应该继续把重点放在聊天或文档包装上
- 下一步应该直接推进 coding task loop

## 当前已完成清单

- 本地 CLI Agent
- 最小 HTTP API
- OpenAI-compatible provider
- session persistence
- memory v2
- 最小长期记忆
- builtin tool safety policy
- 仓库问答闭环
- MCP 最小版
- runtime trace
- ReAct step trace

## 当前风险 / 阻塞

### 1. 还不是 Coding Agent

影响：

- 只能看代码、查代码、解释代码
- 还不能稳定完成“改代码并验证”的闭环

### 2. 缺少代码编辑和验证能力

影响：

- 现阶段无法进入真正的 coding task execution

### 3. README 等外层文档存在过时和编码噪声

影响：

- 会误导另一个开发环境上的协作者
- 会影响项目对外表述一致性

## 下一阶段开发顺序

严格建议按这个顺序推进：

1. 补齐核心文档
2. 建立 coding task phases
3. 增加文件编辑工具
4. 增加验证工具
5. 增加 Git 只读工具

## 最近一次迭代记录

### 迭代日期

- 2026-04-26

### 本轮完成

- 将 agent loop 演化为 ReAct-style runtime
- 增加 `thought_summary / actions / observations`
- 在日志中记录 `react_step`
- 增加对应测试
- 同步核心状态文档

### 本轮未完成

- README 全量重写
- coding task state machine
- 文件编辑工具
- structured validation tools

### 下一步

- 开始实现 coding ReAct agent 的 `inspect / edit / verify` 基础状态流
