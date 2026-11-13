# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**纯净性**的用例 —— 属 **B7F1**（tasks T044）。

覆盖的判定：

* **SC-005** —— 调度内核的用例中 `StateGraph` / `compile()` 的出现次数 == **0**
  （**AST 级**扫描 · 排除字符串与注释 ⇒ 不误伤陈述性文字）；
* **SC-014** —— 内核路径 `src/freegraph/**` 对 `langgraph` / `langchain*` /
  `langsmith` 的导入次数 == **0**；
* **SC-018** —— 零环境变量读取 · 零出站 · 导入无副作用。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点",)}`）⇒ ``subscribes`` **只**决定「读哪些通道」，
**不再**是触发源。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Callable

from freegraph.runtime import (
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
)

#: **上游包名**前缀（内核 MUST NOT 导入它们 · FR-019 / FR-022）。
UPSTREAM_PREFIXES = ("langgraph", "langchain", "langsmith")

#: **禁用标识符**（FR-028 · 不越界）。
#:
#: ⚠️ **回溯修订（2026-11-11 · B9F1 · 发起者特批 · 登记项 R-8 ⑤）**：
#: 原清单**含** ``"Command"`` —— 彼时 ``Command`` 归 **B9F1** ⇒ B7F1 的内核
#: **不实现**它 ⇒ 把它列为禁用名。本 feature 落地后，``Command`` 的**运行期
#: 语义**（``goto`` / ``update``）**由 L2 内核实现** ⇒ ``Command`` **不再是**
#: B7F1 判据里的「越界标识符」⇒ **仅移除这一项**。
#: ⇒ **其余六项逐字保留**（``invoke`` / ``stream`` / ``compile`` /
#: ``StateGraph`` / ``Send`` / ``interrupt``）⇒ 判据**只移除一处**、
#: **不放宽其余**（宪法 v1.6.0「MUST NOT 以此放宽任何门禁判据」）。
FORBIDDEN_NAMES = ("invoke", "stream", "compile", "StateGraph", "Send", "interrupt")

#: 调度内核的**用例**文件（AST 扫描的扫描域）。
SCHEDULER_TEST_FILES = (
    "test_superstep_basic.py",
    "test_superstep_merge.py",
    "test_superstep_trigger.py",
    "test_superstep_convergence.py",
    "test_superstep_atomicity.py",
    "test_superstep_clearing.py",
    "test_superstep_determinism.py",
    "test_superstep_purity.py",
    "test_superstep_contract.py",
)


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


# ── SC-014 / SC-018 · 内核路径的依赖隔离 ─────────────────────────────────


def test_the_kernel_imports_no_upstream_package(run_in_subprocess: Callable[..., Any]) -> None:
    """**SC-014**：导入调度内核 **不**连带加载任何上游包。

    ⚠️ 判定 MUST 在**子进程**里做（测试进程自身已导入 pytest ⇒ 同进程
    ``sys.modules`` 不可用 · 沿用 B4F1 的既有口径）。
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
    """**SC-018**：导入调度内核**无副作用**（零环境变量读取 · 零出站）。"""
    # ⚠️ **回溯修订 T-1 ⑦**（**B10F1** · 宪法 v1.8.0「破冻结面的三条」第 ① 条
    # · **拆分而不删**）：原判据是「``superstep.__all__`` == **一份内联的精确
    # 列表**」⇒ ⇒ **硬编码清单** ⇒ ⇒ B10F1 **增**了 3 个符号 ⇒ ⇒ **必红**
    # ⇒ ⇒ 改为「**与清单集合相等**」⇒ ⇒ **判据零放宽**（仍是「== 某份清单」
    # ⇒ **不是**「⊇」）⇒ ⇒ 清单 = ``tests/runtime/_runtime_export_manifest.py``
    # （**单一事实源**）⇒ ⇒ 清单**在父进程**取 ⇒ **序列化**进子进程源码
    # ⇒ ⇒ 子进程**零**额外依赖（⇒ **零**路径假设）。
    import json as _json

    from ._runtime_export_manifest import SUPERSTEP_EXPORT_SYMBOLS

    expected = _json.dumps(sorted(SUPERSTEP_EXPORT_SYMBOLS))
    payload = run_in_subprocess(
        f"""
import json
import freegraph.runtime.superstep as superstep
print(json.dumps({{"ok": sorted(superstep.__all__) == {expected}}}))
"""
    )

    assert payload["ok"] is True
    assert payload["env_reads"] == 0
    assert payload["egress"] == 0


# ── SC-005 · 脱离构建器（AST 级扫描）────────────────────────────────────


def test_the_scheduler_tests_never_import_the_graph_builder() -> None:
    """**SC-005**：调度内核的用例中 ``freegraph.graph`` / ``freegraph._stategraph``
    的**导入**次数 == **0**。

    ⚠️ 判据是「**导入**」而非「文本出现」⇒ 用例的 docstring 里**陈述**这两个
    名字**不**算违规 ⇒ 扫描 MUST 是 **AST 级**的。
    """
    runtime_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in SCHEDULER_TEST_FILES:
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


def test_the_scheduler_tests_never_use_the_builder_symbols() -> None:
    """**SC-005**：``StateGraph`` / ``compile()`` 的**使用**次数 == **0**。

    ⚠️ 同样是 **AST 级**扫描 ⇒ 排除字符串与注释。
    """
    runtime_dir = Path(__file__).resolve().parent
    offenders: list[str] = []
    for name in SCHEDULER_TEST_FILES:
        path = runtime_dir / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for used in _used_names(tree):
            if used in FORBIDDEN_NAMES:
                offenders.append(f"{name}: {used}")

    assert offenders == [], "\n".join(offenders)


def test_the_kernel_source_never_uses_the_out_of_scope_symbols(
    src_dir: Path,
) -> None:
    """**SC-005 / SC-014**：调度内核的源码 MUST NOT 出现**越界**的标识符。

    ⚠️ 扫描域 = ``src/freegraph/runtime/superstep.py``（AST 级 ⇒ 排除字符串与
    注释 ⇒ docstring 里陈述「本 feature 不做 invoke」**不**算违规）。
    """
    path = src_dir / "freegraph" / "runtime" / "superstep.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    offenders = [name for name in _used_names(tree) if name in FORBIDDEN_NAMES]
    assert offenders == [], "\n".join(offenders)


def test_the_scheduler_runs_without_any_builder_dependency() -> None:
    """**SC-005**：调度内核**不经由**构建器即可跑完一轮（手写图规格直接驱动）。

    ⚠️ **上游同款**：触发源**恒为边** ⇒ 规格**必须**带**入口边**
    （``edges={"__start__": ("worker",)}``）⇒ 图才起得了跑。
    """
    channels = {"count": LastValue("count", int)}
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": NodeSpec(subscribes=(), run=lambda state: {}),
            "worker": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("worker",)},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.executed == ("worker",)
