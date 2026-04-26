# 功能状态文档

## 文档目的

这份文档面向“当前对外可以怎么讲”。

关注点：

- 用户可见能力
- 可演示场景
- 简历可写亮点
- 已完成 / 未完成边界

## 当前产品定位

建议统一表述为：

**一个本地优先的代码仓库智能助手，内核采用 ReAct 风格的多轮工具调用机制。**

## 当前可用功能

### 1. 仓库理解与问答

状态：**可用**

可做：

- 总结项目目录结构
- 搜索入口文件和核心模块
- 读取代码文件并解释实现
- 基于真实工具结果回答仓库问题

依赖能力：

- `list_dir`
- `repo_search`
- `read_file`
- 多轮 tool loop

### 2. 本地命令辅助

状态：**可用**

可做：

- 执行受控只读命令
- 解释命令输出
- 帮助排查环境和仓库状态

依赖能力：

- `run_command`
- shell 安全策略

### 3. 连续会话与记忆

状态：**可用**

可做：

- 保留 session
- 记录 summary / facts / task memory
- 在后续问答中动态注入相关记忆
- 复用项目级最小长期记忆

### 4. Skill 扩展

状态：**可用**

可做：

- 显式指定 skill
- 根据 query 自动选择 skill
- 通过 `SKILL.md` 注入任务策略

### 5. MCP 工具扩展

状态：**可用（最小版）**

可做：

- 接入多个 `stdio` MCP server
- 自动发现 MCP tools
- 让模型像调用内置工具一样调用 MCP 工具

### 6. HTTP API

状态：**可用（最小版）**

可做：

- 通过 `/chat` 发起对话
- 通过 `/sessions/{id}` 查看会话和 memory
- 通过 `/health` 做健康检查

### 7. ReAct 执行轨迹

状态：**已实现**

可做：

- 记录当前轮的 `thought_summary`
- 记录本轮工具动作 `actions`
- 记录工具观察结果 `observations`
- 在日志中保留 `react_step`

这意味着项目已经不是“只有工具调用”的 agent，而是已经具备了工程化 ReAct 内核。

## 当前不应对外宣称已完成的功能

这些能力现在还不能写成“已完成”：

- 自动改代码
- 自动跑测试并修复
- Git diff 感知
- 编码任务状态机
- 反思式失败恢复
- Web UI / 多 channel / multi-agent

## 简历可写亮点

当前已经可以写的技术点：

- 本地优先 Agent Runtime
- ReAct-style 多轮工具调用机制
- OpenAI-compatible provider abstraction
- Structured tool execution and safety policy
- Session persistence, task memory, and minimal long-term retrieval
- `SKILL.md`-based skill runtime
- Multi-server MCP integration
- Runtime tracing and observability

## 推荐演示场景

1. “总结这个仓库结构，并指出入口模块”
2. “搜索某个函数定义，并解释实现”
3. “执行 `python --version` 并解释结果”
4. “跨 session 记住项目事实并在后续复用”
5. “查看 runtime logs 中的 react_step 执行轨迹”

## 下一阶段功能目标

下一阶段不应该继续扩聊天层，而应该进入 Coding Agent 演化：

1. 文件编辑能力
2. 测试 / lint / typecheck
3. Git awareness
4. coding ReAct loop

## 最近一次状态更新时间

- 时间：2026-04-26
- 结论：**功能层面已具备 ReAct 风格仓库助手的第一版价值，下一步是进入 coding 闭环。**
