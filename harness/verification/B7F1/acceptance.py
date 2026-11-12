#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B7F1** 人工验收脚本（任务准备与执行循环 · super-step）。

定位
----
本脚本是 **B7F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收闸口 **V1–V12** + 全部成功标准 SC-001 … SC-025 +
覆盖率取证 + 10 条门禁的实跑结果，**不必**手工逐条执行
（对照 ``specs/b7f1-superstep-loop/quickstart.md`` 的 13 节手册）。

覆盖的分组（**逐组对应一个验收闸口**）：

* **V1** 单 super-step 跑通（**验收判据 A1** · 五阶段产物**逐项可观测**）；
* **V2** 写入合并（**验收判据 A2** · 归约按序归约 · 覆盖型多写显式失败 ·
  未知 key 显式失败）；
* **V3** 脱离构建器（**验收判据 A3** · 零上游导入 · 零出站 · 零环境变量）；
* **V4** 触发判定与版本号（**逐触发源**的合取项 · 同版本不重复触发 ·
  值逐字相等仍触发）；
* **V5** 收敛与步数上限（空任务集立即终止 · 缺省上限 **10007**（上游同款）·
  自环在上限处抛 ``GraphRecursionError`` · 多轮跨轮累计）；
* **V6** 一轮 super-step 的**原子性**（四类错误场景）；
* **V7** C4 回归的**节点边界**口径 + **读取层口径并存** + 挂载点**零改动**；
* **V8** 步末清空范围（只清「本轮未被写入的」路由型通道）；
* **V9** 导出面（**14 → 20**）与既有冻结面（**18 / 7**）；
* **V10** 覆盖率取证（``superstep.py`` 行 / 分支 **100%**）；
* **V11** 跨 feature 接线复核（**H-1…H-5** + **D-1**）；
* **V12** 人工验证记录（五段式 + 来源覆盖表 + 追认栏）。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

⚠️ **覆盖率工具是例外**（research **D-13**）——``coverage`` 是**开发期工具**
⇒ **不进**仓库依赖声明 ⇒ 本机未装时该段标「◌ 环境未就绪」（**不判失败**）
⇒ 装法：``uv pip install coverage``。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树** |

用法
----
    python3 harness/verification/B7F1/acceptance.py                    # 跑全部
    python3 harness/verification/B7F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B7F1/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B7F1/acceptance.py --skip-coverage    # 跳过覆盖率取证段（快）
    python3 harness/verification/B7F1/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import operator
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
SPEC_DIR = REPO_ROOT / "specs" / "b7f1-superstep-loop"
CONTRACT_PATH = SPEC_DIR / "contracts" / "superstep-contract.md"
QUICKSTART_PATH = SPEC_DIR / "quickstart.md"
MANUAL_VERIFICATION = REPO_ROOT / "harness" / "verification" / "B7F1" / "manual-verification.md"
MOUNT_POINT = REPO_ROOT / "tests" / "contracts" / "test_contract_regressions.py"
C4_REGRESSION = REPO_ROOT / "tests" / "runtime" / "test_read_c4_sparse_state.py"
RUNTIME_CONTRACT_TEST = REPO_ROOT / "tests" / "runtime" / "test_read_contract.py"
FEATURES_DIR = REPO_ROOT / "harness" / "features"
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"

#: 当前解释器（提示信息用）。
INTERPRETER = sys.executable

#: 仓库自带的 ``.venv``（提示信息用 · **不存在**时退化）。
PROJECT_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

#: 契约层 / 门面 / L2 内部 API 的公开符号面（**冻结面** · SC-015 / SC-016）。
CONTRACT_PUBLIC_SYMBOL_COUNT = 20
FACADE_PUBLIC_SYMBOL_COUNT = 7
RUNTIME_PUBLIC_SYMBOL_COUNT = 20

#: B7F1 新增的 **6** 个导出符号（FR-023 · SC-016）。
B7F1_NEW_EXPORTS = (
    "GraphSpec",
    "NodeSpec",
    "SchedulerState",
    "SuperStepResult",
    "run_super_step",
    "run_super_steps",
)

#: 门禁总数（**G1–G30** 的连续性是不变量 · SC-015）。
GATE_TOTAL = 30

#: 覆盖率 MUST **100%** 的文件（**阻断判据** · SC-017 · FR-027 ②）。
FULL_COVERAGE_FILES = (
    "src/freegraph/runtime/superstep.py",
    "src/freegraph/runtime/__init__.py",
)

#: **本地直跑**的门禁（纯本地 · 确定性 · **无网络 / 无命名空间**依赖）⇒ **硬断言**。
LOCAL_GATES = ("G21", "G23", "G24", "G25", "G26", "G29", "G30")

#: **Linux only** 的门禁（需**网络**（G22 建隔离 venv）/ **网络命名空间**（G28）
#: / **socket 监测**（G27））⇒ 本脚本**只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
LINUX_ONLY_GATES = ("G22", "G27", "G28")

#: 上游包名（**发行面红线** · FR-019 / FR-022）。
UPSTREAM_PACKAGE_NAMES = (
    "langgraph",
    "langchain",
    "langsmith",
    "typing_extensions",
    "typing-extensions",
)

#: **越界**标识符（FR-028 · MUST NOT 实现）。
#:
#: ⚠️ **回溯修订（2026-11-11 · B9F1 · 发起者特批 · 登记项 R-8 ⑤）**：
#: 原清单**含** ``"Command"`` —— 彼时 ``Command`` 归 **B9F1** ⇒ B7F1 的内核
#: **不实现**它 ⇒ 把它列为禁用名。B9F1 落地后，``Command`` 的**运行期语义**
#: **由 L2 内核实现** ⇒ ``Command`` **不再是**越界标识符 ⇒ **仅移除这一项**。
#: ⇒ **其余七项逐字保留**（``invoke`` / ``stream`` / ``compile`` /
#: ``StateGraph`` / ``Send`` / ``interrupt`` / ``async``）⇒ 判据**只移除一处**、
#: **不放宽其余**。
FORBIDDEN_NAMES = (
    "invoke",
    "stream",
    "compile",
    "StateGraph",
    "Send",
    "interrupt",
    "async",
)

#: 契约 §7 冻结的**不变量编号**（**逐条** · I-1…I-16）。
#: ⚠️ **2026-11-12 · 上游对齐 P2-b**：新增 **I-16**（运行期的通道值住在调度状态里 ⇒
#: **同一份图规格可并发跑多次而互不干扰** · 多会话隔离 · **上游同款**）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 17))

#: 调度内核的**用例**文件（AST 级扫描的扫描域 · SC-005）。
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

# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B5F2/acceptance.py 同款：单文件可独立运行）
# ─────────────────────────────────────────────────────────────────────────────
_CHECKS = 0
_FAILED: list[str] = []
_SOFT: list[str] = []
_SECTION = ""
_CAPTURE: Any = None


def section(title: str) -> None:
    """开一个新分组（打印小节标题）。"""
    global _SECTION
    _SECTION = title
    print(f"\n[{title}]")


def check(cond: object, label: str, detail: str = "") -> bool:
    """一条**硬断言**（不成立 ⇒ 判失败）。"""
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _FAILED.append(f"{_SECTION} · {label}" + (f" — {detail}" if detail else ""))
    print(f"  {'✔' if ok else '✘'} {label}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def soft(cond: object, label: str, note: str = "") -> bool:
    """**环境未就绪**的检查：不判失败，只标注「待环境就绪」。"""
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _SOFT.append(f"{_SECTION} · {label}" + (f" — {note}" if note else ""))
    print(f"  {'✔' if ok else '◌'} {label}" + (f"  ({note})" if note and not ok else ""))
    return ok


def eq(actual: object, expected: object, label: str) -> bool:
    """等值断言（失败时打印期望与实际）。"""
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 加载被验对象
# ─────────────────────────────────────────────────────────────────────────────
class _EnvironmentNotReady(RuntimeError):
    """**环境未就绪** —— 被验对象既未安装、源码树也不可达（退出码 2）。"""


def _load_runtime() -> tuple[Any, str]:
    """导入 ``freegraph.runtime``，返回 ``(模块, 模式说明)``。

    两态运行：

    * 环境**已安装** freegraph ⇒ 测**发行产物**；
    * 环境**未安装** ⇒ 自动把 ``<repo>/src`` 插入 ``sys.path`` 测**源码树**。

    ⚠️ 两者都不可达 ⇒ 抛 :class:`_EnvironmentNotReady` ⇒ 退出码 **2**
    （**环境未就绪**）—— 与「判失败」（退出码 1）**区分**。
    """
    try:
        import freegraph.runtime as runtime

        return runtime, "发行产物（当前环境已安装 freegraph）"
    except ImportError:
        src = SRC_DIR
        if not src.is_dir():
            raise _EnvironmentNotReady(
                f"freegraph 既未安装，且源码树 {src} 不可达"
            ) from None
        sys.path.insert(0, str(src))
        try:
            import freegraph.runtime as runtime
        except ImportError as error:
            raise _EnvironmentNotReady(
                f"源码树 {src} 存在，但 freegraph.runtime 不可导入：{error}"
            ) from error
        return runtime, f"源码树（{src} 已注入 sys.path）"


def _installed() -> bool:
    """当前环境**是否已安装** freegraph。"""
    try:
        import importlib.metadata as md

        md.version("freegraph")
    except Exception:  # noqa: BLE001
        return False
    return True


def _install_hint() -> str:
    """给出「怎么装」的提示（区分**源码树**与**发行产物**两种情形）。"""
    if PROJECT_VENV_PYTHON.is_file():
        return (
            f"uv pip install --python {PROJECT_VENV_PYTHON} -e .   # 发行产物\n"
            f"      uv pip install --python {PROJECT_VENV_PYTHON} coverage   "
            "# 开发期取证工具"
        )
    return (
        f"uv pip install --python {INTERPRETER} -e .\n"
        f"      uv pip install --python {INTERPRETER} coverage"
    )


def finish(title: str) -> int:
    """汇总硬断言并给出退出码（``0`` = PASS · ``1`` = FAIL）。"""
    print(f"\n── {title} 汇总 ──")
    print(f"硬断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待环境就绪 {len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
        print("  ⇒ **skip ≠ pass** —— 补齐环境后请重跑：")
        print(f"      {_install_hint()}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 工具（**只读** · 零副作用）
# ─────────────────────────────────────────────────────────────────────────────
def _table_cells(line: str) -> list[str]:
    """把一行 Markdown 表格拆成单元格（去首尾空单元格 · 去空白）。"""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = stripped.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [cell.strip() for cell in parts]


def _is_separator(cells: list[str]) -> bool:
    """判定是否表格的**分隔行**。"""
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _section_body(text: str, heading: str) -> list[str]:
    """取出某个 ``## `` 小节的正文行（**不含**小节标题本身）。"""
    collected: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(heading)
            continue
        if inside:
            collected.append(line)
    return collected


def _public_symbols(path: Path) -> list[str]:
    """取一个模块的 ``__all__``（静态解析 · 不导入）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = node.value
                    if isinstance(value, ast.List):
                        return [
                            element.value
                            for element in value.elts
                            if isinstance(element, ast.Constant)
                            and isinstance(element.value, str)
                        ]
    return []


def _mount_statuses() -> dict[str, str]:
    """解析挂载点文件的 ``GATE-MOUNT:`` 行 ⇒ ``{编号: status}``。"""
    statuses: dict[str, str] = {}
    if not MOUNT_POINT.is_file():
        return statuses
    pattern = re.compile(r"^#\s*GATE-MOUNT:\s*(\S+)\s*·\s*status=(\S+)")
    for line in MOUNT_POINT.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            statuses[match.group(1)] = match.group(2)
    return statuses


def _contract_invariants() -> list[str]:
    """**解析**调度契约 §7 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(CONTRACT_PATH.read_text(encoding="utf-8"), "## 7."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


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
    """取出 AST 里的**全部**被引用的标识符（**排除**字符串与注释）。"""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
    return names


# ─────────────────────────────────────────────────────────────────────────────
# 用例组（**逐组对应一个验收闸口**）
# ─────────────────────────────────────────────────────────────────────────────
def case_single_super_step(runtime: Any) -> None:
    """**V1** · 单 super-step 跑通（**A1** · SC-001 · SC-004）。

    * 订阅**有值**通道的节点执行**恰好一次**；
    * 订阅**无值**通道的节点执行 **0** 次；
    * 合并后状态与期望**逐项相等**；
    * 五阶段产物（**执行记录** / **待写入** / **合并后状态** / **轮数**）**逐项可观测**。
    """
    section("V1 · 单 super-step 跑通（A1 · 五阶段产物逐项可观测）")
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        GraphSpec,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
    )

    channels = {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
    }
    channels["messages"].update([["seed"]])
    calls: list[str] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("writer")
        return {"messages": ["written"], "count": 7}

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("messages",), run=writer)},
        edges={"__start__": ("writer",)},
    )

    result = run_super_step(spec, SchedulerState())

    eq(len(calls), 1, "订阅**有值**通道的节点执行**恰好一次**")
    eq(result.executed, ("writer",), "**执行记录** == 执行的节点名")
    eq(result.node_writes, {"writer": {"messages": (["written"],), "count": (7,)}},
       "**待写入** == 按节点分组的原始写入值")
    eq(result.state["messages"], ["seed", "written"], "**合并后状态** · 归约通道")
    eq(result.state["count"], 7, "**合并后状态** · 覆盖通道")
    eq(result.steps, 1, "**轮数** == 1")

    # 未被触发的节点执行 0 次
    quiet_spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"quiet": NodeSpec(subscribes=("count",), run=lambda s: {})},
        edges={},
    )
    quiet_result = run_super_step(quiet_spec, SchedulerState())
    eq(quiet_result.executed, (), "订阅**无值**通道的节点执行 **0** 次")


def case_write_merge(runtime: Any) -> None:
    """**V2** · 写入合并（**A2** · SC-002 / SC-007 / SC-023）。

    * 同轮双写归约通道 == ``operator.add`` 的**逐元素**结果；
    * 同轮双写**覆盖型**通道 ⇒ ``InvalidChannelUpdateError``（``.key`` 指向该通道）；
    * 未知 key ⇒ ``InvalidUpdateError``（``invalid_keys`` == **实际未知 key 集合**）。
    """
    section("V2 · 写入合并（A2 · 归约按序 · 覆盖型多写失败 · 未知 key 失败）")
    from freegraph.contracts import InvalidUpdateError
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        GraphSpec,
        InvalidChannelUpdateError,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
    )

    def build(count: int = 2) -> Any:
        channels = {
            "messages": BinaryOperatorAggregate("messages", list, operator.add),
            "count": LastValue("count", int),
        }
        channels["count"].update([0])
        return GraphSpec(
            channels=channels,
            nodes={
                "a": NodeSpec(
                    subscribes=("count",), run=lambda s: {"messages": ["from-a"]}
                ),
                "b": NodeSpec(
                    subscribes=("count",), run=lambda s: {"messages": ["from-b"]}
                ),
            },
            edges={"__start__": ("a", "b")},
        )

    result = run_super_step(build(), SchedulerState())
    eq(
        result.state["messages"],
        operator.add(["from-a"], ["from-b"]),
        "同轮双写归约通道 == `operator.add` 的**逐元素**结果",
    )
    eq(result.state["messages"], ["from-a", "from-b"], "归约的**顺序** == 节点表顺序")

    overwrite = build()
    try:
        run_super_step(
            GraphSpec(
                channels=overwrite.channels,
                nodes={
                    "a": NodeSpec(subscribes=("count",), run=lambda s: {"count": 1}),
                    "b": NodeSpec(subscribes=("count",), run=lambda s: {"count": 2}),
                },
                edges={"__start__": ("a", "b")},
            ),
            SchedulerState(),
        )
        check(False, "同轮双写**覆盖型**通道 ⇒ 抛 `InvalidChannelUpdateError`", "未抛错")
    except InvalidChannelUpdateError as error:
        eq(error.key, "count", "覆盖型冲突的 `.key` 指向该通道")

    unknown = build()
    try:
        run_super_step(
            GraphSpec(
                channels=unknown.channels,
                nodes={
                    "a": NodeSpec(
                        subscribes=("count",),
                        run=lambda s: {"count": 1, "ghost_a": 2, "ghost_b": 3},
                    )
                },
                edges={"__start__": ("a",)},
            ),
            SchedulerState(),
        )
        check(False, "未知 key ⇒ 抛 `InvalidUpdateError`", "未抛错")
    except InvalidUpdateError as error:
        eq(
            sorted(error.invalid_keys),
            ["ghost_a", "ghost_b"],
            "`invalid_keys` == **实际未知 key 集合**",
        )


def case_builder_independence(runtime: Any) -> None:
    """**V3** · 脱离构建器（**A3** · SC-005 / SC-014 / SC-018）。

    * 内核路径对上游包的**导入**次数 == **0**；
    * 调度内核源码 MUST NOT 出现**越界**标识符（**AST 级**）；
    * 导入调度内核**无副作用**（零环境变量 · 零出站）。
    """
    section("V3 · 脱离构建器（A3 · 零上游导入 · 零出站）")
    kernel = SRC_DIR / "freegraph" / "runtime" / "superstep.py"
    check(kernel.is_file(), "调度内核源文件在位", str(kernel))

    upstream_offenders: list[str] = []
    for path in sorted((SRC_DIR / "freegraph").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_modules(tree):
            root = module.split(".")[0]
            if root.startswith(UPSTREAM_PACKAGE_NAMES):
                upstream_offenders.append(f"{path.name}: {module}")
    check(
        upstream_offenders == [],
        "内核路径对上游包的**导入**次数 == **0**",
        "\n".join(upstream_offenders),
    )

    tree = ast.parse(kernel.read_text(encoding="utf-8"), filename=str(kernel))
    forbidden = sorted({n for n in _used_names(tree) if n in FORBIDDEN_NAMES})
    check(forbidden == [], "调度内核源码**零越界**标识符（AST 级）", str(forbidden))

    runtime_dir = REPO_ROOT / "tests" / "runtime"
    builder_offenders: list[str] = []
    for name in SCHEDULER_TEST_FILES:
        path = runtime_dir / name
        if not path.exists():
            continue
        case_tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(case_tree):
            if isinstance(node, ast.Import):
                builder_offenders.extend(
                    f"{name}: import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith(("freegraph.graph", "freegraph._stategraph"))
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith(("freegraph.graph", "freegraph._stategraph")):
                    builder_offenders.append(f"{name}: from {module} import ...")
    check(
        builder_offenders == [],
        "调度内核的用例**零**构建器导入（AST 级）",
        "\n".join(builder_offenders),
    )


def case_trigger_and_versions(runtime: Any) -> None:
    """**V4** · 触发判定与版本号（SC-003 / SC-004）。

    * 未被触发的节点执行 **0** 次 · 被触发的执行 **1** 次；
    * 同一版本**不重复触发**同一节点；
    * 写入一个**逐字相等**的值 ⇒ 下游**仍被触发**；
    * 写入版本**仅**在 ``update()`` 返回**真**时推进。
    """
    section("V4 · 触发判定与版本号（逐触发源 · 版本推进）")
    from freegraph.runtime import (
        GraphSpec,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
    )

    channels = {"count": LastValue("count", int), "seed": LastValue("seed", int)}
    channels["seed"].update([1])
    channels["count"].update([5])
    calls: list[str] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("writer")
        return {"count": 5}  # 与当前值**逐字相等**

    def sink(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("sink")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "sink": NodeSpec(subscribes=("count",), run=sink),
        },
        edges={"__start__": ("writer",), "writer": ("sink",)},
    )
    state = SchedulerState()

    # ⚠️ **上游同款**（2026-11-12 · 上游对齐）：触发源**恒为边** ⇒ 写入方由**入口边**触发，
    # 下游由**写入方的边**触发 ⇒ 下游在**下一轮**才跑（旧的「通道触发」口径已退场）。
    run_super_step(spec, state)
    eq(calls, ["writer"], "第 1 轮：**入口边**触发写入方（下游在**下一轮**才触发）")

    # ⚠️ 通道的值**完全没变**（仍是 5）⇒ 但写入方**执行成功** ⇒ 其**执行版本**推进
    # ⇒ **边**下游**仍被触发**（上游同款：边触发看的是**源节点的执行版本**）。
    run_super_step(spec, state)
    eq(calls, ["writer", "sink"], "第 2 轮：写入方的**执行版本**推进 ⇒ **边**下游被触发")
    eq(channels["count"].get(), 5, "通道的值**完全没变**")
    eq(state.channel_versions["count"], 1,
       "写入版本推进（`update()` 返回**真**）· 初始值豁免 ⇒ 基值 **0**")

    # 同一版本不重复触发
    plain = {"count": LastValue("count", int)}
    plain["count"].update([1])
    plain_calls: list[str] = []
    plain_spec = GraphSpec(
        channels=plain,
        nodes={
            "node": NodeSpec(
                subscribes=("count",), run=lambda s: plain_calls.append("node") or {}
            )
        },
        edges={"__start__": ("node",)},
    )
    plain_state = SchedulerState()
    run_super_step(plain_spec, plain_state)
    run_super_step(plain_spec, plain_state)
    eq(plain_calls, ["node"], "同一版本**不重复触发**同一节点")


def case_convergence(runtime: Any) -> None:
    """**V5** · 收敛与步数上限（SC-006 / SC-001）。

    * 触发集合为空 ⇒ **立即终止**（``executed`` == () 且 ``steps`` == **1**）；
    * 首轮即有任务 ⇒ ``steps`` == **2**；
    * 自环 ⇒ 在上限处抛 ``GraphRecursionError``；
    * **不显式指定上限**时实际生效的上限 == **25**；
    * 多轮入口的**跨轮累计**语义。
    """
    section("V5 · 收敛与步数上限（缺省 **10007** · 跨轮累计）")
    import inspect

    from freegraph.contracts import GraphRecursionError
    from freegraph.runtime import (
        GraphSpec,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
        run_super_steps,
    )

    default = inspect.signature(run_super_steps).parameters["max_steps"].default
    eq(default, 10007, "**签名缺省值** == **10007**（**上游同款** · 上游 "
       "`langgraph/_internal/_config.py:32`；⚠️ 上游可由环境变量覆盖，freegraph **MUST NOT** "
       "读环境变量 ⇒ 硬编码）")

    empty = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"idle": NodeSpec(subscribes=("count",), run=lambda s: {})},
        edges={},
    )
    empty_result = run_super_steps(empty)
    eq(empty_result.executed, (), "触发集合为空 ⇒ `executed` == **空元组**")
    eq(empty_result.steps, 1, "触发集合为空 ⇒ `steps` == **1**（只含空轮）")

    def one_round_spec() -> Any:
        channels = {"count": LastValue("count", int)}
        channels["count"].update([1])
        return GraphSpec(
            channels=channels,
            nodes={"worker": NodeSpec(subscribes=("count",), run=lambda s: {})},
            edges={"__start__": ("worker",)},
        )

    one = run_super_steps(one_round_spec())
    eq(one.executed, ("worker",), "首轮即有任务 ⇒ `executed` **非空**")
    eq(one.steps, 2, "首轮即有任务 ⇒ `steps` == **2**（1 执行轮 + 1 空轮）")
    eq(run_super_step(one_round_spec(), SchedulerState()).steps, 1,
       "单轮入口的 `steps` **恒为 1**")

    def self_loop_spec() -> Any:
        channels = {"count": LastValue("count", int)}
        channels["count"].update([1])
        return GraphSpec(
            channels=channels,
            nodes={
                "loop": NodeSpec(
                    subscribes=("count",),
                    run=lambda s: {"count": s["count"] + 1},
                )
            },
            edges={"__start__": ("loop",), "loop": ("loop",)},
        )

    try:
        # ⚠️ **显式**给一个小上限（否则要跑满缺省的 10007 轮）⇒ 上限**行为**与**缺省值**解耦
        run_super_steps(self_loop_spec(), max_steps=25)
        check(False, "自环规格 ⇒ 在上限处抛 `GraphRecursionError`", "未抛错")
    except GraphRecursionError as error:
        eq(error.recursion_limit, 25, "`recursion_limit` == **25**（显式上限）")
        eq(error.current_step, 25, "`current_step` == **25**")

    # 跨轮累计：同名节点的同一通道按轮次先后拼接
    channels = {
        "ax": LastValue("ax", int),
        "ay": LastValue("ay", int),
        "out": LastValue("out", str),
        "sa": LastValue("sa", int),
    }
    channels["sa"].update([1])
    chain = GraphSpec(
        channels=channels,
        nodes={
            "s1": NodeSpec(subscribes=("sa",), run=lambda s: {"ax": 1}),
            "s2": NodeSpec(subscribes=("ax",), run=lambda s: {"ay": 2}),
            "p": NodeSpec(subscribes=("ax", "ay"), run=lambda s: {"out": "written"}),
        },
        edges={"__start__": ("s1",), "s1": ("s2", "p"), "s2": ("p",)},
    )
    chained = run_super_steps(chain)
    eq(chained.executed, ("s1", "p", "s2", "p"),
       "`executed` == 各轮执行序列的**顺序拼接**（**上游同款** · 同轮顺序 = **节点名序**）")
    eq(chained.node_writes["p"]["out"], ("written", "written"),
       "`node_writes` 同名节点同一通道 == **按轮次先后拼接**")


def case_atomicity(runtime: Any) -> None:
    """**V6** · 一轮 super-step 的**原子性**（SC-024）。

    四类错误场景（节点抛异常 · 未知 key · 归约器抛错 · 覆盖型多写冲突）⇒
    出错后**全部**通道的值与**本轮开始前****逐字相等**。
    """
    section("V6 · 一轮 super-step 的原子性（四类错误场景）")
    from freegraph.contracts import InvalidUpdateError
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        GraphSpec,
        InvalidChannelUpdateError,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
    )

    def exploding_reducer(current: list[Any], new: Any) -> list[Any]:
        if new == ["boom"]:
            raise RuntimeError("reducer exploded")
        return operator.add(current, new)

    def channels() -> dict[str, Any]:
        built = {
            "a": LastValue("a", int),
            "b": BinaryOperatorAggregate("b", list, exploding_reducer),
        }
        built["a"].update([1])
        built["b"].update([["seed"]])
        return built

    def snapshot(built: dict[str, Any]) -> dict[str, Any]:
        return {
            key: (channel.get() if channel.is_available() else None)
            for key, channel in built.items()
        }

    scenarios = (
        ("节点抛异常", lambda s: (_ for _ in ()).throw(RuntimeError("node")), RuntimeError),
        ("未知 key", lambda s: {"a": 2, "ghost": 3}, InvalidUpdateError),
        ("归约器抛错", lambda s: {"a": 99, "b": ["boom"]}, RuntimeError),
    )
    for label, node, error_type in scenarios:
        built = channels()
        before = snapshot(built)
        spec = GraphSpec(
            channels=built,
            nodes={"writer": NodeSpec(subscribes=("a",), run=node)},
            edges={"__start__": ("writer",)},
        )
        try:
            run_super_step(spec, SchedulerState())
            check(False, f"{label} ⇒ 显式失败", "未抛错")
        except error_type:
            check(True, f"{label} ⇒ 显式失败")
        eq(snapshot(built), before, f"{label} ⇒ **全部**通道的值与本轮开始前相等")

    built = channels()
    before = snapshot(built)
    conflict = GraphSpec(
        channels=built,
        nodes={
            "a": NodeSpec(subscribes=("a",), run=lambda s: {"a": 2}),
            "b": NodeSpec(subscribes=("a",), run=lambda s: {"a": 3}),
        },
        edges={"__start__": ("a", "b")},
    )
    try:
        run_super_step(conflict, SchedulerState())
        check(False, "覆盖型多写冲突 ⇒ 显式失败", "未抛错")
    except InvalidChannelUpdateError:
        check(True, "覆盖型多写冲突 ⇒ 显式失败")
    eq(snapshot(built), before, "覆盖型多写冲突 ⇒ **全部**通道的值与本轮开始前相等")


def case_c4_regression(runtime: Any) -> None:
    """**V7** · C4 回归的**节点边界**口径 + 挂载点**零改动**（SC-009 / SC-010 / SC-011）。

    * C4 用例中**读取层口径**与**节点边界口径****并存**；
    * 节点边界口径**真的**存在（经**调度器**执行一次）；
    * 两条 ``GATE-MOUNT:`` 行**逐字未动**。
    """
    section("V7 · C4 回归（两条口径并存 · 挂载点零改动）")
    statuses = _mount_statuses()
    eq(statuses.get("C4"), "landed", "C4 挂载点 `status` == `landed`")
    eq(statuses.get("C8"), "not-landed", "C8 挂载点 `status` == `not-landed`（未落地）")

    text = C4_REGRESSION.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(C4_REGRESSION))
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    check(
        "test_c4_sparse_state_read_excludes_empty_channels" in functions,
        "**读取层口径**的断言**保留**（SC-010）",
    )
    check(
        "test_c4_node_boundary_the_real_node_input_excludes_empty_channels" in functions,
        "**节点边界口径**的断言**已追加**（SC-009）",
    )
    check(
        "run_super_step" in text,
        "节点边界口径**经调度器**执行（不是读取层的替身）",
    )


def case_step_end_clearing(runtime: Any) -> None:
    """**V8** · 步末清空范围（SC-012）。

    * 步末对**覆盖型 / 归约型**通道的**空序列写入**次数 == **0**；
    * 步末对**本轮写过的**路由型通道的**空序列写入**次数 == **0**；
    * 步末对**本轮未写的**路由型通道调用的比例 == **100%**；
    ⚠️ **2026-11-12 · 上游对齐 P2-a**：口径由「``clear()`` 调用」改为「**空序列**写入」
    （上游 ``langgraph/pregel/_algo.py:326-333`` 的 ``update(EMPTY_SEQ)``）⇒ **可观察语义等价**。
    * **两个入口**的清空**调用集合与次数逐项相等**。
    """
    section("V8 · 步末清空范围（只清本轮未写入的路由型通道）")
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        EphemeralValue,
        GraphSpec,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_step,
        run_super_steps,
    )

    # ⚠️ **2026-11-12 · 上游对齐 P2-a**：步末清空的**机制**改为**上游同款**的
    # 「对**未更新且仍有值**的通道调 ``update([])``」（上游 ``langgraph/pregel/_algo.py:326-333``）
    # ⇒ 计数口径由「``clear()`` 调用」改为「**空序列**写入」的次数。
    class _CountingLastValue(LastValue):
        def __init__(self, key: str, value_type: Any) -> None:
            super().__init__(key, value_type)
            self.clear_calls = 0

        def clear(self) -> bool:
            self.clear_calls += 1
            return super().clear()

        def update(self, values):  # type: ignore[no-untyped-def]
            if not values:
                self.clear_calls += 1
            return super().update(values)

    class _CountingEphemeral(EphemeralValue):
        def __init__(self, key: str, value_type: Any, guard: bool = True) -> None:
            super().__init__(key, value_type, guard)
            self.clear_calls = 0

        def clear(self) -> bool:
            self.clear_calls += 1
            return super().clear()

        def update(self, values):  # type: ignore[no-untyped-def]
            if not values:
                self.clear_calls += 1
            return super().update(values)

    class _CountingBinaryOperator(BinaryOperatorAggregate):
        def __init__(self, key: str, value_type: Any, reducer: Any) -> None:
            super().__init__(key, value_type, reducer)
            self.clear_calls = 0

        def clear(self) -> bool:
            self.clear_calls += 1
            return super().clear()

        def update(self, values):  # type: ignore[no-untyped-def]
            if not values:
                self.clear_calls += 1
            return super().update(values)

    def build(writes: dict[str, Any] | None = None) -> tuple[Any, dict[str, Any]]:
        built: dict[str, Any] = {
            "overwrite": _CountingLastValue("overwrite", int),
            "reduce": _CountingBinaryOperator("reduce", list, operator.add),
            "route": _CountingEphemeral("route", str),
            "seed": LastValue("seed", int),
        }
        built["seed"].update([1])
        payload = {"overwrite": 5, "reduce": ["x"]} if writes is None else writes
        spec = GraphSpec(
            channels=built,
            nodes={
                "writer": NodeSpec(subscribes=("seed",), run=lambda s: dict(payload))
            },
            edges={"__start__": ("writer",)},
        )
        return spec, built

    spec, built = build()
    # ⚠️ **上游同款**：路由通道**有值**且本轮**未**写入 ⇒ 被通知一次 ⇒ **清空**
    # （上游 ``langgraph/pregel/_algo.py:326-333`` 的
    # ``if channels[chan].is_available() and chan not in updated_channels``）
    built["route"].update(["payload"])
    state = SchedulerState()
    run_super_step(spec, state)
    # ⚠️ 观测**本次运行**的通道实例（**上游同款** · P2-b：每次运行从规格**新建**实例
    # ⇒ 图规格里的通道是**模板**）
    run_channels = state.channels
    eq(run_channels["overwrite"].clear_calls, 0, "步末对**覆盖型**通道的**空序列写入**次数 == **0**")
    eq(run_channels["reduce"].clear_calls, 0, "步末对**归约型**通道的**空序列写入**次数 == **0**")
    eq(run_channels["route"].clear_calls, 1, "步末对**本轮未写入的**路由型通道调用 == **100%**")
    eq(run_channels["route"].is_available(), False, "路由型通道被清空 ⇒ 无值")

    written_spec, written = build({"route": "payload"})
    written_state = SchedulerState()
    run_super_step(written_spec, written_state)
    eq(written_state.channels["route"].clear_calls, 0,
       "步末对**本轮写过的**路由型通道的**空序列写入** == **0**")
    eq(written_state.channels["route"].get(), "payload",
       "本轮写过的路由型通道的值**保留到下一轮**")

    single_calls: list[int] = []
    multi_calls: list[int] = []
    for sink in (single_calls, multi_calls):
        spec, built = build()
        built["route"].update(["payload"])
        state = SchedulerState()
        if sink is single_calls:
            run_super_step(spec, state)
        else:
            run_super_steps(spec, state)
        sink.append(state.channels["route"].clear_calls)
    eq(single_calls, multi_calls, "**两个入口**的清空**调用集合与次数逐项相等**")


def case_export_and_frozen_surface(runtime: Any) -> None:
    """**V9** · 导出面（**14 → 20**）与既有冻结面（SC-016 / SC-015）。

    * ``freegraph.runtime.__all__`` == **20** 且含 **6** 个新符号；
    * 契约层 == **20** · 门面 == **7**；
    * ``Requires-Dist`` **整体为空**（零新增依赖）。
    """
    section("V9 · 导出面（14 → 20）与既有冻结面")
    eq(len(runtime.__all__), RUNTIME_PUBLIC_SYMBOL_COUNT,
       "`freegraph.runtime.__all__` 的符号数 == **20**")
    missing = [name for name in B7F1_NEW_EXPORTS if name not in runtime.__all__]
    check(missing == [], "**6** 个新导出符号**全部在位**", str(missing))

    contracts_path = SRC_DIR / "freegraph" / "contracts" / "__init__.py"
    facade_path = SRC_DIR / "freegraph" / "graph.py"
    eq(
        len(_public_symbols(contracts_path)),
        CONTRACT_PUBLIC_SYMBOL_COUNT,
        "契约层的公开符号面 == **20**（上游对齐 P3 · **只增**）",
    )
    eq(
        len(_public_symbols(facade_path)),
        FACADE_PUBLIC_SYMBOL_COUNT,
        "门面的公开符号面 == **7**（**一字未动**）",
    )

    try:
        import importlib.metadata as md

        requires = md.requires("freegraph") or []
    except Exception:  # noqa: BLE001
        requires = []
    eq(requires, [], "`Requires-Dist` **整体为空**（零新增依赖）")

    upstream = [name for name in requires if name.split(";")[0].strip().lower() in UPSTREAM_PACKAGE_NAMES]
    check(upstream == [], "发行元数据**零**上游包名", str(upstream))


def case_contract_guard(runtime: Any) -> None:
    """**V10** · 契约守卫（SC-017 的判据侧）。

    * 契约 §7 的不变量编号集合 == **I-1…I-16**（**逐条**）；
    * 每条不变量**都有**「编号 → 断言」的绑定（守卫用例**真**存在）。
    """
    section("V10 · 契约守卫（I-1!I-16 逐条绑定）")
    eq(
        _contract_invariants(),
        list(EXPECTED_INVARIANTS),
        "契约 §7 的不变量编号集合 == **I-1…I-15**",
    )

    guard = REPO_ROOT / "tests" / "runtime" / "test_superstep_contract.py"
    check(guard.is_file(), "契约守卫用例在位", str(guard))
    if guard.is_file():
        tree = ast.parse(guard.read_text(encoding="utf-8"), filename=str(guard))
        functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        bound = 0
        for invariant in EXPECTED_INVARIANTS:
            name = f"test_i{invariant.split('-')[1]}_"
            if any(function.startswith(name) for function in functions):
                bound += 1
        eq(bound, len(EXPECTED_INVARIANTS), "每条不变量**都有**一个真实断言（守卫用例）")


def case_coverage_evidence(runtime: Any) -> None:
    """**V11** · 覆盖率取证（SC-017 · FR-027 ②）。

    * **阻断判据**：``superstep.py`` / ``__init__.py`` 的**行覆盖与分支覆盖**
      MUST 均为 **100%**；
    * **整包**覆盖率**记录但 MUST NOT 阻断**。

    ⚠️ ``coverage`` 是**开发期工具**（**不进**仓库依赖声明）⇒ 未安装时标
    「◌ 环境未就绪」（**不判失败**）。
    """
    section("V11 · 覆盖率取证（superstep.py 行 / 分支 100%）")
    probe = subprocess.run(
        [INTERPRETER, "-c", "import coverage"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if probe.returncode != 0:
        soft(
            False,
            "SC-017 覆盖率取证（行 / 分支 100%）",
            f"本解释器（{INTERPRETER}）**未装** `coverage` ⇒ "
            "**skip ≠ pass**；装法：uv pip install --python "
            f"{INTERPRETER} coverage",
        )
        return

    with tempfile.TemporaryDirectory(prefix="freegraph-b7f1-cov-") as tmp:
        data_file = Path(tmp) / "cov.json"
        env = dict(os.environ)
        env["COVERAGE_FILE"] = str(Path(tmp) / ".coverage")
        run = subprocess.run(
            [
                INTERPRETER,
                "-m",
                "coverage",
                "run",
                "--branch",
                "-m",
                "pytest",
                "-q",
                "tests/runtime",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if run.returncode != 0:
            check(
                False,
                "SC-017 覆盖率跑测（`coverage run --branch -m pytest …`）",
                run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "",
            )
            return
        export = subprocess.run(
            [INTERPRETER, "-m", "coverage", "json", "-o", str(data_file)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if export.returncode != 0 or not data_file.is_file():
            check(False, "SC-017 导出 `coverage json`", export.stderr.strip()[:200])
            return
        payload = json.loads(data_file.read_text(encoding="utf-8"))

    files = payload.get("files", {})
    for relative_path in FULL_COVERAGE_FILES:
        entry = files.get(relative_path)
        if entry is None:
            check(False, f"SC-017 `{relative_path}` 在覆盖率报告中")
            continue
        missing_lines = entry.get("missing_lines", [])
        missing_branches = entry.get("missing_branches", [])
        check(
            missing_lines == [],
            f"SC-017 `{relative_path}` **行覆盖 == 100%**",
            f"未覆盖行 {missing_lines}",
        )
        check(
            missing_branches == [],
            f"SC-017 `{relative_path}` **分支覆盖 == 100%**",
            f"未覆盖分支 {missing_branches}",
        )
    summary = payload.get("totals", {})
    soft(
        True,
        "整包覆盖率（**记录但不阻断**）",
        f"行 {summary.get('percent_covered_display', '?')}",
    )


def case_cross_feature_wiring(runtime: Any) -> None:
    """**V12** · 跨 feature 接线复核（SC-025 · 宪法 v1.8.0）。

    * **H-1**（B5F2 → B7F1 · C4 节点边界）—— 在位；
    * **H-2…H-5**（B5F1 的三条口径交接 + B5F2 的稀疏读唯一实现）—— 在位；
    * **D-1**（下游承接 · B7F1 → B8F1）—— 在位；
    * 导航文件 —— 在位。
    """
    section("V12 · 跨 feature 接线复核（H-1…H-5 + D-1）")
    b7f1 = FEATURES_DIR / "B7F1_任务准备与super-step循环.md"
    b8f1 = FEATURES_DIR / "B8F1_条件边路由与fresh读.md"
    readme = FEATURES_DIR / "README.md"

    check(b7f1.is_file(), "B7F1 提示词初稿在位", str(b7f1))
    check(b8f1.is_file(), "B8F1 提示词初稿在位", str(b8f1))
    check(readme.is_file(), "导航文件在位", str(readme))

    if b7f1.is_file():
        text = b7f1.read_text(encoding="utf-8")
        check(
            "承接条款（B5F2 → B7F1" in text,
            "**H-1**（B5F2 → B7F1 · C4 节点边界）在位",
        )
        check(
            "承接条款（B5F1 → B7F1" in text,
            "**H-2…H-5** 的 B5F1 口径交接在位",
        )
        check(
            "稀疏读唯一实现" in text,
            "**H-5** 的 B5F2 稀疏读唯一实现在位",
        )
        check(
            "只清「本轮未被写入的」路由型" in text,
            "步末清空的措辞**不得弱于** FR-014",
        )

    if b8f1.is_file():
        text = b8f1.read_text(encoding="utf-8")
        check("条件边" in text, "**D-1**（B7F1 的条件边字段预留）在位")
        check(
            "conditional_edges" in text,
            "**D-1** 点名了 `GraphSpec.conditional_edges`",
        )

    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        check("B7F1" in text, "导航文件含 **B7F1** 行")
        check("承接 B5F1" in text, "导航文件的 B7F1 行注明「承接 B5F1」")
        check("承接 B5F2" in text, "导航文件的 B7F1 行注明「承接 B5F2」")


def case_manual_verification_record(runtime: Any) -> None:
    """**V12 的延续** · 人工验证记录（SC-021 / SC-022）。

    * 记录文件**存在**且**五段式**小节齐全；
    * **来源覆盖表**的三张表（判据 / SC / FR）**在位**；
    * **追认栏**的状态**逐条**判定：

      - **未追认**（留白）⇒ 标「◌ 待发起者」⇒ **未追认前 MUST NOT 合入**；
      - **已追认** ⇒ 「追认文字 + 发起者确认 + 日期」**三者 MUST 齐备** ⇒
        **硬断言**（宪法 v1.6.0：追认 MUST 由**发起者本人**作出 ⇒ 实现者
        **未代签** ⇒ 记录里 MUST 点名**追认人**与**日期**）。
    """
    section("V12 · 人工验证记录（五段式 + 来源覆盖表 + 追认栏）")
    check(MANUAL_VERIFICATION.is_file(), "人工验证记录在位", str(MANUAL_VERIFICATION))
    if not MANUAL_VERIFICATION.is_file():
        return
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    for heading in ("## 1. 验证环境", "## 2. 验证步骤", "## 3. 实际输出",
                    "## 4. 结论", "## 5. 遗留问题", "## 6. 来源覆盖表"):
        check(heading in text, f"**五段式**小节齐全 · {heading}")
    check("来源覆盖表" in text, "**来源覆盖表**在位（判据 / SC / FR 三张）")
    check("发起者追认" in text, "**追认栏**在位")

    if "（待发起者填写" in text:
        # 尚未追认 ⇒ 标「◌ 待发起者」（**不判失败** —— 追认是**发起者**的动作）。
        soft(
            False,
            "发起者追认已闭合（tasks T053 · **阻断合入**）",
            "追认 MUST 由**发起者本人**作出（宪法 v1.6.0）⇒ 实现者**未代签**"
            " ⇒ **未追认前 MUST NOT 合入**",
        )
        return

    # 已追认 ⇒ 逐条检查「追认文字 + 发起者确认 + 日期」三者齐备。
    check(
        "追认文字" in text and "追认全部五项" in text,
        "追认栏含**追认文字**（宪法 v1.6.0）",
    )
    check("**追认人（发起者）**" in text, "追认栏**点名追认人（发起者）**")
    check("**追认日期**" in text, "追认栏含**追认日期**")
    check(
        "未代签" in text or "未另留书面签名" in text,
        "追认栏声明**实现者未代签**（宪法 v1.6.0）",
    )
    for item in ("R-1", "R-2", "R-4", "R-5", "Q13"):
        check(
            re.search(rf"\*\*{re.escape(item)}\*\*", text) is not None,
            f"追认清单含 **{item}**（tasks T053 的五项 · 逐项点名）",
        )


def case_gates(runtime: Any, installed: bool) -> None:
    """**门禁实跑**（10 条 · SC-015 / SC-011）。

    * **本地直跑**的 7 条 ⇒ **硬断言**（退出码 == 0）；
    * **Linux only** 的 3 条（``G22`` 需网络 · ``G27`` 需 socket 监测 ·
      ``G28`` 需网络命名空间）⇒ **只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
    """
    section("门禁实跑（10 条 · 零新增门禁编号）")
    extras = [
        "--project",
        "specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml",
    ]
    for gate in LOCAL_GATES:
        matches = sorted(GATES_DIR.glob(f"gate_{gate}_*.py"))
        if not matches:
            check(False, f"门禁 {gate} 的脚本在位", str(GATES_DIR))
            continue
        command = [INTERPRETER, str(matches[0])]
        if gate in {"G21", "G23"}:
            command.extend(extras)
        completed = subprocess.run(
            command, capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        check(
            completed.returncode == 0,
            f"门禁 {gate} 通过（退出码 0）",
            (completed.stdout + completed.stderr).strip().splitlines()[-1]
            if (completed.stdout + completed.stderr).strip()
            else "",
        )
    for gate in LINUX_ONLY_GATES:
        matches = sorted(GATES_DIR.glob(f"gate_{gate}_*.py"))
        if not matches:
            soft(False, f"门禁 {gate} 的脚本在位", str(matches))
            continue
        completed = subprocess.run(
            [INTERPRETER, str(matches[0])],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        soft(
            completed.returncode == 0,
            f"门禁 {gate} 通过（**Linux only** · 只观测不阻断）",
            (completed.stdout + completed.stderr).strip().splitlines()[-1]
            if (completed.stdout + completed.stderr).strip()
            else "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 验收记录片段
# ─────────────────────────────────────────────────────────────────────────────
def build_record(mode: str, verdict: str, rc: int) -> str:
    """产出**五段式**的验收记录片段（可直接并入 ``manual-verification.md``）。"""
    out: list[str] = []
    out.append(
        "# B7F1 验收记录（由 `harness/verification/B7F1/acceptance.py` 生成）"
    )
    out.append("")
    out.append("## 1. 环境")
    out.append("")
    out.append("| 项 | 内容 |")
    out.append("|---|---|")
    out.append(
        f"| 操作系统 | {platform.system()} {platform.release()} ({platform.machine()}) |"
    )
    out.append(f"| Python | {sys.version.split()[0]}（`{sys.executable}`） |")
    out.append(f"| 运行模式 | {mode} |")
    out.append(f"| 工作目录 | `{os.getcwd()}` |")
    out.append("| 依赖 | 本脚本**仅** Python 标准库（零第三方） |")
    out.append("")
    out.append("## 2. 步骤")
    out.append("")
    out.append("```bash")
    out.append("python3 harness/verification/B7F1/acceptance.py")
    out.append("```")
    out.append("")
    out.append("## 3. 实际输出")
    out.append("")
    out.append("```text")
    out.append(_CAPTURE.getvalue().rstrip() or "（无输出）")
    out.append("")
    out.append("```")
    out.append("")
    out.append("## 4. 结论")
    out.append("")
    out.append(f"**验收结论：{verdict}**（退出码 {rc}）")
    out.append("")
    out.append("## 5. 遗留问题")
    out.append("")
    out.append("⬜ 待填")
    out.append("")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    """入口（两态运行 · 退出码 0 / 1 / 2）。"""
    parser = argparse.ArgumentParser(
        description="B7F1 人工验收脚本（一条命令跑完全部验收闸口 V1–V12）"
    )
    parser.add_argument("--record", help="把验收记录片段写到该路径")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="要求当前环境**已安装** freegraph（否则判失败）",
    )
    parser.add_argument(
        "--skip-coverage",
        action="store_true",
        help="跳过**覆盖率取证**段（需 `coverage` · 开发期工具）",
    )
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help="跳过**门禁实跑**段（10 条门禁脚本）",
    )
    args = parser.parse_args()

    global _CAPTURE
    _CAPTURE = io.StringIO()
    _real_stdout = sys.stdout

    class _Tee:
        def write(self, text: str) -> int:
            _real_stdout.write(text)
            _CAPTURE.write(text)
            return len(text)

        def flush(self) -> None:
            _real_stdout.flush()

    sys.stdout = _Tee()

    print("══ acceptance · B7F1 任务准备与执行循环（super-step） ══")
    try:
        runtime, mode = _load_runtime()
    except _EnvironmentNotReady as error:
        sys.stdout = _real_stdout
        print(f"◌ 环境未就绪：{error}")
        print("结论：SKIP（退出码 2）")
        return 2
    installed = _installed()
    section("运行环境")
    if not installed:
        if args.require_installed:
            check(
                False,
                "当前环境**已安装** freegraph（--require-installed）",
                "未安装",
            )
        else:
            soft(
                False,
                "当前环境**已安装** freegraph（发行产物可导入）",
                f"本解释器（{INTERPRETER}）**未安装** ⇒ 已自动把 <repo>/src 注入 "
                "sys.path 测**源码树**（不判失败）；" + _install_hint(),
            )
    started = time.monotonic()

    cases = (
        ("case_single_super_step", lambda: case_single_super_step(runtime)),
        ("case_write_merge", lambda: case_write_merge(runtime)),
        ("case_builder_independence", lambda: case_builder_independence(runtime)),
        ("case_trigger_and_versions", lambda: case_trigger_and_versions(runtime)),
        ("case_convergence", lambda: case_convergence(runtime)),
        ("case_atomicity", lambda: case_atomicity(runtime)),
        ("case_c4_regression", lambda: case_c4_regression(runtime)),
        ("case_step_end_clearing", lambda: case_step_end_clearing(runtime)),
        ("case_export_and_frozen_surface", lambda: case_export_and_frozen_surface(runtime)),
        ("case_contract_guard", lambda: case_contract_guard(runtime)),
        ("case_cross_feature_wiring", lambda: case_cross_feature_wiring(runtime)),
        ("case_manual_verification_record", lambda: case_manual_verification_record(runtime)),
    )
    if not args.skip_coverage:
        cases = cases + (("case_coverage_evidence", lambda: case_coverage_evidence(runtime)),)
    if not args.skip_gates:
        cases = cases + (("case_gates", lambda: case_gates(runtime, installed)),)
    for name, case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {name} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B7F1 人工验收")
    print(f"  · 耗时 {time.monotonic() - started:.1f}s")
    sys.stdout = _real_stdout

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        verdict = "PASS" if rc == 0 else "FAIL"
        path.write_text(build_record(mode, verdict, rc), encoding="utf-8")
        print(f"验收记录片段已写入：{path}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
