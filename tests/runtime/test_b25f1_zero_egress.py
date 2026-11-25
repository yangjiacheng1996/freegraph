# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 框架出站 = 0；用户出站逐条记录、不判失败、不设目标白名单。

本测试**不触网**：在进入 ``_gatekit.record_egress`` 之前把底层
``socket.socket.connect`` / ``socket.create_connection`` 替换为 no-op，
从而在断网（含回环不可用）环境下也可执行（G28 规则 (b1) 无需排除）。
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_GATES = _REPO_ROOT / "harness" / "scripts" / "gates"
for _path in (_SRC, _GATES):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import operator

from freegraph.graph import END, START, StateGraph


class _State(TypedDict, total=False):
    x: int
    log: Annotated[list[str], operator.add]


def test_framework_egress_is_zero() -> None:
    import _gatekit

    def a(state: dict) -> dict:
        return {"log": ["a"], "x": 1}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    records: list[_gatekit.EgressRecord] = []
    with _gatekit.record_egress(records):
        builder.compile().invoke({"log": [], "x": 0})
    framework = [record for record in records if record.attribution == "framework"]
    assert framework == [], [record.target for record in framework]


def test_user_egress_is_recorded_not_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    import _gatekit

    # 把「原 connect」替换为 no-op：包装器仍会放行并记录，但不真正触网。
    monkeypatch.setattr(socket.socket, "connect", lambda self, address, *a, **k: None)
    monkeypatch.setattr(socket, "create_connection", lambda address, *a, **k: None)

    records: list[_gatekit.EgressRecord] = []
    with _gatekit.record_egress(records):
        socket.create_connection(("203.0.113.1", 65535))

    user = [record for record in records if record.attribution == "user"]
    framework = [record for record in records if record.attribution == "framework"]
    assert len(user) == 1
    assert user[0].target == "203.0.113.1:65535"
    assert framework == []
    # 不设目标白名单：任意目标都只记录、不判失败。
    assert user[0].target not in {"api.openai.com:443", "api.anthropic.com:443"}
