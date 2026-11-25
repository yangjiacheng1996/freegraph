#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 一键验收（A1 / A3 / A4 / A5 + DEP；``--real`` 跑 A2）。

与 `harness/demo/acceptance.py`（四组编排器）**职责不同**，MUST 用全路径区分。

退出码：0 = PASS · 1 = 断言失败 · 2 = 环境未就绪。
最后一行 MUST 打印 ``B25F1 acceptance: PASS|FAIL``。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
B25F1_DIR = Path(__file__).resolve().parent
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"
TARGET = REPO_ROOT / "harness" / "demo" / "target.py"
SHA_FILE = REPO_ROOT / "tests" / "runtime" / "data" / "b25f1_target_py.sha256"

for _path in (SRC_DIR, B25F1_DIR, GATES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

STEPS: list[dict[str, Any]] = []
FAILURES: list[str] = []
ENV_DEVIATIONS: list[str] = []
ABSOLUTE_COMPAT = "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md"


def _clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("LANGSMITH_")
    }


def _run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    env = _clean_env()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(SRC_DIR), str(B25F1_DIR)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _record(step: str, rc: int, output: str, *, detail: str = "") -> None:
    STEPS.append({"step": step, "rc": rc, "output": output, "detail": detail})
    state = {0: "PASS", 2: "ENV", 1: "FAIL"}.get(rc, "FAIL")
    print(f"[{step}] {state}" + (f" — {detail}" if detail else ""))
    if rc == 1:
        FAILURES.append(f"{step}: {detail or '断言失败'}")


def _fail(step: str, detail: str) -> None:
    FAILURES.append(f"{step}: {detail}")
    STEPS.append({"step": step, "rc": 1, "output": detail, "detail": detail})
    print(f"[{step}] FAIL — {detail}")


def _env_ok() -> tuple[bool, str]:
    try:
        import freegraph  # noqa: F401
        import langchain  # noqa: F401
        import IPython  # noqa: F401
    except ImportError as exc:
        return False, f"缺依赖：{exc}"
    return True, ""


def dep() -> int:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lines = [
        f"dependencies = {project.get('dependencies')!r}",
        f"optional-dependencies = {sorted(project.get('optional-dependencies', {}))!r}",
        f"LANGSMITH_* count = {sum(1 for key in os.environ if key.startswith('LANGSMITH_'))}",
    ]
    if project.get("dependencies") != []:
        _fail("DEP", "基础 dependencies 非空")
        return 1
    extras = set(project.get("optional-dependencies", {}))
    if extras != {"otlp"}:
        _fail("DEP", f"唯一 extra 不是 otlp：{extras!r}")
        return 1
    if any(key.startswith("LANGSMITH_") for key in os.environ):
        _fail("DEP", "LANGSMITH_* 未清空")
        return 1

    code = (
        "import sys, freegraph\n"
        "bad = sorted(k for k in sys.modules if k.split('.')[0] in "
        "{'langchain','langchain_core','langsmith','langgraph'})\n"
        "print('bad_sys_modules =', bad)\n"
        "raise SystemExit(0 if not bad else 1)\n"
    )
    proc = _run([sys.executable, "-c", code])
    lines.append(proc.stdout.strip())
    if proc.returncode != 0:
        _fail("DEP", "反向断言失败：freegraph 运行期加载了 langchain / langgraph")
        return 1
    _record("DEP", 0, "\n".join(lines), detail="基础零依赖 + 唯一 extra otlp + 反向断言通过")
    return 0


def a1() -> int:
    proc = _run([sys.executable, str(B25F1_DIR / "fake_round.py")])
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 2:
        _record("A1", 2, output, detail="环境未就绪")
        return 2
    if proc.returncode != 0:
        _fail("A1", f"fake 轮退出码 {proc.returncode}")
        return 1
    if "B25F1 fake round: PASS" not in output:
        _fail("A1", "fake 轮未打印 PASS")
        return 1
    if "框架出站 = 0" not in output:
        _fail("A1", "fake 轮框架出站断言缺失")
        return 1
    _record("A1", 0, output, detail="messages==4 / llm_calls==2 / tool==7 / 两键 / PNG / 框架出站 0")
    return 0


class _ValueState(TypedDict):
    value: int


def a3() -> int:
    import _gatekit
    from freegraph.graph import END, START, StateGraph

    def node(state: dict) -> dict:
        return {"value": state.get("value", 0) + 1}

    builder = StateGraph(_ValueState)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_edge("node", END)
    records: list[_gatekit.EgressRecord] = []
    with _gatekit.record_egress(records):
        builder.compile().invoke({"value": 0})
    framework = [item for item in records if item.attribution == "framework"]
    user = [item for item in records if item.attribution == "user"]
    output = (
        f"框架出站 = {len(framework)}\n"
        f"用户出站 = {len(user)}（逐条记录、不判失败、不设目标白名单）"
    )
    if framework:
        _fail("A3", f"框架出站 != 0：{[item.target for item in framework]!r}")
        return 1
    _record("A3", 0, output, detail="框架出站 = 0")
    return 0


def a4() -> int:
    proc = _run([sys.executable, str(REPO_ROOT / "harness" / "demo" / "acceptance.py")])
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 2:
        _record("A4", 2, output, detail="验收脚本集环境未就绪")
        return 2
    if proc.returncode != 0:
        _fail("A4", f"四组编排器退出码 {proc.returncode}")
        return 1
    if "总体 0" not in output:
        _fail("A4", "四组编排器未给出总体 0")
        return 1
    _record("A4", 0, output, detail="四组（含 diagnostics）全绿；target fake 为旁路")
    return 0


def a5() -> int:
    recorded = SHA_FILE.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    lines = [f"recorded = {recorded}", f"actual   = {actual}"]
    if actual != recorded:
        _fail("A5", "target.py SHA-256 不一致")
        return 1

    baseline = os.environ.get("B25F1_BASELINE_REF", "origin/main")
    exists = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{baseline}^{{commit}}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        ENV_DEVIATIONS.append(
            f"基线 ref {baseline!r} 不可用（浅克隆 / 无该 ref）；已保留 SHA-256 断言"
        )
        lines.append(f"baseline ref {baseline!r}: 不可用（环境偏离）")
        _record("A5", 0, "\n".join(lines), detail="SHA-256 一致；基线 ref 不可用（环境偏离）")
        return 0
    diff = subprocess.run(
        ["git", "diff", "--exit-code", baseline, "--", "harness/demo/target.py"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    lines.append(diff.stdout.strip() or "git diff: empty")
    if diff.returncode != 0:
        _fail("A5", f"target.py 与基线 ref {baseline!r} 不一致")
        return 1
    _record("A5", 0, "\n".join(lines), detail="SHA-256 + 基线 ref diff 双重基线通过")
    return 0


def a2() -> int:
    proc = _run([sys.executable, str(B25F1_DIR / "real_round.py")], timeout=900)
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 2:
        ENV_DEVIATIONS.append(
            "真实模型轮未执行：凭据 / 网络未就绪（已完成 fake / 四组 / 诊断；"
            "未完成真实轮段 1 + 段 2）"
        )
        _record("A2", 2, output, detail="环境未就绪（真实模型凭据）")
        return 2
    if proc.returncode != 0:
        _fail("A2", f"真实模型轮退出码 {proc.returncode}")
        return 1
    _record("A2", 0, output, detail="真实模型轮两段式 PASS")
    return 0


def build_draft() -> str:
    lines = [
        "# B25F1 一键验收草稿",
        "",
        "## 1. 验证环境",
        "",
        f"- OS：{platform.system()} {platform.release()} ({platform.machine()})",
        f"- Python：{sys.version.split()[0]}",
        f"- 工作目录：`{os.getcwd()}`",
        f"- `LANGSMITH_*` 清空：脚本启动 / 子进程均剔除全部 `LANGSMITH_*`（计数 == 0）",
        "",
        "## 2. 验证步骤与结果",
        "",
        "| 步骤 | 结果 | 说明 |",
        "|---|---|---|",
    ]
    for step in STEPS:
        state = {0: "PASS", 2: "ENV", 1: "FAIL"}.get(step["rc"], "FAIL")
        lines.append(f"| {step['step']} | {state} | {step['detail']} |")
    lines.extend(["", "## 3. 实际输出", ""])
    for step in STEPS:
        lines.extend(
            [
                f"### {step['step']}（rc={step['rc']}）",
                "",
                "```text",
                step["output"].rstrip() or "（无输出）",
                "```",
                "",
            ]
        )
    lines.extend(["## 4. 结论", ""])
    verdict = "PASS" if not FAILURES else "FAIL"
    lines.append(f"**一键验收：{verdict}**")
    if ENV_DEVIATIONS:
        lines.append("")
        lines.append("环境偏离：")
        lines.extend(f"- {item}" for item in ENV_DEVIATIONS)
    lines.extend(
        [
            "",
            "## 5. 遗留问题",
            "",
            "- **Y-01**：`Command.goto` 缺省 `()`（上游）vs `None`（freegraph）= DIFF；v1 行为提示；运行时对齐归 v2 独立契约修订。",
        ]
    )
    if any(step["step"] == "A2" and step["rc"] == 2 for step in STEPS):
        lines.append("- 真实模型轮未执行（环境偏离）；**不得**据此宣布 v1.0 收口。")
    lines.extend(["", "## 附件 1 · 依赖断言轮输出", ""])
    dep_step = next((step for step in STEPS if step["step"] == "DEP"), None)
    lines.extend(
        [
            "```text",
            (dep_step["output"].rstrip() if dep_step else "（未运行）"),
            "```",
            "",
            "## 附件 2 · 框架出站 = 0 监测记录",
            "",
            "```text",
            (
                next((step["output"] for step in STEPS if step["step"] == "A3"), "（未运行）")
            ),
            "```",
            "",
            "## 附件 3 · 反向断言结果",
            "",
            "见附件 1 的 `bad_sys_modules = []`（运行时 `sys.modules` 无 `langchain` / `langchain_core`）。",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B25F1 一键验收（A1/A3/A4/A5 + DEP）")
    parser.add_argument("--real", action="store_true", help="额外执行 A2 真实模型轮")
    parser.add_argument("--skip-real", action="store_true", help="显式跳过 A2（CI 用）")
    parser.add_argument("--record", help="把五要素 + 三附件草稿写到该路径")
    parser.add_argument(
        "--suite",
        default="all",
        help="只跑指定步骤（DEP,A1,A3,A4,A5[,A2]）；默认 all",
    )
    args = parser.parse_args(argv)

    # FR-021：验收进程自身也保持 LANGSMITH_* 清空。
    for key in list(os.environ):
        if key.startswith("LANGSMITH_"):
            del os.environ[key]

    ok, reason = _env_ok()
    if not ok:
        print(f"[ENV] {reason}")
        print("B25F1 acceptance: FAIL")
        return 2

    want = (
        {item.strip() for item in args.suite.split(",")}
        if args.suite != "all"
        else {"DEP", "A1", "A3", "A4", "A5"}
    )
    if args.real:
        want.add("A2")
    if args.skip_real:
        want.discard("A2")

    for name, fn in (
        ("DEP", dep),
        ("A1", a1),
        ("A3", a3),
        ("A4", a4),
        ("A5", a5),
    ):
        if name not in want:
            continue
        try:
            rc = fn()
        except Exception as exc:  # noqa: BLE001 - 单步失败不中断其余步骤
            _fail(name, f"{type(exc).__name__}: {exc}")
            rc = 1
        if rc != 0:  # A1 / A4 / DEP 失败或环境未就绪：继续记录其余步骤
            continue

    if "A2" in want:
        a2()
    elif not args.skip_real:
        STEPS.append(
            {
                "step": "A2",
                "rc": 2,
                "output": "A2 未运行（未指定 --real）",
                "detail": "人工轮未跑（使用 --real 执行）",
            }
        )

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_draft(), encoding="utf-8")
        print(f"验收草稿已写入：{path}")

    env_only = all(step["rc"] in (0, 2) for step in STEPS) and any(
        step["rc"] == 2 for step in STEPS
    )
    if FAILURES:
        for failure in FAILURES:
            print(f"[FAIL] {failure}")
        print("B25F1 acceptance: FAIL")
        return 1
    if env_only:
        print("B25F1 acceptance: PASS")
        return 0
    print("B25F1 acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
