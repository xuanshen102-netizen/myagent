from __future__ import annotations

from myagent.cli import build_kernel
from myagent.config import Settings


PROMPTS = [
    "列出当前目录",
    "读取 README.md 并总结这个项目",
    "执行 python --version 并解释结果",
]


def main() -> None:
    settings = Settings.from_env()
    kernel = build_kernel(settings)

    for index, prompt in enumerate(PROMPTS, start=1):
        session_id = f"smoke-{index}"
        print(f"===== Prompt {index} =====")
        print(prompt)
        print("----- Response -----")
        print(kernel.run_once(session_id=session_id, user_text=prompt))
        print()


if __name__ == "__main__":
    main()
