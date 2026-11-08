# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G26** · 网络静态扫描（``src/freegraph/**`` 无网络客户端调用）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G26）：
MUST NOT 出现下列网络客户端的 import 或使用 ——

``socket`` · ``ssl`` · ``http`` · ``http.client`` · ``urllib.request`` ·
``urllib3`` · ``requests`` · ``httpx`` · ``aiohttp`` · ``websockets`` ·
``ftplib`` · ``smtplib`` · ``telnetlib`` · ``xmlrpc`` · ``asyncio.open_connection``

**判定口径**：本扫描 MUST 以 **import 形式**判定 ⇒ 清单内的**纯 stdlib 常量
用法**（如 ``http.HTTPStatus`` 这类不含任何网络行为的常量）会被**一并命中**
⇒ 这类形态需**具名例外**才可通过；MUST NOT 因此放宽清单本身。

**唯一例外**（FR-009 ① · FR-018 ① 的「已写死的、具名例外」）：**可选的 OTLP
exporter 模块** —— 例外 MUST 以**显式名单**表达，MUST NOT 放宽扫描域本身。
**当前该例外名单为空**（OTLP exporter 属 B21F1）。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>`` —— 被检的树根。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G26"
RULE_TEXT = "网络静态扫描（src/freegraph/** 无网络客户端调用）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 扫描域（**必须**显式声明 —— MUST NOT 默认全仓）。
SCAN_SUBPATH = "src/freegraph"


def evaluate(root: Path) -> list[_gatekit.Violation]:
    """判定被检树内核的网络客户端调用 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    package_dir = root / SCAN_SUBPATH
    for path in _gatekit.iter_python_files(package_dir):
        rel = _gatekit.relative_to_root(path, root)
        for lineno, module in _gatekit.scan_network_calls(path):
            if module in _gatekit.G26_EXCEPTED_MODULES:
                continue
            violations.append(
                _gatekit.Violation(
                    entry=f"{rel}:{lineno}",
                    rule="G26-01",
                    detail=f"内核引入了网络客户端：{module}",
                    fix=(
                        "移除该导入 / 调用——freegraph 内核 MUST 零出站"
                        "（宪法原则 I · 网络层黑名单）；"
                        "合法的只有**具名例外**（当前例外名单为空 · OTLP exporter 归 B21F1）"
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
    print(
        f"[{GATE_ID}] 扫描域 = {SCAN_SUBPATH}/**"
        f"（具名例外名单：{list(_gatekit.G26_EXCEPTED_MODULES) or '空'}）"
    )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
