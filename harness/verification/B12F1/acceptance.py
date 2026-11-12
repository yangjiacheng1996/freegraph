#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B12F1** 人工验收脚本（并发执行 + 错误传播 + ``GraphInterrupt`` 合并）。

定位
----
本脚本是 **B12F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**——验收闸口 **V1–V14**（逐条对应
``specs/b12f1-concurrency-errors/quickstart.md`` 的 14 节手册）+ 门禁实跑 + 覆盖率取证。

覆盖的分组（**逐组对应一个验收闸口**）：

* **V1** 并行节点**不串行化**（**A1** · SC-001 · I-1 / I-2）；
* **V2** 首个异常**原样**抛出 + **附注** + **取消语义**（**A2** · SC-002 / SC-014 / SC-028）；
* **V3** 异常 ⇒ 后续 super-step **不执行** + **整轮原子**（**A3** · SC-003 / SC-007 / SC-008）；
* **V4** 多个中断**合并抛出**（载荷 = **元组**）（SC-009 / SC-010 · I-12）；
* **V5** 中断与写入的关系 + **暂停** + **异常优先**（SC-011 / SC-012 / SC-013）；
* **V6** 并发 == 串行（``max_concurrency=1`` 的**同一规格**）（SC-004 / SC-005 · I-6 / I-7 / I-8）；
* **V7** ``Command`` 的**并发语义**（SC-015 / SC-016 · 承接 H-2）；
* **V8** 节点**入参口径**（稀疏 · 顺序）（SC-017 · I-9 · 承接 H-1）；
* **V9** **纯净性**（零上游 / 零环境变量 / 零出站）（SC-018 / SC-020）；
* **V10** **结构纪律**（导出面 / 四字段 / 层 / 门禁编号）（SC-019 / SC-024 / SC-026）；
* **V11** **确定性** + **调度状态不串扰** + **零悬挂线程**（SC-025 / SC-026 · I-7 / I-16）；
* **V12** **人工验证**（原则 V）+ **偏离登记 + 发起者追认**（SC-021 / SC-022 / SC-023）；
* **V13** ★ **差分探针场景组**（**A4** · SC-029 · 宪法原则 XI 的「可验证出口」）；
* **V14** ★ **并发度**（缺省上限 / 显式 ``N``）+ **取值校验时机**（SC-027）。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

⚠️ **覆盖率工具是例外**——``coverage`` 是**开发期工具** ⇒ **不进**仓库依赖声明
⇒ 本机未装时该段标「◌ 环境未就绪」（**不判失败**）⇒ 装法：``uv pip install coverage``。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树** |

用法
----
    python3 harness/verification/B12F1/acceptance.py                    # 跑全部
    python3 harness/verification/B12F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B12F1/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B12F1/acceptance.py --skip-coverage    # 跳过覆盖率取证段（快）
    python3 harness/verification/B12F1/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

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
SPEC_DIR = REPO_ROOT / "specs" / "b12f1-concurrency-errors"
QUICKSTART_PATH = SPEC_DIR / "quickstart.md"
MANUAL_VERIFICATION = REPO_ROOT / "harness" / "verification" / "B12F1" / "manual-verification.md"
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

#: 闸口定义（**逐条对应 quickstart §0.3 的 V1…V14**）。
#:
#: ``kind``：
#: * ``pytest`` —— 跑一条 pytest 选择器；
#: * ``file``   —— 断言一个文件存在；
#: * ``grep``   —— 在某个文件里断言一条正则存在。
GATES: list[dict[str, Any]] = [
    {
        "id": "V1",
        "title": "并行节点不串行化（A1 · SC-001）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "parallel or barrier"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
    {
        "id": "V2",
        "title": "首个异常原样抛出 + 附注 + 取消语义（A2 · SC-002 / SC-014 / SC-028）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_errors.py", "-k", "first or note or cancel"],
        "skip_if_missing": "tests/runtime/test_superstep_errors.py",
    },
    {
        "id": "V3",
        "title": "异常 ⇒ 后续 super-step 不执行 + 整轮原子（A3 · SC-003 / SC-007 / SC-008）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_errors.py", "-k", "atomic or stop or ghost"],
        "skip_if_missing": "tests/runtime/test_superstep_errors.py",
    },
    {
        "id": "V4",
        "title": "多个中断合并抛出（载荷 = 元组）（SC-009 / SC-010）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_errors.py", "-k", "interrupt"],
        "skip_if_missing": "tests/runtime/test_superstep_errors.py",
    },
    {
        "id": "V5",
        "title": "中断与写入的关系 + 暂停 + 异常优先（SC-011 / SC-012 / SC-013）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_errors.py", "-k", "writes or pause or priority"],
        "skip_if_missing": "tests/runtime/test_superstep_errors.py",
    },
    {
        "id": "V6",
        "title": "并发 == 串行（同一规格）（SC-004 / SC-005）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "serial or deterministic"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
    {
        "id": "V7",
        "title": "Command 的并发语义（SC-015 / SC-016）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "command"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
    {
        "id": "V8",
        "title": "节点入参口径（稀疏 · 顺序）（SC-017）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "input"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
    {
        "id": "V9",
        "title": "纯净性（零上游 / 零环境变量 / 零出站）（SC-018 / SC-020）",
        "kind": "pytest",
        "args": ["tests/gates", "-k", "G3 or G4 or G6 or G24 or G26 or G27"],
    },
    {
        "id": "V10",
        "title": "结构纪律（导出面 / 四字段 / 层 / 门禁编号）（SC-019 / SC-024 / SC-026）",
        "kind": "pytest",
        "args": ["tests/contracts", "tests/facade"],
    },
    {
        "id": "V11",
        "title": "确定性 + 调度状态不串扰 + 零悬挂线程（SC-025 / SC-026）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "thread or isolation"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
    {
        "id": "V12",
        "title": "人工验证记录（原则 V）+ 偏离登记 + 发起者追认（SC-021 / SC-022 / SC-023）",
        "kind": "file",
        "path": MANUAL_VERIFICATION,
        "also": [
            (REPO_ROOT / "specs" / "b12f1-concurrency-errors" / "plan.md", r"PR-11"),
            (REPO_ROOT / "specs" / "b12f1-concurrency-errors" / "tasks.md", r"T080"),
        ],
    },
    {
        "id": "V13",
        "title": "差分探针场景组（A4 · SC-029）",
        "kind": "pytest",
        "args": ["tests/differential/test_parity_probe.py"],
        "skip_if_missing": "tests/differential/test_parity_probe.py",
        "skip_if_upstream_absent": True,
    },
    {
        "id": "V14",
        "title": "并发度（缺省上限 / 显式 N）+ 取值校验时机（SC-027）",
        "kind": "pytest",
        "args": ["tests/runtime/test_superstep_concurrency.py", "-k", "cap or validation"],
        "skip_if_missing": "tests/runtime/test_superstep_concurrency.py",
    },
]

#: 人工验证记录的**五段式**小节（原则 V · 宪法）。
MANUAL_SECTIONS = ["验证环境", "验证步骤", "实际输出", "结论", "遗留问题"]

#: 追认必须覆盖的**四条「比上游更严」**（X-1 / X-2 / X-3 / X-7 · 一次追认 · 逐条列出）。
RATIFICATION_ITEMS = ["X-1", "X-2", "X-3", "X-7"]


def _env() -> dict[str, str]:
    """构造子进程环境（**零出站** · 不读环境变量做判定 · 只传 PATH / HOME 等基础项）。

    ⚠️ **MUST NOT** 改 ``PYTHONPATH`` —— 门禁 **G22** 的反向用例跑的是**隔离副本**里的
    ``gate_G22_isolated_env.py`` ⇒ 若把本仓库的 ``src`` 塞进 ``PYTHONPATH`` ⇒
    该脚本 import 到的**不是**隔离副本的包 ⇒ 注入的 ``langchain_core`` 检测不到
    ⇒ **反向用例假绿**（本脚本 2026-11-13 首次实跑时踩到 ⇒ 已修）。
    ⇒ 本仓库的 ``freegraph`` 在 venv 里**已可导入**（指向 ``src/freegraph``）⇒ 无需注入。
    """
    return dict(os.environ)


def _run_pytest(args: list[str]) -> tuple[int, str]:
    """跑一条 pytest ⇒ 返回 ``(退出码, 合并输出)``。"""
    proc = subprocess.run(
        [str(PYTHON), "-m", "pytest", *args, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=900,
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
    """校验人工验证记录的**五段式** + 追认文字（原则 V）。"""
    if not MANUAL_VERIFICATION.exists():
        return False, f"缺失：{MANUAL_VERIFICATION}"
    text = MANUAL_VERIFICATION.read_text(encoding="utf-8")
    missing = [s for s in MANUAL_SECTIONS if s not in text]
    if missing:
        return False, f"五段式小节缺失：{missing}"
    missing_ration = [x for x in RATIFICATION_ITEMS if x not in text]
    if missing_ration:
        return False, f"追认文字缺失（须逐条覆盖 {RATIFICATION_ITEMS}）：{missing_ration}"
    return True, "五段式齐全 + 追认文字齐备"


def _check_gates() -> tuple[bool, str]:
    """跑既有门禁套件（``tests/gates``）⇒ 门禁编号连续性等。"""
    code, out = _run_pytest(["tests/gates"])
    lines = out.strip().splitlines()
    tail = lines[-1] if lines else ""
    if code != 0:
        failed = [line for line in lines if line.startswith("FAILED")]
        tail = " · ".join(failed) if failed else tail
    return code == 0, tail


def _check_coverage() -> tuple[str, str]:
    """覆盖率取证（**差分口径** · 行 / 分支）⇒ 返回 ``(状态, 说明)``。"""
    try:
        import coverage  # noqa: F401
    except Exception:
        return "skip", "◌ 环境未就绪（未装 coverage · 开发期工具 · 不判失败）"
    proc = subprocess.run(
        [
            str(PYTHON), "-m", "coverage", "run", "--branch",
            "-m", "pytest", "tests/runtime", "tests/differential", "-q",
            "--no-header", "-p", "no:cacheprovider",
        ],
        cwd=REPO_ROOT, env=_env(), capture_output=True, text=True, timeout=1800,
    )
    if proc.returncode != 0:
        return "fail", (proc.stdout or "")[-800:]
    cov = subprocess.run(
        [str(PYTHON), "-m", "coverage", "report",
         "--include", "src/freegraph/runtime/_concurrency.py,src/freegraph/runtime/superstep.py"],
        cwd=REPO_ROOT, env=_env(), capture_output=True, text=True, timeout=300,
    )
    return ("ok" if cov.returncode == 0 else "fail"), (cov.stdout or cov.stderr or "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B12F1 人工验收脚本")
    parser.add_argument("--record", metavar="PATH", help="同时生成验收记录片段")
    parser.add_argument("--require-installed", action="store_true", help="把「未安装」判为失败")
    parser.add_argument("--skip-coverage", action="store_true", help="跳过覆盖率取证段")
    parser.add_argument("--skip-gates", action="store_true", help="跳过门禁实跑段")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("B12F1 人工验收 · 闸口 V1–V14（对照 specs/b12f1-concurrency-errors/quickstart.md）")
    print("=" * 78)
    print(f"仓库根    : {REPO_ROOT}")
    print(f"Python    : {PYTHON}")
    print(f"平台      : {platform.platform()}")
    print(f"上游 langgraph: {'已安装' if _upstream_installed() else '缺席（V13 将 skip）'}")
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
                results.append({"id": gid, "title": title, "status": "SKIP", "detail": "目标缺失"})
                skipped += 1
                continue
            if gate.get("skip_if_upstream_absent") and not _upstream_installed():
                print(f"[SKIP] {gid:4} {title} —— 上游缺席（缺席即 skip · 非失败）")
                results.append({"id": gid, "title": title, "status": "SKIP", "detail": "上游缺席"})
                skipped += 1
                continue
            code, out = _run_pytest(gate["args"])
            tail = out.strip().splitlines()[-1] if out.strip() else ""
            ok = code == 0
            if ok:
                print(f"[PASS] {gid:4} {title}  ({time.monotonic() - started:.1f}s)  {tail}")
            else:
                failures += 1
                print(f"[FAIL] {gid:4} {title}  ({time.monotonic() - started:.1f}s)")
                print("       " + "\n       ".join(out.strip().splitlines()[-12:]))
            results.append({"id": gid, "title": title, "status": "PASS" if ok else "FAIL",
                            "detail": tail})
        elif kind == "file":
            ok, detail = _check_manual()
            for path, pattern in gate.get("also", []):
                if not path.exists():
                    ok, detail = False, f"缺失：{path}"
                    break
                if not re.search(pattern, path.read_text(encoding="utf-8")):
                    ok, detail = False, f"{path} 未含 {pattern}"
                    break
            if ok:
                print(f"[PASS] {gid:4} {title}  {detail}")
            else:
                failures += 1
                print(f"[FAIL] {gid:4} {title}  {detail}")
            results.append({"id": gid, "title": title, "status": "PASS" if ok else "FAIL",
                            "detail": detail})

    if not args.skip_gates:
        ok, detail = _check_gates()
        if ok:
            print(f"[PASS] GATES 全量门禁实跑  {detail}")
        else:
            failures += 1
            print(f"[FAIL] GATES 全量门禁实跑  {detail}")
        results.append({"id": "GATES", "title": "全量门禁实跑",
                        "status": "PASS" if ok else "FAIL", "detail": detail})

    if not args.skip_coverage:
        status, detail = _check_coverage()
        if status == "ok":
            print("[PASS] COVERAGE 覆盖率取证")
            print(detail)
        elif status == "skip":
            print(f"[SKIP] COVERAGE 覆盖率取证  {detail}")
            skipped += 1
        else:
            failures += 1
            print("[FAIL] COVERAGE 覆盖率取证")
            print(detail)
        results.append({"id": "COVERAGE", "title": "覆盖率取证", "status": status.upper(),
                        "detail": detail})
    else:
        print("[SKIP] COVERAGE 覆盖率取证（--skip-coverage）")
        skipped += 1

    print()
    print("=" * 78)
    verdict = "PASS" if failures == 0 else "FAIL"
    print(f"总闸口 {len(results)} · 失败 {failures} · 跳过 {skipped} ⇒ **{verdict}**")
    print("=" * 78)

    if args.record:
        record = Path(args.record)
        record.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature": "B12F1",
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
