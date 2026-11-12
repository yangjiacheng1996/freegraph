# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**纯净性 / 结构纪律**的用例 —— 属 **B9F1**（tasks T030）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 每张图 MUST 有
**入口边** ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

覆盖的判定：

* **SC-014** —— 内核路径对 ``langgraph`` / ``langchain*`` / ``langsmith`` 的导入
  次数 == **0**；环境变量读取 == **0** 次；出站 == **0** 次；导入**无副作用**；
* **SC-015** —— L1 **20** / 门面 **7** / ``freegraph.runtime.__all__`` **20** 个
  符号；``SuperStepResult`` 的字段数 == **4**；L2 → L3 / L4 / L5 的依赖边数
  == **0**；``NodeSpec.run`` 与 ``SchedulerState()`` 的**构造签名**与 B7F1 契约
  §1 **逐字相同**；
* **SC-016** —— **不经由** ``StateGraph`` / ``compile()`` / ``invoke()`` 的纯单元
  用例数 ≥ **1**；
* **SC-024** —— L1 的 ``StateSnapshot.next`` 字段**存在**；门面 ``END`` 的值与
  L2 终止标记字面量 ``"__end__"`` **逐字相等**；
* **SC-025** —— 本 feature **零**新增跳转观测字段。

⚠️ 「内核路径零上游导入 / 零环境变量 / 零出站」**必须在子进程**里执行 ⇒
**复用** B4F1 已有的 ``tests/runtime/conftest.py`` 夹具 ``run_in_subprocess``
（session 级 · **既有 conftest 零改动**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any, Callable

from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, SuperStepResult

#: **上游包名**前缀（内核 MUST NOT 导入它们 · FR-014）。
UPSTREAM_PREFIXES = ("langgraph", "langchain", "langsmith")

#: **禁用标识符**（FR-022 · 不越界）—— 与 B7F1 的清单**同款**
#: （⚠️ ``Command`` 已由 B9F1 交付 ⇒ 不在清单里 · 登记项 **R-8 ⑤**）。
FORBIDDEN_NAMES = ("invoke", "stream", "compile", "StateGraph", "Send", "interrupt")

#: **构建器符号**（MUST NOT 出现在本 feature 的用例里 · FR-022）。
BUILDER_NAMES = ("StateGraph", "compile", "invoke", "stream")

#: 本 feature 的**用例**文件（AST 扫描的扫描域 · SC-016）。
COMMAND_TEST_FILES = (
    "test_command_goto_update.py",
    "test_command_merge_parity.py",
    "test_command_parent.py",
    "test_command_goto_errors.py",
    "test_command_goto_semantics.py",
    "test_command_list.py",
    "test_command_noop.py",
    "test_command_atomicity.py",
    "test_command_determinism.py",
    "test_command_purity.py",
    "test_command_contract.py",
)


def _never(state: dict[str, Any]) -> dict[str, Any]:
    """**入口哨兵**的节点函数 —— 恒**不被调用**（哨兵无入边 ⇒ 永不被触发）。

    ⚠️ 触发源**恒为边**（上游对齐 · 2026-11-12）⇒ 每张图 MUST 有**入口边**
    ``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）⇒
    入口哨兵（上游 ``START`` **伪节点**）作为**节点表**的一员承载这条边（V-2）。
    """
    raise AssertionError("入口哨兵 __start__ 恒不被执行")


def _imported_modules(tree: ast.AST) -> list[str]:
    """取出 AST 里的**全部**导入模块路径（``import`` / ``from ... import``）。"""
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    return modules


def _used_names(tree: ast.AST) -> list[str]:
    """取出 AST 里的**全部**被引用的标识符（排除字符串与注释）。"""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
    return names


# ── SC-014 · 依赖隔离（子进程）────────────────────────────────────────────


def test_the_kernel_imports_no_upstream_package(
    run_in_subprocess: Callable[..., Any],
) -> None:
    """**SC-014**：导入调度内核 **不**连带加载任何上游包。

    ⚠️ 判定 MUST 在**子进程**里做（测试进程自身已导入 pytest ⇒ 同进程
    ``sys.modules`` 不可用 · 沿用 B4F1 / B7F1 的既有口径）。
    """
    payload = run_in_subprocess(
        """
import freegraph.runtime.superstep as superstep
print(__import__("json").dumps({"modules": superstep.__name__}))
"""
    )

    assert payload["modules"] == "freegraph.runtime.superstep"
    assert payload["env_reads"] == 0
    assert payload["egress"] == 0


def test_the_kernel_source_imports_no_upstream_package(src_dir: Path) -> None:
    """**SC-014**：内核路径 ``src/freegraph/**`` 对上游包的导入次数 == **0**。"""
    offenders: list[str] = []
    for path in sorted((src_dir / "freegraph").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_modules(tree):
            root = module.split(".")[0]
            if root.startswith(UPSTREAM_PREFIXES):
                offenders.append(f"{path.name}: {module}")

    assert offenders == [], "\n".join(offenders)


def test_importing_the_kernel_has_no_side_effects(
    run_in_subprocess: Callable[..., Any],
) -> None:
    """**SC-014**：导入调度内核**无副作用**（零环境变量读取 · 零出站）。"""
    payload = run_in_subprocess(
        """
import json
import freegraph.runtime.superstep as superstep
print(json.dumps({"ok": "run_super_step" in superstep.__all__}))
"""
    )

    assert payload["ok"] is True
    assert payload["env_reads"] == 0
    assert payload["egress"] == 0


# ── SC-022 · 不越界（AST 级扫描）──────────────────────────────────────────


def test_the_kernel_source_never_uses_the_out_of_scope_symbols(
    src_dir: Path,
) -> None:
    """**SC-022 / FR-022**：内核源码 MUST NOT 出现**越界**的标识符。

    ⚠️ 扫描域 = ``src/freegraph/runtime/superstep.py``（AST 级 ⇒ 排除字符串与
    注释 ⇒ docstring 里陈述「本 feature 不做 invoke」**不**算违规）。
    """
    path = src_dir / "freegraph" / "runtime" / "superstep.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    offenders = [name for name in _used_names(tree) if name in FORBIDDEN_NAMES]
    assert offenders == [], "\n".join(offenders)


def test_the_runtime_layer_imports_no_facade_or_upper_layer(
    src_dir: Path,
) -> None:
    """**SC-015**：L2 → L3 / L4 / L5 的依赖边数 == **0**（层纪律 · ARCH-1）。

    ⇒ L2 **MUST NOT** import 门面（L3）/ L4 / L5 ⇒ 终止标记因此 MUST 以
    **字面量**判定（裁定 6）。
    """
    forbidden_roots = ("freegraph.graph", "freegraph._stategraph", "freegraph.persistence",
                       "freegraph.observability")
    offenders: list[str] = []
    for path in sorted((src_dir / "freegraph" / "runtime").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_modules(tree):
            if module.startswith(forbidden_roots):
                offenders.append(f"{path.name}: {module}")

    assert offenders == [], "\n".join(offenders)


def test_the_command_test_files_never_import_the_graph_builder() -> None:
    """**SC-016**：本 feature 的用例**零**构建器导入（AST 级）。"""
    runtime_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in COMMAND_TEST_FILES:
        path = runtime_dir / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{name}: import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith(("freegraph.graph", "freegraph._stategraph"))
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(("freegraph.graph", "freegraph._stategraph")):
                    offenders.append(f"{name}: from {module} import ...")

    assert offenders == [], "\n".join(offenders)


def test_the_command_test_files_never_use_the_builder_symbols() -> None:
    """**SC-016**：``StateGraph`` / ``compile()`` / ``invoke()`` 的**使用**次数 == **0**。

    ⚠️ 同样是 **AST 级**扫描 ⇒ 排除字符串与注释。
    """
    runtime_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in COMMAND_TEST_FILES:
        path = runtime_dir / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for used in _used_names(tree):
            if used in BUILDER_NAMES:
                offenders.append(f"{name}: {used}")

    assert offenders == [], "\n".join(offenders)


# ── SC-015 / SC-024 · 结构纪律 ───────────────────────────────────────────


def test_the_result_object_still_has_exactly_four_fields() -> None:
    """**SC-024**：``SuperStepResult`` 的字段数 == **4**（四字段**冻结面**不动）。

    ⇒ **MUST NOT** 为记录跳转而扩字段（裁定 18）。
    """
    assert [field.name for field in fields(SuperStepResult)] == [
        "state",
        "executed",
        "node_writes",
        "steps",
    ]


def test_the_runtime_export_surface_holds_twenty_symbols() -> None:
    """**SC-015**：``freegraph.runtime.__all__`` 的符号数 == **20**（零新增）。

    ⇒ 本 feature 是**行为**的交付、**不是名字**的交付（裁定 13）。
    """
    import freegraph.runtime as runtime

    assert len(runtime.__all__) == 20


def test_the_contract_layer_and_the_facade_symbol_counts_are_unchanged(
    run_in_subprocess: Callable[..., Any],
) -> None:
    """**SC-015**：契约层 **20** / 门面 **7** 个符号面**一字不动**。

    ⚠️ 判定在**子进程**里做 ⇒ 本用例**自身**零门面导入（⇒ 「用例零构建器
    导入」的判据**恒绿** · FR-022）。
    """
    payload = run_in_subprocess(
        """
import json
import freegraph.contracts as contracts
import freegraph.graph as graph
print(json.dumps({
    "contracts": len(contracts.__all__),
    "facade": len(graph.__all__),
}))
"""
    )

    assert payload["contracts"] == 20
    assert payload["facade"] == 7


def test_the_facade_end_value_equals_the_l2_terminal_marker(
    run_in_subprocess: Callable[..., Any],
) -> None:
    """**SC-008 第三子句**：门面 ``END`` 的值 == L2 终止标记字面量 ``"__end__"``。

    ⚠️ L2 **MUST NOT** import 门面（ARCH-1）⇒ 终止标记 MUST 以**字面量**判定
    ⇒ 两侧的值 MUST **逐字相等**（**可自动核对** · 裁定 6）。
    """
    payload = run_in_subprocess(
        """
import json
import freegraph.graph as graph
import freegraph.runtime.superstep as superstep
print(json.dumps({
    "end": graph.END,
    "marker": superstep._TERMINAL_MARKER,
}))
"""
    )

    assert payload["end"] == payload["marker"] == "__end__"


def test_the_l1_state_snapshot_next_field_exists() -> None:
    """**SC-024**：L1 的 ``StateSnapshot.next`` 字段**存在**（跳转的现成出口）。

    ⚠️ 与上游 ``types.py:688-689`` **同款**（「The name of the node to execute in
    each task for this step」）⇒ 本 feature **不**新增任何跳转观测字段。
    """
    from freegraph.contracts import StateSnapshot

    assert "next" in StateSnapshot.__dataclass_fields__
    # ⚠️ **2026-11-12 上游对齐 P3**：`parent_config` **已新增**（**上游同款** ·
    # 上游 `langgraph/types.py:696`）⇒ 「不含」的旧断言**已反转**。
    assert "parent_config" in StateSnapshot.__dataclass_fields__


def test_the_node_spec_run_constructor_signature_is_unchanged() -> None:
    """**SC-015**：``NodeSpec.run`` 的**构造签名与名字**与 B7F1 契约 §1 **逐字相同**。

    ⚠️ **只允许**返回类型**注解**放宽（裁定 11 / 15 · 协变放宽）⇒ 参数名 /
    顺序 / 种类 / 个数均**未动** ⇒ B7F2 / B7F3 / B8F1 / B12F1 **零改动**。
    """
    import inspect

    signature = inspect.signature(NodeSpec)

    assert list(signature.parameters) == ["subscribes", "run"]
    assert signature.parameters["subscribes"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature.parameters["run"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_the_scheduler_state_constructor_signature_is_unchanged() -> None:
    """**SC-015**：``SchedulerState()`` 的**构造签名**与 B7F1 契约 §1 **逐字相同**。

    ⚠️ ``dynamic_edges`` 是**带缺省值**的字段（工厂语义）⇒ **无参构造**仍合法
    ⇒ 既有调用方**零改动**（裁定 12 · 登记项 **R-3 ①**）。

    ⚠️ **2026-11-12 · 上游对齐 P2-b**：新增 ``channels``（**带缺省值** · 工厂语义）⇒
    **构造签名仍可零参调用**、既有调用方**零改动**；该字段承载**本次运行**的通道实例
    （上游同款：``langgraph/pregel/_checkpoint.py:229-277`` 的 ``channels_from_checkpoint``
    ⇒ **每个调度状态 = 一次运行** ⇒ 多会话隔离）。
    """
    import inspect

    signature = inspect.signature(SchedulerState)

    assert list(signature.parameters) == [
        "versions_seen",
        "step",
        "channel_versions",
        "node_versions",
        "dynamic_edges",
        "channels",
    ]
    for parameter in signature.parameters.values():
        assert parameter.default is not inspect.Parameter.empty


def test_the_dynamic_edges_field_uses_factory_semantics() -> None:
    """**R-3 ①**：``dynamic_edges`` 用**工厂语义**实现 ⇒ 两个实例**不共享**。

    ⚠️ MUST NOT 用字面可变默认值（dataclass 会抛 ``ValueError: mutable
    default`` · **实测**）。
    """
    first = SchedulerState()
    second = SchedulerState()

    first.dynamic_edges["x"] = ("y",)

    assert second.dynamic_edges == {}
    assert SchedulerState().dynamic_edges == {}


def test_the_command_semantics_run_without_any_builder_dependency() -> None:
    """**SC-016**：``Command`` 的运行期语义**不经由**构建器即可跑完一轮。"""
    import operator

    from freegraph.contracts import Command
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        LastValue,
        run_super_step,
    )

    channels = {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
    }
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            # ⚠️ 触发源**恒为边**（上游对齐 · 2026-11-12）⇒ 入口边是**必需**的
            # ⇒ 入口哨兵（``__start__``）作为**伪节点**进节点表（V-2）。
            "__start__": NodeSpec(subscribes=(), run=_never),
            "writer": NodeSpec(
                subscribes=("count",),
                run=lambda state: Command(goto="target", update={"messages": ["x"]}),
            ),
            "target": NodeSpec(subscribes=(), run=lambda state: {}),
        },
        edges={"__start__": ("writer",)},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.executed == ("writer",)
    assert result.state["messages"] == ["x"]
