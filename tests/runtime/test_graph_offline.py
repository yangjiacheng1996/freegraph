# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B22F1 · 断网 / 零出站 / 静态禁用扫描（US3）。"""

from __future__ import annotations

import ast
import socket
from pathlib import Path
from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    count: int


def _node(state: dict[str, object]) -> dict[str, object]:
    return {}


def _build() -> StateGraph:
    builder = StateGraph(State)
    builder.add_node("a", _node)
    builder.add_node("b", _node)
    builder.add_edge(START, "a")
    builder.add_conditional_edges("a", lambda s: "b", ["b", END])
    builder.add_edge("b", END)
    return builder

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_MODULES = (
    REPO_ROOT / "src" / "freegraph" / "contracts" / "graph.py",
    REPO_ROOT / "src" / "freegraph" / "_stategraph.py",
)


class _SocketGuard:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> object:
        self.calls += 1
        raise AssertionError("框架尝试出站")


def test_draw_mermaid_and_get_graph_are_zero_egress(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = _SocketGuard()
    monkeypatch.setattr(socket, "socket", guard)
    compiled = _build().compile()
    graph = compiled.get_graph()
    text = graph.draw_mermaid()
    assert isinstance(text, str) and text.strip()
    assert guard.calls == 0


def test_graph_sources_have_no_forbidden_network_or_env_usage() -> None:
    forbidden_imports = {"socket", "http", "urllib", "subprocess"}
    for path in GRAPH_MODULES:
        source = path.read_text(encoding="utf-8")
        # 署名头含项目 GitHub URL（原则 X）⇒ 只看代码体。
        body = "\n".join(
            line for line in source.splitlines() if not line.startswith("# Copyright")
        )
        assert "mermaid.ink" not in body
        assert "os.environ" not in body and "os.getenv" not in body
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(forbidden_imports), (path, imported & forbidden_imports)
