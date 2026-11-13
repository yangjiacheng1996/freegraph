# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**单调时钟的分辨率**的守卫 —— 属 **B7F4**（CI 修复的**防回归**装置）。

为什么需要这个文件
------------------
``tests/runtime/test_superstep_concurrency.py`` 的
``test_two_nodes_in_one_round_really_overlap_in_parallel`` 是一条**时序测量**
断言（**两个节点的执行时间窗 MUST 重叠** ⇒ ``overlap > 0``）⇒ ⇒ 它测量的是一段
**亚毫秒**的区间。

⚠️ **Windows + CPython < 3.13** 的 ``time.monotonic()`` 走 ``GetTickCount64()``
⇒ 粒度 ≈ **15.6ms**（**CPython 3.13 起**改用 ``QueryPerformanceCounter()``
⇒ 粒度 ≈ **1µs** · 官方 What's New in 3.13 的 ``time`` 段 · gh-88494）⇒ ⇒
那段**亚毫秒**区间会被**量化到同一 tick** ⇒ ⇒ ``overlap`` 算出 **0** ⇒ ⇒ **假红**
（语义上两个节点**确实**并行 —— 屏障**确实**被放行）。

⇒ 根因是**测量精度**，**不是**被测行为 ⇒ ⇒ 修法是「**只修测量 · 不动断言**」
⇒ ⇒ `tests/conftest.py` 的 `_fine_grained_monotonic_clock` 夹具在 Windows 上把
``time.monotonic`` 换成 ``time.perf_counter``（**恒为 QPC**）⇒ ⇒ **与 CPython
3.13+ 的口径一致** ⇒ ⇒ **冻结断言文件零改动**。

⚠️ **为什么还要本守卫**：CI 的 **windows-3.11** 档是那条断言的**唯一**探测器
⇒ ⇒ 而它**本身**是**时序敏感**的 ⇒ ⇒ 「探测器」可能**假绿** ⇒ ⇒ 本守卫把
「**时钟够细**」变成一条**确定性**判据 ⇒ ⇒ 夹具一旦被移除 ⇒ ⇒ **本守卫立刻红**
（而**不是**等到某次运气不好的时序）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import sys
import time

import pytest

#: 判定「够细」的**阈值**（**1ms**）—— ⚠️ CPython < 3.13 的 Windows 刻度
#: ≈ **15.6ms** ⇒ 必过不了 ⇒ ⇒ 该阈值能**确定性地**区分两种刻度。
_FINE_RESOLUTION_SECONDS = 0.001

#: 取样次数（**够密** ⇒ 相邻样本**至少**有一次跨过亚毫秒边界）。
_SAMPLE_COUNT = 64


def test_the_monotonic_clock_is_fine_grained_enough_for_timing_assertions() -> None:
    """Windows 档：``time.monotonic`` 的**分辨率** MUST **够细**（≤ **1ms**）。

    ⚠️ 判据 = 「**存在**一对相邻样本，其差值**非零且小于 1ms**」⇒ ⇒

    * **QPC 口径**（CPython 3.13+ / 本仓的 Windows 夹具）⇒ 相邻差值是**微秒**级
      ⇒ ⇒ **命中** ⇒ ✅；
    * ``GetTickCount64`` 口径（CPython < 3.13 的原生 Windows）⇒ 相邻差值要么
      **恰为 0**（同一 tick）要么 **≥ 15.6ms**（跨 tick）⇒ ⇒ **永不**落在
      ``(0, 1ms)`` ⇒ ⇒ **不命中** ⇒ ❌（⇒ 夹具被移除 ⇒ 本守卫**立刻红**）。
    """
    if sys.platform != "win32":
        pytest.skip("仅 Windows 档需要（其余平台恒为高精度时钟）")

    ticks = [time.monotonic() for _ in range(_SAMPLE_COUNT)]
    deltas = [b - a for a, b in zip(ticks, ticks[1:])]
    fine = [delta for delta in deltas if 0 < delta < _FINE_RESOLUTION_SECONDS]

    assert fine, (
        "time.monotonic 的分辨率过粗（相邻样本的差值既不非零、也不小于 1ms）"
        "⇒ ⇒ Windows 上大概率是 GetTickCount64 口径（15.6ms）"
        "⇒ ⇒ tests/conftest.py 的 _fine_grained_monotonic_clock 夹具未生效"
        "⇒ ⇒ 「执行时间窗重叠」类断言会**假红**"
    )
