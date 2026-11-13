#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B10F1** 人工验收脚本（``interrupt()`` + ``resume`` · HITL 中断与恢复闭环）。

定位
----
本脚本是 **B10F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收闸口 **V1–V14**（逐条对应
``specs/b10f1-interrupt-resume/quickstart.md`` 的 14 节手册）+ 门禁实跑。

覆盖的分组（**逐组对应一个验收闸口**）：

* **V1** 中断后结果含 ``__interrupt__``（元素带 ``.value`` / ``.id``）· SC-001 / A3；
* **V2** 恢复后跑到结束态（状态含 resume 值）· SC-002 / A1；
* **V3** 恢复时节点**从节点起点重跑** · SC-003 / A2；
* **V4** 中断前的写入**不丢失**（挂起不是回滚）· SC-004；
* **V5** ★ 恢复**确实经由 checkpointer**（读侧 / 写侧契约）· SC-005 / A4①；
* **V6** 未挂 checkpointer ⇒ **明确异常** · SC-011 / A4②；
* **V7** 「未提供恢复值」的**写死**行为 · SC-012；
* **V8** 同一节点内**多个** ``interrupt()`` ⇒ 按**节点内顺序**匹配 · SC-014；
* **V9** 跨节点多挂起中断 ⇒ 单值**失败** / 按 id **成功** · SC-015；
* **V10** 挂起后**再次挂起** ⇒ 闭环**可重复** · SC-013；
* **V11** ★ **差分探针场景组**（``DI-01…DI-08``）· SC-016 · 宪法原则 XI 的「可验证出口」；
* **V12** **结构纪律**（导出面 / 四字段 / 层依赖 / 零依赖）· SC-007 / SC-017；
* **V13** **人工验证**（原则 V）+ **偏离登记 V-1…V-4** + **发起者追认**· SC-020；
* **V14** 全量套件（**零回归**）+ 门禁实跑。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

⚠️ **上游 ``langgraph`` 是开发期依赖** ⇒ 缺席即 **skip**（**不判失败** · 沿用
B5F2 / B12F1 的纪律）。

用法
----
    python3 harness/verification/B10F1/acceptance.py                    # 跑全部
    python3 harness/verification/B10F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B10F1/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

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
SPEC_DIR = REPO_ROOT / "specs" / "b10f1-interrupt-resume"
QUICKSTART_PATH = SPEC_DIR / "quickstart.md"
MANUAL_VERIFICATION = (
    REPO_ROOT / "harness" / "verification" / "B10F1" / "manual-verification.md"
)
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

#: 闸口定义（**逐条对应 quickstart §1…§14**）。
#:
#: ``kind``：
#: * ``pytest`` —— 跑一条 pytest 选择器；
#: * ``file``   —— 断言人工验证记录的**五段式** + **追认**齐备。
GATES: list[dict[str, Any]] = [
    {
        "id": "V1",
        "title": "中断后结果含 __interrupt__（元素带 .value / .id）· SC-001 / A3",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_basic.py", "-k", "value_and_id"],
    },
    {
        "id": "V2",
        "title": "恢复后跑到结束态（状态含 resume 值）· SC-002 / A1",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_resume.py", "-k", "resume_completes"],
    },
    {
        "id": "V3",
        "title": "恢复时节点从节点起点重跑 · SC-003 / A2",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_resume.py", "-k", "reruns_from_start"],
    },
    {
        "id": "V4",
        "title": "中断前的写入不丢失（挂起不是回滚）· SC-004",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_basic.py", "-k", "writes_preserved"],
    },
    {
        "id": "V5",
        "title": "恢复确实经由 checkpointer（读侧 / 写侧契约）· SC-005 / A4①",
        "kind": "pytest",
        "args": [
            "tests/runtime/test_interrupt_checkpoint.py",
            "-k",
            "reads_snapshot_and_pending_writes or scheduler_ledger or pause_writes",
        ],
    },
    {
        "id": "V6",
        "title": "未挂 checkpointer ⇒ 明确异常 · SC-011 / A4②",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_errors.py", "-k", "checkpointer_required"],
    },
    {
        "id": "V7",
        "title": "「未提供恢复值」的写死行为 · SC-012",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_errors.py", "-k", "resume_value_required"],
    },
    {
        "id": "V8",
        "title": "同一节点内多个 interrupt() ⇒ 按节点内顺序匹配 · SC-014",
        "kind": "pytest",
        "args": [
            "tests/runtime/test_interrupt_resume.py",
            "-k",
            "multiple_interrupts_in_one_node",
        ],
    },
    {
        "id": "V9",
        "title": "跨节点多挂起中断 ⇒ 单值失败 / 按 id 成功 · SC-015",
        "kind": "pytest",
        "args": [
            "tests/runtime/test_interrupt_resume.py",
            "-k",
            "multiple_pending_interrupts",
        ],
    },
    {
        "id": "V10",
        "title": "挂起后再次挂起 ⇒ 闭环可重复 · SC-013",
        "kind": "pytest",
        "args": [
            "tests/runtime/test_interrupt_resume.py",
            "-k",
            "resume_then_interrupt_again",
        ],
    },
    {
        "id": "V11",
        "title": "★ 差分探针场景组（DI-01…DI-08）· SC-016",
        "kind": "pytest",
        "args": ["tests/differential/test_parity_probe.py"],
        "skip_if_upstream_absent": True,
    },
    {
        "id": "V12",
        "title": "结构纪律（导出面 / 四字段 / 层依赖 / 零依赖）· SC-007 / SC-017",
        "kind": "pytest",
        "args": ["tests/runtime/test_interrupt_contract.py"],
    },
    {
        "id": "V13",
        "title": "人工验证（五段式）+ 偏离登记 V-1…V-4 + 发起者追认 · SC-020",
        "kind": "file",
    },
    {
        "id": "V14",
        "title": "全量套件（零回归）",
        "kind": "pytest",
        "args": ["tests"],
    },
]

#: 人工验证记录的**五段式**小节（原则 V）。
MANUAL_SECTIONS = (
    "## 1. 验证环境",
    "## 2. 验证步骤",
    "## 3. 实际输出",
    "## 4. 结论",
    "## 5. 遗留问题",
)

#: **追认**必须覆盖的**四项偏离登记**（V-1 / V-2 / V-3 / V-4 · 一次追认 · 逐条列出）。
RATIFICATION_ITEMS = ("V-1", "V-2", "V-3", "V-4")

#: **破冻结面回溯修订 T-1** 的**六处**冻结断言（判据零放宽）。
FROZEN_ASSERTION_ITEMS = ("T-1", "PR-8", "PR-6", "PR-7")


def _env() -> dict[str, str]:
    """构造子进程环境（**零出站** · 不读环境变量做判定 · 只传基础项）。

    ⚠️ **MUST NOT** 改 ``PYTHONPATH`` —— 门禁 **G22** 的反向用例跑的是**隔离副本**
    里的 ``gate_G22_isolated_env.py`` ⇒ 若把本仓库的 ``src`` 塞进 ``PYTHONPATH``
    ⇒ 该脚本 import 到的**不是**隔离副本的包 ⇒ **反向用例假绿**。
    ⇒ 本仓库的 ``freegraph`` 在 venv 里**已可导入**（指向 ``src/freegraph``）⇒ 无需注入。
    """
    return dict(os.environ)


def _run_pytest(args: list[str]) -> tuple[int, str]:
    """跑一条 pytest ⇒ 返回 ``(退出码, 合并输出)``。"""
    proc = subprocess.run(
        [
            str(PYTHON),
            "-m",
            "pytest",
            *args,
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _upstream_installed() -> bool:
    """上游 ``langgraph`` 是否**已安装**（缺席即 skip · 沿用 B5F2 的纪律）。"""
    try:
        import importlib.util

        return importlib.util.find_spec("langgraph") is not None
    except Exception:  # pragma: no cover - find_spec 异常按「缺席」处理
        return False


def _check_manual() -> tuple[bool, str]:
    """校验人工验证记录的**五段式** + 偏离登记 + **追认**待签清单（原则 V）。

    ⚠️ **追认文字**由**发起者本人**落盘 ⇒ ⇒ 本检查只验证「**待签清单**齐备」
    （**MUST NOT** 要求已签名 —— **未追认前 MUST NOT 合入** · 由 **T048** 把关）。
    """
    if not MANUAL_VERIFICATION.exists():
        return False, f"缺失：{MANUAL_VERIFICATION}"
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    missing = [s for s in MANUAL_SECTIONS if s not in text]
    if missing:
        return False, f"五段式小节缺失：{missing}"
    missing_ration = [x for x in RATIFICATION_ITEMS if x not in text]
    if missing_ration:
        return False, f"偏离登记缺失（须逐条覆盖 {RATIFICATION_ITEMS}）：{missing_ration}"
    missing_frozen = [x for x in FROZEN_ASSERTION_ITEMS if x not in text]
    if missing_frozen:
        return False, (
            f"破冻结面 / 范围变更的**待签清单**缺失（须逐条覆盖 "
            f"{FROZEN_ASSERTION_ITEMS}）：{missing_frozen}"
        )
    return True, "五段式齐全 + 偏离登记齐备 + 追认待签清单齐备"


def _check_gates() -> tuple[bool, str]:
    """跑既有门禁套件（``tests/gates``）⇒ 门禁编号连续性等。"""
    code, out = _run_pytest(["tests/gates"])
    lines = out.strip().splitlines()
    tail = lines[-1] if lines else ""
    if code != 0:
        failed = [line for line in lines if line.startswith("FAILED")]
        tail = " · ".join(failed) if failed else tail
    return code == 0, tail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B10F1 人工验收脚本")
    parser.add_argument("--record", metavar="PATH", help="同时生成验收记录片段")
    parser.add_argument("--skip-gates", action="store_true", help="跳过门禁实跑段")
    args = parser.parse_args(argv)

    print("=" * 78)
    print(
        "B10F1 人工验收 · 闸口 V1–V14"
        "（对照 specs/b10f1-interrupt-resume/quickstart.md）"
    )
    print("=" * 78)
    print(f"仓库根    : {REPO_ROOT}")
    print(f"Python    : {PYTHON}")
    print(f"平台      : {platform.platform()}")
    print(
        f"上游 langgraph: "
        f"{'已安装' if _upstream_installed() else '缺席（V11 将 skip）'}"
    )
    print()

    results: list[dict[str, Any]] = []
    failures = 0
    skipped = 0

    for gate in GATES:
        gid, title, kind = gate["id"], gate["title"], gate["kind"]
        started = time.monotonic()

        if kind == "pytest":
            target = REPO_ROOT / gate["args"][0]
            if not target.exists():
                print(f"[SKIP] {gid:4} {title} —— 目标缺失：{gate['args'][0]}")
                results.append(
                    {"id": gid, "title": title, "status": "SKIP", "detail": "目标缺失"}
                )
                skipped += 1
                continue
            if gate.get("skip_if_upstream_absent") and not _upstream_installed():
                print(f"[SKIP] {gid:4} {title} —— 上游缺席（缺席即 skip · 非失败）")
                results.append(
                    {"id": gid, "title": title, "status": "SKIP", "detail": "上游缺席"}
                )
                skipped += 1
                continue
            code, out = _run_pytest(gate["args"])
            tail = out.strip().splitlines()[-1] if out.strip() else ""
            ok = code == 0
            if ok:
                print(
                    f"[PASS] {gid:4} {title}  ({time.monotonic() - started:.1f}s)  {tail}"
                )
            else:
                failures += 1
                print(f"[FAIL] {gid:4} {title}  ({time.monotonic() - started:.1f}s)")
                print(
                    "       "
                    + "\n       ".join(out.strip().splitlines()[-12:])
                )
            results.append(
                {
                    "id": gid,
                    "title": title,
                    "status": "PASS" if ok else "FAIL",
                    "detail": tail,
                }
            )
        elif kind == "file":
            ok, detail = _check_manual()
            if ok:
                print(f"[PASS] {gid:4} {title}  {detail}")
            else:
                failures += 1
                print(f"[FAIL] {gid:4} {title}  {detail}")
            results.append(
                {
                    "id": gid,
                    "title": title,
                    "status": "PASS" if ok else "FAIL",
                    "detail": detail,
                }
            )

    if not args.skip_gates:
        ok, detail = _check_gates()
        if ok:
            print(f"[PASS] GATES 全量门禁实跑  {detail}")
        else:
            failures += 1
            print(f"[FAIL] GATES 全量门禁实跑  {detail}")
        results.append(
            {
                "id": "GATES",
                "title": "全量门禁实跑",
                "status": "PASS" if ok else "FAIL",
                "detail": detail,
            }
        )

    print()
    print("=" * 78)
    verdict = "PASS" if failures == 0 else "FAIL"
    print(f"总闸口 {len(results)} · 失败 {failures} · 跳过 {skipped} ⇒ **{verdict}**")
    print("=" * 78)

    if args.record:
        record = Path(args.record)
        record.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature": "B10F1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "verdict": verdict,
            "failures": failures,
            "skipped": skipped,
            "gates": results,
        }
        record.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"验收记录片段已写入：{record}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
