# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **状态读取组装** —— 属 **B15F1**（内部模块）。

本模块只做**读取侧组装**（由 L3 ``_stategraph.CompiledGraph.get_state`` /
``get_state_history`` / ``stream(checkpoints)`` 调用）：

* ``resolve_read_config`` —— config 归一 + ``thread_id`` / ``checkpoint_ns`` 校验；
* ``require_saver`` —— 未挂 saver 的明确失败信号；
* ``assemble_tasks`` —— 上游 **next-tasks** 语义重建 ``PregelTask``
  （``snapshot.next`` + ``.scheduler["fanout"]`` + pending ``__interrupt__``）；
* ``assemble_interrupts`` —— 按任务顺序展平 / snapshot 回退；
* ``assemble_snapshot`` —— 组装 8 字段 ``StateSnapshot``（可选 pending 合并）。

**两类 fan-out 来源的 id 域不同、互斥**：``next`` 来源的 ``id`` = 运行时
``task_key``（权威 · 全局 records 下标）；``fanout`` 账本来源的 ``id`` = 本地
``index``（**不是** ``task_key``）。**MUST NOT** 跨源按 ``id`` 去重 / 相等合并。

**依赖纪律**（L2）：只依赖 L1 ``freegraph.contracts`` + 同层 runtime；**MUST NOT**
import ``freegraph.persistence``（L4）；零第三方、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from freegraph.contracts.types import (
    Interrupt,
    PregelTask,
    RunConfig,
    StateSnapshot,
)

from ._recursion import resolve_config
from .superstep import merge_pending_writes

__all__: list[str] = []

_INTERRUPT_CHANNEL = "__interrupt__"


def resolve_read_config(
    config: RunConfig | Mapping[str, Any] | None,
) -> RunConfig:
    """归一读取用 config，并校验 ``thread_id`` / ``checkpoint_ns``。

    * ``None`` 仅在类型层接受：解析为空配置后缺 ``thread_id`` ⇒ ``ValueError``；
    * 裸 ``str`` / 数字 ⇒ ``TypeError``（``resolve_config`` 抛出）；
    * ``configurable["checkpoint_ns"]`` 非空 ⇒ ``ValueError``（v1 无子图）。
    """
    resolved = resolve_config(config)
    if not resolved.resolved_thread_id():
        raise ValueError("config.configurable['thread_id'] is required")
    checkpoint_ns = resolved.configurable.get("checkpoint_ns")
    if checkpoint_ns not in (None, ""):
        raise ValueError("checkpoint_ns is not supported in v1 (no subgraphs)")
    return resolved


def require_saver(checkpointer: Any) -> Any:
    """返回可用的 saver；``None`` / ``True`` / ``False`` ⇒ ``ValueError``。"""
    if checkpointer is None or isinstance(checkpointer, bool):
        raise ValueError(
            "No checkpointer set: get_state() / get_state_history() require "
            "compile(checkpointer=...)"
        )
    return checkpointer


def _normalize_interrupt_payload(value: Any) -> tuple[Interrupt, ...]:
    if isinstance(value, Interrupt):
        return (value,)
    if isinstance(value, (tuple, list)):
        items = tuple(value)
        for item in items:
            if not isinstance(item, Interrupt):
                raise TypeError(
                    "__interrupt__ payload must contain only Interrupt objects, "
                    f"got {type(item).__name__}"
                )
        return items
    raise TypeError(
        "__interrupt__ payload must be an Interrupt or a sequence of Interrupt"
    )


def _fanout_key(key: Any) -> tuple[int, Any]:
    text = str(key)
    if text.lstrip("-").isdigit():
        return (0, int(text))
    return (1, text)


def _task_sort_key(name: str, kind: int, value: Any) -> tuple[Any, ...]:
    if isinstance(value, int) and not isinstance(value, bool):
        return (name, kind, 0, value)
    return (name, kind, 1, str(value))


def assemble_tasks(
    next_nodes: Sequence[str],
    scheduler: Mapping[str, Any] | None,
    pending_writes: Sequence[tuple[str, str, Any]],
) -> tuple[PregelTask, ...]:
    """按上游 **next-tasks** 语义重建 ``PregelTask``。"""
    pending: dict[str, tuple[Interrupt, ...]] = {}
    for task_id, channel, value in pending_writes:
        if channel != _INTERRUPT_CHANNEL:
            continue
        items = _normalize_interrupt_payload(value)
        if task_id in pending:
            pending[task_id] = pending[task_id] + items
        else:
            pending[task_id] = items

    collected: list[tuple[tuple[Any, ...], PregelTask]] = []

    # (a) fanout 账本来源（已调度、尚未执行）· id = 本地 index · interrupts 恒 ()
    fanout = (scheduler or {}).get("fanout") or {}
    if isinstance(fanout, Mapping):
        for producer_key in sorted(fanout, key=_fanout_key):
            payload = fanout[producer_key]
            if not isinstance(payload, Mapping):
                continue
            rounds = payload.get("tasks") or ()
            ordered = sorted(
                rounds,
                key=lambda item: item.get("index", 0)
                if isinstance(item, Mapping)
                else 0,
            )
            for item in ordered:
                if not isinstance(item, Mapping):
                    continue
                target = str(item.get("target", ""))
                index = item.get("index", 0)
                task = PregelTask(
                    id=f"{target}:{index}",
                    name=target,
                    path=(target, index),
                    error=None,
                    interrupts=(),
                    state=None,
                    result=None,
                )
                collected.append((_task_sort_key(target, 1, index), task))

    # (b) next 来源（已调度 / 挂起现场）· id = 运行时 task_key（权威）
    for node in next_nodes:
        if ":" in node:
            name, suffix = node.split(":", 1)
            task_id_value: Any = int(suffix) if suffix.lstrip("-").isdigit() else suffix
            interrupts = pending.pop(node, ())
            task = PregelTask(
                id=node,
                name=name,
                path=(name, task_id_value),
                error=None,
                interrupts=interrupts,
                state=None,
                result=None,
            )
            collected.append((_task_sort_key(name, 1, task_id_value), task))
        else:
            interrupts = pending.pop(node, ())
            task = PregelTask(
                id=node,
                name=node,
                path=(node,),
                error=None,
                interrupts=interrupts,
                state=None,
                result=None,
            )
            collected.append((_task_sort_key(node, 0, 0), task))

    # (c) 兜底：未被 next / fanout 关联的 pending __interrupt__ ⇒ 追加为任务
    for task_id, interrupts in pending.items():
        name = task_id.split(":", 1)[0]
        task = PregelTask(
            id=task_id,
            name=name,
            path=(name,),
            error=None,
            interrupts=interrupts,
            state=None,
            result=None,
        )
        collected.append((_task_sort_key(name, 1, 0), task))

    collected.sort(key=lambda item: item[0])
    return tuple(task for _key, task in collected)


def assemble_interrupts(
    tasks: Sequence[PregelTask],
    snapshot_interrupts: Sequence[Interrupt],
) -> tuple[Interrupt, ...]:
    """按任务顺序展平；无任务中断时回退 ``snapshot.interrupts``。"""
    flattened: list[Interrupt] = []
    for task in tasks:
        flattened.extend(task.interrupts)
    if flattened:
        return tuple(flattened)
    if snapshot_interrupts:
        return tuple(snapshot_interrupts)
    return ()


def assemble_snapshot(
    snapshot: StateSnapshot,
    scheduler: Mapping[str, Any] | None,
    pending_writes: Sequence[tuple[str, str, Any]],
    *,
    apply_values: bool,
    spec: Any,
) -> StateSnapshot:
    """组装 8 字段 ``StateSnapshot``（``apply_values=True`` ⇒ 合并 pending writes）。"""
    if apply_values:
        values = merge_pending_writes(spec, snapshot.values, pending_writes)
    else:
        values = dict(snapshot.values)
    tasks = assemble_tasks(snapshot.next, scheduler, pending_writes)
    interrupts = assemble_interrupts(tasks, snapshot.interrupts)
    return StateSnapshot(
        values=values,
        next=tuple(snapshot.next),
        config=snapshot.config,
        metadata=snapshot.metadata,
        created_at=snapshot.created_at,
        parent_config=snapshot.parent_config,
        tasks=tasks,
        interrupts=interrupts,
    )
