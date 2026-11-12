#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""**差分探针** 的**命令行入口** —— freegraph ↔ langgraph 上游的同场景对跑。

为什么需要它
------------
本仓库的权威判据是「**上游 langgraph 是唯一权威**」（见
``harness/proposals/主路线.md``）。但仓库里的 8 个
``harness/verification/*/acceptance.py`` **全部只验 freegraph 自身**的契约 ——
它们证明「freegraph 符合自己的 spec」，**不能**证明「freegraph 与上游同款」。

⇒ 于是出现了一个结构性盲区：**spec 与上游分叉了，验收脚本仍然是绿的。**
（这不是假想：B4F1 的「只接受 ``TypedDict``」、B5F2 的 fresh 视图保留路由通道、
B9F1 的「空列表 = 无操作」三处分叉，都是在 P3 回改**之前**长期保持绿色的。）

本脚本把「**同场景 · 两边跑 · 比可观察结果**」变成可重复执行的检查：

* **上游侧**：用**已安装的** ``langgraph``（``StateGraph`` · ``compile().invoke()``）
  —— 只在**开发期**使用，不进发行面；
* **freegraph 侧**：用 ``freegraph.runtime`` 的 ``GraphSpec`` / ``run_super_steps``；
* **比对三件事**：① **执行的节点序列** ② **最终状态** ③ **失败与否**
  （失败时**不比对异常类名** —— 两边本就不该同名）。

场景与判定逻辑的**唯一实现**在 ``tests/differential/parity_probe.py``
⇒ 本脚本只是它的**打印外壳** ⇒ **pytest 侧**（``tests/differential/
test_parity_probe.py``）消费**同一份**场景 ⇒ **CI 里真跑**（Linux 全量档装了
上游差分组）⇒ ⇒ **判据只有一处** ⇒ 不会出现「脚本说绿、pytest 说红」。

用法
----
    python harness/scripts/diff_parity.py            # 全跑 · 退出码 0 = 全部符合判词
    python harness/scripts/diff_parity.py -v         # 附带打印两边的原始结果
    python harness/scripts/diff_parity.py -k 命令     # 只跑名字含「命令」的场景
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "differential"))

import parity_probe  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="freegraph ↔ langgraph 上游的差分探针")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印两边的原始结果")
    parser.add_argument("-k", "--keyword", default="", help="只跑名字含该关键字的场景")
    args = parser.parse_args(argv)

    results = parity_probe.run_all(args.keyword)
    if not results:
        print("没有匹配的场景", file=sys.stderr)
        return 2

    failures = [r for r in results if not r.ok]
    width = max(len(r.name) for r in results)
    print("\n" + "=" * (width + 46))
    print(f"{'场景'.ljust(width)} | {'判词'.ljust(20)} | freegraph | 上游")
    print("-" * (width + 46))
    for r in results:
        label = {
            "SAME": "✅ 一致" if r.ok else "❌ 不一致",
            "STRICTER": "✅ 更严（已登记）" if r.ok else "❌ 不一致",
            "DIFF": "ℹ️ 已知差异",
        }[r.verdict]
        print(f"{r.name.ljust(width)} | {label.ljust(20)} | {r.freegraph_kind.ljust(10)} | {r.upstream_kind}")
        if args.verbose:
            print(f"    {r.detail}")
    print("=" * (width + 46))
    print(f"场景数 {len(results)} · 符合判词 {len(results) - len(failures)} · 失败 {len(failures)}")
    for r in failures:
        print(f"  ✘ {r.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
