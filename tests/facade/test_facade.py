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
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ._gatesupport import (
    FACADE_MANIFEST,
    g15_equality_violations,
    parse_manifest_symbols,
)

#: 未接线异常的消息正则（``data-model.md`` §4 · FR-009）。
NOT_WIRED_PATTERN = re.compile(
    r"(?:add_node|add_edge|add_conditional_edges|compile) 尚未接线（由 B\dF\d 交付）"
)

#: US1 阶段先交付的 **3 个**符号（US3 才补齐其余 4 个）。
US1_SUBSET = {"StateGraph", "START", "END"}


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
        """构造**零副作用**——只存下私有的 ``schema``，不暴露任何公开属性。"""
        schema = {"count": 0}
        graph = facade.StateGraph(schema)  # type: ignore[attr-defined]
        assert vars(graph) == {"_schema": schema}
        assert not hasattr(graph, "schema")
        for name in vars(graph):
            assert name.startswith("_")


# ── T015 · 未接线语义 + 「未越界」（SC-011 / SC-016）───────────────────


class TestNotWired:
    """**未接线** —— 四个方法一律抛内置 ``NotImplementedError``。"""

    @pytest.mark.parametrize(
        ("method_name", "args"),
        [
            ("add_node", ("a", lambda state: state)),
            ("add_edge", ("a", "b")),
            ("add_conditional_edges", ("a", lambda state: "b", ["b"])),
            ("compile", ()),
        ],
        ids=["add_node", "add_edge", "add_conditional_edges", "compile"],
    )
    def test_not_wired_method_raises_not_implemented(
        self, facade: object, method_name: str, args: tuple[object, ...]
    ) -> None:
        """每个方法 MUST 抛 ``NotImplementedError``，消息**点名归属 feature**。"""
        graph = facade.StateGraph({})  # type: ignore[attr-defined]
        with pytest.raises(NotImplementedError) as excinfo:
            getattr(graph, method_name)(*args)
        assert NOT_WIRED_PATTERN.search(str(excinfo.value)), str(excinfo.value)

    def test_not_wired_compile_reports_b7f2(self, facade: object) -> None:
        """``compile`` 的消息 MUST 点名 **B7F2**（其余三个点名 B6F1）。"""
        graph = facade.StateGraph({})  # type: ignore[attr-defined]
        with pytest.raises(NotImplementedError) as excinfo:
            graph.compile()
        assert "compile 尚未接线（由 B7F2 交付）" in str(excinfo.value)

    def test_not_wired_methods_produce_no_real_semantics(self, facade: object) -> None:
        """**未越界** —— 四个方法**不产生**任何节点 / 边 / 编译产物。"""
        graph = facade.StateGraph({"a": 1})  # type: ignore[attr-defined]
        calls = [
            lambda: graph.add_node("n", lambda state: state),
            lambda: graph.add_edge("a", "b"),
            lambda: graph.add_conditional_edges("a", lambda s: "b", ["b"]),
            lambda: graph.compile(),
        ]
        for call in calls:
            with pytest.raises(NotImplementedError):
                call()
        assert vars(graph) == {"_schema": {"a": 1}}
        for forbidden in ("nodes", "edges", "invoke", "stream", "compiled"):
            assert not hasattr(graph, forbidden), forbidden

    def test_not_wired_compile_does_not_return_an_executable(self, facade: object) -> None:
        """``compile()`` MUST **不返回**任何可执行产物。"""
        graph = facade.StateGraph({})  # type: ignore[attr-defined]
        with pytest.raises(NotImplementedError):
            graph.compile()
        assert not hasattr(graph, "invoke")


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
    """既有消费者（验收脚本）的**导入段** MUST 成功（退出码 ≠ 2）。"""

    @pytest.mark.parametrize(
        "script",
        ["harness/demo/graph_core.py", "harness/demo/acceptance.py"],
        ids=["graph_core", "acceptance"],
    )
    def test_script_does_not_exit_with_environment_not_ready(
        self, repo_root: Path, src_dir: Path, script: str
    ) -> None:
        """脚本 MUST **不**以退出码 **2**（「环境未就绪」）结束。

        退出码 **1**（断言失败）是**本 feature 的预期状态**——``StateGraph``
        尚未接线（行为归 B6F1 / B7F2）。**2** 才说明门面还取不到。
        """
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
        assert proc.returncode != 2, (
            f"{script} 以退出码 2（环境未就绪）结束——门面导出面尚未就位：\n"
            f"{proc.stdout}\n{proc.stderr}"
        )
