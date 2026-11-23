# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **流式 checkpoint 写盘** —— 属 **B15F1**（内部模块）。

``stream(stream_mode="checkpoints")`` 的消费端接线：在**本次运行**期间，每次成功
``put`` 产出恰好一条 checkpoint 事件（由 L3 主循环读回快照后发事件）。本模块只
**复用** B14F1 已冻结的写盘助手（``put_initial`` / ``put_step`` / ``_write_suspend`` /
``put_error_interrupts``），**不**另立事件路径、**不**伪造历史。

**关键边界**：不恢复历史（``prepare`` 只读最新 checkpoint id 以接续父链）；无 saver /
无 ``thread_id`` ⇒ 不写；只把**本次运行**的新快照追加到该 thread。

**依赖纪律**（L2）：只依赖 L1 + 同层 runtime；MUST NOT import ``freegraph.persistence``（L4）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from freegraph.contracts.types import Interrupt, PregelTask, RunConfig, StateSnapshot

from . import _state_read
from ._checkpoint import (
    checkpoint_id_of,
    config_for_checkpoint,
    put_error_interrupts,
    put_initial,
    put_step,
)
from .superstep import (
    _determine_triggers,
    _evaluate_start_routes,
    _sparse_state,
    _write_suspend,
)

__all__: list[str] = []


class StreamCheckpointWriter:
    """本次 ``stream`` 运行的 checkpoint 写盘助手（仅 ``checkpoints`` 档启用）。"""

    def __init__(self, spec: Any, saver: Any, run_config: RunConfig) -> None:
        self._spec = spec
        self._saver = saver
        self._run_config = run_config
        self.current_checkpoint_id: str | None = None

    def prepare(self, state: Any) -> Any | None:
        """无历史 ⇒ 写惰性初始快照；有历史 ⇒ 只接续父链（返回 ``None``）。"""
        history = self._saver.get_tuple(self._run_config)
        if history is not None:
            config = getattr(history.snapshot, "config", None) or self._run_config
            self.current_checkpoint_id = checkpoint_id_of(config)
            return None
        _evaluate_start_routes(self._spec, state, route_config=None)
        triggers = tuple(_determine_triggers(self._spec, state))
        written = put_initial(
            self._run_config,
            self._saver,
            state,
            _sparse_state(self._spec, state),
            triggers,
        )
        self.current_checkpoint_id = checkpoint_id_of(written) or self.current_checkpoint_id
        return written

    def after_result(self, state: Any, result: Any) -> Any:
        """每次成功执行一轮 ⇒ 写该轮完成态快照。"""
        next_nodes = tuple(_determine_triggers(self._spec, state))
        written = put_step(
            self._run_config,
            self._saver,
            state,
            _sparse_state(self._spec, state),
            next_nodes,
            result.tasks,
        )
        self.current_checkpoint_id = checkpoint_id_of(written) or self.current_checkpoint_id
        return written

    def on_interrupt(
        self,
        state: Any,
        tasks: Sequence[PregelTask],
        interrupts: Sequence[Interrupt],
    ) -> Any:
        """动态中断挂起 ⇒ 写快照 + 待写入（``__interrupt__`` 留痕）。"""
        produced: dict[str, Interrupt] = {}
        for task in tasks:
            if not task.interrupts:
                continue
            key = task.name
            if len(task.path) > 1 and isinstance(task.path[1], int):
                key = f"{task.name}:{task.path[1]}"
            produced[key] = task.interrupts[0]
        written = _write_suspend(
            self._run_config,
            self._saver,
            state,
            _sparse_state(self._spec, state),
            produced,
            tuple(interrupts),
        )
        self.current_checkpoint_id = checkpoint_id_of(written) or self.current_checkpoint_id
        return written

    def on_error(self, collector: Sequence[tuple[str, Interrupt]]) -> None:
        """真异常 + 中断同现 ⇒ 把中断留痕写到本轮起点 checkpoint（无新快照）。"""
        if not collector or not self.current_checkpoint_id:
            return
        put_error_interrupts(
            config_for_checkpoint(self._run_config, self.current_checkpoint_id),
            self._saver,
            collector,
        )

    def snapshot_of(self, written: Any) -> StateSnapshot:
        """读回刚写入的 checkpoint，组装 8 字段快照（``values`` 不合并 pending）。"""
        checkpoint_tuple = self._saver.get_tuple(written)
        if checkpoint_tuple is None:
            raise RuntimeError(
                "checkpoint just written is not readable; refusing to fabricate an event"
            )
        return _state_read.assemble_snapshot(
            checkpoint_tuple.snapshot,
            checkpoint_tuple.scheduler,
            checkpoint_tuple.pending_writes,
            apply_values=False,
            spec=self._spec,
        )
