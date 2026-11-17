# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US6 —— **多会话隔离**（连续两次不累积 / 并发两次不串扰 / 通道零残留）。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-004 / FR-005 / FR-006 · SC-008 / SC-009 · 契约 §6 的 **I-09**。
"""

from __future__ import annotations

import threading
from typing import Any

from ._invoke_support import build_conditional_graph, build_two_node_graph


class TestConsecutiveCalls:
    def test_second_call_does_not_contain_the_first_calls_values(self) -> None:
        """**连续**两次调用 ⇒ ⇒ 第二次的结果 MUST **不含**第一次的新增（FR-004 · SC-008）。"""
        app = build_two_node_graph().compile()
        first = app.invoke({"messages": ["first"]})
        second = app.invoke({"messages": ["second"]})
        assert "first" in first["messages"]
        assert "first" not in second["messages"]
        assert second["messages"] == ["second", "a", "b"]

    def test_route_channels_do_not_leak_into_the_next_call(self) -> None:
        """**步末清空**口径：路由通道的值 MUST **不残留**到下一次调用（FR-006 · SC-008）。

        ⚠️ 用**带** ``path_map`` 的条件边图 ⇒ ⇒ 才有路由通道 ⇒ ⇒ 断言**非空洞**。
        """
        app = build_conditional_graph().compile()
        first = app.invoke({"messages": ["first"]})
        second = app.invoke({"messages": ["second"]})
        assert list(first) == list(second)
        assert not any(key.startswith("branch:to:") for key in second)


class TestConcurrentCalls:
    def test_two_concurrent_calls_do_not_cross_talk(self) -> None:
        """**并发**两次调用 ⇒ ⇒ 两次结果 MUST **互不含**对方的值（FR-004 · SC-009）。"""
        app = build_two_node_graph().compile()
        results: dict[str, list[Any]] = {}

        def _run(tag: str) -> None:
            results[tag] = list(app.invoke({"messages": [tag]}).get("messages", []))

        threads = [threading.Thread(target=_run, args=(tag,)) for tag in ("x", "y")]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert set(results) == {"x", "y"}
        assert "x" in results["x"] and "y" not in results["x"]
        assert "y" in results["y"] and "x" not in results["y"]


class TestNoResidue:
    def test_compiled_product_channels_stay_value_free(self) -> None:
        """编译产物持有的通道 MUST **仍是零状态残留**的规格模板（FR-004 · SC-008）。

        ⚠️ 每次运行由 L2 **从规格新建**通道实例 ⇒ ⇒ 编译产物里的模板**永不**被写入。

        ⚠️ **覆盖型**通道（``LastValue``）⇒ ⇒ 模板**无值**（``is_available()`` 为假）；
        ⚠️ **归约型**通道（``BinaryOperatorAggregate``）⇒ ⇒ 模板里只有**类型空值**
        （``[]``）⇒ ⇒ **不含**任何运行期写入。
        """
        app = build_two_node_graph().compile()
        app.invoke({"messages": ["seed"]})
        app.invoke({"messages": ["seed"]})
        channels = app._spec.channels  # type: ignore[attr-defined]
        assert not channels["llm_calls"].is_available()
        assert channels["messages"].value == []
