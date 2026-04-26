# 路线图

## 已完成

- 项目骨架与 Conda 环境搭建
- CLI Agent 内核
- session 持久化
- 内置工具：`list_dir`、`repo_search`、`read_file`、`run_command`
- 结构化工具结果模型
- shell 安全策略
- OpenAI provider 集成
- `base_url` 支持
- `responses` / `chat` API 模式支持
- provider error 模型
- provider retry / backoff
- runtime logging 与 provider dump
- memory v2
- 最小长期记忆
- 仓库问答闭环：`repo_search -> read_file -> synthesize`
- `SKILL.md` skill runtime
- 最小 `stdio` MCP 接入
- 最小 HTTP API
- provider 调试脚本
- smoke 脚本
- ReAct 第一阶段落地：
  - prompt 约束
  - `thought_summary`
  - action / observation trace
  - `react_step` 日志

## 近期

1. 清理 README 与外层说明文档
2. 开始实现 coding task phases
3. 为 coding agent 增加文件编辑能力

## 后续

1. 增加 structured validation tools
2. 增加 Git awareness
3. 增加 coding-focused memory
4. 再考虑更复杂的 MCP / skill / channel 扩展
