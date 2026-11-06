#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 人工验收编排器（**验收脚本之一**，自身也 import 并使用 freegraph）。

定位
----
它既**是**验收脚本（自己 import 并执行 freegraph、做可判定的断言），
**又**是编排器（串跑其余验收脚本并按 §9.3 生成《人工验收记录》）。

作为验收脚本，它做四件**只有真跑起来才可能做**的检查：

1. **前置自检** —— freegraph 可导入、版本可读、**公开门面导出面**齐备
   （C9 的 `StateGraph` / `START` / `END`，以及 C16 / C17 / C18 / C22 的
   `Command` / `interrupt` / `Send` / `RunConfig`）。
2. **最小图可执行** —— 现场搭一个两节点图并 `invoke()`，确认**门面不是空壳**。
3. **框架零出站断言** —— 在进程内跑上面那张最小图，全程套一个**只观测、不阻断**的
   socket 夹具，按调用栈归因，断言 **freegraph 自身发起的出站数 = 0**。
   这是「零出站」这条对外承诺（立项书 §2.3 / §9.2）的**可执行证据**。
4. **编排其余脚本** —— 逐个以子进程执行，把退出码与输出汇总。

执行顺序（**内核在前、兼容在后**）::

    graph_core   图运行时内核      ← 前置：内核不过，图兼容无从谈起
    agent_loop   Agent 工具循环    ← 固定脚本的零依赖等价物
    visualization 图导出与可视化
    target.py    LangChain 兼容性   ← 只读基准（需 fake 注入或真实模型）

依赖：**只 import `freegraph` 与 Python 标准库**。

用法
----
    python harness/demo/acceptance.py                     # 跑全部
    python harness/demo/acceptance.py --suite core,viz    # 只跑指定组
    python harness/demo/acceptance.py --record out.md     # 同时生成人工验收记录
"""

from __future__ import annotations

import argparse
import os
import platform
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path

try:
    from freegraph.graph import (
        END,
        START,
        Command,
        RunConfig,
        Send,
        StateGraph,
        interrupt,
    )
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    print("→ freegraph 尚未实现（内核自 B1F1 起），或当前环境未安装本仓库。")
    raise SystemExit(2) from exc

import freegraph

HERE = Path(__file__).resolve().parent

SUITES: list[tuple[str, str, str]] = [
    ("core", "graph_core.py", "图运行时内核（C1–C25 / B4F1–B13F1）"),
    ("agent", "agent_loop.py", "Agent 工具循环（零依赖等价物 / C4·C7·C8·C11·C16·C17）"),
    ("viz", "visualization.py", "图导出与可视化（C12–C15·C26 / B8F2·B22F1·B23F1）"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（刻意内联：每个脚本都能单文件独立运行，只依赖 freegraph + 标准库）
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
    """**章程未锁定形态**的检查：不判失败，只标注「待锁定」，不计入失败数。

    用于「语义由章程规定、但调用形态尚未拍板」的检查点——形态一旦拍板，
    这里就该升级为硬断言（`check`）。
    """
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    mark = "✔" if ok else "◌"
    if not ok:
        _SOFT.append(f"{_SECTION} · {label}" + (f" — {note}" if note else ""))
    print(f"  {mark} {label}" + (f"  ({note})" if note else ""))
    return ok


def eq(actual: object, expected: object, label: str) -> bool:
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


def finish(title: str) -> int:
    print(f"\n── {title} 汇总 ──")
    print(f"硬断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待锁定形态 {_SOFT and len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 零出站夹具：只观测、不阻断、按调用栈归因（对应 §9.2 的方法表）
# ─────────────────────────────────────────────────────────────────────────────
class EgressProbe:
    """socket 监测夹具（只观测不阻断）。

    * 包装 `socket.socket.connect` / `socket.create_connection`，记录目标与调用栈后**放行**；
    * 归因：调用栈中出现 `freegraph/` 包路径 → 「框架出站」，否则 → 「用户出站」。
    """

    def __init__(self) -> None:
        self.framework: list[tuple[str, str]] = []
        self.user: list[tuple[str, str]] = []
        self._orig_connect = socket.socket.connect
        self._orig_create = socket.create_connection

    @staticmethod
    def _classify(stack: str) -> str:
        return "framework" if "freegraph" in stack else "user"

    @staticmethod
    def _target(addr: object) -> str:
        if isinstance(addr, tuple) and len(addr) >= 2:
            return f"{addr[0]}:{addr[1]}"
        return str(addr)

    def __enter__(self) -> "EgressProbe":
        probe = self

        def connect(self_sock, address):  # type: ignore[no-untyped-def]
            stack = "".join(traceback.format_stack())
            bucket = probe.framework if probe._classify(stack) == "framework" else probe.user
            bucket.append((probe._target(address), stack))
            return probe._orig_connect(self_sock, address)

        def create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
            stack = "".join(traceback.format_stack())
            bucket = probe.framework if probe._classify(stack) == "framework" else probe.user
            bucket.append((probe._target(address), stack))
            return probe._orig_create(address, *args, **kwargs)

        socket.socket.connect = connect  # type: ignore[method-assign]
        socket.create_connection = create_connection  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        socket.socket.connect = self._orig_connect  # type: ignore[method-assign]
        socket.create_connection = self._orig_create  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────────────
# 1 · 前置自检：freegraph 可用 + 公开门面导出面齐备
# ─────────────────────────────────────────────────────────────────────────────
def case_preflight() -> None:
    section("A1 前置自检 · 可导入 / 版本 / 公开门面导出面")

    version = getattr(freegraph, "__version__", None)
    check(version is not None, "freegraph 暴露 __version__", f"实际 {version!r}")
    if version:
        print(f"  · freegraph 版本 = {version}")

    # C9：公开门面必须导出 StateGraph / START / END
    for name in ("StateGraph", "START", "END"):
        check(name in globals(), f"C9 公开门面 `freegraph.graph` 导出 {name}")

    # C16 / C17 / C18 / C22：原语与运行配置也须从同一门面导出
    for name in ("Command", "Send", "interrupt", "RunConfig"):
        check(name in globals(), f"C16/C17/C18/C22 公开门面导出 {name}")

    # C9：取值
    eq(START, "__start__", "C9 START 取值")
    eq(END, "__end__", "C9 END 取值")


# ─────────────────────────────────────────────────────────────────────────────
# 2 · 最小图可执行：门面不是空壳
# ─────────────────────────────────────────────────────────────────────────────
def build_minimal_graph():
    """一个两节点的最小图——只用章程已锁死的 API 形态（§4.3 #2–#7）。"""

    def first(state: dict) -> dict:
        return {"value": state.get("value", 0) + 1}

    def second(state: dict) -> dict:
        return {"value": state.get("value", 0) + 10}

    g = StateGraph(dict)
    g.add_node("first", first)
    g.add_node("second", second)
    g.add_edge(START, "first")
    g.add_edge("first", "second")
    g.add_edge("second", END)
    return g


def case_minimal_graph_runs() -> None:
    section("A2 最小图可执行 · C10 / C11")

    try:
        out = build_minimal_graph().compile().invoke({"value": 0})
    except Exception as exc:  # noqa: BLE001
        check(False, "最小两节点图可 compile + invoke", f"{type(exc).__name__}: {exc}")
        return
    check(isinstance(out, dict), "C11 invoke() 返回 dict")
    eq(out.get("value"), 11, "最小图执行结果正确（0 → +1 → +10）")


# ─────────────────────────────────────────────────────────────────────────────
# 3 · 框架零出站断言：零出站这条承诺的可执行证据
# ─────────────────────────────────────────────────────────────────────────────
def case_zero_egress() -> None:
    section("A3 框架零出站断言 · §2.3 / §9.2")

    with EgressProbe() as probe:
        build_minimal_graph().compile().invoke({"value": 0})

    eq(len(probe.framework), 0, "框架出站数 = 0（freegraph 自身未发起任何连接）")
    print(f"  · 用户出站记录 {len(probe.user)} 条（记录在案，不判失败）")


# ─────────────────────────────────────────────────────────────────────────────
# 4 · 编排其余验收脚本
# ─────────────────────────────────────────────────────────────────────────────
def run_suite(script: str) -> tuple[int, str, float]:
    path = HERE / script
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=str(HERE.parent.parent),
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or ""), time.monotonic() - started


def collect_env() -> dict:
    env_vars = sorted(k for k in os.environ if k.startswith(("LANG", "PYPI", "TWINE", "UV_")))
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "env_vars": ", ".join(f"`{k}`" for k in env_vars) if env_vars else "（无 LANG*/PYPI*/TWINE*/UV_* 环境变量）",
        "freegraph": str(getattr(freegraph, "__version__", "?")),
    }


def build_record(results: list[dict], env: dict, verdict: str) -> str:
    """按 §9.3 的规范生成《人工验收记录》。"""
    out: list[str] = []
    out.append("# freegraph 人工验收记录")
    out.append("")
    out.append("> 本文件由 `harness/demo/acceptance.py` 生成；**遗留问题**需人工补充。")
    out.append("")
    out.append("## 1. 验证环境")
    out.append("")
    out.append("| 项 | 内容 |")
    out.append("|---|---|")
    out.append(f"| 操作系统 | {env['os']} |")
    out.append(f"| Python | {env['python']} |")
    out.append(f"| freegraph | {env['freegraph']} |")
    out.append(f"| 解释器 | `{env['executable']}` |")
    out.append(f"| 工作目录 | `{env['cwd']}` |")
    out.append(f"| 相关环境变量清理 | {env['env_vars']} |")
    out.append("| 依赖 | 本脚本与三组脚本：**仅 freegraph + Python 标准库**（无第三方依赖）；`target.py`：脚本自带 `langchain.*` |")
    out.append("| 网络 | 零出站断言要求**无网 / 断网**环境亦可通过 |")
    out.append("")
    out.append("## 2. 验收步骤与结果")
    out.append("")
    out.append("| # | 步骤 | 脚本 | 覆盖范围 | 结果 | 耗时 |")
    out.append("|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        status = {0: "✅ PASS", 2: "⚠️ 环境未就绪"}.get(r["rc"], "❌ FAIL")
        out.append(
            f"| {i} | {r['title']} | `{r['script']}` | {r['scope']} | {status} | {r['elapsed']:.1f}s |"
        )
    out.append("")
    out.append("### 2.1 只读基准（target.py，双跑）")
    out.append("")
    out.append("| 轮次 | 模型 | 环境 | 结果 | 证据 |")
    out.append("|---|---|---|---|---|")
    out.append("| CI 轮 | fake（猴补 `init_chat_model` 注入，见立项书 §9.2） | 验收环境 + socket 监测夹具 | ⬜ 待填 | ⬜ 待填 |")
    out.append("| 人工轮 | 真实模型 `claude-sonnet-4-6` | 干净环境（拦截列表允许「模型厂商端点」一条） | ⬜ 待填 | ⬜ 待填 |")
    out.append("")
    out.append("## 3. 实际输出")
    out.append("")
    for i, r in enumerate(results, 1):
        out.append(f"### 3.{i} `{r['script']}`（退出码 {r['rc']}）")
        out.append("")
        out.append("```text")
        out.append(r["output"].rstrip() or "（无输出）")
        out.append("```")
        out.append("")
    out.append("## 4. 结论")
    out.append("")
    out.append(f"**验收结论：{verdict}**")
    out.append("")
    out.append("## 5. 遗留问题")
    out.append("")
    out.append("⬜ 待填")
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="freegraph 人工验收编排器")
    parser.add_argument("--suite", default="all", help="要执行的组（core,agent,viz）；默认 all")
    parser.add_argument("--record", help="把人工验收记录写到该路径")
    args = parser.parse_args()

    want = {s.strip() for s in args.suite.split(",")} if args.suite != "all" else {s[0] for s in SUITES}

    print("══ acceptance · freegraph 人工验收 ══")
    env = collect_env()
    print(f"环境：{env['os']} · Python {env['python']} · freegraph {env['freegraph']}")
    print()

    # ── 作为验收脚本：先做自己的三项检查 ──
    for case in (case_preflight, case_minimal_graph_runs, case_zero_egress):
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {case.__name__} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    # ── 作为编排器：串跑其余脚本 ──
    results: list[dict] = []
    print("\n── 编排其余验收脚本 ──")
    for name, script, scope in SUITES:
        if name not in want:
            continue
        rc, output, elapsed = run_suite(script)
        results.append(
            {
                "name": name,
                "script": script,
                "scope": scope,
                "title": script.removesuffix(".py"),
                "rc": rc,
                "output": output,
                "elapsed": elapsed,
            }
        )
        for line in [ln for ln in output.splitlines() if ln.strip()][-2:]:
            print(f"  {line}")
        print(f"  → {script} 退出码 {rc}（{elapsed:.1f}s）\n")

    own_rc = finish("acceptance（自身检查）")
    script_rcs = [r["rc"] for r in results]
    if script_rcs and all(rc == 0 for rc in script_rcs):
        script_verdict = "PASS"
    elif script_rcs and all(rc == 2 for rc in script_rcs):
        script_verdict = "环境未就绪"
    else:
        script_verdict = "FAIL"

    total = own_rc or (0 if script_verdict == "PASS" else (2 if script_verdict == "环境未就绪" else 1))
    print(f"\n── 编排结论 ──\n自身检查 {own_rc} · 子脚本 {script_verdict} → 总体 {total}")

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        verdict = "PASS" if total == 0 else ("FAIL" if total == 1 else "环境未就绪（freegraph 尚未实现）")
        path.write_text(build_record(results, env, verdict), encoding="utf-8")
        print(f"人工验收记录已写入：{path}")

    return total


if __name__ == "__main__":
    raise SystemExit(main())
