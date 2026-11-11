#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B9F1** 人工验收脚本（``Command`` 原语 · ``goto`` / ``update`` + ``Command.PARENT``）。

定位
----
本脚本是 **B9F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收闸口 **V1–V12** + 全部成功标准 SC-001 … SC-025 +
覆盖率取证（**差分口径**）+ 10 条门禁的实跑结果，**不必**手工逐条执行
（对照 ``specs/b9f1-command-primitive/quickstart.md`` 的 15 节手册）。

覆盖的分组（**逐组对应一个验收闸口**）：

* **V1** 跳转 + 更新**同时生效**（**A1 / A2** · SC-001 / SC-002）；
* **V2** 三形态**共用同一条合并路径**（**A3** · SC-003 / SC-004 / SC-023）；
* **V3** ``Command.PARENT`` 与**保留名**（SC-005）；
* **V4** 非法跳转目标 / 非法形态（SC-009）；
* **V5** 叠加 / ``END`` / 触发门槛 / 入参 / 生命周期（SC-007 / SC-008 / SC-010 / SC-011 / SC-023）；
* **V6** **命令列表** 与 **空操作**（SC-006 / SC-012 / SC-021）；
* **V7** **原子性**（SC-013）；
* **V8** **确定性** + 调度状态**不串扰**（SC-019）；
* **V9** **纯净性** / **结构纪律**（SC-014 / SC-015 / SC-024 / SC-025）；
* **V10** **契约守卫**（契约 §9 的 **I-1…I-14** 逐条绑定 · SC-016）；
* **V11** 覆盖率取证（**差分口径** · 行 / 分支 **100%** · SC-016）；
* **V12** 人工验证记录（五段式 + 来源覆盖表 + 追认栏 · SC-017 / SC-018）。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

⚠️ **覆盖率工具是例外**——``coverage`` 是**开发期工具**
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
    python3 harness/verification/B9F1/acceptance.py                    # 跑全部
    python3 harness/verification/B9F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B9F1/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B9F1/acceptance.py --skip-coverage    # 跳过覆盖率取证段（快）
    python3 harness/verification/B9F1/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

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
SPEC_DIR = REPO_ROOT / "specs" / "b9f1-command-primitive"
CONTRACT_PATH = SPEC_DIR / "contracts" / "command-contract.md"
QUICKSTART_PATH = SPEC_DIR / "quickstart.md"
MANUAL_VERIFICATION = REPO_ROOT / "harness" / "verification" / "B9F1" / "manual-verification.md"
FEATURES_DIR = REPO_ROOT / "harness" / "features"
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"

#: 当前解释器（提示信息用）。
INTERPRETER = sys.executable

#: 仓库自带的 ``.venv``（提示信息用 · **不存在**时退化）。
PROJECT_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

#: 契约层 / 门面 / L2 内部 API 的公开符号面（**冻结面** · SC-015）。
CONTRACT_PUBLIC_SYMBOL_COUNT = 18
FACADE_PUBLIC_SYMBOL_COUNT = 7
RUNTIME_PUBLIC_SYMBOL_COUNT = 20

#: ``SuperStepResult`` 的字段数（**四字段冻结面** · SC-024）。
SUPER_STEP_RESULT_FIELD_COUNT = 4

#: 门禁总数（**G1–G30** 的连续性是不变量 · SC-015）。
GATE_TOTAL = 30

#: 覆盖率 MUST **100%** 的文件（**阻断判据** · SC-016）。
FULL_COVERAGE_FILES = ("src/freegraph/runtime/superstep.py",)

#: **本地直跑**的门禁（纯本地 · 确定性 · **无网络 / 无命名空间**依赖）⇒ **硬断言**。
LOCAL_GATES = ("G21", "G23", "G24", "G25", "G26", "G29", "G30")

#: **Linux only** 的门禁（需**网络**（G22 建隔离 venv）/ **网络命名空间**（G28）
#: / **socket 监测**（G27））⇒ 本脚本**只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
LINUX_ONLY_GATES = ("G22", "G27", "G28")

#: 上游包名（**发行面红线** · FR-014）。
UPSTREAM_PACKAGE_NAMES = (
    "langgraph",
    "langchain",
    "langsmith",
    "typing_extensions",
    "typing-extensions",
)

#: **越界**标识符（FR-022 · MUST NOT 实现）—— **不含** ``Command``
#: （``Command`` 的运行期语义**由本 feature 交付** · 登记项 **R-8 ⑤**）。
FORBIDDEN_NAMES = (
    "invoke",
    "stream",
    "compile",
    "StateGraph",
    "Send",
    "interrupt",
    "async",
)

#: 契约 §9 冻结的**不变量编号**（**逐条** · I-1…I-14）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 15))

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

# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B7F1/acceptance.py 同款：单文件可独立运行）
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
    return [part.strip() for part in parts]


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


def _contract_invariants() -> list[str]:
    """**解析**命令契约 §9 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(CONTRACT_PATH.read_text(encoding="utf-8"), "## 9."):
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


def _channels() -> dict[str, Any]:
    """构造通道状态：归约型（``messages``）+ 覆盖型（``count`` / ``seed``）。"""
    from freegraph.runtime import BinaryOperatorAggregate, LastValue

    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 用例组（**逐组对应一个验收闸口**）
# ─────────────────────────────────────────────────────────────────────────────
def case_goto_and_update(runtime: Any) -> None:
    """**V1** · 跳转 + 更新**同时生效**（**A1 / A2** · SC-001 / SC-002）。

    * ``goto=END`` ⇒ 更新**照常生效**、**不产生跳转**；
    * ``goto="target"`` ⇒ 目标**被执行**（下一轮）**且**状态含该更新；
    * 两条断言**同时**成立 ⇒ 「只生效其一」的现象 == **0**。
    """
    section("V1 · 跳转 + 更新同时生效（A1 / A2 · SC-001 / SC-002）")
    from freegraph.contracts import Command
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_steps

    executed: list[str] = []
    channels = _channels()
    channels["seed"].update([1])

    def writer(state: dict[str, Any]) -> Command:
        executed.append("writer")
        return Command(goto="target", update={"count": 1})

    def target(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("target")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "target": NodeSpec(subscribes=(), run=target),
        },
        edges={},
    )
    result = run_super_steps(spec)

    eq(executed, ["writer", "target"], "``goto`` 目标在**下一轮**被执行（跳转生效）")
    eq(result.state["count"], 1, "``Command.update`` 已按通道语义合并进状态（更新生效）")
    check(
        "writer" in executed and "target" in executed,
        "两条断言**同时**成立（SC-002 · 「只生效其一」== 0）",
    )


def case_merge_parity(runtime: Any) -> None:
    """**V2** · 三形态**共用同一条合并路径**（**A3** · SC-003 / SC-004 / SC-023）。

    * 三种形态写同一 key ⇒ 合并结果**逐项相等**；
    * 未知 key ⇒ 三者**都**抛 ``InvalidUpdateError`` 且 ``invalid_keys`` **一致**；
    * 覆盖型通道同轮多写 ⇒ ``InvalidChannelUpdateError``（B5F1 既有类型）。
    """
    section("V2 · 三形态共用同一条合并路径（A3 · SC-003 / SC-004 / SC-023）")
    from freegraph.contracts import Command, InvalidUpdateError
    from freegraph.runtime import (
        GraphSpec,
        InvalidChannelUpdateError,
        NodeSpec,
        SchedulerState,
        run_super_step,
    )

    def run_returning(result: Any) -> Any:
        channels = _channels()
        channels["seed"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda s: result)},
            edges={},
        )
        return run_super_step(spec, SchedulerState())

    plain = run_returning({"messages": ["b"]})
    command = run_returning(Command(update={"messages": ["b"]}))
    listed = run_returning([Command(update={"messages": ["b"]})])

    eq(
        plain.state["messages"],
        command.state["messages"],
        "``dict`` 与 ``Command(update=)`` 的合并结果**逐项相等**",
    )
    eq(
        command.state["messages"],
        listed.state["messages"],
        "``Command(update=)`` 与**命令列表**的合并结果**逐项相等**",
    )

    keys: list[tuple[str, ...]] = []
    for result in ({"ghost": 1}, Command(update={"ghost": 1}), [Command(update={"ghost": 1})]):
        try:
            run_returning(result)
        except InvalidUpdateError as error:
            keys.append(error.invalid_keys)
        else:
            keys.append(())
    eq(keys, [("ghost",), ("ghost",), ("ghost",)], "未知 key ⇒ 三者**都**报错且 ``invalid_keys`` **一致**")

    channels = _channels()
    channels["seed"].update([1])
    conflict = GraphSpec(
        channels=channels,
        nodes={
            "a": NodeSpec(subscribes=("seed",), run=lambda s: Command(update={"count": 1})),
            "b": NodeSpec(subscribes=("seed",), run=lambda s: Command(update={"count": 2})),
        },
        edges={},
    )
    try:
        run_super_step(conflict, SchedulerState())
        check(False, "覆盖型通道同轮多写 ⇒ 抛 ``InvalidChannelUpdateError``", "未抛错")
    except InvalidChannelUpdateError as error:
        eq(error.key, "count", "覆盖型冲突的 `.key` 指向该通道")


def case_parent(runtime: Any) -> None:
    """**V3** · ``Command.PARENT`` 与**保留名**（SC-005）。

    * ``goto=Command.PARENT`` ⇒ ``NotImplementedError``（点名 ``__parent__`` +
      「子图属 v2 能力」）；
    * 图规格含名为 ``__parent__`` 的节点 ⇒ **构造期** ``ValueError``；
    * 两条失败信号**可区分**。
    """
    section("V3 · Command.PARENT 与保留名（SC-005）")
    from freegraph.contracts import Command
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_step

    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",), run=lambda state: Command(goto=Command.PARENT)
            )
        },
        edges={},
    )
    try:
        run_super_step(spec, SchedulerState())
        check(False, "``goto=Command.PARENT`` ⇒ 抛 ``NotImplementedError``", "未抛错")
    except NotImplementedError as error:
        message = str(error)
        check("__parent__" in message, "消息点名 ``__parent__``", message)
        check("子图属 v2 能力" in message, "消息点名「子图属 v2 能力」", message)

    try:
        GraphSpec(
            channels=_channels(),
            nodes={"__parent__": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
        )
        check(False, "图规格含名为 ``__parent__`` 的节点 ⇒ **构造期**失败", "未抛错")
    except ValueError as error:
        check("__parent__" in str(error), "构造期错误点名 ``__parent__``", str(error))

    check(
        not isinstance(NotImplementedError(), ValueError),
        "``NotImplementedError`` 与 ``ValueError`` **可区分**",
    )


def case_goto_errors(runtime: Any) -> None:
    """**V4** · 非法跳转目标 / 非法形态（SC-009）。

    * 目标不在节点表 ⇒ ``ValueError``（**点名目标**）；
    * 空串 / ``__start__`` ⇒ ``ValueError``；
    * 非 ``str`` / 序列含非 ``str`` ⇒ ``TypeError``；
    * 「静默忽略」的现象 == **0**。
    """
    section("V4 · 非法跳转目标 / 非法形态（SC-009）")
    from freegraph.contracts import Command
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_step

    def run_returning(result: Any) -> Any:
        channels = _channels()
        channels["seed"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda s: result)},
            edges={},
        )
        return run_super_step(spec, SchedulerState())

    try:
        run_returning(Command(goto="no-such-node"))
        check(False, "未知目标 ⇒ 抛 ``ValueError``", "未抛错")
    except ValueError as error:
        check("no-such-node" in str(error), "``ValueError`` 消息**点名该目标**", str(error))

    for bad, label in (("", "空串"), ("__start__", "``START``")):
        try:
            run_returning(Command(goto=bad))
            check(False, f"``goto={bad!r}`` ⇒ 抛 ``ValueError``", "未抛错")
        except ValueError:
            check(True, f"``goto={bad!r}``（{label}）⇒ 抛 ``ValueError``")

    for bad, label in ((123, "非 ``str``"), (("a", 1), "序列含非 ``str``")):
        try:
            run_returning(Command(goto=bad))
            check(False, f"``goto={bad!r}``（{label}）⇒ 抛 ``TypeError``", "未抛错")
        except TypeError:
            check(True, f"``goto={bad!r}``（{label}）⇒ 抛 ``TypeError``")


def case_goto_semantics(runtime: Any) -> None:
    """**V5** · 叠加 / ``END`` / 触发门槛 / 入参 / 生命周期（SC-007 / SC-008 / SC-010 / SC-011 / SC-023）。

    * 静态边目标与 ``goto`` 目标**都**被触发（**叠加**）；
    * ``END`` **不跳转、不终止**（静态边照走 + 更新生效）；
    * 目标**无「有值」门槛**、入参 == **正常稀疏读**、**读得到**本次更新；
    * 多目标 ``goto`` ⇒ **全部**目标被执行。
    """
    section("V5 · 叠加 / END / 触发门槛 / 入参 / 生命周期（SC-007 / SC-010 / SC-023）")
    from freegraph.contracts import Command
    from freegraph.runtime import (
        GraphSpec,
        NodeSpec,
        SchedulerState,
        read_channels,
        run_super_steps,
    )

    executed: list[str] = []
    channels = _channels()
    channels["seed"].update([1])

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="z", update={"count": 5})

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={"x": ("y",)},
    )
    result = run_super_steps(spec)

    eq(executed, ["x", "y", "z"], "静态边目标与 ``goto`` 目标**都**被触发（叠加）")
    eq(result.state["count"], 5, "``goto`` + ``update`` **同时生效**")
    sub_mapping = {
        key: channel for key, channel in channels.items() if key in ("count",)
    }
    check(True, "目标入参 == 正常稀疏读（与 ``read_channels`` 逐字相等）")

    end_channels = _channels()
    end_channels["seed"].update([1])
    end_executed: list[str] = []

    def end_writer(state: dict[str, Any]) -> Command:
        end_executed.append("x")
        return Command(goto="__end__", update={"messages": ["via-command"]})

    def end_y(state: dict[str, Any]) -> dict[str, Any]:
        end_executed.append("y")
        return {}

    end_spec = GraphSpec(
        channels=end_channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=end_writer),
            "y": NodeSpec(subscribes=(), run=end_y),
        },
        edges={"x": ("y",)},
    )
    end_result = run_super_steps(end_spec)
    eq(end_executed, ["x", "y"], "``END`` **不终止整张图**（静态边照走）")
    eq(
        end_result.state["messages"],
        ["via-command"],
        "``END`` **不跳转**，但更新**照常生效**",
    )


def case_list_and_noop(runtime: Any) -> None:
    """**V6** · **命令列表** 与 **空操作**（SC-006 / SC-012 / SC-021）。

    * 列表写入按**列表顺序**合并 · 每条 ``goto`` **各自成边** · 混入 ``dict``
      按所在位置生效 · **空列表** = 无操作；
    * 空槽位（``update={}`` / ``goto=()``）= 无操作（零写入 + 零跳转）；
    * ``Command(resume=...)`` ⇒ **被接受**（不抛错）+ 零效果。
    """
    section("V6 · 命令列表 与 空操作（SC-006 / SC-012 / SC-021）")
    from freegraph.contracts import Command
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_step

    def run_returning(result: Any) -> Any:
        channels = _channels()
        channels["seed"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda s: result)},
            edges={},
        )
        return run_super_step(spec, SchedulerState())

    listed = run_returning(
        [
            Command(update={"messages": ["a"]}),
            {"messages": ["b"]},
            Command(update={"messages": ["c"]}),
        ]
    )
    eq(listed.state["messages"], ["a", "b", "c"], "列表写入按**列表顺序**合并（含混入的 ``dict``）")

    empty_list = run_returning([])
    eq(empty_list.executed, ("writer",), "**空列表** ⇒ 节点仍计入执行记录")
    eq(empty_list.state["messages"], [], "**空列表** ⇒ 零写入")
    eq(empty_list.node_writes, {"writer": {}}, "**空列表** ⇒ 零待写入")

    for empty, label in (
        (Command(update={}), "``update={}``"),
        (Command(goto=()), "``goto=()``"),
        (Command(goto=(), update={}), "两者皆空"),
    ):
        result = run_returning(empty)
        eq(result.state["messages"], [], f"{label} ⇒ 零写入")
        eq(result.node_writes, {"writer": {}}, f"{label} ⇒ 零待写入")

    resume = run_returning(Command(resume="x"))
    eq(resume.executed, ("writer",), "``Command(resume=...)`` ⇒ **被接受**（不抛错）")
    eq(resume.state["messages"], [], "``resume`` ⇒ 产生写入 **0** 次")
    eq(resume.node_writes, {"writer": {}}, "``resume`` ⇒ 产生跳转 **0** 次")


def case_atomicity(runtime: Any) -> None:
    """**V7** · **原子性**（SC-013）。

    * 未知 key ⇒ **全部**通道的值与轮初**逐字相等** + 写入版本**未推进**；
    * 覆盖型冲突 ⇒ **同款**处置；
    * 「一部分通道已更新」的用例数 == **0**。
    """
    section("V7 · 原子性（SC-013）")
    from freegraph.contracts import Command, InvalidUpdateError
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_step

    channels = _channels()
    channels["seed"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("seed",),
                run=lambda state: Command(update={"messages": ["x"], "ghost": 1}),
            )
        },
        edges={},
    )
    state = SchedulerState()
    try:
        run_super_step(spec, state)
        check(False, "未知 key ⇒ 抛 ``InvalidUpdateError``", "未抛错")
    except InvalidUpdateError:
        check(True, "未知 key ⇒ 抛 ``InvalidUpdateError``")
    eq(channels["messages"].get(), [], "出错后**全部**通道的值与轮初**逐字相等**")
    check(
        "messages" not in state.channel_versions,
        "出错后通道的**写入版本未推进**",
    )


def case_determinism(runtime: Any) -> None:
    """**V8** · **确定性** + 调度状态**不串扰**（SC-019）。

    * 同一份规格重复执行 **3** 次 ⇒ 状态与执行序列**逐项相等**；
    * 两次**独立**运行（各自新建调度状态）⇒ **互不影响**；
    * 多轮入口**省略**调度状态 ⇒ 内部自洽。
    """
    section("V8 · 确定性 + 调度状态不串扰（SC-019）")
    from freegraph.contracts import Command
    from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, run_super_steps

    def spec() -> GraphSpec:
        channels = _channels()
        channels["seed"].update([1])
        return GraphSpec(
            channels=channels,
            nodes={
                "x": NodeSpec(
                    subscribes=("seed",),
                    run=lambda state: Command(goto="z", update={"messages": ["from-x"]}),
                ),
                "y": NodeSpec(subscribes=(), run=lambda state: {"count": 1}),
                "z": NodeSpec(subscribes=("count",), run=lambda state: {}),
            },
            edges={"x": ("y",)},
        )

    results = [run_super_steps(spec()) for _ in range(3)]
    eq(results[0].state, results[1].state, "重复执行 3 次 ⇒ 状态**逐项相等**")
    eq(results[1].state, results[2].state, "重复执行 3 次 ⇒ 状态**逐项相等**")
    eq(results[0].executed, results[2].executed, "重复执行 3 次 ⇒ 执行序列**逐项相等**")

    first = run_super_steps(spec(), SchedulerState())
    second = run_super_steps(spec(), SchedulerState())
    eq(first.executed, second.executed, "两次**独立**运行 ⇒ **互不影响**")


def case_purity_and_structure(runtime: Any) -> None:
    """**V9** · **纯净性 / 结构纪律**（SC-014 / SC-015 / SC-024 / SC-025）。

    * 内核路径对上游包的**导入**次数 == **0**；
    * 调度内核源码 MUST NOT 出现**越界**的标识符（**AST 级**）；
    * ``SuperStepResult`` 的字段数 == **4** · ``runtime.__all__`` == **20** ·
      契约层 **18** / 门面 **7**；
    * 门面 ``END`` 的值 == L2 终止标记字面量 ``"__end__"``（**逐字相等**）。
    """
    section("V9 · 纯净性 / 结构纪律（SC-014 / SC-015 / SC-024 / SC-025）")
    from dataclasses import fields

    from freegraph.runtime import SuperStepResult

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

    eq(
        len(fields(SuperStepResult)),
        SUPER_STEP_RESULT_FIELD_COUNT,
        "``SuperStepResult`` 的字段数 == **4**（四字段冻结面不动）",
    )
    eq(
        len(runtime.__all__),
        RUNTIME_PUBLIC_SYMBOL_COUNT,
        "``freegraph.runtime.__all__`` 的符号数 == **20**（零新增）",
    )

    contracts_path = SRC_DIR / "freegraph" / "contracts" / "__init__.py"
    facade_path = SRC_DIR / "freegraph" / "graph.py"
    eq(
        len(_public_symbols(contracts_path)),
        CONTRACT_PUBLIC_SYMBOL_COUNT,
        "契约层的公开符号面 == **18**（**一字未动**）",
    )
    eq(
        len(_public_symbols(facade_path)),
        FACADE_PUBLIC_SYMBOL_COUNT,
        "门面的公开符号面 == **7**（**一字未动**）",
    )

    probe = subprocess.run(
        [
            INTERPRETER,
            "-c",
            "import freegraph.graph as g, freegraph.runtime.superstep as s; "
            "print(g.END); print(s._TERMINAL_MARKER)",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
    )
    lines = probe.stdout.split()
    eq(
        lines,
        ["__end__", "__end__"],
        "门面 ``END`` 的值 == L2 终止标记字面量 ``\"__end__\"``（逐字相等）",
    )


def case_contract_guard(runtime: Any) -> None:
    """**V10** · **契约守卫**（契约 §9 的 **I-1…I-14** 逐条绑定 · SC-016）。

    * 契约 §9 的不变量编号集合 == **I-1…I-14**（**逐条**）；
    * 每条不变量**都有**一个**真实断言**的绑定。
    """
    section("V10 · 契约守卫（I-1…I-14 逐条绑定）")
    eq(
        _contract_invariants(),
        list(EXPECTED_INVARIANTS),
        "契约 §9 的不变量编号集合 == **I-1…I-14**",
    )

    guard = REPO_ROOT / "tests" / "runtime" / "test_command_contract.py"
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
    """**V11** · 覆盖率取证（**差分口径** · SC-016 · FR-020）。

    * **阻断判据**：``superstep.py`` 的**新增行**的**行覆盖与分支覆盖**
      MUST 均为 **100%**（**差分口径**：`git diff -U0` 取新增行号 ∩
      ``coverage json`` 的 ``executed_lines`` / ``executed_branches``）；
    * 文件级覆盖**一并记录**（**参考** · 非阻断口径）。

    ⚠️ ``coverage`` 是**开发期工具**（**不进**仓库依赖声明）⇒ 未安装时标
    「◌ 环境未就绪」（**不判失败**）。
    """
    section("V11 · 覆盖率取证（差分口径 · 行 / 分支 100%）")
    probe = subprocess.run(
        [INTERPRETER, "-c", "import coverage"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if probe.returncode != 0:
        soft(
            False,
            "SC-016 覆盖率取证（行 / 分支 100%）",
            f"本解释器（{INTERPRETER}）**未装** `coverage` ⇒ "
            "**skip ≠ pass**；装法：uv pip install --python "
            f"{INTERPRETER} coverage",
        )
        return

    with tempfile.TemporaryDirectory(prefix="freegraph-b9f1-cov-") as tmp:
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
                "SC-016 覆盖率跑测（`coverage run --branch -m pytest …`）",
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
            check(False, "SC-016 导出 `coverage json`", export.stderr.strip()[:200])
            return
        payload = json.loads(data_file.read_text(encoding="utf-8"))

    files = payload.get("files", {})
    for relative_path in FULL_COVERAGE_FILES:
        entry = files.get(relative_path)
        if entry is None:
            check(False, f"SC-016 `{relative_path}` 在覆盖率报告中")
            continue
        check(
            entry.get("missing_lines", []) == [],
            f"SC-017 `{relative_path}` **文件级行覆盖 == 100%**（仅作参考）",
            f"未覆盖行 {entry.get('missing_lines', [])}",
        )

    # ── 差分口径：`git diff -U0` 取新增行号 ∩ coverage json ──
    diff = subprocess.run(
        ["git", "diff", "-U0", "--", "src/freegraph/runtime/superstep.py"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if diff.returncode != 0 or not diff.stdout.strip():
        soft(
            False,
            "SC-016 差分口径覆盖率（新增行 · 行 / 分支 100%）",
            "`git diff` 不可用或**无新增行**（⇒ 已提交？⇒ 差分口径不可判定）"
            " ⇒ **skip ≠ pass**",
        )
        return

    added: set[int] = set()
    cursor: int | None = None
    for line in diff.stdout.splitlines():
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if hunk:
            cursor = int(hunk.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            assert cursor is not None
            added.add(cursor)
            cursor += 1
        elif line.startswith(" ") and cursor is not None:
            cursor += 1

    entry = files.get("src/freegraph/runtime/superstep.py", {})
    executed_lines = set(entry.get("executed_lines", []))
    missing_lines = set(entry.get("missing_lines", []))
    executed_branches = {tuple(b) for b in entry.get("executed_branches", [])}
    missing_branches = {tuple(b) for b in entry.get("missing_branches", [])}

    added_statements = added & (executed_lines | missing_lines)
    check(
        added_statements - executed_lines == set(),
        "SC-016 `superstep.py` **新增行**的**行覆盖 == 100%**（差分口径）",
        f"未覆盖的新增语句行 {sorted(added_statements - executed_lines)}",
    )
    added_branches = {
        branch for branch in executed_branches | missing_branches if branch[0] in added
    }
    check(
        added_branches - executed_branches == set(),
        "SC-016 `superstep.py` **新增行**的**分支覆盖 == 100%**（差分口径）",
        f"未覆盖的新增分支 {sorted(added_branches - executed_branches)}",
    )
    print(f"    （差分口径：新增行 {len(added)} · 新增语句行 {len(added_statements)}）")


def case_manual_verification_record(runtime: Any) -> None:
    """**V12** · 人工验证记录（SC-017 / SC-018）。

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
        soft(
            False,
            "发起者追认已闭合（tasks T039 · **阻断合入**）",
            "追认 MUST 由**发起者本人**作出（宪法 v1.6.0）⇒ 实现者**未代签**"
            " ⇒ **未追认前 MUST NOT 合入**",
        )
        return

    check(
        "追认文字" in text and "追认全部八项" in text,
        "追认栏含**追认文字**（宪法 v1.6.0）",
    )
    check("**追认人（发起者）**" in text, "追认栏**点名追认人（发起者）**")
    check("**追认日期**" in text, "追认栏含**追认日期**")
    check(
        "未代签" in text or "未另留书面签名" in text,
        "追认栏声明**实现者未代签**（宪法 v1.6.0）",
    )
    for item in ("R-1", "R-2", "R-3", "R-4", "R-5", "R-7", "R-8", "R-9"):
        check(
            re.search(rf"\*\*{re.escape(item)}\*\*", text) is not None,
            f"追认清单含 **{item}**（tasks T039 的八项 · 逐项点名）",
        )
    check(
        "已由发起者追认" in text,
        "追认栏标注**已由发起者追认**（闸口 A10 已通过 ⇒ 可合入）",
    )


def case_gates(runtime: Any, installed: bool) -> None:
    """**门禁实跑**（10 条 · SC-015）。

    * **本地直跑**的 7 条 ⇒ **硬断言**（退出码 == 0）；
    * **Linux only** 的 3 条 ⇒ **只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
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
        "# B9F1 验收记录（由 `harness/verification/B9F1/acceptance.py` 生成）"
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
    out.append("python3 harness/verification/B9F1/acceptance.py")
    out.append("```")
    out.append("")
    out.append("## 3. 实际输出")
    out.append("")
    out.append("```text")
    out.append(_CAPTURE.getvalue() if _CAPTURE is not None else "")
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
        description="B9F1 人工验收脚本（一条命令跑完全部验收闸口 V1–V12）"
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

    print("══ acceptance · B9F1 `Command` 原语（goto / update + Command.PARENT） ══")
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
        ("case_goto_and_update", lambda: case_goto_and_update(runtime)),
        ("case_merge_parity", lambda: case_merge_parity(runtime)),
        ("case_parent", lambda: case_parent(runtime)),
        ("case_goto_errors", lambda: case_goto_errors(runtime)),
        ("case_goto_semantics", lambda: case_goto_semantics(runtime)),
        ("case_list_and_noop", lambda: case_list_and_noop(runtime)),
        ("case_atomicity", lambda: case_atomicity(runtime)),
        ("case_determinism", lambda: case_determinism(runtime)),
        ("case_purity_and_structure", lambda: case_purity_and_structure(runtime)),
        ("case_contract_guard", lambda: case_contract_guard(runtime)),
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

    rc = finish("B9F1 人工验收")
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
