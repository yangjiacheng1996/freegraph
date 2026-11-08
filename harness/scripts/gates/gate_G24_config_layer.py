# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G24** · 配置层（``LANGSMITH_*`` / ``LANGCHAIN_*`` 零读取 + 内核零环境变量）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G24）：

1. ``freegraph`` 包内 MUST NOT 出现对 ``LANGSMITH_*`` / ``LANGCHAIN_*`` /
   ``LANGGRAPH_CLOUD_LICENSE_KEY`` / ``LANGGRAPH_AUTH*`` 的**读取**；
2. ``freegraph`` **内核**（``src/freegraph/**``）MUST NOT 读取**任何**环境变量。

**扫描域 MUST 限于 ``src/freegraph/**``**（MUST NOT 扫门禁脚本 / 测试夹具 /
CI 配置 —— 否则门禁会**把自己判红**）。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>`` —— 被检的树根。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G24"
RULE_TEXT = "配置层（LANGSMITH_* / LANGCHAIN_* / LANGGRAPH_* 零读取 + 内核零环境变量）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 扫描域（**必须**显式声明 —— MUST NOT 默认全仓）。
SCAN_SUBPATH = "src/freegraph"


def _is_config_layer(identifier: str) -> bool:
    """该读取是否命中**配置层黑名单**（宪法「配置层黑名单」）。"""
    upper = identifier.upper()
    for prefix in _gatekit.CONFIG_LAYER_PREFIXES:
        if prefix.upper() in upper:
            return True
    for exact in _gatekit.CONFIG_LAYER_EXACT:
        if exact.upper() in upper:
            return True
    for prefix in _gatekit.CONFIG_LAYER_PREFIXES_EXTRA:
        if prefix.upper() in upper:
            return True
    return False


def evaluate(root: Path) -> list[_gatekit.Violation]:
    """判定被检树内核的配置层 / 环境变量读取 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    package_dir = root / SCAN_SUBPATH
    for path in _gatekit.iter_python_files(package_dir):
        rel = _gatekit.relative_to_root(path, root)
        for lineno, identifier in _gatekit.scan_env_reads(path):
            if _is_config_layer(identifier):
                violations.append(
                    _gatekit.Violation(
                        entry=f"{rel}:{lineno}",
                        rule="G24-01",
                        detail=f"配置层黑名单的环境变量读取：{identifier}",
                        fix=(
                            "移除该读取——provider key 由 freechain / 用户代码自行传入"
                            "（宪法原则 I · 配置层黑名单）"
                        ),
                    )
                )
            else:
                violations.append(
                    _gatekit.Violation(
                        entry=f"{rel}:{lineno}",
                        rule="G24-02",
                        detail=f"内核读取了环境变量：{identifier}",
                        fix=(
                            "移除该读取——freegraph 内核 MUST NOT 读取任何环境变量"
                            "（宪法「配置层黑名单」条）"
                        ),
                    )
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（扫描域：<root>/src/freegraph/**；默认：仓库根）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    violations = evaluate(root)
    print(f"[{GATE_ID}] 扫描域 = {SCAN_SUBPATH}/**（内核零环境变量读取）")
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
