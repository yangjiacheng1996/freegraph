# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G28** · 断网等价性（**Linux 专属** · 全量测试套件 + 可机读排除清单）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G28）：

1. 在**网络命名空间**中执行（``unshare --net --map-root-user``）⇒ 全部网络接口
   不可用（含回环 · FR-010）；
2. 重跑**核心用例** = **全量测试套件**（``tests/``），**扣除**排除清单中的条目；
3. 排除清单 = ``tests/gates/data/offline_exclusions.txt``（**可机读** · **逐条
   理由** · FR-010 ④）；排除项**仅限两类**（FR-010 ③）：
   (a) **断网任务自身**（不可嵌套）；(b) **语义上必须能建立连接**的用例
   （含 (b1) 用户出站归因 / (b2) 需联网安装的用例）；
4. 断言**通过率 == 100%**（SC-004）；
5. **排除清单的自校验（MUST）** —— 清单中的每一条用例标识 MUST **实际存在且
   确实被排除**：① 先收集本次运行的测试 node ID 全集；② 逐条比对清单里的每个
   标识：不存在 ⇒ **判失败并指名该条**（清单漂移）；存在 ⇒ 确认它**未出现在**
   实际执行的测试集中。
   > **为什么必须加这条**：实测 pytest 7.4.4 与 9.2.0 对「指向**不存在** node id
   > 的 ``--deselect``」**均不报错**（静默忽略 · 退出码 0）⇒ 清单与用例名一旦
   > 漂移，排除会**静默失效** ⇒ 被排除的用例在断网下**假红**（原因被误判为
   > 「断网等价性失败」）⇒ 本条把「清单漂移」变成**指名报错**。

**命名空间的归属**：**本脚本 MUST NOT** 调用 ``unshare`` / MUST NOT 创建网络
命名空间 —— 命名空间由**外层**施加（CI 步骤：
``unshare --net --map-root-user uv run … gate_G28_offline_equiv.py``）⇒ 本脚本在
**已断网**的环境内只负责：读清单 → 逐条转 ``--deselect`` → 跑 ``pytest tests/``
→ 断言通过率 == 100%。

**CLI 契约**：``--root <路径>``（被检的树根）· ``--exclusions <路径>``
（排除清单；默认 ``tests/gates/data/offline_exclusions.txt``）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G28"
RULE_TEXT = "断网等价性（Linux 网络命名空间 · 全量测试套件 + 可机读排除清单）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 排除清单的默认位置（**单文件** · 唯一权威）。
DEFAULT_EXCLUSIONS = "tests/gates/data/offline_exclusions.txt"

#: pytest 收集输出的 node ID 形态（``tests/gates/test_gates.py::test_x``）。
NODE_ID_PATTERN = re.compile(r"^(tests/\S+?\.py)::\S+")


def read_exclusions(path: Path) -> list[tuple[str, str]]:
    """读排除清单 ⇒ ``[(用例标识, 排除理由), ...]``。

    清单的每行格式 = ``用例标识 :: 排除理由`` ⇒ 分隔符是**带空格**的
    ``" :: "`` —— **MUST NOT** 用 ``"::"`` 切分（用例标识**本身**就含 ``::``
    —— pytest node ID 的形态）⇒ 否则会把 ``tests/.../test_gates.py`` 当成
    用例标识 ⇒ ``--deselect`` 变成**整文件**排除 ⇒ 排除范围被静默放大。
    """
    entries: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " :: " not in line:
            raise ValueError(
                f"排除清单的行格式 MUST 是「用例标识 :: 排除理由」：{raw!r}"
            )
        node_id, _, reason = line.partition(" :: ")
        entries.append((node_id.strip(), reason.strip()))
    return entries


def _collect_node_ids(root: Path, extra: list[str]) -> tuple[list[str], int]:
    """收集 pytest 的 node ID 全集 ⇒ ``(node ID 列表, 退出码)``。"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(root / "tests"),
        "--collect-only",
        "-q",
        *extra,
    ]
    proc = subprocess.run(
        command, cwd=str(root), capture_output=True, text=True, timeout=600, check=False
    )
    node_ids = [
        line.strip()
        for line in proc.stdout.splitlines()
        if NODE_ID_PATTERN.match(line.strip())
    ]
    return node_ids, proc.returncode


def _run_suite(root: Path, deselect: list[str]) -> tuple[int, str]:
    """跑全量测试套件（逐条 ``--deselect``）⇒ ``(退出码, 输出)``。"""
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(root / "tests"),
        "-ra",
        *deselect,
    ]
    proc = subprocess.run(
        command, cwd=str(root), capture_output=True, text=True, timeout=3600, check=False
    )
    return proc.returncode, proc.stdout + proc.stderr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（默认：仓库根）",
    )
    parser.add_argument(
        "--exclusions",
        default=str(REPO_ROOT / DEFAULT_EXCLUSIONS),
        help="断网排除清单（单文件 · 唯一权威）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    exclusions_path = Path(args.exclusions)
    return _gatekit.run_gate(
        lambda: _run(root, exclusions_path), GATE_ID, RULE_TEXT
    )


def _run(root: Path, exclusions_path: Path) -> int:
    violations: list[_gatekit.Violation] = []
    if not exclusions_path.is_file():
        return _gatekit.report(
            [
                _gatekit.Violation(
                    entry=_gatekit.relative_to_root(exclusions_path, root),
                    rule="G28-01",
                    detail="断网排除清单不存在",
                    fix="补上排除清单（单文件 · 逐条带理由 · FR-010 ④）",
                )
            ],
            GATE_ID,
            RULE_TEXT,
        )
    entries = read_exclusions(exclusions_path)
    deselect: list[str] = []
    for node_id, reason in entries:
        if not reason:
            violations.append(
                _gatekit.Violation(
                    entry=node_id,
                    rule="G28-02",
                    detail="排除项没有理由（排除项无理由者 == 0 · SC-004）",
                    fix="写明排除理由（仅限两类：断网任务自身 / 语义上必须能建立连接）",
                )
            )
        deselect.extend(["--deselect", node_id])
    all_ids, collect_code = _collect_node_ids(root, [])
    selected_ids, _ = _collect_node_ids(root, deselect)
    if collect_code != 0:
        violations.append(
            _gatekit.Violation(
                entry="pytest --collect-only",
                rule="G28-03",
                detail=f"收集测试 node ID 失败（退出码 {collect_code}）",
                fix="先修好测试套件的收集",
            )
        )
    for node_id, _reason in entries:
        if node_id not in all_ids:
            violations.append(
                _gatekit.Violation(
                    entry=node_id,
                    rule="G28-04",
                    detail=(
                        "清单漂移 —— 该用例标识不存在于实际收集到的 node ID 全集"
                        "（pytest 对不存在的 --deselect 静默忽略 ⇒ 排除会静默失效）"
                    ),
                    fix=(
                        "让排除清单与用例名**逐字一致**"
                        "（用例标识 MUST 用 pytest node ID · contracts/ci-matrix.md §3.2）"
                    ),
                )
            )
        elif node_id in selected_ids:
            violations.append(
                _gatekit.Violation(
                    entry=node_id,
                    rule="G28-04",
                    detail="该用例未被真正排除（仍出现在实际执行的测试集中）",
                    fix="检查 --deselect 的施加方式（逐条转成参数）",
                )
            )
    print(
        f"[{GATE_ID}] 排除项 = {len(entries)} 条（逐条有理由）· "
        f"实际执行 = {len(selected_ids)} / 收集到 {len(all_ids)}"
    )
    exit_code, output = _run_suite(root, deselect)
    summary = [
        line for line in output.splitlines() if " passed" in line or " failed" in line
    ]
    for line in summary[-3:]:
        print(f"[{GATE_ID}] {line.strip()}")
    if exit_code != 0:
        violations.append(
            _gatekit.Violation(
                entry="pytest tests/（断网）",
                rule="G28-05",
                detail=(
                    f"断网下的测试套件退出码 = {exit_code} —— 通过率 < 100%"
                    f"（{summary[-1].strip() if summary else '无汇总行'}）"
                ),
                fix=(
                    "按**判据**决定是否进排除清单（逐条写理由）——"
                    "MUST NOT 随手跳过（FR-010 ⑤）"
                ),
            )
        )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
