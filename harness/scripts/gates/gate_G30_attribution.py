# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G30** · 全仓署名头（覆盖率 == 100%）**+ 第三方品牌资产**（FR-021）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G30）：

1. 取仓库内**全部受版本控制的 ``.py`` 文件**（``git ls-files '*.py'``）
   —— 即 ``src/`` + ``tests/`` + ``harness/`` **三个目录**，**无例外目录**；
2. 每个文件 MUST 在**顶部**含署名声明，**逐字**等于::

       # Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

3. **两个具名例外**：``py.typed``（PEP 561 要求为空）· ``harness/demo/target.py``
   （只读基准 · 宪法原则 III）；
4. 带 shebang 的脚本：署名头 MUST 在 shebang **之后**；模块 docstring MUST 仍是
   **首个语句**（FR-013 ②）；
5. 缺失的文件 MUST 被**逐个指名**（含路径）⇒ MUST NOT 只报总数（FR-013 ③）；
6. **第三方品牌资产断言**（宪法原则 IX 第三条 · spec FR-021 / SC-016）：
   断言仓库内**无第三方品牌资产** —— **图像资产** / **品牌色定义** /
   官方 **"Approved copy"** 描述文案 三类扫描域。
   **白名单口径**（FR-021 ②）= **禁止第三方品牌资产**；**自有资产** MUST 登记在
   已具名的「自有品牌资产白名单」中 ⇒ **MUST NOT** 采用「白名单为空 ⇒ 禁止一切
   图像」的过宽口径。**与既有 G8 的分工**（FR-021 ③）：原则 IX 第三条第 ③ 项
   （README / 文档 MUST 声明「独立实现、非 LangChain Inc. 产品」）**已由既有 G8
   覆盖** ⇒ 本门禁 **MUST NOT** 重复实现该条。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>`` —— 被检的树根。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G30"
RULE_TEXT = "全仓署名头（覆盖率 == 100%）+ 第三方品牌资产（FR-021）"

REPO_ROOT = Path(__file__).resolve().parents[3]


def evaluate(root: Path) -> list[_gatekit.Violation]:
    """判定全仓署名头与第三方品牌资产 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    files = _gatekit.list_tracked_files(root)
    for path in files:
        if path.suffix != ".py":
            continue
        rel = _gatekit.relative_to_root(path, root)
        if rel in _gatekit.G30_EXCEPTED_FILES:
            continue
        for message in _gatekit.signature_header_violations(path, rel):
            violations.append(
                _gatekit.Violation(
                    entry=message.split(":", 1)[0],
                    rule="G30-01",
                    detail=message,
                    fix=(
                        "在文件顶部加上署名头（首行；首行是 shebang 时取第二行）"
                        "——宪法原则 X · FR-013 ②"
                    ),
                )
            )
    for message in _gatekit.brand_asset_violations(root, files):
        violations.append(
            _gatekit.Violation(
                entry=message.split(":", 1)[0],
                rule="G30-02",
                detail=message,
                fix=(
                    "移除该第三方品牌资产——宪法原则 IX 第三条（商标红线 · NON-NEGOTIABLE）；"
                    "**自有**资产 MUST 登记进「自有品牌资产白名单」"
                    "（当前为空集 · FR-021 ②）"
                ),
            )
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（默认：仓库根）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    violations = evaluate(root)
    files = _gatekit.list_tracked_files(root)
    python_files = [path for path in files if path.suffix == ".py"]
    print(
        f"[{GATE_ID}] 受版本控制的 .py 文件数 = {len(python_files)}"
        f"（具名例外：{sorted(_gatekit.G30_EXCEPTED_FILES)}）"
    )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
