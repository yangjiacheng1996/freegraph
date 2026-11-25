#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · fake 模型注入（测试 / 验收层，**不得进入 freegraph 运行时依赖**）。

固定脚本 `harness/demo/target.py` 在导入期即 `from langchain.chat_models import
init_chat_model` 并立即调用。要跑 fake 且**不改脚本**，只能由外部替换
`langchain.chat_models.init_chat_model`。

固定输出序列（与立项书 §9.2 一致）：

1. 第 1 轮：`AIMessage(tool_calls=[{name: "add", args: {"a": 3, "b": 4},
   id: "call_1", type: "tool_call"}])`；
2. 第 2 轮：最终文本答案（与脚本的「Add 3 and 4.」对齐）；
3. 第 3 次调用：**显式失败**（防止脚本意外多打一轮模型）。
"""

from __future__ import annotations

import importlib
from typing import Any

TOOL_CALL_ID = "call_1"
FINAL_TEXT = "The answer is 7."


class FakeModel:
    """实现 ``bind_tools()`` / ``invoke()`` 的最小 fake 模型。"""

    def __init__(self) -> None:
        self.calls = 0
        self.bound_tools: list[Any] | None = None

    def bind_tools(self, tools: Any) -> "FakeModel":
        self.bound_tools = list(tools)
        return self

    def invoke(self, messages: Any) -> Any:
        from langchain_core.messages import AIMessage

        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add",
                        "args": {"a": 3, "b": 4},
                        "id": TOOL_CALL_ID,
                        "type": "tool_call",
                    }
                ],
            )
        if self.calls == 2:
            return AIMessage(content=FINAL_TEXT)
        raise RuntimeError(
            f"FakeModel 只允许 2 轮调用，实际第 {self.calls} 次调用"
        )


def install() -> FakeModel:
    """猴补 ``langchain.chat_models.init_chat_model`` 并返回 fake 实例。"""

    chat_models = importlib.import_module("langchain.chat_models")
    fake = FakeModel()

    def _init_chat_model(*args: Any, **kwargs: Any) -> FakeModel:
        return fake

    chat_models.init_chat_model = _init_chat_model  # type: ignore[attr-defined]
    return fake
