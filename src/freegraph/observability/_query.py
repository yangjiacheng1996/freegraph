# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L5 可观测层 · **共享查询引擎** —— 属 **B20F2**（内部模块）。

一套语义供 JSONL 与 SQLite 两个后端共用：

* :func:`normalize_query` —— 请求类型校验（``TraceQuery`` / 5 字段 ``str | None``）；
* :func:`parse_instant_ns` —— ISO-8601 瞬时 → UTC 纳秒整数；
* :func:`normalize_row` —— 行视图校验 / 冻结字段裁剪 / 额外字段丢弃；
* :func:`finalize` —— 四类过滤（AND）+ 有效起始时刻 + 稳定排序。

本模块**纯函数、无 I/O**；不 import ``sqlite3`` / 文件 API，不读环境变量。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from freegraph.contracts.trace import TraceQuery

__all__: list[str] = [
    "finalize",
    "normalize_query",
    "normalize_row",
    "parse_instant_ns",
]

SPAN_FIELDS: tuple[str, ...] = (
    "kind",
    "id",
    "name",
    "attributes",
    "parent",
    "start_time",
    "end_time",
    "context",
    "thread_id",
    "run_id",
    "node",
    "checkpoint_id",
)

RECORD_FIELDS: tuple[str, ...] = (
    "kind",
    "span_id",
    "task_id",
    "run_id",
    "thread_id",
    "checkpoint_id",
    "node",
    "superstep",
    "triggers",
    "concurrency_group",
    "barrier_groups",
    "input_state",
    "output_state",
    "error",
)

QUERY_FIELDS: tuple[str, ...] = (
    "run_id",
    "thread_id",
    "node",
    "start_time",
    "end_time",
)

_INSTANT_RE = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<frac>\d+))?"
    r"(?P<offset>Z|z|[+-]\d{2}:?\d{2})?$"
)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def normalize_query(query: TraceQuery | None) -> TraceQuery:
    """把 ``None`` 归一为 ``TraceQuery()`` 并校验 5 字段类型；不合法 ⇒ ``TypeError``。"""
    if query is None:
        return TraceQuery()
    if not isinstance(query, TraceQuery):
        raise TypeError(f"query must be TraceQuery or None, got {type(query).__name__}")
    for name in QUERY_FIELDS:
        value = getattr(query, name)
        if value is not None and not isinstance(value, str):
            raise TypeError(f"TraceQuery.{name} must be str or None")
    return query


def parse_instant_ns(text: str) -> int:
    """把 ISO-8601 瞬时解析为 UTC **纳秒**整数；非法 ⇒ ``ValueError``。

    接受末尾 ``Z`` / ``±HH:MM`` / ``±HHMM`` / 无时区（按 UTC）；小数位不足
    9 位右侧补 ``0``，超过 9 位按纳秒精度截断（MUST NOT 截断到微秒）。
    """
    if not isinstance(text, str):
        raise TypeError("instant must be str")
    match = _INSTANT_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"invalid ISO-8601 instant: {text!r}")
    base = datetime.strptime(match.group("base"), "%Y-%m-%dT%H:%M:%S")
    offset = match.group("offset")
    if offset is None or offset in ("Z", "z"):
        tz = timezone.utc
    else:
        sign = 1 if offset[0] == "+" else -1
        body = offset[1:].replace(":", "")
        hours = int(body[:2])
        minutes = int(body[2:4])
        tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
    moment = base.replace(tzinfo=tz).astimezone(timezone.utc)
    delta = moment - _EPOCH
    seconds = delta.days * 86400 + delta.seconds
    ns = seconds * 1_000_000_000
    frac = match.group("frac")
    if frac:
        ns += int((frac + "000000000")[:9])
    return ns


def _str_or_none(value: Any) -> bool:
    return value is None or isinstance(value, str)


def _span_valid(row: dict[str, Any]) -> bool:
    if not set(SPAN_FIELDS) <= row.keys():
        return False
    return (
        isinstance(row["id"], str)
        and isinstance(row["name"], str)
        and isinstance(row["attributes"], dict)
        and _str_or_none(row["parent"])
        and isinstance(row["start_time"], str)
        and _str_or_none(row["end_time"])
        and isinstance(row["context"], dict)
        and _str_or_none(row["thread_id"])
        and isinstance(row["run_id"], str)
        and isinstance(row["node"], str)
        and _str_or_none(row["checkpoint_id"])
    )


def _record_valid(row: dict[str, Any]) -> bool:
    if not set(RECORD_FIELDS) <= row.keys():
        return False
    error = row["error"]
    if error is not None:
        if not isinstance(error, dict):
            return False
        if not isinstance(error.get("type"), str) or not isinstance(
            error.get("message"), str
        ):
            return False
    return (
        isinstance(row["span_id"], str)
        and isinstance(row["task_id"], str)
        and isinstance(row["run_id"], str)
        and _str_or_none(row["thread_id"])
        and _str_or_none(row["checkpoint_id"])
        and isinstance(row["node"], str)
        and type(row["superstep"]) is int
        and isinstance(row["triggers"], list)
        and isinstance(row["concurrency_group"], list)
        and isinstance(row["barrier_groups"], list)
    )


def normalize_row(row: Any) -> dict[str, Any] | None:
    """校验一行并**只**返回已冻结字段；未知 / 残缺 / 类型不符 ⇒ ``None``。"""
    if not isinstance(row, dict):
        return None
    kind = row.get("kind")
    if kind == "span":
        if not _span_valid(row):
            return None
        return {name: row[name] for name in SPAN_FIELDS}
    if kind == "trace_record":
        if not _record_valid(row):
            return None
        return {name: row[name] for name in RECORD_FIELDS}
    return None


def _stable_id(row: dict[str, Any]) -> str:
    if row["kind"] == "trace_record":
        return row["span_id"]
    return row["id"]


def finalize(rows: list[dict[str, Any]], query: TraceQuery | None) -> list[dict[str, Any]]:
    """对已归一化的行执行 AND 过滤、有效起始时刻时间窗与稳定排序。"""
    q = normalize_query(query)
    start_ns = parse_instant_ns(q.start_time) if q.start_time is not None else None
    end_ns = parse_instant_ns(q.end_time) if q.end_time is not None else None
    if start_ns is not None and end_ns is not None and start_ns > end_ns:
        return []

    span_start: dict[tuple[str, str], int | None] = {}
    for row in rows:
        if row["kind"] != "span":
            continue
        run_id = row["run_id"]
        span_id = row["id"]
        try:
            span_start[(run_id, span_id)] = parse_instant_ns(row["start_time"])
        except (TypeError, ValueError):
            span_start[(run_id, span_id)] = None

    filtered: list[tuple[int, dict[str, Any], int | None]] = []
    for index, row in enumerate(rows):
        if q.run_id is not None and row["run_id"] != q.run_id:
            continue
        if q.thread_id is not None and row["thread_id"] != q.thread_id:
            continue
        if q.node is not None and row["node"] != q.node:
            continue
        if row["kind"] == "span":
            moment = span_start.get((row["run_id"], row["id"]))
        else:
            moment = span_start.get((row["run_id"], row["span_id"]))
        if start_ns is not None or end_ns is not None:
            if moment is None:
                continue
            if start_ns is not None and moment < start_ns:
                continue
            if end_ns is not None and moment > end_ns:
                continue
        filtered.append((index, row, moment))

    timed: list[tuple[int, int, dict[str, Any]]] = []
    untimed: list[tuple[int, dict[str, Any]]] = []
    for index, row, moment in filtered:
        if moment is None:
            untimed.append((index, row))
        else:
            timed.append((moment, index, row))

    timed.sort(
        key=lambda item: (
            item[0],
            item[2]["run_id"],
            0 if item[2]["kind"] == "trace_record" else 1,
            _stable_id(item[2]),
        )
    )

    def _untimed_key(item: tuple[int, dict[str, Any]]) -> tuple[Any, ...]:
        row = item[1]
        if row["kind"] == "trace_record":
            return (row["run_id"], 0, row["superstep"], row["task_id"], row["span_id"])
        return (row["run_id"], 1, 0, "", row["id"])

    untimed.sort(key=_untimed_key)
    return [row for _, _, row in timed] + [row for _, row in untimed]
