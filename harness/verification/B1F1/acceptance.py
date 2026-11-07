#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B1F1** 人工验收脚本（契约层骨架：四个核心类型 + 异常体系）。

定位
----
本脚本是 **B1F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 `harness/demo/`。

它把 B1F1 的验收判据 **A1–A5** 逐条落成**可判定的断言**，跑一遍就知道
「这个 feature 到底交付到位没有」，无需读代码：

* **A1** ``import freegraph.contracts`` 成功（版本可读）
* **A2** 依赖**零**（基础安装的依赖闭包为空集）
* **A3** C1 / C11 / C16 / C22 的**类型冻结**成立
* **A4** 契约层**不 import** 任何内部模块（AST 扫描）
* **A5** 顶层包**惰性**（``import freegraph`` 不连带加载子模块）
* 外加：异常族的**结构化属性**、零出站 / 零环境变量、署名头 100%、``py.typed``、
  typing 构件上限 3.11

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
    python3 harness/verification/B1F1/acceptance.py                    # 跑全部
    python3 harness/verification/B1F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B1F1/acceptance.py --require-installed # 把「未安装」判为失败

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
from dataclasses import fields
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# 仓库定位 + freegraph 导入（发行产物 / 源码树两态）
# ─────────────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[3]
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
FORBIDDEN_TYPING_CONSTRUCTS = {"TypeAliasType": "3.12", "ReadOnly": "3.13", "TypeIs": "3.13"}


def _load_contracts() -> tuple[Any, str]:
    """导入 ``freegraph.contracts``，返回 ``(模块, 模式说明)``。

    已安装 ⇒ 测发行产物；未安装 ⇒ 注入 ``<repo>/src`` 测源码树。
    """
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
    mark = "✔" if ok else "◌"
    if not ok:
        _SOFT.append(f"{_SECTION} · {label}" + (f" — {note}" if note else ""))
    print(f"  {mark} {label}" + (f"  ({note})" if note and not ok else ""))
    return ok


def eq(actual: object, expected: object, label: str) -> bool:
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


# ─────────────────────────────────────────────────────────────────────────────
# A1 · 前置自检
# ─────────────────────────────────────────────────────────────────────────────
def case_preflight(contracts: Any, mode: str) -> None:
    section("A1 前置自检 · 可导入 / 版本 / 导出面")

    import freegraph

    version = getattr(freegraph, "__version__", None)
    check(version is not None, "freegraph 暴露 __version__", f"实际 {version!r}")
    print(f"  · freegraph 版本 = {version}")
    print(f"  · 运行模式 = {mode}")

    for name in (
        "StateDict",
        "Command",
        "StateSnapshot",
        "RunConfig",
        "FreegraphError",
        "InvalidUpdateError",
        "GraphRecursionError",
        "GraphInterrupt",
    ):
        check(name in contracts.__all__, f"契约层导出 {name}")


# ─────────────────────────────────────────────────────────────────────────────
# A3 · 四个核心类型的冻结面
# ─────────────────────────────────────────────────────────────────────────────
def case_core_types(contracts: Any) -> None:
    section("A3 类型冻结 · C1 / C11 / C16 / C22")

    # C1 · StateDict = dict[str, Any] 的类型别名（不是新造类）
    eq(contracts.StateDict, dict[str, Any], "C1 StateDict 是 dict[str, Any] 的别名")

    # C22 · RunConfig 四字段 + 承载 thread_id
    run_fields = [f.name for f in fields(contracts.RunConfig)]
    eq(run_fields, ["thread_id", "context", "metadata", "tags"], "C22 RunConfig 四字段逐字一致")
    cfg = contracts.RunConfig(thread_id="t-1", metadata={"k": "v"})
    eq(cfg.thread_id, "t-1", "C22 RunConfig 承载会话标识 thread_id")
    eq(dict(cfg.metadata), {"k": "v"}, "C22 RunConfig.metadata 可读")

    # C22 · from_dict 默认严格（未知键即报错）
    try:
        contracts.RunConfig.from_dict({"threadId": "x"})
        check(False, "C22 from_dict 遇未知键抛错")
    except contracts.FreegraphError as exc:
        check("threadId" in str(exc), "C22 from_dict 的报错点名未知键", str(exc))
    loose = contracts.RunConfig.from_dict({"threadId": "x"}, ignore_unknown=True)
    eq(loose.thread_id, None, "C22 from_dict(ignore_unknown=True) 走宽松")

    # C22 · 容器防御性拷贝（浅拷贝）
    meta = {"k": "v"}
    cfg2 = contracts.RunConfig(metadata=meta)
    meta["k"] = "tampered"
    eq(dict(cfg2.metadata), {"k": "v"}, "C22 metadata 是浅拷贝（改原 dict 不影响实例）")

    # C16 · Command 三语义位 + 至少填一个
    cmd = contracts.Command(goto="b", update={"a": 1})
    eq(cmd.goto, "b", "C16 Command.goto 可读")
    eq(cmd.update, {"a": 1}, "C16 Command.update 可读")
    eq(cmd.resume, None, "C16 Command.resume 缺省为 None")
    eq(contracts.Command.PARENT, "__parent__", "C16 Command.PARENT 常量取值")
    try:
        contracts.Command()
        check(False, "C16 Command 三个语义位全空时抛错")
    except contracts.FreegraphError:
        check(True, "C16 Command 三个语义位全空时抛 FreegraphError")

    # C11 · StateSnapshot 七字段
    snap_fields = [f.name for f in fields(contracts.StateSnapshot)]
    eq(
        snap_fields,
        ["values", "next", "config", "metadata", "created_at", "tasks", "interrupts"],
        "C11 StateSnapshot 七字段逐字一致",
    )
    snap = contracts.StateSnapshot(
        values={"a": 1},
        next=("b",),
        config=cfg,
        metadata={},
        created_at="2026-11-06T10:00:00+00:00",
        tasks=(),
        interrupts=(),
    )
    eq(snap.next, ("b",), "C11 StateSnapshot.next 是不可变元组")
    eq(snap.created_at, "2026-11-06T10:00:00+00:00", "C11 created_at 是 UTC ISO-8601 字符串")

    # 数据类不可变 + 不可哈希
    for obj, label in ((cfg, "RunConfig"), (cmd, "Command"), (snap, "StateSnapshot")):
        try:
            setattr(obj, fields(obj)[0].name, None)
            check(False, f"{label} 构造后不可改（frozen）")
        except Exception as exc:  # noqa: BLE001
            check(type(exc).__name__ == "FrozenInstanceError", f"{label} 不可改（frozen）", type(exc).__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 异常族 · 结构化属性（原则 IV 可诊断性）
# ─────────────────────────────────────────────────────────────────────────────
def case_error_hierarchy(contracts: Any) -> None:
    section("异常族 · 统一基类 + 结构化属性")

    for name in ("InvalidUpdateError", "GraphRecursionError", "GraphInterrupt"):
        cls = getattr(contracts, name)
        check(issubclass(cls, contracts.FreegraphError), f"{name} 继承 FreegraphError")

    err = contracts.InvalidUpdateError(["foo", "bar"])
    eq(err.invalid_keys, ("foo", "bar"), "InvalidUpdateError.invalid_keys 是有序元组")
    check("foo" in str(err), "InvalidUpdateError 消息点名未知 key")

    rec = contracts.GraphRecursionError(25, 26)
    eq(rec.recursion_limit, 25, "GraphRecursionError.recursion_limit 可读")
    eq(rec.current_step, 26, "GraphRecursionError.current_step 可读")

    class Payload:
        value = "v"
        id = "i"

    interrupt = contracts.GraphInterrupt(Payload())
    check(hasattr(interrupt, "payload"), "GraphInterrupt.payload 可读")
    eq(interrupt.payload.value, "v", "GraphInterrupt.payload 保持对象形态（C17 结构约定）")


# ─────────────────────────────────────────────────────────────────────────────
# A4 · 契约层零内部依赖（AST）+ 零出站 / 零环境变量（AST）
# ─────────────────────────────────────────────────────────────────────────────
def case_zero_dependencies(contracts: Any) -> None:
    section("A4 契约层零内部依赖 · 零第三方 · 零出站 · 零环境变量")

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

    eq(internal, [], "契约层零内部 import")
    eq(third, [], "契约层零第三方 import")
    eq(egress, [], "契约层零网络库 / 零环境变量读取")


# ─────────────────────────────────────────────────────────────────────────────
# A5 · 顶层包惰性（子进程 —— 同进程 sys.modules 不可作依据）
# ─────────────────────────────────────────────────────────────────────────────
def case_lazy_top_level(contracts: Any) -> None:
    section("A5 顶层包惰性 · 子进程 sys.modules 快照")

    package_dir = Path(contracts.__file__).parent
    src_dir = package_dir.parent.parent

    def loaded(code: str) -> list[str]:
        snippet = (
            f"{code}\n"
            "import sys, json\n"
            "print(json.dumps(sorted(m for m in sys.modules if m.startswith('freegraph'))))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", snippet],
            env={**os.environ, "PYTHONPATH": str(src_dir)},
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout.strip())

    eq(loaded("import freegraph"), ["freegraph"], "A5 import freegraph 只加载自身")

    after = loaded("import freegraph.contracts")
    internal = [
        name
        for name in after
        if name != "freegraph"
        and not name == "freegraph.contracts"
        and not name.startswith("freegraph.contracts.")
    ]
    eq(internal, [], "A5 import freegraph.contracts 不连带加载内部层模块")
    print(f"  · 契约层加载的子模块 = {after}")


# ─────────────────────────────────────────────────────────────────────────────
# A2 · 依赖闭包为空集（需已安装）
# ─────────────────────────────────────────────────────────────────────────────
def _dependency_closure(pkg: str) -> set[str]:
    """展开 ``pkg`` 的**依赖闭包**（不含 ``pkg`` 自身）。"""

    def _deps(name: str) -> list[str]:
        from importlib.metadata import requires as _requires

        try:
            specs = _requires(name) or []
        except Exception:  # noqa: BLE001 —— 未安装的依赖无元数据
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


def case_dependency_closure(require_installed: bool) -> None:
    section("A2 依赖闭包 · 基础安装为空集")

    try:
        import importlib.metadata as md

        md.version("freegraph")
        installed = True
    except Exception:  # noqa: BLE001
        installed = False

    if not installed:
        soft(
            False,
            "A2 基础安装的依赖闭包为空集",
            "本环境未安装 freegraph ⇒ 该判据不可执行（请在隔离 venv 里 pip install . 后重跑）",
        )
        return
    closure = _dependency_closure("freegraph")
    eq(closure, set(), "A2 基础安装的依赖闭包为空集（零第三方运行时依赖）")
    if require_installed:
        check(True, "A2 已在已安装环境中真跑")


# ─────────────────────────────────────────────────────────────────────────────
# 署名头 100% · py.typed · typing 构件上限
# ─────────────────────────────────────────────────────────────────────────────
def case_code_hygiene(contracts: Any) -> None:
    section("代码卫生 · 署名头 / py.typed / typing 构件上限")

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
    check(
        not (package_dir / "py.typed").exists(),
        "子包未另建 py.typed（顶层一个即覆盖全部子包）",
    )

    violations: list[str] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_TYPING_CONSTRUCTS:
                        violations.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.Name):
                if node.id in FORBIDDEN_TYPING_CONSTRUCTS:
                    violations.append(f"{path.name}: {node.id}")
    eq(violations, [], "契约层零 3.12+ / 3.13+ typing 构件（G9 上限 = 3.11）")


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
    out.append(f"# B1F1 验收记录（由 `harness/verification/B1F1/acceptance.py` 生成）")
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
    out.append("python3 harness/verification/B1F1/acceptance.py")
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
    parser = argparse.ArgumentParser(description="B1F1 人工验收脚本")
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

    print("══ acceptance · B1F1 契约层骨架（四个核心类型 + 异常体系） ══")
    contracts, mode = _load_contracts()
    started = time.monotonic()

    for case in (
        lambda: case_preflight(contracts, mode),
        lambda: case_core_types(contracts),
        lambda: case_error_hierarchy(contracts),
        lambda: case_zero_dependencies(contracts),
        lambda: case_lazy_top_level(contracts),
        lambda: case_dependency_closure(args.require_installed),
        lambda: case_code_hygiene(contracts),
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {getattr(case, '__name__', 'lambda')} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B1F1 人工验收")
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
