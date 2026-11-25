# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 差分用的 fake 模型工厂（模型形状图规格）。"""

from __future__ import annotations

from typing import Any


class FakeModel:
    """最小模型替身：只实现 ``invoke()``。"""

    def __init__(self, answer: str = "ok") -> None:
        self.answer = answer
        self.calls = 0

    def invoke(self, messages: Any) -> str:
        self.calls += 1
        return self.answer


class FakeModelFactory:
    """可调用工厂：每次调用创建一个新的 :class:`FakeModel`。"""

    def __init__(self, answer: str = "ok") -> None:
        self.answer = answer
        self.created: list[FakeModel] = []

    def __call__(self) -> FakeModel:
        model = FakeModel(self.answer)
        self.created.append(model)
        return model


def make_fake_model(answer: str = "ok") -> FakeModel:
    return FakeModel(answer)
