#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""内容丢失检查：比对工作区与基准提交，报告**净删除**的文件。

为什么需要它
------------
本仓库的改动大量是**批量替换**（术语统一 / ID 改名 / 门禁计数同步）。
批量替换的风险有二：

1. **正则边界漏洞** —— ``\\b`` 在中文与下划线边界不成立
   （``Phase拆解`` / ``F3P1_文件名.md``），导致漏改；
2. **误伤** —— 替换命中了本不该命中的内容
   （speckit 模板派生文本、真实文件名、vendored 清单的键与哈希），
   **静默丢失既有内容**。

本脚本把第 2 类风险变成**可自动判定**的：任何文件的**净删除行数 > 0**
都会被列出来，供人工确认。它**不做判断**（删除可能是有意的），
只负责**把可疑的删除摆到眼前**。

用法
----
::

    python harness/scripts/check_content_loss.py            # 基准 = HEAD
    python harness/scripts/check_content_loss.py 3d89102    # 基准 = 指定提交
    python harness/scripts/check_content_loss.py --exit-zero

退出码：0 = 无净删除；1 = 有净删除（需人工确认）；2 = 用法/环境错误。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# 与「依赖闭包」门禁同源：纯标准库，零第三方依赖。
SKIP_DIRS = {".git", "docs", "node_modules", "__pycache__", ".opencode", "dist"}


def _run(*args: str) -> str:
    result = subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(2)
    return result.stdout


def _numstat(base: str) -> list[tuple[int, int, str]]:
    """返回 (新增行, 删除行, 文件路径)。"""
    out = _run(
        "git", "diff", "--numstat", base, "--", "."
    )
    rows: list[tuple[int, int, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        if not added.isdigit() or not deleted.isdigit():
            continue  # 二进制文件
        rows.append((int(added), int(deleted), path))
    return rows


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    base = args[0] if args else "HEAD"
    _run("git", "rev-parse", "--verify", f"{base}^{{commit}}")

    rows = _numstat(base)
    suspects = [(d - a, p) for a, d, p in rows if d - a > 0]
    suspects.sort(reverse=True)

    if not suspects:
        print(f"[内容丢失检查] ✅ 相对 {base} 无任何文件的净删除行。")
        print(f"[内容丢失检查]    共比对 {len(rows)} 个有差异的文件。")
        return 0

    print(f"[内容丢失检查] ⚠️ 相对 {base} 有 {len(suspects)} 个文件存在**净删除**，")
    print("[内容丢失检查]    逐条确认是「有意删除」还是「批量替换误伤」：")
    for net, path in suspects:
        print(f"    净删 {net:>4} 行  {path}")
    print("[内容丢失检查]    确认无误可忽略；若有误伤，用 `git checkout <基准> -- <文件>` 恢复。")
    return 0 if "--exit-zero" in argv else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
