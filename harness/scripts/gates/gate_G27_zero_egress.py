# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G27** · 零出站动态断言（**只观测不阻断** + 第一个非标准库帧归因）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G27）：

1. **只包装** ``socket.connect`` 与 ``socket.create_connection`` ⇒ **记录**目标与
   调用栈、**放行**全部连接（FR-009 ② · 裁定 7）；
2. 每次连接按**第一个非标准库帧**规则归因（裁定 19 · research D-11）：
   从栈顶向下**跳过全部标准库帧**，遇到的**第一个非标准库帧**在 ``freegraph/``
   内 ⇒「框架出站」；否则 ⇒「用户出站」；
3. 断言**「框架出站」条目数 == 0**；「用户出站」**记录在案但不判失败**。

**两个入口 · 同一实现** —— 归因函数与 socket 包装 MUST 落在
``harness/scripts/gates/_gatekit.py``（纯函数 / 上下文管理器）⇒
① 本脚本作为**独立可执行入口**调用它（FR-016「退出码即判定」· CI 可逐条调用）；
② pytest 夹具调用**同一实现** ⇒ MUST NOT 各写一份归因逻辑。

**独立入口的观测面（MUST 声明）**：本入口的观测面 = **在 egress 监测下跑整个
测试套件**（``pytest tests/``，夹具全程监测 · 裁定 7）⇒ 输出 MUST 同时打印
「**当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）**」
⇒ MUST NOT 让「空断言 / 极窄观测面」被误读为「零出站已被证明」。

**SC-006 的双向可验证**（注入一次用户出站 ⇒ 归因为「用户出站」）由 **pytest
夹具路径**承担（`tests/gates/test_gates.py`）⇒ 本入口**不**承担该反向验证。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G27"
RULE_TEXT = "零出站动态断言（只观测不阻断 + 第一个非标准库帧归因）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 观测面声明（**MUST 原样打印** · 裁定 7 · spec SC-006 ①）。
OBSERVATION_SCOPE = (
    "当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（测试套件的执行根；默认：仓库根）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    return _gatekit.run_gate(lambda: _run(root), GATE_ID, RULE_TEXT)


def _run(root: Path) -> int:
    """在 **egress 监测**下跑**整个测试套件** ⇒ 判定「框架出站」== 0。"""
    import pytest

    records: list[_gatekit.EgressRecord] = []
    print(f"[{GATE_ID}] {OBSERVATION_SCOPE}")
    print(f"[{GATE_ID}] 开始：在 egress 监测下跑整个测试套件（pytest tests/）")
    with _gatekit.record_egress(records):
        exit_code = int(pytest.main([str(root / "tests"), "-ra"]))
    framework = [record for record in records if record.attribution == "framework"]
    user = [record for record in records if record.attribution == "user"]
    print(
        f"[{GATE_ID}] 框架出站 = {len(framework)} · "
        f"用户出站 = {len(user)}（记录在案，不判失败）"
    )
    for record in framework:
        top = record.frames[0] if record.frames else None
        print(
            f"  框架出站: {record.target}"
            f"（最近一帧：{top.module if top else '?'}）"
        )
    violations: list[_gatekit.Violation] = []
    for record in framework:
        violations.append(
            _gatekit.Violation(
                entry=record.target,
                rule="G27-01",
                detail=(
                    "框架出站 —— 第一个非标准库帧在 freegraph 包内："
                    + " ← ".join(
                        f"{frame.module} ({frame.path})" for frame in record.frames[:5]
                    )
                ),
                fix=(
                    "移除该出站——freegraph 内核 MUST 零出站（宪法原则 I · 网络层黑名单）"
                ),
            )
        )
    if exit_code != 0:
        violations.append(
            _gatekit.Violation(
                entry="pytest tests/",
                rule="G27-02",
                detail=f"监测下的测试套件退出码 = {exit_code}",
                fix="先修好测试套件（CI 步骤 6 是它的主判定）",
            )
        )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
