# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""门面的**导出面**与**行为边界**断言（US1 + US3）。

覆盖的成功标准：

* **SC-001** import 冒烟（**子进程**执行 · 退出码 0）；
* **SC-002** ``START`` / ``END`` 的**取值**（逐字相等 + 均为 ``str``）；
* **SC-003** 导出面**两处相等**（``__all__`` **且** 模块内公开名集合）；
* **SC-010** 构造语义（成功构造 / 多传一个位置参数 ⇒ ``TypeError`` / 零副作用）；
* **SC-011** 未接线语义（``NotImplementedError`` + 消息**点名归属 feature**）；
* **SC-016** 「**未越界**」——四个方法**不产生**任何真实语义；
* **SC-017** ``Send`` 的不可变 / **不可哈希** / 位置与关键字两种形态。

**期望值一律从** ``contracts/facade-api.md`` §0 **解析**（手写清单）——
MUST NOT 硬编码，也 MUST NOT 从**生成的**快照解析（research D-07：
那会让判定变成「代码 → 快照 → 快照 vs 代码」的循环论证）。
"""

from __future__ import annotations

import dataclasses
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import pytest

from ._gatesupport import (
    FACADE_MANIFEST,
    g15_equality_violations,
    parse_manifest_symbols,
)

#: B7F2 后仍未交付的 **5 个构建方法**的消息正则（``compile()`` 已接线）。
NOT_DELIVERED_PATTERN = re.compile(
    r"(?:add_sequence|set_entry_point|set_conditional_entry_point|"
    r"set_finish_point|set_node_defaults) 本版本不交付"
)

#: US1 阶段先交付的 **3 个**符号（US3 才补齐其余 4 个）。
US1_SUBSET = {"StateGraph", "START", "END"}


class _InterruptState(TypedDict):
    count: int


@pytest.fixture(scope="module")
def manifest_symbols() -> set[str]:
    """门面导出面的**手写权威**（``facade-api.md`` §0 解析出的 7 个）。"""
    return parse_manifest_symbols(FACADE_MANIFEST)


@pytest.fixture(scope="module")
def facade() -> object:
    """门面模块（``freegraph.graph``）。"""
    import freegraph.graph as graph

    return graph


# ── T013 · import 冒烟 + 常量取值（SC-001 / SC-002）────────────────────


class TestImportSmoke:
    """**import 冒烟** —— 门面的 7 个名字在**干净解释器**里取得到。"""

    def test_import_succeeds_in_a_fresh_interpreter(self, src_dir: Path) -> None:
        """子进程执行 ``from freegraph.graph import ...`` ⇒ **退出码 0**。

        **必须子进程**：测试进程自身已导入 pytest，同进程的导入状态不可作依据。
        """
        code = (
            "from freegraph.graph import StateGraph, START, END\n"
            "assert StateGraph is not None\n"
            "assert START == '__start__'\n"
            "assert END == '__end__'\n"
            "print('import-ok')\n"
        )
        env = {**os.environ, "PYTHONPATH": str(src_dir)}
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            cwd=str(Path(src_dir).parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        assert proc.returncode == 0, f"子进程失败：\n{proc.stderr}"
        assert proc.stdout.strip() == "import-ok"

    def test_start_and_end_values(self, facade: object) -> None:
        """``START == '__start__'`` / ``END == '__end__'`` —— **逐字相等**。"""
        assert facade.START == "__start__"  # type: ignore[attr-defined]
        assert facade.END == "__end__"  # type: ignore[attr-defined]

    def test_start_and_end_are_plain_strings(self, facade: object) -> None:
        """两个常量 MUST 是**字符串**（不是枚举成员、不是自定义对象）。"""
        assert isinstance(facade.START, str)  # type: ignore[attr-defined]
        assert isinstance(facade.END, str)  # type: ignore[attr-defined]
        assert type(facade.START) is str  # type: ignore[attr-defined]
        assert type(facade.END) is str  # type: ignore[attr-defined]


# ── T014 · 导出面子集 + 构造语义（SC-010）──────────────────────────────


class TestExportSurfaceSubset:
    """**导出面子集** —— US1 先交付 3 个符号（US3 才补齐 7 个）。"""

    def test_all_contains_the_us1_subset(self, facade: object) -> None:
        """``__all__`` MUST **含** US1 的 3 个符号。"""
        assert US1_SUBSET <= set(facade.__all__)  # type: ignore[attr-defined]

    def test_public_names_contain_the_us1_subset(self, facade: object) -> None:
        """模块内**公开名集合** MUST **含** US1 的 3 个符号。"""
        public = {n for n in vars(facade) if not n.startswith("_")}
        assert US1_SUBSET <= public

    def test_constructor_accepts_exactly_one_positional_argument(
        self, facade: object
    ) -> None:
        """``StateGraph(schema)`` **构造成功**；**第三个**位置参数 ⇒ ``TypeError``。

        ⚠️ **2026-11-12 上游对齐 P3**：构造签名**逐字对齐上游**
        （``state_schema`` / ``context_schema`` / ``input_schema`` / ``output_schema`` ·
        上游 ``langgraph/graph/state.py:216-224``）⇒ **必填**位置参数**仍恰一个**
        （「只传 schema 一个位置参数」的口径**不受影响**）⇒ 但**可选**的第二个位置参数
        （``context_schema``）**可传** ⇒ 越界点顺延到**第三个**位置参数。
        """
        graph = facade.StateGraph({"count": 0})  # type: ignore[attr-defined]
        assert graph is not None
        # 上游同款：第二个位置参数 = ``context_schema``（可选）⇒ **合法**
        with_context = facade.StateGraph({"count": 0}, {"user": "x"})  # type: ignore[attr-defined]
        assert with_context is not None
        # 第三个位置参数不存在 ⇒ TypeError
        with pytest.raises(TypeError):
            facade.StateGraph({"count": 0}, {"user": "x"}, "extra")  # type: ignore[attr-defined]

    def test_constructor_has_no_side_effect(self, facade: object) -> None:
        """构造**零副作用**——只保存 schema 与空私有容器，不暴露公开属性。"""
        schema = {"count": 0}
        graph = facade.StateGraph(schema)  # type: ignore[attr-defined]
        assert set(vars(graph)) == {
            "_schema",
            "_nodes",
            "_edges",
            "_conditional_edges",
            "_branch_names",
        }
        assert vars(graph)["_schema"] is schema
        assert not hasattr(graph, "schema")
        for name in vars(graph):
            assert name.startswith("_")


# ── T015 · compile 已接线 + 其余构建方法未交付（SC-004 / SC-011 / SC-016）──


def _valid_graph(facade: object) -> object:
    """构造一张最小合法图（``START → a → END``）。"""
    graph = facade.StateGraph(_InterruptState)  # type: ignore[attr-defined]
    graph.add_node("a", lambda state: {})
    graph.add_edge(facade.START, "a")  # type: ignore[attr-defined]
    graph.add_edge("a", facade.END)  # type: ignore[attr-defined]
    return graph


class TestCompileIsWired:
    """**compile 已接线**（B7F2）—— 返回产物；能力面仍未就绪。"""

    def test_compile_returns_a_non_null_product_with_capability_surface(
        self, facade: object
    ) -> None:
        """``compile()`` 返回非空产物，6 个能力面方法**全部存在**。"""
        compiled = _valid_graph(facade).compile()  # type: ignore[attr-defined]
        assert compiled is not None
        for name in (
            "invoke",
            "stream",
            "get_graph",
            "get_state",
            "get_state_history",
            "update_state",
        ):
            assert hasattr(compiled, name), name

    def test_compile_reports_invoke_b7f3(self, facade: object) -> None:
        """**B7F3 已交付** ⇒ ``invoke()`` 在合法路径上 MUST **不**抛 ``NotImplementedError``。

        ⚠️ **替换为反面断言**（B7F3 · 破冻结面 · 追认项 ⑤）⇒ ⇒ **判据只可更严**：
        原断言「抛 ``NotImplementedError`` 且点名 B7F3」⇒ ⇒ 反面「MUST **不**抛」
        ⇒ ⇒ 语义**不删**（仍是「产物具备 ``invoke`` 能力面」这条纪律的判据）。
        """
        compiled = _valid_graph(facade).compile()  # type: ignore[attr-defined]
        try:
            compiled.invoke({})
        except NotImplementedError as exc:  # pragma: no cover - 失败路径
            pytest.fail(f"invoke 已由 B7F3 交付，不应抛 NotImplementedError：{exc}")

    def test_compile_does_not_mutate_the_builder(self, facade: object) -> None:
        """``compile()`` MUST NOT 改变构建器状态（可重复调用）。"""
        graph = _valid_graph(facade)
        before = set(vars(graph))
        assert before == {
            "_schema",
            "_nodes",
            "_edges",
            "_conditional_edges",
            "_branch_names",
        }
        graph.compile()  # type: ignore[attr-defined]
        graph.compile()  # type: ignore[attr-defined]
        assert set(vars(graph)) == before

    def test_compile_returns_a_product_but_capability_methods_are_not_implemented(
        self, facade: object
    ) -> None:
        """产物返回后，6 个能力面方法仍抛 ``NotImplementedError``（未越界）。"""
        graph = _valid_graph(facade)
        compiled = graph.compile()  # type: ignore[attr-defined]
        assert not hasattr(graph, "invoke")
        calls = (
            ("stream", ({},)),
            ("get_graph", ()),
            ("get_state", ({},)),
            ("get_state_history", ({},)),
            ("update_state", ({}, {})),
        )
        for name, args in calls:
            with pytest.raises(NotImplementedError):
                getattr(compiled, name)(*args)
        # ⚠️ **拆分而不删**（B7F3 · 破冻结面 · 追认项 ⑤）：``invoke`` 已由 B7F3 交付
        # ⇒ ⇒ 从参数化列表中**提出** ⇒ ⇒ 改为**独立断言** ⇒ ⇒ 其余 **5** 条目**逐字不动**。
        try:
            compiled.invoke({})
        except NotImplementedError as exc:  # pragma: no cover - 失败路径
            pytest.fail(f"invoke 已由 B7F3 交付，不应抛 NotImplementedError：{exc}")


class TestRemainingBuilderMethodsNotWired:
    """其余 **5 个**构建方法仍抛 ``NotImplementedError``（消息「本版本不交付」）。"""

    @pytest.mark.parametrize(
        ("method_name", "args"),
        [
            ("add_sequence", ([],)),
            ("set_entry_point", ("a",)),
            ("set_conditional_entry_point", (lambda state: "a",)),
            ("set_finish_point", ("a",)),
            ("set_node_defaults", ()),
        ],
        ids=[
            "add_sequence",
            "set_entry_point",
            "set_conditional_entry_point",
            "set_finish_point",
            "set_node_defaults",
        ],
    )
    def test_remaining_builder_methods_raise_not_implemented(
        self, facade: object, method_name: str, args: tuple[object, ...]
    ) -> None:
        graph = facade.StateGraph(_InterruptState)  # type: ignore[attr-defined]
        with pytest.raises(NotImplementedError) as excinfo:
            getattr(graph, method_name)(*args)
        assert NOT_DELIVERED_PATTERN.search(str(excinfo.value)), str(excinfo.value)


# ── T032b · 静态断点透传（SC-013）──────────────────────────────────────


class TestStaticInterruptPassthrough:
    """构建器不拦截 / 不新增静态断点字段；compile 签名仍接收两个关键字。"""

    def test_compile_signature_accepts_interrupt_keywords(self, facade: object) -> None:
        parameters = inspect.signature(facade.StateGraph.compile).parameters  # type: ignore[attr-defined]
        assert "interrupt_before" in parameters
        assert "interrupt_after" in parameters

    def test_builder_has_no_public_interrupt_fields(self, facade: object) -> None:
        graph = facade.StateGraph(_InterruptState)  # type: ignore[attr-defined]
        assert not hasattr(graph, "interrupt_before")
        assert not hasattr(graph, "interrupt_after")

    def test_validate_rejects_unknown_interrupt_node(self, facade: object) -> None:
        graph = facade.StateGraph(_InterruptState)  # type: ignore[attr-defined]
        graph.add_node("a", lambda state: {})
        graph.add_edge(facade.START, "a")  # type: ignore[attr-defined]
        graph.add_edge("a", facade.END)  # type: ignore[attr-defined]
        with pytest.raises(ValueError, match="nope"):
            graph.validate(interrupt=["nope"])


# ── T026 · 导出面集合相等（SC-003）─────────────────────────────────────


class TestExportSurfaceEquality:
    """导出面**两处相等**（Q1）：``__all__`` **且** 公开名集合 == §0 的 7 个。"""

    def test_all_matches_the_manifest(self, facade: object, manifest_symbols: set[str]) -> None:
        """``__all__`` 的集合 MUST **等于** §0 解析出的 7 个。"""
        exports = set(facade.__all__)  # type: ignore[attr-defined]
        public = {name for name in vars(facade) if not name.startswith("_")}
        violations = g15_equality_violations(exports, public, manifest_symbols)
        assert violations == [], f"``__all__`` 与 §0 清单的差集（对称差）：{violations}"

    def test_public_names_match_the_manifest(
        self, facade: object, manifest_symbols: set[str]
    ) -> None:
        """门面模块内**公开名集合** MUST **等于**同一集合。"""
        exports = set(facade.__all__)  # type: ignore[attr-defined]
        public = {n for n in vars(facade) if not n.startswith("_")}
        violations = g15_equality_violations(exports, public, manifest_symbols)
        assert violations == [], f"公开名集合与 §0 清单的差集（对称差）：{violations}"

    def test_selfcheck_detects_a_missing_export(
        self, facade: object, manifest_symbols: set[str]
    ) -> None:
        """**门禁自检** —— 删掉一个导出符号 ⇒ 集合相等段**确实报出「漏导出」**。

        **零副作用**：只在内存里从真实导出面**去掉一个**符号，
        再喂给同一套判定逻辑——子集段抓不到这一类（子集仍然成立）。
        """
        exports = set(facade.__all__)  # type: ignore[attr-defined]
        missing = sorted(exports - manifest_symbols) or ["StateGraph"]
        dropped = exports - {missing[0]}
        violations = g15_equality_violations(dropped, dropped, manifest_symbols)
        assert violations, "漏导出未被集合相等段报出"
        assert missing[0] in violations


# ── T027 · 转出同一性 + ``Send``（SC-017 / FR-004 / FR-005）───────────


class TestReExportedObjects:
    """``Command`` / ``RunConfig`` MUST **原样转出**（同一对象，非副本 / 非子类）。"""

    def test_command_is_the_contract_object(self) -> None:
        """``freegraph.graph.Command is freegraph.contracts.Command`` ⇒ **True**。"""
        import freegraph.contracts as contracts
        import freegraph.graph as graph

        assert graph.Command is contracts.Command

    def test_run_config_is_the_contract_object(self) -> None:
        """``freegraph.graph.RunConfig is freegraph.contracts.RunConfig`` ⇒ **True**。"""
        import freegraph.contracts as contracts
        import freegraph.graph as graph

        assert graph.RunConfig is contracts.RunConfig

    def test_re_exported_types_are_not_subclasses(self) -> None:
        """转出对象 MUST NOT 是**子类**（否则门面改动了契约层的形状）。"""
        import freegraph.contracts as contracts
        import freegraph.graph as graph

        assert graph.Command is contracts.Command
        assert graph.RunConfig is contracts.RunConfig
        # 未引入任何额外的基类 ⇒ 不是「子类化后再转出」。
        assert graph.Command.__mro__ == contracts.Command.__mro__
        assert graph.RunConfig.__mro__ == contracts.RunConfig.__mro__


class TestSend:
    """``Send`` —— 不可变记录 + **不可哈希** + 位置 / 关键字两种形态。"""

    def test_both_call_forms_are_legal(self, facade: object) -> None:
        """``Send("w", {...})`` 与 ``Send(node="w", arg={...})`` **都合法**。"""
        positional = facade.Send("w", {"n": 1})  # type: ignore[attr-defined]
        keyword = facade.Send(node="w", arg={"n": 1})  # type: ignore[attr-defined]
        assert positional == keyword
        assert positional.node == "w"
        assert positional.arg == {"n": 1}

    def test_is_a_frozen_dataclass(self, facade: object) -> None:
        """``Send`` MUST 是 ``frozen=True`` 的 dataclass（不可变记录）。"""
        assert dataclasses.is_dataclass(facade.Send)  # type: ignore[attr-defined]
        params = facade.Send.__dataclass_params__  # type: ignore[attr-defined]
        assert params.frozen is True

    def test_mutating_an_attribute_fails(self, facade: object) -> None:
        """改属性 MUST **失败**（抛 ``FrozenInstanceError``）。"""
        payload = facade.Send("w", {"n": 1})  # type: ignore[attr-defined]
        with pytest.raises(dataclasses.FrozenInstanceError):
            payload.node = "other"  # type: ignore[misc]

    def test_is_explicitly_unhashable(self, facade: object) -> None:
        """``Send`` MUST **不可哈希**（显式 ``__hash__ = None`` · 裁定 11）。"""
        assert facade.Send.__dict__["__hash__"] is None  # type: ignore[attr-defined]
        with pytest.raises(TypeError):
            hash(facade.Send("w", {"n": 1}))  # type: ignore[attr-defined]

    def test_does_not_use_kw_only(self, facade: object) -> None:
        """MUST NOT 用 ``kw_only=True``——上游与验收脚本都用**位置参数**。"""
        fields = dataclasses.fields(facade.Send)  # type: ignore[attr-defined]
        assert [f.name for f in fields] == ["node", "arg"]
        assert all(not f.kw_only for f in fields)


# ── T028 · ``interrupt`` + 验收脚本导入段（SC-011）─────────────────────


class TestInterrupt:
    """``interrupt`` —— **已接线**（**B10F1** · 图运行之外 ⇒ ``InterruptError``）。"""

    @pytest.mark.parametrize(
        "call",
        [
            lambda fn: fn("value"),
            lambda fn: fn(value="value"),
        ],
        ids=["positional", "keyword"],
    )
    def test_outside_a_run_raises_the_structured_failure(
        self, facade: object, call: object
    ) -> None:
        """位置与关键字两种调用形态 MUST 走**同一分支**（均抛 ``InterruptError``）。

        ⚠️ **回溯修订 T-1 ⑤**（**B10F1** · 宪法 v1.8.0「破冻结面的三条」第 ① 条
        · **拆分而不删**）：原判据是「恒抛 ``NotImplementedError``（消息点名
        B10F1）⇒ ⇒ 它守的是「``interrupt`` **未接线**」这个**中间态**
        ⇒ ⇒ B10F1 把它**接线**后 ⇒ ⇒ **必红** ⇒ ⇒ 改为「**接线后**抛
        ``InterruptError(reason="not_in_run")``」⇒ ⇒ **判据零放宽**（断言
        **更具体**：结构化原因码 **取代** 未接线哨兵）⇒ ⇒ 同步本类的
        **docstring / 类名**（不再说「未接线（由 B10F1 交付）」）。

        ⇒ 判据形态保留：「**位置 / 关键字两种形态走同一分支**」。
        """
        from freegraph.runtime.errors import InterruptError

        with pytest.raises(InterruptError) as excinfo:
            call(facade.interrupt)  # type: ignore[attr-defined]
        assert excinfo.value.reason == "not_in_run"
        assert "outside of a graph run" in str(excinfo.value)


class TestAcceptanceScriptsCanImportTheFacade:
    """既有消费者（验收脚本）的**导入段** MUST 成功。

    ⚠️ **B13F1（2026-11-15）**：``graph_core.py`` 新增「门面未就绪守卫」——
    M1 阶段 ``compile()`` / ``invoke()`` 仍为桩时以退出码 **2** 结束（不判 FAIL）。
    因此本测试对 ``graph_core`` 允许退出码 2，但 MUST 是**门面已导入**后的
    「运行时未就绪」，而不是导入失败（输出不含「无法导入 freegraph」）。
    """

    @pytest.mark.parametrize(
        "script",
        ["harness/demo/graph_core.py", "harness/demo/acceptance.py"],
        ids=["graph_core", "acceptance"],
    )
    def test_script_does_not_exit_with_environment_not_ready(
        self, repo_root: Path, src_dir: Path, script: str
    ) -> None:
        env = {**os.environ, "PYTHONPATH": str(src_dir)}
        # **验收脚本的输出含中文**（用例名 / 失败详情）⇒
        # ① 子进程强制 UTF-8 输出（Windows 默认 cp1252 ⇒ 打印中文即崩）·
        # ② 父进程按 UTF-8 **容错解码**（否则 Windows 上解码失败 ⇒ 用例崩，
        #    而非被测行为失败）—— **实测**：CI 首跑的 2 个 Windows 作业即止步于此。
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, str(repo_root / script)],
            env=env,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if script.endswith("graph_core.py") and proc.returncode == 2:
            assert "[环境未就绪]" in proc.stdout, proc.stdout
            assert "无法导入 freegraph" not in proc.stdout, proc.stdout
            return
        assert proc.returncode != 2, (
            f"{script} 以退出码 2（环境未就绪）结束——门面导出面尚未就位：\n"
            f"{proc.stdout}\n{proc.stderr}"
        )
