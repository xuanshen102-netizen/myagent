# 开发跟进文档

## 文档目的

这份文档用于持续跟进 `myagent` 从“本地 Agent 内核”演进到“本地优先代码仓库智能助手”的开发进度。

建议每次完成一个明确阶段后，更新：

- 当前阶段
- 已完成项
- 阻塞项
- 下一步

## 项目总目标

做出一个可以写进简历、具有明确技术难点的项目：

**本地优先的代码仓库智能助手**

要求：

- 能运行
- 能演示
- 有真实技术点
- 有明确工程边界

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

- 结构化 provider error
- provider retry / backoff
- 结构化 tool result
- tool failure budget
- runtime trace
- memory v2
- 最小 MCP 接入

### Milestone 2：简历版项目

状态：**进行中**

目标：

- 形成“代码仓库智能助手”的明确产品形态
- 在现有 CLI 基础上提供更稳定的服务入口
- 增强 MCP 与 memory，形成更强展示价值

当前建议范围：

- 最小长期记忆
- 仓库问答闭环
- 输出与演示收尾

当前已新增：

- 最小 HTTP API
- 多 MCP server 支持
- Memory v2
- 最小长期记忆
- `repo_search` 与仓库问答闭环
- `SKILL.md` skill runtime

### Milestone 3：平台化扩展

状态：**未开始**

目标：

- channel
- plugin / skill
- 更完整 MCP
- 后台执行

## 当前阶段判断

当前所处阶段：

**Milestone 2：简历版项目**

当前结论：

- 内核已经足够支撑一个严肃的小型项目
- 现在已经具备最小 API 化能力
- 已完成“最小长期记忆”和“仓库问答闭环”，项目已进入收尾阶段
- 不建议马上扩散到 channel / multi-agent / UI

## 当前已完成清单

- 本地 CLI Agent
- 最小 HTTP API
- OpenAI-compatible provider
- session persistence
- memory v2
- 最小长期记忆
- builtin tool safety policy
- repo_search / file selection / answer synthesis 闭环
- MCP 最小版
- runtime trace
- 完整测试覆盖到当前核心能力

## 当前阻塞 / 风险

### 1. 只有 CLI，没有服务化入口

状态：**已解决**

说明：

- 已支持最小 HTTP API
- 后续重点转为增强 API，而不是从零开始做 API

### 2. Memory 还缺更完整的 consolidation 与长期检索

影响：

- 当前已具备最小长期记忆，但复杂任务下长期压缩与检索仍然有限

## 下一阶段开发顺序

建议严格按这个顺序推进：

1. 输出格式稳定化与 README / 使用手册收尾
2. 更完整的 memory consolidation / 长期检索
3. Skill 资源治理 / Channel / UI

## 下一阶段验收标准

### HTTP API 验收

状态：**已完成**

完成结果：

- 已支持 HTTP 发起 agent 请求
- 已支持 session id
- 已支持返回最终回答
- 已支持健康检查

### 多 MCP server 验收

状态：**已完成**

完成结果：

- 已支持多个 MCP server 配置
- 已支持同时加载多个 MCP tools
- 已有明确命名空间
- 已支持冲突校验

### Memory v2 验收

状态：**已完成**

完成结果：

- 已支持显式相关性检索
- 已支持更稳定的摘要更新策略
- 已支持动态 memory 注入
- 已支持 task memory

### 最小长期记忆验收

状态：**已完成**

完成结果：

- 已支持项目级长期记忆文件
- 已支持跨 session 复用稳定事实
- 已支持按 query 注入长期任务结论

### 仓库问答闭环验收

状态：**已完成**

完成结果：

- 已支持 `repo_search`
- 已支持候选文件选择
- 已支持 search -> read -> synthesize 闭环

## 每轮开发建议记录格式

建议后续每次迭代都按下面补充：

### 迭代日期

- YYYY-MM-DD

### 本轮完成

- ...

### 本轮未完成

- ...

### 风险 / 问题

- ...

### 下一步

- ...

## 最近一次状态更新时间

- 时间：2026-04-22
- 当前建议：**项目第一版核心功能已经成型，下一步优先做文档、演示和输出格式收尾；不要再扩到 channel、多 agent 或重型框架。**
