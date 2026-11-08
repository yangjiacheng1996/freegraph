# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G29** · 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 兼容矩阵分层）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G29）：

1. **只读基准 diff 断言** —— ``harness/demo/target.py`` 的内容 MUST 与
   **入库基准**逐字相同 ⇒ 改动即失败（FR-011 ① · **不设「已批准豁免」通道**）。
   **基准载体** = Git 索引中的 ``HEAD:harness/demo/target.py``
   （``git show <baseline>:harness/demo/target.py``）—— 仓库内**不存在**第二份
   基准副本 ⇒ MUST NOT 依赖「仓库内另一份文件」；读取基准 MUST 经 ``git show``
   （**只读**，MUST NOT 改动工作树）；
2. **验收脚本集的退出码断言** —— 跑 ``harness/demo/{graph_core,agent_loop,
   visualization}.py`` ⇒ 退出码 ∈ **{0, 1, 2}**，并按**失败来源**细分：
   ① **1 且全部失败均源于 ``NotImplementedError``** ⇒ 判为**环境未就绪**
   （内核运行时未接线 · 属预期状态）⇒ **通过**；
   ② **1 且存在非 ``NotImplementedError`` 的失败** ⇒ 判为**真断言失败** ⇒ **失败**；
   ③ **2** ⇒ 环境未就绪（freegraph 不可导入）⇒ **通过**；
   ⇒ 落地时 MUST **解析脚本输出**以区分失败来源（**MUST NOT 只看退出码**）；
3. **C4 / C8 两条独立回归测试的挂载点** MUST 存在且**明确标记为「未落地」**
   （MUST NOT 伪装成「已通过」· FR-011 ②）；
4. ``--check-compat`` 模式：**只**负责 ``COMPAT.md`` 的**分层判定** ——
   **存在** ⇒ **严格比对**（有不一致 ⇒ 退出码非 0，并指名**哪一行、哪一个符号**）；
   **不存在** ⇒ 输出「**未落地**」且**退出码 0**（非阻断 · MUST NOT 静默跳过）
   ⇒「自动转为严格比对」由**文件是否存在**驱动，**同一套判据、无需改门禁实现**。
   **README「API 兼容矩阵」章节的严格比对由既有门禁 G8 / G19 承担** ⇒ 本模式
   MUST **引用**其判据来源、MUST NOT **重复实现**。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>``（被检的树根）·
``--baseline <git ref>``（只读基准的来源，默认 ``HEAD``）· ``--check-compat``。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G29"
RULE_TEXT = "契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 只读基准的仓库相对路径（宪法原则 III · **不可修改**）。
BASELINE_RELPATH = "harness/demo/target.py"

#: 验收脚本集（**只这三个** —— ``target.py`` 是只读基准、``acceptance.py`` 归 B25F1）。
ACCEPTANCE_SCRIPTS = ("graph_core", "agent_loop", "visualization")

#: C4 / C8 的**挂载点**文件（仓库级工件 —— 两条独立回归测试的落点）。
MOUNT_POINT_RELPATH = "tests/contracts/test_contract_regressions.py"

#: 挂载点的**机器可读标记**前缀。
MOUNT_MARKER = "GATE-MOUNT:"


def _run_script(script: Path, root: Path) -> tuple[int, str]:
    """跑一个验收脚本 ⇒ ``(退出码, 输出)``。"""
    env = dict(os.environ)
    src_dir = root / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    )
    # **子进程的输出含中文**（验收脚本的用例名 / 失败详情）⇒
    # ① 强制子进程用 UTF-8 输出（Windows 默认 cp1252 ⇒ 打印中文即崩）·
    # ② 父进程按 UTF-8 **容错解码**（否则 Windows 上解码失败 ⇒ 门禁崩）。
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _classify_script(returncode: int, output: str) -> tuple[str, str]:
    """按**失败来源**细分验收脚本的退出码 ⇒ ``(判定, 说明)``。

    * ``0`` ⇒ PASS；
    * ``2`` ⇒ 环境未就绪（freegraph 不可导入）；
    * ``1`` ⇒ 解析输出里的失败行：**全部**源于 ``NotImplementedError`` ⇒
      环境未就绪（内核运行时未接线 · 属预期状态）；否则 ⇒ 真断言失败。
    """
    if returncode == 0:
        return "PASS", "退出码 0"
    if returncode == 2:
        return "ENV_NOT_READY", "退出码 2 —— 环境未就绪（freegraph 不可导入）"
    if returncode != 1:
        return "FAIL", f"退出码 {returncode} —— 不在 {{0, 1, 2}} 内"
    failures = [line for line in output.splitlines() if "✘" in line]
    if not failures:
        return "FAIL", "退出码 1 —— 输出里没有可解析的失败行（MUST NOT 只看退出码）"
    non_not_implemented = [
        line for line in failures if "NotImplementedError" not in line
    ]
    if non_not_implemented:
        return "FAIL", (
            f"退出码 1 且存在非 NotImplementedError 的失败（真断言失败）："
            f"{non_not_implemented[0].strip()}"
        )
    return "ENV_NOT_READY", (
        f"退出码 1 且全部 {len(failures)} 条失败均源于 NotImplementedError"
        "⇒ 环境未就绪（内核运行时未接线 · 属预期状态）"
    )


def _mount_points(repo_root: Path) -> dict[str, str]:
    """解析挂载点文件里的 ``GATE-MOUNT:`` 标记 ⇒ ``{编号: status}``。"""
    path = repo_root / MOUNT_POINT_RELPATH
    found: dict[str, str] = {}
    if not path.is_file():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        if MOUNT_MARKER not in line:
            continue
        body = line.split(MOUNT_MARKER, 1)[1]
        fields = [item.strip() for item in body.split("·")]
        ident = fields[0].strip()
        status = ""
        for field in fields[1:]:
            if field.startswith("status="):
                status = field.split("=", 1)[1].strip()
        found[ident] = status
    return found


def evaluate(root: Path, baseline_ref: str) -> list[_gatekit.Violation]:
    """判定契约门禁载体 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    # ① 只读基准 diff
    baseline = _gatekit.git_show(baseline_ref, BASELINE_RELPATH, cwd=REPO_ROOT)
    target = root / BASELINE_RELPATH
    if baseline is None:
        violations.append(
            _gatekit.Violation(
                entry=BASELINE_RELPATH,
                rule="G29-01",
                detail=f"取不到只读基准（git show {baseline_ref}:{BASELINE_RELPATH}）",
                fix=(
                    "确认基准 ref 存在（默认 HEAD）——"
                    "基准 MUST 来自 Git 索引，仓库内不存在第二份基准副本"
                ),
            )
        )
    elif not target.is_file():
        violations.append(
            _gatekit.Violation(
                entry=BASELINE_RELPATH,
                rule="G29-01",
                detail="被检树内没有只读基准文件",
                fix="恢复 harness/demo/target.py（宪法原则 III · 只读基准）",
            )
        )
    else:
        actual = target.read_text(encoding="utf-8")
        if actual != baseline:
            diff = _gatekit.unified_diff(
                baseline, actual, f"{baseline_ref}:{BASELINE_RELPATH}", str(target)
            )
            violations.append(
                _gatekit.Violation(
                    entry=f"{_gatekit.relative_to_root(target, root)}",
                    rule="G29-01",
                    detail=f"只读基准被改动（diff）：\n{diff}",
                    fix=(
                        "还原 harness/demo/target.py —— 它是**只读基准**"
                        "（宪法原则 III）；不设「已批准豁免」通道"
                    ),
                )
            )
    # ② 验收脚本集的退出码
    for name in ACCEPTANCE_SCRIPTS:
        script = root / "harness" / "demo" / f"{name}.py"
        if not script.is_file():
            violations.append(
                _gatekit.Violation(
                    entry=f"harness/demo/{name}.py",
                    rule="G29-02",
                    detail="验收脚本不存在",
                    fix="恢复该验收脚本（立项书 §9.1 门禁 3 的「固定脚本原样可跑」）",
                )
            )
            continue
        returncode, output = _run_script(script, root)
        verdict, reason = _classify_script(returncode, output)
        if verdict == "FAIL":
            violations.append(
                _gatekit.Violation(
                    entry=f"harness/demo/{name}.py",
                    rule="G29-02",
                    detail=reason,
                    fix=(
                        "修复该验收脚本的失败——真断言失败 MUST 阻断"
                        "（内核未开工时 CI 应显示「环境未就绪」而非「验收失败」）"
                    ),
                )
            )
        else:
            print(f"[{GATE_ID}] harness/demo/{name}.py ⇒ {verdict} —— {reason}")
    # ③ C4 / C8 挂载点
    mounts = _mount_points(REPO_ROOT)
    for ident in ("C4", "C8"):
        status = mounts.get(ident)
        if status is None:
            violations.append(
                _gatekit.Violation(
                    entry=f"{MOUNT_POINT_RELPATH} · {ident}",
                    rule="G29-03",
                    detail="挂载点缺失（或未带机器可读标记）",
                    fix=(
                        "补上挂载点标记："
                        f"# {MOUNT_MARKER} {ident} · status=not-landed · owner=<承接方> · "
                        "milestone=<里程碑> · desc=<说明>"
                    ),
                )
            )
        elif status not in {"not-landed", "landed"}:
            violations.append(
                _gatekit.Violation(
                    entry=f"{MOUNT_POINT_RELPATH} · {ident}",
                    rule="G29-03",
                    detail=f"挂载点状态非法：{status!r}",
                    fix="状态只能是 not-landed（未落地）或 landed（已落地）",
                )
            )
        else:
            label = "未落地" if status == "not-landed" else "已落地"
            print(f"[{GATE_ID}] 挂载点 {ident}：{label}（{MOUNT_POINT_RELPATH}）")
    return violations


def check_compat(root: Path) -> int:
    """``--check-compat`` 模式 —— ``COMPAT.md`` 的**分层判定**。

    **不存在** ⇒ 输出「**未落地**」且**退出码 0**（非阻断 · MUST NOT 静默跳过）；
    **存在** ⇒ **严格比对**：有不一致 ⇒ 退出码非 0（并指名**行 / 符号**）；
    一致 ⇒ 退出码 0。
    """
    compat_path = root / "COMPAT.md"
    if not compat_path.is_file():
        print(
            "[G29] COMPAT.md：**未落地**（非阻断）——"
            "终版兼容矩阵归后续 feature；已入库的 README「API 兼容矩阵」章节"
            "由既有门禁 G8 / G19 严格比对（只接线 · 判据零改动）"
        )
        return 0
    violations = _compare_compat(root, compat_path)
    if not violations:
        print("[G29] COMPAT.md：与 README「API 兼容矩阵」**一致**（严格比对通过）")
        return 0
    for violation in violations:
        print(f"  违规条目: {violation.entry}")
        print(f"  规则编号: {violation.rule}")
        print(f"  细节    : {violation.detail}")
        print(f"  修复指引: {violation.fix}")
    print(f"[G29] COMPAT.md 严格比对失败：{len(violations)} 处不一致")
    return 1


def _compare_compat(root: Path, compat_path: Path) -> list[_gatekit.Violation]:
    """比对 ``COMPAT.md`` 与 README 的兼容矩阵 ⇒ 违规清单。

    **判据来源 = 既有门禁 G8 / G19 的取行实现**
    （`tests/facade/_gatesupport.py` 的 `compat_matrix_rows`）⇒
    MUST **引用**其判据来源、MUST NOT **重复实现**（裁定 8 第三条理由）。
    """
    violations: list[_gatekit.Violation] = []
    support = _load_facade_gate_support(root)
    if support is None:
        return [
            _gatekit.Violation(
                entry=_gatekit.relative_to_root(compat_path, root),
                rule="G29-04",
                detail="取不到既有门禁 G8 / G19 的判据来源（tests/facade/_gatesupport.py）",
                fix="恢复 tests/facade/_gatesupport.py（MUST NOT 在本门禁里重复实现矩阵取行）",
            )
        ]
    readme = (root / "README.md").read_text(encoding="utf-8")
    try:
        expected = dict(
            (symbol, cells) for symbol, cells in support.compat_matrix_rows(readme)
        )
        actual = dict(
            (symbol, cells) for symbol, cells in support.compat_matrix_rows(
                compat_path.read_text(encoding="utf-8")
            )
        )
    except AssertionError as exc:
        return [
            _gatekit.Violation(
                entry=_gatekit.relative_to_root(compat_path, root),
                rule="G29-04",
                detail=f"取行失败：{exc}",
                fix="让 COMPAT.md 具备「## API 兼容矩阵」章节（与 README 同构）",
            )
        ]
    for symbol in sorted(set(expected) | set(actual)):
        if symbol not in actual:
            violations.append(
                _gatekit.Violation(
                    entry=f"COMPAT.md · 符号 {symbol}",
                    rule="G29-04",
                    detail="COMPAT.md 缺少该符号的兼容矩阵行",
                    fix="补齐该行（README 的兼容矩阵是已入库的权威）",
                )
            )
        elif symbol not in expected:
            violations.append(
                _gatekit.Violation(
                    entry=f"COMPAT.md · 符号 {symbol}",
                    rule="G29-04",
                    detail="COMPAT.md 出现了 README 兼容矩阵里没有的符号",
                    fix="删除该行或先在 README 的兼容矩阵中登记该符号",
                )
            )
        elif expected[symbol] != actual[symbol]:
            violations.append(
                _gatekit.Violation(
                    entry=f"COMPAT.md · 符号 {symbol}",
                    rule="G29-04",
                    detail=(
                        f"单元格不一致：README = {expected[symbol]} · "
                        f"COMPAT.md = {actual[symbol]}"
                    ),
                    fix="让 COMPAT.md 与 README 的兼容矩阵逐格一致",
                )
            )
    return violations


def _load_facade_gate_support(root: Path) -> object | None:
    """按需 import 既有门禁的判据来源（``tests/facade/_gatesupport.py``）。"""
    facade_dir = root / "tests" / "facade"
    if not facade_dir.is_dir():
        facade_dir = REPO_ROOT / "tests" / "facade"
    path = str(facade_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
    try:
        import _gatesupport  # noqa: PLC0415 —— 按需加载（避免硬依赖）
    except ImportError:
        return None
    return _gatesupport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（与 --baseline 组合使用；默认：仓库根）",
    )
    parser.add_argument(
        "--baseline",
        default="HEAD",
        help="只读基准的来源（git show <ref>:harness/demo/target.py；默认：HEAD）",
    )
    parser.add_argument(
        "--check-compat",
        action="store_true",
        help="兼容矩阵分层报告（COMPAT.md 不存在 ⇒ 报告「未落地」且退出码 0）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.check_compat:
        return _gatekit.run_gate(
            lambda: check_compat(root), GATE_ID, "兼容矩阵分层报告"
        )
    violations = evaluate(root, args.baseline)
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
