# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B7F3 · US7 —— **执行期纯净**（零环境变量 / 零出站 / 零第三方依赖）+ 文档守卫。

**共享夹具**：``tests/facade/_invoke_support.py``。

**判据**：spec FR-024 · SC-011 / SC-012 / SC-020 · 契约 §6 的 **I-11 / I-14**。
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any

from ._invoke_support import build_two_node_graph

#: **仓库根**（文档守卫用）。
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: **第三方家族**（零依赖判据的扫描域）。
_THIRD_PARTY = ("langchain", "langchain_core", "langgraph", "langsmith")


class TestPurity:
    def test_no_environment_variable_is_read_during_invoke(self) -> None:
        """``invoke()`` 全过程 MUST **零环境变量读取**（FR-024 · SC-011）。

        ⚠️ **测量机制 MUST 可判定** ⇒ ⇒ 对 ``os.environ`` / ``os.getenv`` 做**代理计数**
        ⇒ ⇒ **MUST NOT** 只断言「结果未受影响」（那**不**证明「未读取」）。
        """
        reads: list[str] = []
        real_environ_get = os.environ.get
        real_getenv = os.getenv

        def _tracking_environ_get(key: str, default: Any = None) -> Any:
            reads.append(f"environ.get:{key}")
            return real_environ_get(key, default)

        def _tracking_getenv(key: str, default: Any = None) -> Any:
            reads.append(f"getenv:{key}")
            return real_getenv(key, default)

        os.environ.get = _tracking_environ_get  # type: ignore[method-assign]
        os.getenv = _tracking_getenv  # type: ignore[assignment]
        try:
            build_two_node_graph().compile().invoke({"messages": ["seed"]})
        finally:
            os.environ.get = real_environ_get  # type: ignore[method-assign]
            os.getenv = real_getenv  # type: ignore[assignment]
        assert reads == []

    def test_no_third_party_module_is_imported_during_invoke(self) -> None:
        """``invoke()`` 之后 ``sys.modules`` MUST **不含**第三方家族（FR-024 · SC-012）。"""
        before = set(sys.modules)
        build_two_node_graph().compile().invoke({"messages": ["seed"]})
        added = {name for name in set(sys.modules) - before}
        assert not any(
            name == family or name.startswith(family + ".")
            for name in added
            for family in _THIRD_PARTY
        )

    def test_no_socket_connection_is_opened_during_invoke(self) -> None:
        """``invoke()`` 全过程 MUST **零出站连接**（FR-024 · SC-011）。

        ⚠️ **socket 监测夹具**（**只观测不阻断**）⇒ ⇒ 记录 ``socket.connect`` /
        ``socket.create_connection`` 的调用。
        """
        opened: list[Any] = []
        real_connect = socket.socket.connect
        real_create = socket.create_connection

        def _tracking_connect(self: Any, address: Any) -> Any:
            opened.append(address)
            return real_connect(self, address)

        def _tracking_create(address: Any, *args: Any, **kwargs: Any) -> Any:
            opened.append(address)
            return real_create(address, *args, **kwargs)

        socket.socket.connect = _tracking_connect  # type: ignore[method-assign]
        socket.create_connection = _tracking_create  # type: ignore[assignment]
        try:
            build_two_node_graph().compile().invoke({"messages": ["seed"]})
        finally:
            socket.socket.connect = real_connect  # type: ignore[method-assign]
            socket.create_connection = real_create  # type: ignore[assignment]
        assert opened == []

    def test_user_nodes_are_called_exactly_once_each(self) -> None:
        """用户节点 MUST **恰好**被调用一次（门面**不**引入额外调用）。"""
        calls: list[str] = []

        def _a(state: dict[str, Any]) -> dict[str, Any]:
            calls.append("a")
            return {"messages": ["a"]}

        def _b(state: dict[str, Any]) -> dict[str, Any]:
            calls.append("b")
            return {"messages": ["b"]}

        from freegraph.graph import END, START, StateGraph

        from ._invoke_support import State

        builder = StateGraph(State)
        builder.add_node("a", _a)
        builder.add_node("b", _b)
        builder.add_edge(START, "a")
        builder.add_edge("a", "b")
        builder.add_edge("b", END)
        builder.compile().invoke({"messages": []})
        assert calls == ["a", "b"]


class TestDocumentationGuard:
    def test_invoke_docstring_states_the_read_only_snapshot_rule(self) -> None:
        """``invoke`` 的 docstring MUST 含「**只读快照 · 不要原样回喂**」**及理由**
        （FR-009 · SC-020 · 契约 I-11）。

        ⚠️ **子串**断言（**不是**逐字相等）。
        """
        from freegraph._stategraph import CompiledGraph

        docstring = CompiledGraph.invoke.__doc__ or ""
        assert "只读快照" in docstring
        assert "不要原样回喂" in docstring
        assert "TypeError" in docstring  # 理由（回喂 ⇒ 节点里 `state.get(...) + 1` 会 TypeError）

    def test_manual_verification_record_covers_both_model_rounds(self) -> None:
        """**人工验证记录** MUST 含 **fake 模型轮** 与 **真实模型轮** 两轮的
        **实测输出**（SC-018 · 契约 **I-14**）。

        ⚠️ **MUST NOT** 只写「符合预期」⇒ ⇒ **MUST NOT** 出现该措辞。
        """
        record = _REPO_ROOT / "harness" / "verification" / "B7F3" / "manual-verification.md"
        assert record.exists(), "人工验证记录不存在"
        text = record.read_text(encoding="utf-8")
        assert "fake 模型轮" in text
        assert "真实模型轮" in text
        # ⚠️ 「符合预期」**只允许**出现在**禁止语境**里（``MUST NOT`` / 「不写」）
        # ⇒ ⇒ **不得**作为**实测输出**出现。
        for line in text.splitlines():
            if "符合预期" in line:
                assert "MUST NOT" in line or "不写" in line, line
        for marker in ("messages   :", "model.calls :"):
            assert marker in text, marker

    def test_manual_verification_record_carries_the_ratification_five_items(
        self,
    ) -> None:
        """**人工验证记录** MUST 含**发起者追认**文字与**五项**破面（SC-019 · 契约 **I-14**）。

        ⚠️ **五项**的唯一事实源 = ``spec.md``「Assumptions」的「破面全集 **5 类**」⇒ ⇒
        **MUST NOT** 少于五项 ⇒ ⇒ **MUST NOT** 多于五项。
        """
        record = _REPO_ROOT / "harness" / "verification" / "B7F3" / "manual-verification.md"
        assert record.exists(), "人工验证记录不存在"
        text = record.read_text(encoding="utf-8")
        assert "追认" in text
        items = (
            "L1 `invoke` 的 `input` 注解放宽",
            "L1 `invoke` 的 `config` 注解放宽",
            "L2 `run_graph` 的 `max_concurrency` 读取点",
            "G19「既有契约层矩阵行逐字未改」判据",
            "四处「`invoke` 未就绪」冻结断言的拆分替换",
        )
        for item in items:
            assert item in text, item
        # ⚠️ **MUST NOT** 多于五项 ⇒ ⇒ 破面清单的行数恰为 5。
        section = text[text.find("### 7.1") : text.find("### 7.2")]
        rows = [line for line in section.splitlines() if line.startswith("| **")]
        assert len(rows) == 5, rows

    def test_readme_states_the_read_only_snapshot_rule(self) -> None:
        """``README.md`` MUST 含「**只读快照 · 不要原样回喂**」**及理由**（SC-020）。

        ⚠️ **本守卫由 T047 追加**（Phase 10）—— README 由 **T047** 写就 ⇒ ⇒ 守卫
        **紧贴**其产物 ⇒ ⇒ **T034 → T047 之间零红窗口**（宪法「MUST NOT 写永久红
        CI」）。
        """
        readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "只读快照" in readme
        assert "不要原样回喂" in readme
        assert "TypeError" in readme  # 理由（回喂 ⇒ 节点里 `state.get(...) + 1` 会 TypeError）
