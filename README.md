# myagent

一个面向后续扩展的 Agent 项目骨架，按 `agent / providers / tools / session / cli` 分层，先把最小内核搭起来。

## 当前目标

这一版只解决三件事：

1. 有一个可运行的 CLI 入口。
2. 有清晰的 Provider / Tool / Session 抽象。
3. 后续接真实模型和更多工具时，不需要重做目录结构。

## 目录结构

```text
.
├─ src/myagent/
│  ├─ agent/        # agent 主循环
│  ├─ providers/    # 模型提供方适配层
│  ├─ session/      # 会话持久化
│  ├─ tools/        # 工具注册与内置工具
│  ├─ cli.py        # 命令行入口
│  └─ config.py     # 环境配置
├─ tests/
├─ .env.example
└─ pyproject.toml
```

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy .env.example .env
myagent "hello"
```

默认使用 `mock` provider，只用于验证骨架和主循环。

## 切换到 OpenAI

把 `.env` 里的配置改成：

```text
OPENAI_API_KEY=your_key_here
MYAGENT_OPENAI_BASE_URL=
MYAGENT_OPENAI_API_MODE=responses
MYAGENT_PROVIDER=openai
MYAGENT_MODEL=gpt-4.1-mini
```

然后直接运行：

```bash
myagent "读取 README.md 并总结一下"
```

如果你使用自定义 OpenAI 兼容端点，把 `MYAGENT_OPENAI_BASE_URL` 设成对应的 `/v1` 地址即可。
如果第三方端点不兼容 `Responses API`，把 `MYAGENT_OPENAI_API_MODE=chat` 作为回退模式。

## 下一步建议

1. 先把 `providers/openai_provider.py` 接成真实模型调用。
2. 把 `tools/builtin.py` 里的工具改成更严格的权限模型。
3. 给 `agent/loop.py` 增加真正的 tool-calling 协议。
4. 再考虑 memory、skills、web/api channel。
## Debug And Validation

```bash
python scripts/debug_openai_compat.py
python scripts/smoke_agent_tasks.py
```

Runtime logs are written under:

- `.data/logs/` for per-session JSONL event logs
- `.data/provider-debug/` for the latest raw provider response dump
- `.data/debug-openai-response.json` for the compatibility debug script output
