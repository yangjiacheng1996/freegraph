# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · A1 fake 轮固定断言点（fake 注入与路由函数正交）。"""

from __future__ import annotations

import runpy
import struct
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_TARGET = _REPO_ROOT / "harness" / "demo" / "target.py"
_B25F1 = _REPO_ROOT / "harness" / "verification" / "B25F1"
_GATES = _REPO_ROOT / "harness" / "scripts" / "gates"

for _path in (_SRC, _B25F1, _GATES):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _png_ok(data: Any) -> bool:
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    if len(data) < 8 + 12 + 13:
        return False
    length = struct.unpack(">I", bytes(data[8:12]))[0]
    return data[12:16] == b"IHDR" and length == 13


def test_fake_round_fixed_assertions(install_fake_init_chat_model: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import _gatekit
    import IPython.display as ipython_display

    png: list[bytes] = []

    def _capture(value: Any) -> None:
        data = getattr(value, "data", None)
        if data is not None:
            png.append(bytes(data))

    monkeypatch.setattr(ipython_display, "display", _capture)
    records: list[_gatekit.EgressRecord] = []
    with _gatekit.record_egress(records):
        namespace = runpy.run_path(str(_TARGET), run_name="__main__")

    state = namespace["messages"]
    assert isinstance(state, dict)
    assert {"messages", "llm_calls"}.issubset(state)

    messages = list(state["messages"])
    assert len(messages) == 4, [type(m).__name__ for m in messages]
    assert state["llm_calls"] == 2
    assert install_fake_init_chat_model.calls == 2

    tool = next(m for m in messages if type(m).__name__ == "ToolMessage")
    assert int(tool.content) == 7
    assert tool.tool_call_id == "call_1"

    first_ai = next(m for m in messages if type(m).__name__ == "AIMessage")
    assert first_ai.tool_calls
    assert first_ai.tool_calls[0]["id"] == "call_1"
    assert first_ai.tool_calls[0]["name"] == "add"
    assert first_ai.tool_calls[0]["args"] == {"a": 3, "b": 4}

    # 路由正交：第 1 轮 tool_calls 触发工具节点，第 2 轮文本答案结束循环。
    assert type(messages[0]).__name__ == "HumanMessage"
    assert type(messages[1]).__name__ == "AIMessage"
    assert type(messages[2]).__name__ == "ToolMessage"
    assert type(messages[3]).__name__ == "AIMessage"
    assert not getattr(messages[3], "tool_calls", None)

    assert png and _png_ok(png[-1])
    framework = [record for record in records if record.attribution == "framework"]
    assert framework == [], [record.target for record in framework]
    assert all(record.attribution in {"framework", "user"} for record in records)
