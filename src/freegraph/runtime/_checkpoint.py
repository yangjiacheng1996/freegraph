# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核 · **checkpoint 私有接线助手** —— 属 **B14F1**（内部模块）。

本模块只做四件事：

* 归一化运行期 ``checkpointer``（``None`` / ``True`` / ``False`` / 无 ``thread_id`` ⇒ ``None``）；
* 组装初始 / 每轮快照的 ``metadata`` 并调用鸭子类型 saver；
* 在「真异常 + 中断同现」时收集该轮中断，供 ``_run_graph_loop`` 写 pending writes；
* 从 config 提取 checkpoint id。

**依赖纪律**（L2）：只依赖 L1 ``freegraph.contracts`` + 标准库；
**MUST NOT** import ``freegraph.persistence``（L4）；零第三方、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from contextvars import ContextVar
from typing import Any

from freegraph.contracts.types import Interrupt, RunConfig

__all__: list[str] = []


_ROUND_ERROR_INTERRUPTS: ContextVar[
    list[tuple[str, Interrupt]] | None
] = ContextVar("freegraph_round_error_interrupts", default=None)


def effective_checkpointer(
    checkpointer: Any | None,
    run_config: RunConfig,
) -> Any | None:
    """返回**本次运行**可用的 saver；不满足条件 ⇒ ``None``。

    只归一 ``None`` / ``True`` / ``False`` / 缺失或空 ``thread_id``；
    **MUST NOT** 判 ``isinstance(..., Checkpointer)`` —— 协议校验只在 L3
    ``compile()`` 边界，L2 的 3 方法测试桩 / 差分探针必须继续可用。
    """
    if checkpointer is None or isinstance(checkpointer, bool):
        return None
    if not run_config.resolved_thread_id():
        return None
    return checkpointer


def checkpoint_id_of(config: Any) -> str | None:
    """从 config 的 ``configurable["checkpoint_id"]`` 取 checkpoint id。"""
    configurable = getattr(config, "configurable", None)
    if isinstance(configurable, Mapping):
        value = configurable.get("checkpoint_id")
        return value if isinstance(value, str) and value else None
    return None


def config_for_checkpoint(run_config: RunConfig, checkpoint_id: str) -> RunConfig:
    """构造只带生效 ``thread_id`` + ``checkpoint_id`` 的快照/写入配置。"""
    return RunConfig(
        thread_id=run_config.resolved_thread_id(),
        configurable={"checkpoint_id": checkpoint_id},
    )


def _metadata(
    state: Any,
    next_nodes: Sequence[str],
    *,
    tasks: Sequence[Any] = (),
    interrupts: Sequence[Interrupt] = (),
    suspension_kind: str | None = None,
    static_ack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "next": tuple(next_nodes),
        "interrupts": tuple(interrupts),
        "tasks": tuple(tasks),
        "suspension_kind": suspension_kind,
        "static_ack": static_ack,
        "scheduler": state.to_checkpoint(),
    }


def put_initial(
    config: RunConfig,
    checkpointer: Any,
    state: Any,
    values: Mapping[str, Any],
    next_nodes: Sequence[str],
) -> Any:
    """写**全新会话**的惰性初始快照，返回 saver 的返回值。"""
    return checkpointer.put(
        config,
        values=dict(values),
        metadata=_metadata(state, next_nodes),
    )


def put_step(
    config: RunConfig,
    checkpointer: Any,
    state: Any,
    values: Mapping[str, Any],
    next_nodes: Sequence[str],
    tasks: Sequence[Any],
) -> Any:
    """写**每轮执行完成**快照（``tasks`` = 本轮 ``PregelTask``）。"""
    return checkpointer.put(
        config,
        values=dict(values),
        metadata=_metadata(state, next_nodes, tasks=tasks),
    )


def put_error_interrupts(
    round_start_config: RunConfig,
    checkpointer: Any,
    task_payloads: Iterable[tuple[str, Interrupt]],
) -> None:
    """把「真异常 + 中断同现」的中断元组写入该轮起点 checkpoint。"""
    for task_key, payload in task_payloads:
        checkpointer.put_writes(
            round_start_config,
            writes=[("__interrupt__", (payload,))],
            task_id=task_key,
            task_path=task_key,
        )


def bind_error_interrupts() -> tuple[list[tuple[str, Interrupt]], Any]:
    """开始收集本轮中断；返回 ``(collector, token)``。"""
    collector: list[tuple[str, Interrupt]] = []
    return collector, _ROUND_ERROR_INTERRUPTS.set(collector)


def reset_error_interrupts(token: Any) -> None:
    """恢复收集器上下文。"""
    _ROUND_ERROR_INTERRUPTS.reset(token)


def record_error_interrupts(items: Iterable[tuple[str, Interrupt]]) -> None:
    """记录一条 / 多条本轮中断（收集器未设置 ⇒ no-op）。"""
    collector = _ROUND_ERROR_INTERRUPTS.get()
    if collector is not None:
        collector.extend(items)
