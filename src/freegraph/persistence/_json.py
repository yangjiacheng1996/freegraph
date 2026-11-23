# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L4 持久化层 · **纯数据 JSON 编解码** —— 属 **B15F1**（内部模块）。

`SqliteSaver` 用标准库 ``json`` 持久化 checkpoint 载荷；本模块集中处理
「纯数据 ⇒ JSON 字符串 ⇒ 纯数据 / L1 对象」的**唯一**转换点：

* ``values`` / ``metadata`` 的普通键 ⇒ 标准 JSON（tuple 往返为 list · X-05）；
* **冻结字段** ``next`` / ``tasks`` / ``interrupts`` ⇒ 读回重建 tuple / 对象；
* ``PregelTask`` / ``Interrupt`` ⇒ JSON 安全投影；
* pending write 的 ``__interrupt__`` 通道 ⇒ **channel-aware** 投影
  （``Interrupt → {"value", "id"}``），其余通道仍按纯 JSON。

**原子性**：所有编码在**任何 SQL 写入之前**完成 ⇒ 不可序列化 ⇒ ``TypeError``
且该次调用**零写入**。

**依赖纪律**（L4）：只依赖 L1 ``freegraph.contracts`` + 标准库；零第三方、零 env、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from freegraph.contracts.types import Interrupt, PregelTask

__all__: list[str] = []

#: 需要 channel-aware 编码的保留通道名（与 B14F1 冻结口径逐字一致）。
_INTERRUPT_CHANNEL = "__interrupt__"


def _reject_default(obj: Any) -> Any:
    """``json.dumps(default=...)`` —— 不可序列化 ⇒ ``TypeError``。"""
    raise TypeError(
        "payload is not JSON serializable: "
        f"{type(obj).__name__} is not a pure-data value"
    )


def dumps(obj: Any) -> str:
    """把**纯数据**编码为 JSON 字符串（不可序列化 ⇒ ``TypeError``）。"""
    return json.dumps(obj, ensure_ascii=False, default=_reject_default)


def encode_interrupt(interrupt: Interrupt) -> dict[str, Any]:
    """``Interrupt`` ⇒ ``{"value", "id"}``（JSON 安全投影）。"""
    if not isinstance(interrupt, Interrupt):
        raise TypeError(
            f"__interrupt__ payload must be Interrupt, got {type(interrupt).__name__}"
        )
    return {"value": interrupt.value, "id": interrupt.id}


def decode_interrupt(data: Mapping[str, Any]) -> Interrupt:
    """``{"value", "id"}`` ⇒ ``Interrupt``。"""
    if not isinstance(data, Mapping):
        raise TypeError("interrupt payload must be a mapping")
    return Interrupt(value=data.get("value"), id=str(data.get("id", "")))


def _normalize_interrupts(value: Any) -> tuple[Interrupt, ...]:
    """把 ``Interrupt`` / ``Interrupt`` 序列归一为 ``tuple[Interrupt, ...]``。"""
    if isinstance(value, Interrupt):
        return (value,)
    if isinstance(value, (tuple, list)):
        items = tuple(value)
    else:
        raise TypeError(
            "__interrupt__ payload must be an Interrupt or a sequence of Interrupt"
        )
    for item in items:
        if not isinstance(item, Interrupt):
            raise TypeError(
                "__interrupt__ payload must contain only Interrupt objects, "
                f"got {type(item).__name__}"
            )
    return items


def encode_task(task: PregelTask) -> dict[str, Any]:
    """``PregelTask`` ⇒ JSON 安全投影。

    v1 持久化快照**不含**异常对象 / 子图状态 ⇒ ``error`` 与 ``state`` MUST 为
    ``None``（否则 ``TypeError``）；``result`` MUST 可 JSON 序列化。
    """
    if not isinstance(task, PregelTask):
        raise TypeError(
            f"tasks must contain PregelTask, got {type(task).__name__}"
        )
    if task.error is not None:
        raise TypeError("PregelTask.error must be None for a persisted snapshot")
    if task.state is not None:
        raise TypeError("PregelTask.state must be None for a persisted snapshot")
    return {
        "id": task.id,
        "name": task.name,
        "path": list(task.path),
        "interrupts": [encode_interrupt(item) for item in task.interrupts],
        "result": task.result,
    }


def decode_task(data: Mapping[str, Any]) -> PregelTask:
    """JSON 投影 ⇒ ``PregelTask``（``path`` / ``interrupts`` 重建为 tuple）。"""
    if not isinstance(data, Mapping):
        raise TypeError("task payload must be a mapping")
    raw_path = data.get("path") or []
    interrupts = tuple(
        decode_interrupt(item) for item in (data.get("interrupts") or [])
    )
    return PregelTask(
        id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        path=tuple(raw_path),
        error=None,
        interrupts=interrupts,
        state=None,
        result=data.get("result"),
    )


def encode_metadata(metadata: Mapping[str, Any]) -> str:
    """把 ``put`` 的 ``metadata`` 编码为 JSON（冻结字段按对象投影）。"""
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a Mapping")
    projected: dict[str, Any] = dict(metadata)
    if "next" in projected:
        projected["next"] = list(projected["next"] or ())
    if "interrupts" in projected:
        projected["interrupts"] = [
            encode_interrupt(item)
            for item in _normalize_interrupts(projected["interrupts"])
        ]
    if "tasks" in projected:
        projected["tasks"] = [
            encode_task(item) for item in (projected["tasks"] or ())
        ]
    return dumps(projected)


def decode_metadata(raw: str) -> dict[str, Any]:
    """JSON 字符串 ⇒ ``metadata`` 字典（``next`` / ``tasks`` / ``interrupts`` 重建）。"""
    data = json.loads(raw)
    if not isinstance(data, Mapping):
        raise TypeError("decoded metadata must be a JSON object")
    result: dict[str, Any] = dict(data)
    if "next" in result:
        result["next"] = tuple(result["next"] or ())
    if "interrupts" in result:
        result["interrupts"] = tuple(
            decode_interrupt(item) for item in (result["interrupts"] or ())
        )
    if "tasks" in result:
        result["tasks"] = tuple(
            decode_task(item) for item in (result["tasks"] or ())
        )
    return result


def encode_values(values: Mapping[str, Any]) -> str:
    """把 ``values`` 编码为 JSON（标准 JSON 语义 · tuple → list）。"""
    if not isinstance(values, Mapping):
        raise TypeError("values must be a Mapping")
    return dumps(dict(values))


def decode_values(raw: str) -> dict[str, Any]:
    """JSON 字符串 ⇒ ``values`` 字典。"""
    data = json.loads(raw)
    if not isinstance(data, Mapping):
        raise TypeError("decoded values must be a JSON object")
    return dict(data)


def encode_write_value(channel: str, value: Any) -> str:
    """编码一条 pending write 的 ``value``（``__interrupt__`` 走 channel-aware）。"""
    if channel == _INTERRUPT_CHANNEL:
        items = _normalize_interrupts(value)
        return dumps([encode_interrupt(item) for item in items])
    return dumps(value)


def decode_write_value(channel: str, raw: str) -> Any:
    """解码一条 pending write 的 ``value``（``__interrupt__`` 重建为 tuple）。"""
    data = json.loads(raw)
    if channel == _INTERRUPT_CHANNEL:
        return tuple(decode_interrupt(item) for item in (data or []))
    return data
