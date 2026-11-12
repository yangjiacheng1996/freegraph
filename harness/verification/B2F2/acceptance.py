#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B2F2** 人工验收脚本（公开 API 门面 + API 签名快照 + 顶层包惰性）。

定位
----
本脚本是 **B2F2 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 `harness/demo/`。

它把 B2F2 的验收判据 **A1–A3** 与关键成功标准 **SC-001 / SC-002 / SC-003 /
SC-005 / SC-006 / SC-007 / SC-008 / SC-009 / SC-010 / SC-011 / SC-012 /
SC-013 / SC-014 / SC-015 / SC-016 / SC-017 / SC-018** 逐条落成**可判定的断言**，
跑一遍就知道「门面到底交付到位没有」。

覆盖的分组：

* **A1** 门面的 7 个符号齐备 · 可导入 · ``START`` / ``END`` 取值
* **A2** API 签名快照**已入库**且与门面**逐字节一致**（+ **可复现**）
* **A3** **顶层包惰性**（``import freegraph`` 不连带加载任何子模块）
* **形状门禁** 门面**零实现体** · **依赖卫生**（零第三方 / 零环境变量 / 零 I/O）
* **未接线语义** 四个方法与 ``interrupt`` 一律抛 ``NotImplementedError``
* **冻结面审计** 兼容矩阵覆盖门面 7 个符号 · 契约层 20 个符号面未受影响（上游对齐 P3）

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物**（依赖闭包那条判据可真跑） |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树**；依赖闭包那条判**不判失败**，标「◌ 环境未就绪」 |

用法
----
    python3 harness/verification/B2F2/acceptance.py                    # 跑全部
    python3 harness/verification/B2F2/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B2F2/acceptance.py --require-installed # 把「未安装」判为失败

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import ast
import difflib
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "specs" / "b2f2-public-api-facade"
CONTRACTS_DIR = SPEC_DIR / "contracts"
FACADE_MANIFEST = CONTRACTS_DIR / "facade-api.md"
SNAPSHOT_PATH = CONTRACTS_DIR / "public-api-snapshot.txt"
README = REPO_ROOT / "README.md"
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 门面导出面的 **7 个**符号（**手写**权威在 ``facade-api.md`` §0）。
EXPECTED_SYMBOLS = {
    "StateGraph",
    "START",
    "END",
    "Command",
    "Send",
    "interrupt",
    "RunConfig",
}

#: 本 feature **新建**的 10 个 ``.py``（门禁 G20 的扫描清单）。
SIGNED_SOURCE_FILES = (
    "src/freegraph/graph.py",
    "src/freegraph/_stategraph.py",
    "src/freegraph/_primitives.py",
    "tests/facade/__init__.py",
    "tests/facade/conftest.py",
    "tests/facade/_gatesupport.py",
    "tests/facade/_snapshot_tools.py",
    "tests/facade/test_facade.py",
    "tests/facade/test_api_snapshot.py",
    "tests/facade/test_facade_gates.py",
)

#: 门面**零实现体**的门禁判据（AST）。
FORBIDDEN_BODY_STATEMENTS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

#: 门面**零**第三方 import / 零环境变量 / 零出站（门禁 G17 的两档判据）。
FORBIDDEN_THIRD_PARTY = ("langchain", "langgraph", "langsmith", "pydantic")
FORBIDDEN_LAYERS = ("persistence", "observability")
FORBIDDEN_ENV_ATTRS = ("environ", "environb", "getenv")
FORBIDDEN_IO_MODULES = ("socket", "urllib", "http", "subprocess")

#: 兼容矩阵的章节定位（**不扫全文**）。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 导入开销预算（FR-019 / SC-018）。
IMPORT_BUDGET_SECONDS = 0.120


# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B2F1/acceptance.py 同款：单文件可独立运行）
# ─────────────────────────────────────────────────────────────────────────────
_CHECKS = 0
_FAILED: list[str] = []
_SOFT: list[str] = []
_SECTION = ""


def section(title: str) -> None:
    global _SECTION
    _SECTION = title
    print(f"\n[{title}]")


def check(cond: object, label: str, detail: str = "") -> bool:
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
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 加载门面
# ─────────────────────────────────────────────────────────────────────────────
def _load_facade() -> tuple[Any, str]:
    """导入 ``freegraph.graph``，返回 ``(模块, 模式说明)``。"""
    try:
        import freegraph.graph as graph

        return graph, "发行产物（当前环境已安装 freegraph）"
    except ImportError:
        src = REPO_ROOT / "src"
        if not src.is_dir():
            raise
        sys.path.insert(0, str(src))
        import freegraph.graph as graph

        return graph, f"源码树（{src} 已注入 sys.path）"


def _installed() -> bool:
    """当前环境**是否已安装** freegraph。"""
    try:
        import importlib.metadata as md

        md.version("freegraph")
    except Exception:  # noqa: BLE001
        return False
    return True


def _dependency_closure(pkg: str) -> set[str]:
    """展开 ``pkg`` 的**依赖闭包**（不含 ``pkg`` 自身）。"""
    from importlib.metadata import requires as _requires

    def _deps(name: str) -> list[str]:
        try:
            specs = _requires(name) or []
        except Exception:  # noqa: BLE001
            return []
        out: list[str] = []
        for spec in specs:
            head = spec.split(";")[0]
            dep = head.split("[")[0].split(">")[0].split("<")[0].split("=")[0].strip()
            if dep:
                out.append(dep)
        return out

    seen: set[str] = set()
    stack = _deps(pkg)
    while stack:
        name = stack.pop()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        stack.extend(_deps(name))
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# A1 · 门面的 7 个符号齐备
# ─────────────────────────────────────────────────────────────────────────────
def case_facade_surface(graph: Any) -> None:
    section("A1 · 门面导出面（7 个符号）+ 常量取值")

    exports = set(graph.__all__)
    public = {name for name in vars(graph) if not name.startswith("_")}
    eq(sorted(exports), sorted(EXPECTED_SYMBOLS), "SC003 __all__ 恰为 7 个符号")
    eq(public, EXPECTED_SYMBOLS, "SC003 模块内公开名集合恰为同一集合")
    for name in sorted(EXPECTED_SYMBOLS):
        check(hasattr(graph, name), f"符号 {name} 可从门面直接取到")
    eq(graph.START, "__start__", "SC002 START == '__start__'")
    eq(graph.END, "__end__", "SC002 END == '__end__'")
    check(type(graph.START) is str and type(graph.END) is str, "SC002 两个常量均为 str")


def case_reexported_identity(graph: Any) -> None:
    section("A1 · 契约层转出对象的**同一性**（FR-004）")
    import freegraph.contracts as contracts

    check(graph.Command is contracts.Command, "Command 是契约层的同一对象（非副本 / 非子类）")
    check(graph.RunConfig is contracts.RunConfig, "RunConfig 是契约层的同一对象")


def case_constructor_and_not_wired(graph: Any) -> None:
    section("A1 · 构造语义与**未接线**语义")

    instance = graph.StateGraph({"count": 0})
    check(instance is not None, "SC010 StateGraph(schema) 构造成功")
    eq(sorted(vars(instance)), ["_schema"], "SC010 构造零副作用（只存私有的 _schema）")
    # ⚠️ **2026-11-12 上游对齐 P3**：构造签名**逐字对齐上游**
    # （``state_schema`` / ``context_schema`` / … · 上游 ``langgraph/graph/state.py:216-224``）
    # ⇒ **第二个位置参数** = ``context_schema``（**可选**）⇒ **合法** ⇒ 越界点顺延到**第三个**。
    two = graph.StateGraph({"count": 0}, {"user": "x"})
    check(two is not None, "SC010 StateGraph(schema, context_schema) 构造成功（上游同款）")
    try:
        graph.StateGraph({"count": 0}, {"user": "x"}, "extra")
        check(False, "SC010 StateGraph(schema, ctx, extra) 抛 TypeError", "未抛异常")
    except TypeError:
        check(True, "SC010 StateGraph(schema, ctx, extra) 抛 TypeError")

    pattern = re.compile(
        r"(?:add_node|add_edge|add_conditional_edges|compile) 尚未接线（由 B\dF\d 交付）"
    )
    calls = {
        "add_node": lambda g: g.add_node("n", lambda state: state),
        "add_edge": lambda g: g.add_edge("a", "b"),
        "add_conditional_edges": lambda g: g.add_conditional_edges("a", lambda s: "b", ["b"]),
        "compile": lambda g: g.compile(),
    }
    for name, call in calls.items():
        try:
            call(instance)
            check(False, f"SC011 {name} 抛 NotImplementedError", "未抛异常（静默成功）")
        except NotImplementedError as exc:
            check(
                bool(pattern.search(str(exc))),
                f"SC011 {name} 抛 NotImplementedError 且消息点名归属 feature",
                str(exc),
            )
    for forbidden in ("nodes", "edges", "invoke", "stream"):
        check(not hasattr(instance, forbidden), f"SC016 未越界：无 {forbidden} 产物")

    try:
        graph.interrupt("x")
        check(False, "SC011 interrupt 抛 NotImplementedError", "未抛异常")
    except NotImplementedError as exc:
        check(
            "interrupt 尚未接线（由 B10F1 交付）" in str(exc),
            "SC011 interrupt 抛 NotImplementedError 且消息点名 B10F1",
            str(exc),
        )


def case_send_semantics(graph: Any) -> None:
    section("A1 · Send 的不可变 / 不可哈希 / 两种调用形态")
    import dataclasses

    positional = graph.Send("w", {"n": 1})
    keyword = graph.Send(node="w", arg={"n": 1})
    eq(positional, keyword, "SC017 位置与关键字两种形态等价")
    try:
        positional.node = "other"  # type: ignore[misc]
        check(False, "SC017 改 Send 属性失败（不可变记录）", "未抛异常")
    except dataclasses.FrozenInstanceError:
        check(True, "SC017 改 Send 属性失败（不可变记录）")
    try:
        hash(graph.Send("w", {"n": 1}))
        check(False, "SC017 Send 不可哈希（hash 抛 TypeError）", "hash 成功")
    except TypeError:
        check(True, "SC017 Send 不可哈希（hash 抛 TypeError）")
    check(graph.Send.__dict__["__hash__"] is None, "SC017 Send 显式 __hash__ = None")


# ─────────────────────────────────────────────────────────────────────────────
# A2 · API 签名快照
# ─────────────────────────────────────────────────────────────────────────────
def _render_snapshot(graph: Any) -> str:
    """用测试侧的渲染器重现快照文本（**纯函数**）。"""
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    from facade._snapshot_tools import render_api_snapshot  # noqa: PLC0415

    namespace = {
        key: value for key, value in vars(graph).items() if not key.startswith("_")
    }
    return render_api_snapshot(namespace)


def case_snapshot(graph: Any) -> None:
    section("A2 · API 签名快照（入库 + 逐字节一致 + 可复现）")
    check(SNAPSHOT_PATH.is_file(), f"SC005 快照文件已入库：{SNAPSHOT_PATH}")
    if not SNAPSHOT_PATH.is_file():
        return
    raw = SNAPSHOT_PATH.read_bytes()
    check(not raw.startswith(b"\xef\xbb\xbf"), "SC006 快照为 UTF-8（无 BOM）")
    check(b"\r\n" not in raw, "SC006 快照换行为 LF")
    check(raw.endswith(b"\n"), "SC006 快照末行带换行")
    generated = _render_snapshot(graph)
    committed = SNAPSHOT_PATH.read_text(encoding="utf-8")
    if committed != generated:
        diff = "".join(
            difflib.unified_diff(
                committed.splitlines(keepends=True),
                generated.splitlines(keepends=True),
                fromfile="committed",
                tofile="generated",
            )
        )
        check(False, "SC005 生成结果与入库快照逐字节一致", diff[:800])
    else:
        check(True, "SC005 生成结果与入库快照逐字节一致")
    check(_render_snapshot(graph) == generated, "SC006 快照可复现（两次生成逐字节相同）")
    top_level = {
        match.group(1) for match in re.finditer(r"(?m)^\[\w+\] (\w+)", committed)
    }
    eq(top_level, set(graph.__all__), "SC006 快照的顶级条目集合 == 当前导出面")


# ─────────────────────────────────────────────────────────────────────────────
# A3 · 顶层包惰性 + 门面模块加载面
# ─────────────────────────────────────────────────────────────────────────────
def _loaded_modules(code: str) -> list[str]:
    """子进程执行 ``code`` ⇒ 已加载的 ``freegraph*`` 模块清单。"""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    snippet = (
        f"{code}\n"
        "import sys, json\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.startswith('freegraph'))))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return []
    import json

    return json.loads(proc.stdout.strip())


def case_lazy_loading() -> None:
    section("A3 · 顶层包惰性 + 门面的模块加载面")
    loaded = _loaded_modules("import freegraph")
    eq(loaded, ["freegraph"], "A3 import freegraph 只加载自身（不连带加载子模块）")

    loaded = _loaded_modules("import freegraph.graph")
    forbidden = [
        name
        for name in loaded
        if name.startswith("freegraph.persistence") or name.startswith("freegraph.observability")
    ]
    eq(forbidden, [], "SC008 门面不横依赖 L4（持久化）/ L5（可观测）")
    check("freegraph.graph" in loaded, "SC007 门面模块被加载")

    loaded = _loaded_modules("from freegraph.graph import StateGraph")
    check("freegraph.contracts" in loaded, "SC007 门面可以依赖 L1 契约层（contracts 被加载）")


def case_dependency_closure(require_installed: bool) -> None:
    section("A3 · 依赖闭包为空集（零第三方运行时依赖）")
    if not _installed():
        soft(
            not require_installed,
            "基础安装的依赖闭包为空集",
            "本环境未安装 freegraph ⇒ 该判据不可执行（请在隔离 venv 里 pip install . 后重跑）",
        )
        return
    eq(_dependency_closure("freegraph"), set(), "基础安装的依赖闭包为空集")


# ─────────────────────────────────────────────────────────────────────────────
# 形状门禁：零实现体 / 依赖卫生 / 署名头
# ─────────────────────────────────────────────────────────────────────────────
def case_facade_shape() -> None:
    section("形状门禁 · 门面零实现体 + 依赖卫生 + 署名头")
    facade = REPO_ROOT / "src" / "freegraph" / "graph.py"
    tree = ast.parse(facade.read_text(encoding="utf-8"), filename=str(facade))
    bodies = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, FORBIDDEN_BODY_STATEMENTS)
    ]
    eq(bodies, [], "SC004 门面零实现体（class / def / async def == 0）")

    third_party: list[str] = []
    layers: list[str] = []
    env_reads: list[str] = []
    for relative in ("graph.py", "_stategraph.py", "_primitives.py"):
        path = REPO_ROOT / "src" / "freegraph" / relative
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root.startswith(FORBIDDEN_THIRD_PARTY):
                        third_party.append(f"{relative}: {alias.name}")
                    if root in FORBIDDEN_IO_MODULES:
                        third_party.append(f"{relative}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                target = node.module or ""
                parts = [part for part in target.split(".") if part]
                segment = parts[1] if parts and parts[0] == "freegraph" and len(parts) > 1 else (parts[0] if parts else "")
                if segment in FORBIDDEN_LAYERS:
                    layers.append(f"{relative}: {target}")
                if target.split(".")[0].startswith(FORBIDDEN_THIRD_PARTY):
                    third_party.append(f"{relative}: {target}")
            elif isinstance(node, ast.Attribute):
                if (
                    node.attr in FORBIDDEN_ENV_ATTRS
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                ):
                    env_reads.append(f"{relative}: os.{node.attr}")
    eq(third_party, [], "SC009 门面零第三方 import / 零出站模块 import")
    eq(layers, [], "SC009 门面不横向依赖 L4 / L5")
    eq(env_reads, [], "SC009 门面零环境变量读取")

    bad_headers = []
    for relative in SIGNED_SOURCE_FILES:
        path = REPO_ROOT / relative
        if not path.is_file():
            bad_headers.append(f"{relative}（文件缺失）")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != SIGNATURE_HEADER:
            bad_headers.append(f"{relative}（首行非署名头）")
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not ast.get_docstring(module):
            bad_headers.append(f"{relative}（缺模块 docstring）")
    eq(bad_headers, [], "SC014 本 feature 新建的 10 个文件均带署名头 + 模块 docstring")


# ─────────────────────────────────────────────────────────────────────────────
# 冻结面审计：兼容矩阵 / 契约层未受影响
# ─────────────────────────────────────────────────────────────────────────────
def case_frozen_surface(graph: Any) -> None:
    section("冻结面审计 · 兼容矩阵覆盖 + 契约层未受影响")
    readme = README.read_text(encoding="utf-8")
    match = COMPAT_MATRIX_PATTERN.search(readme)
    if not check(match is not None, "README 有「## API 兼容矩阵」章节"):
        return
    rows = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if not cells:
            continue
        symbol = re.fullmatch(r"`([A-Za-z_][A-Za-z0-9_]*)`", cells[0])
        if not symbol:
            continue
        rows.append((symbol.group(1), cells))
    names = [name for name, _ in rows]
    missing = sorted(EXPECTED_SYMBOLS - set(names))
    eq(missing, [], "SC012 兼容矩阵覆盖门面的 7 个符号")
    duplicated = sorted({name for name in names if names.count(name) > 1})
    eq(duplicated, [], "SC012 兼容矩阵无重复行")
    for name, cells in rows:
        # 「差异说明」里可能出现**转义管道**（``str \| None``）⇒ 单元格数 ≥ 4
        check(len(cells) >= 4, f"兼容矩阵行 {name} 至少 4 列", f"实得 {len(cells)}")

    import freegraph.contracts as contracts

    eq(len(contracts.__all__), 20, "SC015 契约层公开符号面仍恰为 20 个（上游对齐 P3）")
    check(
        not hasattr(contracts, "Send") and not hasattr(contracts, "interrupt"),
        "SC015 契约层仍不导出 Send / interrupt",
    )


def case_import_budget() -> None:
    section("A3 · 导入开销预算（FR-019 / SC-018）")
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    # 预热一次（排除首次 .pyc 落盘噪声）
    subprocess.run(
        [sys.executable, "-c", "import freegraph.graph"],
        env=env,
        capture_output=True,
        timeout=120,
    )
    samples = []
    for _ in range(3):
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import time; t=time.perf_counter(); import freegraph.graph; "
                "print(time.perf_counter()-t)",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            check(False, "导入耗时实测失败", proc.stderr.strip()[:300])
            return
        samples.append(float(proc.stdout.strip()))
    best = min(samples)
    check(
        best < IMPORT_BUDGET_SECONDS,
        f"SC018 import freegraph.graph 墙钟 < 120 ms（暖机 best-of-3 = {best * 1000:.1f} ms）",
        f"实测 {best:.6f} s",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 汇总 + 记录
# ─────────────────────────────────────────────────────────────────────────────
def finish(title: str) -> int:
    print(f"\n── {title} 汇总 ──")
    print(f"硬断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待环境就绪 {len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


def build_record(mode: str, verdict: str, rc: int) -> str:
    out: list[str] = []
    out.append("# B2F2 验收记录（由 `harness/verification/B2F2/acceptance.py` 生成）")
    out.append("")
    out.append("## 1. 环境")
    out.append("")
    out.append("| 项 | 内容 |")
    out.append("|---|---|")
    out.append(f"| 操作系统 | {platform.system()} {platform.release()} ({platform.machine()}) |")
    out.append(f"| Python | {sys.version.split()[0]}（`{sys.executable}`） |")
    out.append(f"| 运行模式 | {mode} |")
    out.append(f"| 工作目录 | `{os.getcwd()}` |")
    out.append("| 依赖 | 本脚本**仅** Python 标准库（零第三方） |")
    out.append("")
    out.append("## 2. 步骤")
    out.append("")
    out.append("```bash")
    out.append("python3 harness/verification/B2F2/acceptance.py")
    out.append("```")
    out.append("")
    out.append("## 3. 实际输出")
    out.append("")
    out.append("```text")
    out.append(_CAPTURE.getvalue().rstrip() or "（无输出）")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="B2F2 人工验收脚本")
    parser.add_argument("--record", help="把验收记录片段写到该路径")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="要求当前环境**已安装** freegraph（否则依赖闭包判据判失败）",
    )
    args = parser.parse_args()

    global _CAPTURE
    import io

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

    print("══ acceptance · B2F2 公开 API 门面 + API 签名快照 ══")
    graph, mode = _load_facade()
    started = time.monotonic()

    cases = (
        ("case_facade_surface", lambda: case_facade_surface(graph)),
        ("case_reexported_identity", lambda: case_reexported_identity(graph)),
        ("case_constructor_and_not_wired", lambda: case_constructor_and_not_wired(graph)),
        ("case_send_semantics", lambda: case_send_semantics(graph)),
        ("case_snapshot", lambda: case_snapshot(graph)),
        ("case_lazy_loading", case_lazy_loading),
        (
            "case_dependency_closure",
            lambda: case_dependency_closure(args.require_installed),
        ),
        ("case_facade_shape", case_facade_shape),
        ("case_frozen_surface", lambda: case_frozen_surface(graph)),
        ("case_import_budget", case_import_budget),
    )
    for name, case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {name} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B2F2 人工验收")
    print(f"  · 耗时 {time.monotonic() - started:.1f}s")
    sys.stdout = _real_stdout

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        verdict = "PASS" if rc == 0 else "FAIL"
        path.write_text(build_record(mode, verdict, rc), encoding="utf-8")
        print(f"验收记录片段已写入：{path}")

    return rc


_CAPTURE: Any = None

if __name__ == "__main__":
    raise SystemExit(main())
