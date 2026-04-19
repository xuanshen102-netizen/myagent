# 路线图

## 已完成

- 项目骨架与 Conda 环境搭建
- CLI Agent 内核
- 会话持久化
- 内置工具：`list_dir`、`read_file`、`run_command`
- 结构化工具结果模型
- 更严格的 shell 命令安全策略
- OpenAI provider 集成
- 自定义 `base_url` 支持
- `responses` / `chat` API 模式支持
- 结构化 provider 错误模型
- 有界 provider retry / backoff
- runtime logging 与原始 provider dump
- memory v1.5：摘要、事实、去重与选择性注入
- 最小 `stdio` MCP 接入
- provider 兼容性调试脚本
- 真实调用 smoke 脚本
- 回归测试套件

## 近期

1. 增加 HTTP API：
   - 基础 chat 接口
   - session 查询接口
   - 健康检查接口
2. 扩展 MCP：
   - 多 MCP server 支持
   - 更清晰的命名空间管理
   - 更好的错误与超时日志
3. 改进 memory：
   - 更明确的检索策略
   - 更稳定的摘要刷新策略
   - 更好的事实筛选
4. 使用真实 provider 跑 `scripts/smoke_agent_tasks.py`，检查失败模式。
5. 根据真实日志继续调整 prompt 和工具行为。

## 后续

1. 增加更丰富的 memory 检索与 consolidation。
2. 增加 plugin / skill 加载模型。
3. 在 API 稳定后再加 channel 集成。
4. 根据实际任务需要再考虑 multi-agent 或 workflow orchestration。
