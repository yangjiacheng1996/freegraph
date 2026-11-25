# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 上游差分场景 B25F1-D-01…D-03（D-04 在 model factory 测试）。"""

from __future__ import annotations

import hashlib
import os
import runpy
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TARGET = _REPO_ROOT / "harness" / "demo" / "target.py"
_B25F1 = _REPO_ROOT / "harness" / "verification" / "B25F1"
_SHA_FILE = _REPO_ROOT / "tests" / "runtime" / "data" / "b25f1_target_py.sha256"

for _path in (_REPO_ROOT / "src", _B25F1):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _tiny_png() -> bytes:
    """1x1 合法 PNG —— 仅用于**离线**替换上游 `draw_mermaid_png()` 的网络渲染。"""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _projection(state: dict[str, Any]) -> dict[str, Any]:
    messages = list(state["messages"])
    return {
        "classes": [type(message).__name__ for message in messages],
        "contents": [
            getattr(message, "content", None) for message in messages
        ],
        "tool_calls": [
            list(getattr(message, "tool_calls", []) or []) for message in messages
        ],
        "tool_call_ids": [
            getattr(message, "tool_call_id", None) for message in messages
        ],
        "llm_calls": state.get("llm_calls"),
        "keys": sorted(state),
    }


def _run_target_copy(monkeypatch: pytest.MonkeyPatch, package: str) -> dict[str, Any]:
    pytest.importorskip("langchain")
    pytest.importorskip("IPython")
    import IPython.display as ipython_display
    import fake_model
    import langchain.chat_models as chat_models

    text = _TARGET.read_text(encoding="utf-8")
    if package == "langgraph":
        text = text.replace(
            "from freegraph.graph import StateGraph, START, END",
            "from langgraph.graph import StateGraph, START, END",
        )
        assert "from langgraph.graph import" in text
        # 上游 `draw_mermaid_png()` 会请求 mermaid.ink；D-01 只比对 agent 状态，
        # 因此在**离线**下用合法 1x1 PNG 替换该网络渲染（不触碰 target.py）。
        from langchain_core.runnables.graph import Graph as UpstreamGraph

        monkeypatch.setattr(
            UpstreamGraph,
            "draw_mermaid_png",
            lambda self, *args, **kwargs: _tiny_png(),
            raising=False,
        )
    with tempfile.TemporaryDirectory() as raw:
        copy = Path(raw) / "target_copy.py"
        copy.write_text(text, encoding="utf-8")
        original_init = chat_models.init_chat_model
        original_display = ipython_display.display
        fake_model.install()
        monkeypatch.setattr(ipython_display, "display", lambda value: None)
        try:
            namespace = runpy.run_path(str(copy), run_name="__main__")
        finally:
            chat_models.init_chat_model = original_init  # type: ignore[attr-defined]
            ipython_display.display = original_display  # type: ignore[assignment]
    state = namespace["messages"]
    assert isinstance(state, dict)
    return _projection(state)


def test_d01_same_fake_input_freegraph_vs_langgraph(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("langgraph")
    freegraph = _run_target_copy(monkeypatch, "freegraph")
    upstream = _run_target_copy(monkeypatch, "langgraph")

    assert freegraph["classes"] == upstream["classes"]
    assert freegraph["contents"] == upstream["contents"]
    assert freegraph["tool_calls"] == upstream["tool_calls"]
    assert freegraph["tool_call_ids"] == upstream["tool_call_ids"]
    assert freegraph["llm_calls"] == upstream["llm_calls"] == 2
    assert freegraph["keys"] == upstream["keys"]
    assert len(freegraph["classes"]) == 4


def test_d02_tool_loop_c4_c8_regression(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_target_copy(monkeypatch, "freegraph")
    assert result["classes"] == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    assert result["llm_calls"] == 2
    assert result["tool_calls"][1] and result["tool_calls"][1][0]["id"] == "call_1"
    assert result["tool_call_ids"][2] == "call_1"
    assert int(result["contents"][2]) == 7
    assert not result["tool_calls"][3]


def test_d03_target_py_read_only_dual_baseline() -> None:
    recorded = _SHA_FILE.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(_TARGET.read_bytes()).hexdigest()
    assert actual == recorded, "target.py 内容 SHA-256 不一致"

    baseline = os.environ.get("B25F1_BASELINE_REF", "origin/main")
    exists = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{baseline}^{{commit}}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        pytest.skip(
            f"基线 ref {baseline!r} 不可用 —— 保留 SHA-256 断言，MUST NOT 静默通过"
        )
    diff = subprocess.run(
        ["git", "diff", "--exit-code", baseline, "--", "harness/demo/target.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert diff.returncode == 0, diff.stdout + diff.stderr
