# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **时间助手** —— 属 **B18F1**（内部模块）。

提供 UTC ISO-8601（9 位小数）与严格正耗时保证；只依赖标准库。
L2 的 ``runtime/_span_hook.py`` 保留一份等价实现（层隔离 · 不跨层 import）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

__all__: list[str] = []

_ISO_NS_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(?P<frac>\d{9})\+00:00$"
)


def iso_from_ns(ns: int) -> str:
    """把 Unix 纳秒转成 ``YYYY-MM-DDTHH:MM:SS.<9 digits>+00:00``。"""
    seconds, fraction = divmod(ns, 1_000_000_000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{fraction:09d}+00:00"


def parse_iso_ns(text: str) -> int | None:
    """解析本模块产出的 ISO 纳秒字符串；无法解析 ⇒ ``None``。"""
    match = _ISO_NS_RE.match(text)
    if match is None:
        return None
    base = datetime.strptime(
        match.group("base"), "%Y-%m-%dT%H:%M:%S"
    ).replace(tzinfo=timezone.utc)
    return int(base.timestamp()) * 1_000_000_000 + int(match.group("frac"))


def utc_now_iso_ns() -> tuple[str, int]:
    """返回 ``(iso_text, ns)``（标准库时钟 · UTC · 9 位小数）。"""
    ns = time.time_ns()
    return iso_from_ns(ns), ns


def end_iso_after(start_iso: str) -> tuple[str, int]:
    """返回严格大于 ``start_iso`` 的结束时刻（相等时 +1ns）。"""
    end_iso, end_ns = utc_now_iso_ns()
    start_ns = parse_iso_ns(start_iso)
    if start_ns is not None and end_ns <= start_ns:
        end_ns = start_ns + 1
        end_iso = iso_from_ns(end_ns)
    return end_iso, end_ns
