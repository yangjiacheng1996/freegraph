# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **流式会话初始化** —— 属 **B8F2**（内部模块）。

本模块只做**会话初始化**：输入写入 / ``bind_run`` / 运行标识与流式上下文的
绑定 / 初始稀疏状态。主循环与事件封装在 **L3**（``_stategraph.py``），
本模块 **MUST NOT** 求值路由 / 触发 / 执行节点。

**契约权威**：``specs/b8f2-stream-modes/contracts/stream-contract.md``
（§1.2 私有落点 · §4 生命周期）· spec **Q8 / FR-023 / FR-028 / FR-037**。

**关键边界**：

* ``checkpointer`` **不参与** stream v1（不读/写快照、不触发恢复）；
* ``RunConfig.run_id`` **被忽略**；事件 ``run_id`` 由门面生成；
* 含静态断点（``interrupt_before`` / ``interrupt_after``）⇒ 首次迭代
  复用 V-26 的 ``ValueError``，
* ``input`` 只接受 ``dict`` / ``None``；``Command`` 及其他类型 ⇒ 首次迭代
  ``TypeError``（点名恢复路径归 B14F1 / B15F1）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any

from freegraph.contracts.types import Command, RunConfig, StateDict

from ._context import bind_context
from ._interrupt import bind_run, new_run_table
from ._recursion import resolve_config, resolve_limit
from ._stream_context import (
    _CustomSink,
    _RoundCapture,
    bind_stream,
)
from .superstep import (
    SchedulerState,
    _apply_input_writes,
    _reject_static_points_for_low_level,
    _sparse_state,
)

__all__: list[str] = []


class StreamSession:
    """一次 ``stream()`` 的 L2 私有会话（首次迭代进入 · ``finally`` 复原）。"""

    def __init__(
        self,
        spec: Any,
        input: StateDict | None,
        config: RunConfig | Mapping[str, Any] | None,
        *,
        run_id: str,
    ) -> None:
        self._spec = spec
        self._input = input
        self._raw_config = config
        self.run_id = run_id
        self.thread_id: str | None = None
        self.max_steps: int = 0
        self.max_concurrency: int | None = None
        self.state: SchedulerState | None = None
        self.initial_sparse: dict[str, Any] = {}
        self._sink: _CustomSink | None = None
        self._capture: _RoundCapture | None = None
        self._run_cm: Any = None
        self._context_cm: Any = None
        self._stream_cm: Any = None

    def __enter__(self) -> "StreamSession":
        spec = self._spec
        # V-26：静态断点只在图级 run_graph 生效（stream v1 显式拒绝）。
        _reject_static_points_for_low_level(spec)

        input = self._input
        if input is not None and not isinstance(input, dict):
            if isinstance(input, Command):
                raise TypeError(
                    "stream() 不支持 Command 输入；恢复路径归 B14F1 / B15F1"
                )
            raise TypeError(
                "stream() input must be a dict or None, "
                f"got {type(input).__name__}"
            )

        run_config = resolve_config(self._raw_config)
        self.thread_id = run_config.resolved_thread_id()
        self.max_steps = resolve_limit(run_config.recursion_limit)
        self.max_concurrency = run_config.max_concurrency

        state = SchedulerState()
        if isinstance(input, dict):
            _apply_input_writes(spec, state, input)
        self.state = state

        self._run_cm = bind_run(new_run_table())
        self._run_cm.__enter__()
        try:
            self._context_cm = bind_context(run_config.context)
            self._context_cm.__enter__()
            try:
                self._sink = _CustomSink()
                self._capture = _RoundCapture()
                self._stream_cm = bind_stream(
                    self.run_id,
                    self.thread_id,
                    sink=self._sink,
                    capture=self._capture,
                )
                self._stream_cm.__enter__()
            except BaseException:
                self._context_cm.__exit__(None, None, None)
                raise
        except BaseException:
            self._run_cm.__exit__(None, None, None)
            raise

        self.initial_sparse = _sparse_state(spec, state)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._stream_cm is not None:
                self._stream_cm.__exit__(exc_type, exc, tb)
        finally:
            try:
                if self._context_cm is not None:
                    self._context_cm.__exit__(exc_type, exc, tb)
            finally:
                if self._run_cm is not None:
                    self._run_cm.__exit__(exc_type, exc, tb)

    @property
    def route_config(self) -> Any:
        """用户交给 ``stream()`` 的**原始** ``config``（逐字透传）。"""
        return self._raw_config

    def take_custom(self) -> list[Any]:
        """取出本轮 custom 写入（TaskId 升序 + 任务内写入序）。"""
        return self._sink.take() if self._sink is not None else []

    def take_round_tasks(self) -> tuple[Any, ...]:
        """取出中断轮的任务定格。"""
        if self._capture is None:
            return ()
        tasks = self._capture.tasks
        self._capture.tasks = ()
        return tasks

    def sparse_state(self) -> dict[str, Any]:
        """取当前稀疏通道状态。"""
        if self.state is None:
            return {}
        return _sparse_state(self._spec, self.state)
