# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **动态 fan-out 内部形状与校验** —— 属 **B11F1**（私有模块）。

本模块承载 ``Send`` 的**运行期语义**所需的内部形状、校验与任务构造：

* :class:`_FanOutTask` —— **一个** ``Send`` 对应的任务（目标 + 逐字入参 + 序号 + 载体标志）；
* :class:`_FanOut` —— **一个产生者任务**的 fan-out 载荷（``producer`` + tasks + 聚合载体标志）；
* :data:`TaskId` —— 本轮任务的**规范序号**（``int`` · 0 起）；
* :func:`make_fanout` / :func:`validate_send` / :func:`fanout_from_result`。

**契约权威**：``specs/b11f1-send-fanout/contracts/send-contract.md`` 与
``specs/b11f1-send-fanout/data-model.md`` §3.1 / §5。

**依赖纪律**：只依赖标准库与 L1 的 ``freegraph.contracts`` ⇒ 零第三方依赖。
**本模块私有** ⇒ 不进 ``freegraph.runtime.__all__``。
"""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from freegraph.contracts.types import Command, Send

__all__: list[str] = []

#: 本轮任务的**规范序号**（0 起 · ``int`` 字典序即 TaskId 序）。
TaskId = int

_START_MARKER = "__start__"
_END_MARKER = "__end__"
_PARENT = Command.PARENT


@dataclass(frozen=True, slots=True)
class _FanOutTask:
    """一个 fan-out 任务（**一个** ``Send`` ⇒ **一个**任务）。"""

    target: str
    arg: Any
    index: int
    suppresses_static: bool


@dataclass(frozen=True, slots=True)
class _FanOut:
    """一个**产生者任务**的 fan-out 载荷（键 = 产生者 TaskId）。"""

    producer: str
    tasks: tuple[_FanOutTask, ...]
    suppresses_static: bool


def validate_send(send: Any, node_names: Container[str], producer: str) -> None:
    """校验一个 ``Send`` 的目标（V-17…V-21）· **产生轮立即失败**。"""
    if not isinstance(send, Send):
        raise TypeError(
            f"Node {producer!r} returned a non-Send fan-out element: "
            f"{type(send).__name__} (V-15)"
        )
    node = send.node
    if not isinstance(node, str):
        raise TypeError(
            f"Send.node must be str, got {type(node).__name__} (V-17)"
        )
    if node == "":
        raise ValueError("Send.node must not be empty (V-18)")
    if node == _PARENT:
        raise NotImplementedError(
            "Send.node == Command.PARENT ('__parent__') is not supported "
            "in this version: 子图属 v2 能力（跨层传播归 C26 · v2）(V-20)"
        )
    if node in (_START_MARKER, _END_MARKER):
        raise ValueError(
            f"Send.node {node!r} is a sentinel, not a callable node (V-21)"
        )
    if node not in node_names:
        raise ValueError(
            f"节点 {producer!r} 的 Send 指向了不存在的节点 {node!r} (V-19)"
        )


def make_fanout(
    producer: str,
    sends: Iterable[Any],
    node_names: Container[str],
    *,
    suppresses_static: bool,
) -> tuple[_FanOutTask, ...]:
    """把一串 ``Send`` 归一为**逐任务的** fan-out 任务（保序 · 逐字入参）。"""
    tasks: list[_FanOutTask] = []
    for index, send in enumerate(sends):
        validate_send(send, node_names, producer)
        tasks.append(
            _FanOutTask(
                target=send.node,
                arg=send.arg,
                index=index,
                suppresses_static=suppresses_static,
            )
        )
    return tuple(tasks)


def encode_fanout(fanout: Mapping[TaskId, _FanOut]) -> dict[str, Any]:
    """把 fan-out 账本编码为**纯数据**（JSON 可序列化 · F-3）。

    外层 key = ``str(TaskId)``（JSON 对象的 key 只能是字符串）；``arg`` **原样**
    保存 ⇒ 非 JSON 兼容对象的持久化失败面归 B14F1（DR-01）。
    """
    return {
        str(producer_id): {
            "producer": payload.producer,
            "suppresses_static": payload.suppresses_static,
            "tasks": [
                {
                    "target": task.target,
                    "arg": task.arg,
                    "index": task.index,
                    "suppresses_static": task.suppresses_static,
                }
                for task in payload.tasks
            ],
        }
        for producer_id, payload in fanout.items()
    }


def decode_fanout(data: Mapping[str, Any] | None) -> dict[Any, _FanOut]:
    """还原 fan-out 账本（缺键宽容 · 外层 key 能转 ``int`` 则转）。

    防御性解码：单个载荷形状损坏 ⇒ 跳过该条，不因**旧快照 / 手工数据**阻断恢复。
    """
    restored: dict[Any, _FanOut] = {}
    for raw_key, raw in (data or {}).items():
        if not isinstance(raw, Mapping):
            continue
        try:
            producer_id: Any = int(raw_key)
        except (TypeError, ValueError):
            producer_id = raw_key
        tasks: list[_FanOutTask] = []
        for item in raw.get("tasks") or ():
            if not isinstance(item, Mapping):
                continue
            target = item.get("target")
            if not isinstance(target, str):
                continue
            tasks.append(
                _FanOutTask(
                    target=target,
                    arg=item.get("arg"),
                    index=int(item.get("index", len(tasks))),
                    suppresses_static=bool(
                        item.get(
                            "suppresses_static",
                            raw.get("suppresses_static", False),
                        )
                    ),
                )
            )
        restored[producer_id] = _FanOut(
            producer=str(raw.get("producer", "")),
            tasks=tuple(tasks),
            suppresses_static=bool(raw.get("suppresses_static", False)),
        )
    return restored
