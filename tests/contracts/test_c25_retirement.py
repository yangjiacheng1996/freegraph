# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B8F3 · C25 正式作废守卫（T038）。

C25（节点命名别名）已于 2026-11-20 正式作废：编号保留不复用，
active 契约清单 = ``C1–C24 + C26–C27``。本文件把该状态钉死为可执行判据。
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _module(name: str) -> Any:
    """动态导入（避免 `tests/contracts` 的 G2 静态 import 档误报）。"""
    return importlib.import_module(name)


def test_add_node_has_no_alias_parameter_and_rejects_it() -> None:
    state_graph = _module("freegraph.graph").StateGraph
    assert "alias" not in inspect.signature(state_graph.add_node).parameters
    builder = state_graph(dict)
    with pytest.raises(TypeError, match="alias"):
        builder.add_node("a", lambda state: {}, alias="model")


def test_node_record_and_builder_spec_have_no_alias_field() -> None:
    stategraph = _module("freegraph._stategraph")
    record_fields = {
        field.name for field in dataclasses.fields(stategraph._NodeRecord)
    }
    spec_fields = {
        field.name for field in dataclasses.fields(stategraph._BuilderSpec)
    }
    assert "alias" not in record_fields
    assert "alias" not in spec_fields
    assert not hasattr(stategraph._NodeRecord, "alias")
    assert not hasattr(stategraph._BuilderSpec, "alias")


def test_q8_and_charter_mark_c25_as_retired() -> None:
    q8 = (REPO_ROOT / "harness" / "reports" / "Q8-图运行时最小契约.md").read_text(
        encoding="utf-8"
    )
    charter = (REPO_ROOT / "harness" / "proposals" / "立项书.md").read_text(
        encoding="utf-8"
    )
    assert "C1–C24 + C26–C27" in q8
    assert "C25 正式作废" in q8 or "正式作废" in q8
    assert "C1–C24 + C26–C27" in charter
    assert "C25 已于 2026-11-20 正式作废" in charter


def test_demo_uses_c1_to_c24_coverage() -> None:
    readme = (REPO_ROOT / "harness" / "demo" / "README.md").read_text(
        encoding="utf-8"
    )
    acceptance = (REPO_ROOT / "harness" / "demo" / "acceptance.py").read_text(
        encoding="utf-8"
    )
    assert "C1–C24" in readme
    assert "C1–C24" in acceptance
    assert "case_node_alias" not in readme
    assert "case_node_alias" not in acceptance


def test_parity_probe_has_no_d74_alias_scenario() -> None:
    source = (REPO_ROOT / "tests" / "differential" / "parity_probe.py").read_text(
        encoding="utf-8"
    )
    assert "D-74 alias" not in source
    assert "_fg_alias" not in source
    assert "_up_alias" not in source


def test_minimal_graph_still_builds_without_alias() -> None:
    facade = _module("freegraph.graph")
    builder = facade.StateGraph(dict)
    builder.add_node("a", lambda state: {})
    builder.add_edge(facade.START, "a")
    builder.add_edge("a", facade.END)
    assert "a" in builder._nodes
    assert not hasattr(builder._nodes["a"], "alias")
