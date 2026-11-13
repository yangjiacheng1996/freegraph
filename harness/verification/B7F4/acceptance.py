#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B7F4** 人工验收脚本（多源汇合边 · AND / 屏障）。

定位
----
本脚本是 **B7F4 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收判据 **A1…A10**（逐条对应
``specs/b7f4-multisource-join/quickstart.md`` 的 §2）。

覆盖的分组（**逐组对应一条验收判据**）：

* **A1** 多源边**可表达**（``edges={("a","b"): ("c",)}`` ⇒ 构造成功）·
  FR-001 · **M-1**；
* **A2** **屏障语义正确**（目标**严格晚于**所有源 · 屏障**不齐** ⇒ 静默等待 ·
  屏障**后齐** ⇒ 再执行一次 · **组间任一** · 同一轮至多一次）· FR-003 / FR-004 ·
  **M-2 / M-3 / M-4 / M-5 / M-8**；
* **A3** **与上游同款**（差分探针场景组 **D-16…D-28** 全绿）· FR-005 · SC-004 / SC-011；
* **A4** **既有断言零削弱**（**10 个**冻结断言文件的 ``git diff HEAD --stat`` **全为空**）
  · SC-005 · **M-6**；
* **A5** **冻结面追认**（人工验证记录**五段式** + **追认**文字在位）· FR-012 / FR-015 · SC-009；
* **A6** **导出面零新增**（``runtime.__all__ == 20`` · ``contracts.__all__ == 20``）·
  SC-006 · **M-9**；
* **A7** **回溯修订落全**（**R-1…R-10** 逐条命中）· FR-013 · SC-008；
* **A8** **形态校验生效**（**V-16** 四条 · **V-2** 两条 · 边键**类型**非法）·
  FR-017 / FR-021 · SC-008；
* **A9** **参数化场景全绿**（**D-24** · 屏障形态 × 通道类型 × 源可达性）·
  FR-020 · SC-013 · **M-13**；
* **A10** **门禁偏离已登记**（门禁 **3 / 4 / 5 / 7** 的「**物理不可达成**」**如实登记**）·
  FR-019 · SC-009。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树** |

⚠️ **上游缺席即 skip**（沿用 B5F2 的「缺席即 skip」纪律）⇒ ⇒ 差分闸口（**A3 / A9**）
在上游未安装时**跳过**而非**失败**。

用法
----
    python3 harness/verification/B7F4/acceptance.py                    # 跑全部
    python3 harness/verification/B7F4/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B7F4/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B7F4/acceptance.py --skip-differential # 跳过差分闸口（快）

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
SPEC_DIR = REPO_ROOT / "specs" / "b7f4-multisource-join"
QUICKSTART_PATH = SPEC_DIR / "quickstart.md"
MANUAL_VERIFICATION = REPO_ROOT / "harness" / "verification" / "B7F4" / "manual-verification.md"
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

#: **10 个**冻结断言文件（B7F1 / B9F1 / B12F1 的触发相关断言 · B5F2 的 C4 回归）
#: —— **R-9** 的核对面（**MUST NOT** 只查其中一个）。
FROZEN_ASSERTION_FILES = [
    "test_superstep_trigger",
    "test_superstep_contract",
    "test_command_contract",
    "test_command_goto_semantics",
    "test_command_noop",
    "test_command_purity",
    "test_superstep_concurrency",
    "test_command_list",
    "test_command_merge_parity",
    "test_read_c4_sparse_state",
]

#: **R-1…R-10** 的**逐条落点**（**A7** 的机械判据）⇒（文件 · 正则）。
RETRO_LANDINGS: list[tuple[str, str]] = [
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"tuple\[str, \.\.\.\]"),
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"触发源组"),
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"∀ s ∈ g"),
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"只消费「已满足的组」"),
    ("specs/b7f1-superstep-loop/contracts/superstep-contract.md", r"屏障两源的执行先后不确定"),
    ("specs/b7f1-superstep-loop/spec.md", r"多源口径"),
    ("specs/b7f1-superstep-loop/data-model.md", r"V-16"),
    ("specs/b7f1-superstep-loop/data-model.md", r"只记「已满足的组」的源"),
    ("specs/b7f1-superstep-loop/tasks.md", r"2026-11-13 · B7F4 回溯修订"),
    ("specs/b7f1-superstep-loop/research.md", r"2026-11-13 · B7F4 回溯修订"),
]

#: 人工验证记录的**五段式**小节（原则 V · 宪法）。
MANUAL_SECTIONS = ["验证环境", "验证步骤", "实际输出", "结论", "遗留问题"]

#: **追认必须覆盖**的**八项登记项**（PR-1…PR-8 · **一次**追认 · 逐条列出）。
RATIFICATION_ITEMS = [
    "PR-1",
    "PR-2",
    "PR-3",
    "PR-4",
    "PR-5",
    "PR-6",
    "PR-7",
    "PR-8",
]

#: **门禁偏离登记**必须逐条点名的门禁项（**A10** · 宪法 v1.6.0）。
GATE_DEVIATIONS = ["门禁 3", "门禁 4", "门禁 5", "门禁 7", "物理不可达成"]


def _env() -> dict[str, str]:
    """构造子进程环境（**零出站** · 不读环境变量做判定 · 只传基础项）。"""
    return dict(os.environ)


def _run_pytest(args: list[str]) -> tuple[int, str]:
    """跑一条 pytest ⇒ 返回 ``(退出码, 合并输出)``。"""
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", *args, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _run_python(code: str) -> tuple[int, str]:
    """跑一段 Python ⇒ 返回 ``(退出码, 输出)``。"""
    proc = subprocess.run(
        [str(PYTHON), "-c", code],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _run_git(args: list[str]) -> tuple[int, str]:
    """跑一条 git ⇒ 返回 ``(退出码, 输出)``。"""
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _upstream_installed() -> bool:
    """上游 ``langgraph`` 是否**已安装**（缺席即 skip · 沿用 B5F2 的纪律）。"""
    try:
        import importlib.util

        return importlib.util.find_spec("langgraph") is not None
    except Exception:  # pragma: no cover - find_spec 异常按「缺席」处理
        return False


def _check_export_surface() -> tuple[bool, str]:
    """**A6** · SC-006 · **M-9**：导出面 == **20 / 20**（**零新增导出符号**）。"""
    code, out = _run_python(
        "import sys; sys.path.insert(0, 'src');"
        "import freegraph.runtime as r, freegraph.contracts as c;"
        "print(len(r.__all__), len(c.__all__))"
    )
    if code != 0:
        return False, out.strip()[-200:]
    text = out.strip().splitlines()[-1] if out.strip() else ""
    parts = text.split()
    ok = len(parts) == 2 and parts == ["20", "20"]
    return ok, f"runtime.__all__ / contracts.__all__ = {text}（期望 20 / 20）"


def _check_frozen_assertions() -> tuple[bool, str]:
    """**A4** · SC-005 · **M-6** · **R-9**：**10 个**冻结断言文件的 diff **全为空**。

    ⚠️ **MUST 用** ``git diff HEAD --stat`` —— **不是** ``git diff --stat``（后者
    **不比对已暂存的改动** ⇒ 可假通过）。
    """
    dirty: list[str] = []
    for name in FROZEN_ASSERTION_FILES:
        rel = f"tests/runtime/{name}.py"
        code, out = _run_git(["diff", "HEAD", "--stat", "--", rel])
        if code != 0:
            dirty.append(f"{rel}（git 失败）")
        elif out.strip():
            dirty.append(rel)
    if dirty:
        return False, f"以下文件的 diff **非空**（MUST 全为空）：{dirty}"
    return True, f"{len(FROZEN_ASSERTION_FILES)} 个冻结断言文件的 `git diff HEAD --stat` 全为空"


def _check_retro_landings() -> tuple[bool, str]:
    """**A7** · FR-013 · SC-008：**R-1…R-10** 的**逐条落点**命中。"""
    missing: list[str] = []
    for rel, pattern in RETRO_LANDINGS:
        path = REPO_ROOT / rel
        if not path.exists():
            missing.append(f"{rel}（文件缺失）")
            continue
        if not re.search(pattern, path.read_text(encoding="utf-8")):
            missing.append(f"{rel}（未含 {pattern}）")
    if missing:
        return False, f"回溯修订落点未命中：{missing}"
    return True, f"R-1…R-10 的 {len(RETRO_LANDINGS)} 个落点逐条命中"


def _check_manual() -> tuple[bool, str]:
    """**A5** · SC-009：人工验证记录的**五段式** + **追认**文字（原则 V）。"""
    if not MANUAL_VERIFICATION.exists():
        return False, f"缺失：{MANUAL_VERIFICATION}"
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    missing = [s for s in MANUAL_SECTIONS if s not in text]
    if missing:
        return False, f"五段式小节缺失：{missing}"
    missing_ration = [x for x in RATIFICATION_ITEMS if x not in text]
    if missing_ration:
        return False, f"追认文字缺失（须逐条覆盖 {RATIFICATION_ITEMS}）：{missing_ration}"
    if "追认" not in text:
        return False, "追认文字缺失"
    return True, "五段式齐全 + 追认文字齐备（PR-1…PR-8 八项打包成一次）"


def _check_gate_deviations() -> tuple[bool, str]:
    """**A10** · FR-019 · SC-009：门禁 **3 / 4 / 5 / 7** 的偏离**如实登记**。"""
    if not MANUAL_VERIFICATION.exists():
        return False, f"缺失：{MANUAL_VERIFICATION}"
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    missing = [g for g in GATE_DEVIATIONS if g not in text]
    if missing:
        return False, f"门禁偏离登记缺失：{missing}"
    return True, "门禁 3 / 4 / 5 / 7 的「物理不可达成」已逐条点名登记"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B7F4 人工验收脚本")
    parser.add_argument("--record", metavar="PATH", help="同时生成验收记录片段")
    parser.add_argument("--require-installed", action="store_true", help="把「未安装」判为失败")
    parser.add_argument("--skip-differential", action="store_true", help="跳过差分闸口（快）")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("B7F4 人工验收 · 判据 A1–A10（对照 specs/b7f4-multisource-join/quickstart.md §2）")
    print("=" * 78)
    print(f"仓库根    : {REPO_ROOT}")
    print(f"Python    : {PYTHON}")
    print(f"平台      : {platform.platform()}")
    print(f"上游 langgraph: {'已安装' if _upstream_installed() else '缺席（A3 / A9 将 skip）'}")
    print()

    results: list[dict[str, Any]] = []
    failures = 0
    skipped = 0

    def _record(gid: str, title: str, status: str, detail: str) -> None:
        results.append({"id": gid, "title": title, "status": status, "detail": detail})

    def _pytest_gate(gid: str, title: str, args: list[str], *, needs_upstream: bool = False) -> None:
        nonlocal failures, skipped
        target = REPO_ROOT / args[0]
        if not target.exists():
            skipped += 1
            print(f"[SKIP] {gid:4} {title} —— 目标缺失：{args[0]}")
            _record(gid, title, "SKIP", "目标缺失")
            return
        if needs_upstream and not _upstream_installed():
            skipped += 1
            print(f"[SKIP] {gid:4} {title} —— 上游缺席（缺席即 skip · 非失败）")
            _record(gid, title, "SKIP", "上游缺席")
            return
        code, out = _run_pytest(args)
        tail = out.strip().splitlines()[-1] if out.strip() else ""
        if code == 0:
            print(f"[PASS] {gid:4} {title}  {tail}")
        else:
            failures += 1
            print(f"[FAIL] {gid:4} {title}")
            print("       " + "\n       ".join(out.strip().splitlines()[-12:]))
        _record(gid, title, "PASS" if code == 0 else "FAIL", tail)

    def _check_gate(gid: str, title: str, fn: Any) -> None:
        nonlocal failures
        ok, detail = fn()
        if ok:
            print(f"[PASS] {gid:4} {title}  {detail}")
        else:
            failures += 1
            print(f"[FAIL] {gid:4} {title}  {detail}")
        _record(gid, title, "PASS" if ok else "FAIL", detail)

    # ── A1 · 多源边可表达 ──────────────────────────────────────────────────
    _pytest_gate(
        "A1",
        "多源边可表达（FR-001 · M-1）",
        ["tests/runtime/test_superstep_multisource.py", "-k", "multi_source_edge_can_be_expressed"],
    )

    # ── A2 · 屏障语义正确 ──────────────────────────────────────────────────
    _pytest_gate(
        "A2",
        "屏障语义正确（FR-003 / FR-004 · M-2 / M-3 / M-4 / M-5 / M-8）",
        ["tests/runtime/test_superstep_multisource.py", "-k", "barrier or group"],
    )

    # ── A3 · 与上游同款（差分场景组）────────────────────────────────────────
    if args.skip_differential:
        skipped += 1
        print("[SKIP] A3   与上游同款（差分场景组 D-16…D-28）—— --skip-differential")
        _record("A3", "与上游同款（差分场景组 D-16…D-28）", "SKIP", "--skip-differential")
    else:
        _pytest_gate(
            "A3",
            "与上游同款（差分场景组 D-16…D-28 · SC-004 / SC-011）",
            ["tests/differential/test_parity_probe.py"],
            needs_upstream=True,
        )

    # ── A4 · 既有断言零削弱 ────────────────────────────────────────────────
    _pytest_gate(
        "A4a",
        "既有单源口径用例全绿（SC-005 · M-6）",
        ["tests/runtime/"],
    )
    _check_gate("A4b", "10 个冻结断言文件的 diff 全为空（R-9）", _check_frozen_assertions)

    # ── A5 · 冻结面追认 ────────────────────────────────────────────────────
    _check_gate("A5", "人工验证记录五段式 + 追认文字在位（FR-012 / FR-015 · SC-009）", _check_manual)

    # ── A6 · 导出面零新增 ──────────────────────────────────────────────────
    _check_gate("A6", "导出面零新增（runtime / contracts == 20 · SC-006 · M-9）", _check_export_surface)

    # ── A7 · 回溯修订落全 ──────────────────────────────────────────────────
    _check_gate("A7", "回溯修订 R-1…R-10 逐条命中（FR-013 · SC-008）", _check_retro_landings)

    # ── A8 · 形态校验生效 ──────────────────────────────────────────────────
    _pytest_gate(
        "A8",
        "形态校验生效（V-16 / V-2 / 边键类型非法 · FR-017 / FR-021）",
        [
            "tests/runtime/test_superstep_multisource.py",
            "-k",
            "rejected or missing or illegal or terminal or exactly_one_target",
        ],
    )

    # ── A9 · 参数化场景全绿 ────────────────────────────────────────────────
    if args.skip_differential:
        skipped += 1
        print("[SKIP] A9   参数化场景全绿（D-24 · SC-013）—— --skip-differential")
        _record("A9", "参数化场景全绿（D-24 · SC-013）", "SKIP", "--skip-differential")
    else:
        _pytest_gate(
            "A9",
            "参数化场景全绿（D-24 · 屏障形态 × 通道类型 × 源可达性 · SC-013 · M-13）",
            ["tests/differential/test_parity_probe.py", "-k", "d24_parameterized"],
            needs_upstream=True,
        )

    # ── A10 · 门禁偏离已登记 ───────────────────────────────────────────────
    _check_gate("A10", "门禁 3 / 4 / 5 / 7 的偏离已如实登记（FR-019 · SC-009）", _check_gate_deviations)

    print()
    print("=" * 78)
    verdict = "PASS" if failures == 0 else "FAIL"
    print(f"总闸口 {len(results)} · 失败 {failures} · 跳过 {skipped} ⇒ **{verdict}**")
    print("=" * 78)

    if args.record:
        record = Path(args.record)
        record.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature": "B7F4",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "verdict": verdict,
            "failures": failures,
            "skipped": skipped,
            "gates": results,
        }
        record.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"验收记录片段已写入：{record}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
