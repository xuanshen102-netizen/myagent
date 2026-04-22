# 路线图

## 已完成

- 项目骨架与 Conda 环境搭建
- CLI Agent 内核
- 会话持久化
- 内置工具：`list_dir`、`repo_search`、`read_file`、`run_command`
- 结构化工具结果模型
- 更严格的 shell 命令安全策略
- OpenAI provider 集成
- 自定义 `base_url` 支持
- `responses` / `chat` API 模式支持
- 结构化 provider 错误模型
- 有界 provider retry / backoff
- runtime logging 与原始 provider dump
- memory v2：增量摘要、事实提取、相关性检索、task memory 与动态注入
- 最小长期记忆：项目级稳定事实与任务结论沉淀
- 仓库问答闭环：`repo_search -> read_file -> synthesize`
- skill runtime：`SKILL.md` 发现、自动选择、惰性加载、prompt 注入
- 最小 `stdio` MCP 接入
- 最小 HTTP API
- provider 兼容性调试脚本
- 真实调用 smoke 脚本
- 回归测试套件

## 近期

1. 使用真实 provider 跑 `scripts/smoke_agent_tasks.py`，检查失败模式。
2. 根据真实日志继续调整 prompt 和输出格式。
3. 完成 README、使用手册和 demo 场景收尾。

## 后续

1. 增加更丰富的 memory consolidation 与长期检索。
2. 增加更完整的 provider telemetry 与 MCP 协议面。
3. 增加更强的 skill 资源加载、隔离与版本治理。
4. 在 API 稳定后再加 channel 集成。
