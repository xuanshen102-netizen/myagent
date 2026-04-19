from __future__ import annotations

from typing import Any

from myagent.providers.base import BaseProvider, Message, ModelResponse


class MockProvider(BaseProvider):
    def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        del tools
        last_user = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        return ModelResponse(
            text=(
                f"[mock:{self.model}] received: {last_user}\n"
                "The project scaffold is running. Replace this provider with a real model next."
            )
        )

