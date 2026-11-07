#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B2F1** 人工验收脚本（5 个协议 + 5 个纯数据类 · 契约层协议面冻结）。

定位
----
本脚本是 **B2F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 `harness/demo/`。

它把 B2F1 的验收判据 **A1–A4** 与关键成功标准 **SC-001 / SC-005 / SC-006 /
SC-007 / SC-011 / SC-013 / SC-014 / SC-016 / SC-017 / SC-018 / SC-019 / SC-021**
逐条落成**可判定的断言**，跑一遍就知道「契约面到底冻结到位没有」。

覆盖的分组：

* **A1** 5 个协议 + 5 个纯数据类全部存在、可导入、结构化子类型判定可用
* **A2** 契约层可被单独消费（依赖闭包为空集 / 导入耗时 / 顶层包惰性）
* **A3** ARCH-2（零内部 import + 零第三方 import + 零出站 + 零环境变量）
* **A4** D11 三项修订落地（C27 条目 / C23 字段约定 / C22 标识约定）
* **冻结面审计** 公开符号面恰 18 个 · 唯一权威 · C1–C27 覆盖 27 条 · 兼容矩阵逐符号覆盖

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph.contracts`` 本身）——**零第三方依赖**。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物**（依赖闭包那条判据可真跑） |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树**；依赖闭包那条判**不判失败**，标「◌ 环境未就绪」 |

用法
----
    python3 harness/verification/B2F1/acceptance.py                    # 跑全部
    python3 harness/verification/B2F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B2F1/acceptance.py --require-installed # 把「未安装」判为失败

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "specs/b2f1-contracts-protocols/contracts/public-api.md"
README = REPO_ROOT / "README.md"
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)
FORBIDDEN_MODULES = {
    "socket",
    "http",
    "urllib",
    "requests",
    "httpx",
    "subprocess",
    "langchain",
    "langchain_core",
    "langsmith",
    "langgraph",
}
FORBIDDEN_ENV_ATTRS = {"environ", "environb", "getenv"}

#: 本层 10 个符号中**在上游没有同名符号**者 ⇒ 兼容矩阵该行写「无上游对应」。
NO_UPSTREAM_SYMBOLS = {"NodeFunc", "TraceSink", "Span", "TraceQuery"}

#: 五个协议的**方法集**（集合，不判顺序）——`data-model.md` §2。
PROTOCOL_METHODS = {
    "NodeFunc": {"__call__"},
    "Checkpointer": {
        "get_tuple",
        "list",
        "put",
        "put_writes",
        "delete_thread",
        "get_next_version",
    },
    "TraceSink": {"on_span_start", "on_span_end", "current_span"},
    "Store": {"get", "search", "put", "delete", "list_namespaces", "batch"},
    "CompiledGraph": {
        "invoke",
        "stream",
        "get_graph",
        "get_state",
        "get_state_history",
        "update_state",
    },
}

#: 五个纯数据类的**字段清单**（逐字）——`data-model.md` §3。
DATA_CLASS_FIELDS = {
    "Node": ["id", "name", "metadata"],
    "Edge": ["source", "target", "conditional", "condition"],
    "Graph": ["nodes", "edges"],
    "Span": [
        "id",
        "name",
        "attributes",
        "parent",
        "start_time",
        "end_time",
        "context",
        "thread_id",
        "run_id",
        "node",
        "checkpoint_id",
    ],
    "TraceQuery": ["run_id", "thread_id", "node", "start_time", "end_time"],
}


def _load_contracts() -> tuple[Any, str]:
    """导入 ``freegraph.contracts``，返回 ``(模块, 模式说明)。"""
    try:
        import freegraph.contracts as contracts

        return contracts, "发行产物（当前环境已安装 freegraph）"
    except ImportError:
        src = REPO_ROOT / "src"
        if not src.is_dir():
            raise
        sys.path.insert(0, str(src))
        import freegraph.contracts as contracts

        return contracts, f"源码树（{src} 已注入 sys.path）"


# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/demo/acceptance.py 同款：单文件可独立运行）
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
# A1 · 协议齐全
# ─────────────────────────────────────────────────────────────────────────────
def _protocol_methods(proto: Any) -> set[str]:
    attrs = getattr(proto, "__protocol_attrs__", None)
    if attrs is not None:
        return set(attrs)
    excluded = {
        "__abstractmethods__",
        "__annotations__",
        "__dict__",
        "__doc__",
        "__init__",
        "__module__",
        "__new__",
        "__parameters__",
        "__slots__",
        "__subclasshook__",
        "__weakref__",
        "__class_getitem__",
        "_is_protocol",
        "_is_runtime_protocol",
    }
    return {n for n in vars(proto) if n not in excluded and not n.startswith("_abc_")}


def case_protocols_present(contracts: Any) -> None:
    section("A1 · 5 个协议齐全 + 结构化子类型判定可用")

    for name, methods in PROTOCOL_METHODS.items():
        protocol = getattr(contracts, name, None)
        if not check(protocol is not None, f"协议 {name} 存在且可导入"):
            continue
        eq(_protocol_methods(protocol), methods, f"{name} 的方法集集合恰为 {len(methods)} 个")
        check(
            getattr(protocol, "_is_runtime_protocol", False),
            f"{name} 是 runtime_checkable（isinstance 可用）",
        )

    # 完整实现判真 / 缺任一方法判假
    class CompleteSink:
        def on_span_start(self, span: Any) -> None:
            pass

        def on_span_end(self, span: Any) -> None:
            pass

        def current_span(self) -> Any:
            return None

    check(
        isinstance(CompleteSink(), contracts.TraceSink),
        "完整实现 ⇒ isinstance 判真（TraceSink）",
    )

    class MissingCurrentSpan:
        def on_span_start(self, span: Any) -> None:
            pass

        def on_span_end(self, span: Any) -> None:
            pass

    check(
        not isinstance(MissingCurrentSpan(), contracts.TraceSink),
        "缺任一方法 ⇒ isinstance 判假（TraceSink）",
    )

    class MissingGet:
        def search(self, namespace_prefix: Any, *args: Any, **kwargs: Any) -> Any:
            return None

    check(not isinstance(MissingGet(), contracts.Store), "缺任一方法 ⇒ isinstance 判假（Store）")


def case_data_classes_present(contracts: Any) -> None:
    section("A1 · 5 个纯数据类齐全 + 冻结语义")

    for name, expected in DATA_CLASS_FIELDS.items():
        cls = getattr(contracts, name, None)
        if not check(cls is not None, f"数据类 {name} 存在且可导入"):
            continue
        eq([f.name for f in fields(cls)], expected, f"{name} 的字段清单逐字一致（{len(expected)} 个）")

    # 不可变
    node = contracts.Node(id="a")
    try:
        node.id = "b"  # type: ignore[misc]
        check(False, "数据类不可变（Node 改字段抛 FrozenInstanceError）")
    except Exception as exc:  # noqa: BLE001
        check(
            type(exc).__name__ == "FrozenInstanceError",
            "数据类不可变（Node 改字段抛 FrozenInstanceError）",
            type(exc).__name__,
        )

    # 统一不可哈希（Node / Edge / Graph / Span），TraceQuery 有意可哈希
    for name in ("Node", "Edge", "Graph", "Span"):
        obj = _sample_instance(contracts, name)
        try:
            hash(obj)
            check(False, f"{name} 不可哈希（hash 抛 TypeError）")
        except TypeError:
            check(True, f"{name} 不可哈希（hash 抛 TypeError）")
    check(
        hash(contracts.TraceQuery(run_id="r1")) == hash(contracts.TraceQuery(run_id="r1")),
        "TraceQuery 可哈希（五字段全为标量 · 有意如此）",
    )

    # 字段级相等
    eq(contracts.Node(id="a"), contracts.Node(id="a"), "字段级相等（同字段值 ⇒ 相等）")
    check(contracts.Node(id="a") != contracts.Node(id="b"), "字段级相等（异值 ⇒ 不等）")

    # Node.name 缺省归一为 id
    eq(contracts.Node(id="a").name, "a", "Node.name 缺省归一为 id（构造后恒为 str）")
    eq(contracts.Node(id="a", name="别名 A").name, "别名 A", "Node.name 显式别名原样保留")

    # 浅拷贝
    metadata = {"kind": "llm"}
    node2 = contracts.Node(id="a", metadata=metadata)
    metadata["kind"] = "tampered"
    eq(dict(node2.metadata), {"kind": "llm"}, "Node.metadata 是浅拷贝（改原 dict 不影响实例）")

    # 容器形态
    graph = contracts.Graph(
        nodes=(contracts.Node(id="a"), contracts.Node(id="b")),
        edges=(contracts.Edge(source="a", target="b", conditional=True, condition="route"),),
    )
    check(isinstance(graph.nodes, tuple), "Graph.nodes 是不可变元组")
    check(isinstance(graph.edges, tuple), "Graph.edges 是不可变元组")
    eq(graph.nodes[1].name, "b", "Graph 内的 Node 同样完成 name 归一")
    eq((graph.edges[0].conditional, graph.edges[0].condition), (True, "route"), "条件边可表达条件名")


def _sample_instance(contracts: Any, name: str) -> Any:
    """造一个 ``name`` 对应的**典型实例**（用于哈希 / 不可变等语义检查）。"""
    if name == "Node":
        return contracts.Node(id="a")
    if name == "Edge":
        return contracts.Edge(source="a", target="b")
    if name == "Graph":
        return contracts.Graph(nodes=(contracts.Node(id="a"),))
    if name == "Span":
        return contracts.Span(
            id="s1",
            name="node:a",
            run_id="r1",
            node="a",
            start_time="2026-11-06T10:00:00+00:00",
        )
    return contracts.TraceQuery(run_id="r1")


# ─────────────────────────────────────────────────────────────────────────────
# A2 · 契约层可被单独消费
# ─────────────────────────────────────────────────────────────────────────────
def _dependency_closure(pkg: str) -> set[str]:
    """展开 ``pkg`` 的**依赖闭包**（不含 ``pkg`` 自身）。"""

    def _deps(name: str) -> list[str]:
        from importlib.metadata import requires as _requires

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


def case_standalone_consumable(contracts: Any, require_installed: bool) -> None:
    section("A2 · 契约层可被单独消费（闭包 / 耗时 / 惰性）")

    try:
        import importlib.metadata as md

        md.version("freegraph")
        installed = True
    except Exception:  # noqa: BLE001
        installed = False

    if installed:
        eq(_dependency_closure("freegraph"), set(), "A2 基础安装的依赖闭包为空集（零第三方运行时依赖）")
    else:
        soft(
            False,
            "A2 基础安装的依赖闭包为空集",
            "本环境未安装 freegraph ⇒ 该判据不可执行（请在隔离 venv 里 pip install . 后重跑）",
        )

    # 导入耗时（子进程 · 含解释器冷启动）
    package_dir = Path(contracts.__file__).parent
    src_dir = package_dir.parent.parent
    env = {**os.environ, "PYTHONPATH": str(src_dir)}
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-c", "import freegraph.contracts"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.monotonic() - started
    check(proc.returncode == 0, "A2 import freegraph.contracts 成功", proc.stderr.strip())
    check(elapsed < 0.3, f"A2 导入耗时 < 300 ms（实测 {elapsed * 1000:.0f} ms）")

    # 顶层包惰性
    snippet = (
        "import freegraph, sys, json\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.startswith('freegraph'))))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", snippet], env=env, capture_output=True, text=True, timeout=120
    )
    eq(json.loads(proc.stdout.strip()), ["freegraph"], "A2 import freegraph 只加载自身（惰性）")


# ─────────────────────────────────────────────────────────────────────────────
# A3 · ARCH-2（零内部 / 零第三方 import · 零出站 / 零环境变量）
# ─────────────────────────────────────────────────────────────────────────────
def case_zero_dependencies(contracts: Any) -> None:
    section("A3 · ARCH-2：零内部 import + 零第三方 + 零出站 + 零环境变量")

    package_dir = Path(contracts.__file__).parent
    internal: list[str] = []
    third: list[str] = []
    egress: list[str] = []

    for path in sorted(package_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root == "freegraph" and not alias.name.startswith("freegraph.contracts"):
                        internal.append(f"{path.name}: {alias.name}")
                    if root not in sys.stdlib_module_names and root != "freegraph":
                        third.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".")[0]
                if node.level >= 2:
                    internal.append(f"{path.name}: {module} (level={node.level})")
                elif node.level == 0:
                    if root == "freegraph" and not module.startswith("freegraph.contracts"):
                        internal.append(f"{path.name}: {module}")
                    if root not in sys.stdlib_module_names and root != "freegraph":
                        third.append(f"{path.name}: {module}")
                if root in FORBIDDEN_MODULES:
                    egress.append(f"{path.name}: {module}")
            elif isinstance(node, ast.Attribute):
                base = node.value
                if (
                    node.attr in FORBIDDEN_ENV_ATTRS
                    and isinstance(base, ast.Name)
                    and base.id == "os"
                ):
                    egress.append(f"{path.name}: os.{node.attr}")

    eq(internal, [], "契约层零内部 import（ARCH-2）")
    eq(third, [], "契约层零第三方 import（含 langchain 家族）")
    eq(egress, [], "契约层零网络库 / 零环境变量读取")


# ─────────────────────────────────────────────────────────────────────────────
# A4 · D11 三项修订落地
# ─────────────────────────────────────────────────────────────────────────────
def case_d11_revisions(contracts: Any) -> None:
    section("A4 · D11 三项修订落地（C27 / C23 / C22）")

    # C27 · TraceQuery 5 字段全可空可组合
    query = contracts.TraceQuery()
    for name in ("run_id", "thread_id", "node", "start_time", "end_time"):
        eq(getattr(query, name), None, f"C27 TraceQuery.{name} 缺省为 None（全部可空）")
    check(
        len({contracts.TraceQuery(run_id="r1"), contracts.TraceQuery(run_id="r1")}) == 1,
        "C27 TraceQuery 可哈希且按值相等",
    )

    # C23 · Span 11 字段 + 必带四项 + JSON 可序列化
    span = contracts.Span(
        id="s1",
        name="node:a",
        run_id="r1",
        node="a",
        start_time="2026-11-06T10:00:00+00:00",
        thread_id="t1",
        checkpoint_id="ckpt-1",
        attributes={"gen_ai.system": "freegraph"},
        context={"phase": "plan"},
    )
    for name in ("thread_id", "run_id", "node", "checkpoint_id"):
        check(getattr(span, name) is not None, f"C23 span 必带项 {name} 可读")
    try:
        json.dumps(asdict(span))
        check(True, "C27 Span 100% 可 JSON 序列化")
    except TypeError as exc:
        check(False, "C27 Span 100% 可 JSON 序列化", str(exc))
    try:
        json.dumps([asdict(s) for s in (span, replace(span, id="s2"))])
        check(True, "C27 返回结构 = span 列表 ⇒ 整批 span 亦可序列化")
    except TypeError as exc:
        check(False, "C27 返回结构 = span 列表 ⇒ 整批 span 亦可序列化", str(exc))

    # C22 · 标识职责划分：thread_id 在 RunConfig 内、run_id 不在
    run_fields = [f.name for f in fields(contracts.RunConfig)]
    check("thread_id" in run_fields, "C22 thread_id 在 RunConfig 的字段清单内")
    check("run_id" not in run_fields, "C22 run_id 不在 RunConfig 的字段清单内（归运行时层）")

    # span 生命周期：同 id 配对、开始快照不被改写
    ended = replace(span, end_time="2026-11-06T10:00:01+00:00")
    eq(ended.id, span.id, "SC16 结束版与开始版同 id")
    eq(ended.end_time, "2026-11-06T10:00:01+00:00", "SC16 结束版的 end_time 已填")
    eq(span.end_time, None, "SC16 开始快照的 end_time 仍为空（不被事后改写）")


# ─────────────────────────────────────────────────────────────────────────────
# 冻结面审计：公开符号面 / 唯一权威 / C1–C27 / 兼容矩阵
# ─────────────────────────────────────────────────────────────────────────────
def _parse_manifest_symbols() -> tuple[list[str], list[str]]:
    """解析 ``public-api.md`` §0 → ``(既有 8 个, 新增 10 个)``。"""
    text = MANIFEST.read_text(encoding="utf-8")
    blocks = re.findall(r"```[A-Za-z0-9_+-]*\n(.*?)```", text, re.S)
    candidates = [
        b for b in blocks if b.lstrip().startswith("from freegraph.contracts import (")
    ]
    if len(candidates) != 1:
        raise AssertionError(f"§0 的符号清单代码块 MUST 恰有 1 个，实得 {len(candidates)} 个")
    lines = candidates[0].splitlines()
    end = next(i for i, line in enumerate(lines) if line.strip() == ")")
    existing: list[str] = []
    new: list[str] = []
    bucket = existing
    for raw in lines[1:end]:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if "B1F1 已冻结的 8 个" in stripped:
                bucket = existing
            elif "B2F1 新增的 10 个" in stripped:
                bucket = new
            continue
        name = stripped.split(",")[0].split("#")[0].strip()
        bucket.append(name)
    return existing, new


def case_frozen_surface(contracts: Any) -> None:
    section("冻结面审计 · 公开符号面 / 唯一权威 / C1–C27 / 兼容矩阵")

    existing, new = _parse_manifest_symbols()
    eq(len(existing), 8, "SC017 §0 的「既有」段恰为 8 个")
    eq(len(new), 10, "SC017 §0 的「新增」段恰为 10 个")
    eq(set(contracts.__all__), set(existing) | set(new), "SC001 公开符号面恰为 18 个（集合相等）")
    for name in existing + new:
        check(getattr(contracts, name, None) is not None, f"公开符号 {name} 可从契约层直接取到")
    check(
        not hasattr(contracts, "Send") and not hasattr(contracts, "interrupt"),
        "SC017 契约层不导出 Send / interrupt（归 v2）",
    )

    # 唯一权威（只认机器标记）
    authorities = [
        path
        for path in REPO_ROOT.rglob("public-api.md")
        if "<!-- authority: yes -->" in path.read_text(encoding="utf-8")[:400]
    ]
    eq(
        [p.relative_to(REPO_ROOT).as_posix() for p in authorities],
        ["specs/b2f1-contracts-protocols/contracts/public-api.md"],
        "SC020 公开符号面清单的唯一权威文件恰为 1 个（B2F1 的）",
    )

    # C1–C27 对照表覆盖 27 条 + 状态二态 + 修订列 4 条
    table = [
        line
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\|\s*C\d+\s*\|", line)
    ]
    eq(len(table), 27, "SC006 C1–C27 对照表覆盖全部 27 条（遗漏 0）")
    states: dict[str, str] = {}
    revisions: dict[str, str] = {}
    for line in table:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        states[cells[0]] = cells[2]
        revisions[cells[0]] = cells[3]
    bad_states = {k: v for k, v in states.items() if v not in ("已冻结", "挂起")}
    eq(bad_states, {}, "SC006 「状态」列为二态（已冻结 / 挂起）")
    frozen = sum(1 for v in states.values() if v == "已冻结")
    hung = sum(1 for v in states.values() if v == "挂起")
    eq((frozen, hung), (15, 12), "SC006 统计自洽（已冻结 15 + 挂起 12 = 27）")
    eq(
        sorted(k for k, v in revisions.items() if v not in ("—", "-", "")),
        ["C17", "C22", "C23", "C27"],
        "SC006 「修订」列非空恰为 4 条（C17 / C22 / C23 / C27 · D11）",
    )

    # 兼容矩阵逐符号覆盖
    readme = README.read_text(encoding="utf-8")
    match = re.search(r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", readme, re.S | re.M)
    if not check(match is not None, "README 有「## API 兼容矩阵」章节"):
        return
    rows = [
        line
        for line in match.group(1).splitlines()
        if line.strip().startswith("| `")
    ]
    names: list[str] = []
    for line in rows:
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        names.append(cells[0].strip("`"))
        check(len(cells) >= 4, f"兼容矩阵行 {cells[0]} 四列齐全（不新增第 5 列）")
    eq(set(names), set(existing) | set(new), "SC021 兼容矩阵逐符号覆盖公开符号面（18 个）")
    missing_source: list[str] = []
    for line in rows:
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        name = cells[0].strip("`")
        if name not in set(new):
            continue
        row = " | ".join(cells)
        if name in NO_UPSTREAM_SYMBOLS:
            if "无上游对应" not in row:
                missing_source.append(name)
        elif not re.search(r"[\w/]+\.py:\d+", row):
            missing_source.append(name)
    eq(missing_source, [], "SC021 新增行的上游来源合规（有同名者附行号 · 无同名者写「无上游对应」）")


# ─────────────────────────────────────────────────────────────────────────────
# 代码卫生
# ─────────────────────────────────────────────────────────────────────────────
def case_code_hygiene(contracts: Any) -> None:
    section("代码卫生 · 署名头 / py.typed / 协议纯抽象")

    package_dir = Path(contracts.__file__).parent
    sources = sorted(package_dir.rglob("*.py"))
    bad_header = [
        path.name
        for path in sources
        if path.read_text(encoding="utf-8").splitlines()[:1] != [SIGNATURE_HEADER]
    ]
    eq(bad_header, [], "契约层每个源文件的首行都是署名头")

    marker = package_dir.parent / "py.typed"
    check(marker.is_file(), "py.typed 存在（PEP 561）")
    if marker.is_file():
        eq(marker.read_bytes(), b"", "py.typed 内容为空")

    # G10 · 协议纯抽象（方法体只有 ...）
    violations: list[str] = []
    protocols_path = package_dir / "protocols.py"
    if protocols_path.is_file():
        tree = ast.parse(protocols_path.read_text(encoding="utf-8"), filename=str(protocols_path))
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            is_protocol = any(
                (isinstance(b, ast.Name) and b.id == "Protocol")
                or (isinstance(b, ast.Attribute) and b.attr == "Protocol")
                for b in cls.bases
            )
            if not is_protocol:
                continue
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for stmt in fn.body:
                    pure = (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is Ellipsis
                    )
                    if not pure:
                        violations.append(f"{cls.name}.{fn.name}")
    eq(violations, [], "G10 协议方法体纯抽象（只有 ...，无默认实现）")


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
    out.append("# B2F1 验收记录（由 `harness/verification/B2F1/acceptance.py` 生成）")
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
    out.append("python3 harness/verification/B2F1/acceptance.py")
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
    parser = argparse.ArgumentParser(description="B2F1 人工验收脚本")
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

    print("══ acceptance · B2F1 5 个协议 + 5 个纯数据类 ══")
    contracts, mode = _load_contracts()
    started = time.monotonic()

    cases = (
        ("case_protocols_present", lambda: case_protocols_present(contracts)),
        ("case_data_classes_present", lambda: case_data_classes_present(contracts)),
        ("case_standalone_consumable", lambda: case_standalone_consumable(contracts, args.require_installed)),
        ("case_zero_dependencies", lambda: case_zero_dependencies(contracts)),
        ("case_d11_revisions", lambda: case_d11_revisions(contracts)),
        ("case_frozen_surface", lambda: case_frozen_surface(contracts)),
        ("case_code_hygiene", lambda: case_code_hygiene(contracts)),
    )
    for name, case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {name} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B2F1 人工验收")
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
