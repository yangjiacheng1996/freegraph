# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **时间旅行 / update_state 私有助手** —— 属 **B16F1**。

本模块只实现 ``CompiledGraph.update_state`` 的 L2 行为：

* 基准 checkpoint 定位（显式 ``configurable["checkpoint_id"]`` 或 thread 最新）；
* ``as_node`` 显式 / 单节点兜底 / ``versions_seen`` 推断；
* 与普通节点写入**完全相同**的 C6 合并 / 条件边 / fan-out 求值；
* 通过同一 ``put`` 渠道追加新分支快照，并返回新 ``RunConfig``。

**依赖纪律**（L2）：只依赖 L1 ``freegraph.contracts`` + 同层 runtime；
MUST NOT import ``freegraph.persistence``（L4）；零第三方、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from freegraph.contracts.errors import InvalidUpdateError
from freegraph.contracts.types import RunConfig, StateDict

from ._checkpoint import _metadata, checkpoint_id_of, config_for_checkpoint
from ._concurrency import _TaskOutcome
from ._state_read import resolve_read_config
from .superstep import (
    GraphSpec,
    SchedulerState,
    _clear_step_end,
    _commit_outcome,
    _determine_triggers,
    _evaluate_source_routes,
    _merge_writes,
    _restore_channels,
    _restore_scheduler,
    _run_channels,
    _sparse_state,
)

__all__: list[str] = []

#: 分支快照的内部标记（**不新增公开面**；仅用于：
#: ``update_state`` 分支快照兼任 branch anchor ⇒ 后续 ``invoke`` 不再写额外 anchor）。
BRANCH_ANCHOR_KEY = "_freegraph_branch_anchor"


def update_state(
    spec: GraphSpec,
    checkpointer: Any,
    config: RunConfig | Mapping[str, Any] | None,
    values: StateDict,
    as_node: str | None = None,
) -> RunConfig:
    """基于历史 checkpoint 修改状态并开新分支（L2 实现体）。"""
    if checkpointer is None or isinstance(checkpointer, bool):
        raise ValueError(
            "No checkpointer set: update_state() requires compile(checkpointer=...)"
        )
    run_config = resolve_read_config(config)
    if not isinstance(values, Mapping):
        raise TypeError(
            f"values must be a Mapping, got {type(values).__name__}"
        )
    if as_node is not None and not isinstance(as_node, str):
        raise TypeError(
            f"as_node must be a str or None, got {type(as_node).__name__}"
        )

    explicit_id = checkpoint_id_of(run_config)
    base = checkpointer.get_tuple(run_config)
    if base is None:
        if explicit_id:
            raise ValueError(
                f"checkpoint_id {explicit_id!r} does not exist for "
                f"thread_id {run_config.resolved_thread_id()!r}"
            )
        raise ValueError(
            "no base checkpoint found for thread_id "
            f"{run_config.resolved_thread_id()!r}; update_state() requires "
            "an existing base snapshot"
        )

    base_config = getattr(base.snapshot, "config", None) or run_config
    base_id = checkpoint_id_of(base_config)
    if base_id is None:
        raise ValueError("base snapshot has no checkpoint_id")

    state = SchedulerState()
    _restore_scheduler(state, base.scheduler)
    _restore_channels(spec, state, base.snapshot.values)
    state.fanout.clear()

    node = _resolve_as_node(spec, state, as_node)
    writes = {key: (value,) for key, value in values.items()}
    channels = _run_channels(spec, state)
    gotos, fanout = _evaluate_source_routes(
        spec,
        state,
        node,
        writes,
        channels=channels,
        route_config=config,
    )
    outcome = _TaskOutcome(
        writes=writes,
        gotos=(),
        error=None,
        interrupts=(),
        fanout=(),
    )
    _commit_outcome(
        spec,
        state,
        0,
        node,
        outcome,
        extra_gotos=gotos,
        extra_fanout=fanout,
    )
    written = _merge_writes(spec, state, [(node, node, writes)])
    _clear_step_end(spec, state, written)
    next_nodes = tuple(_determine_triggers(spec, state))

    metadata = _metadata(
        state,
        next_nodes,
        tasks=(),
        interrupts=(),
        suspension_kind=None,
        static_ack=None,
    )
    metadata[BRANCH_ANCHOR_KEY] = True
    return checkpointer.put(
        config_for_checkpoint(run_config, base_id),
        values=_sparse_state(spec, state),
        metadata=metadata,
    )


def _resolve_as_node(
    spec: GraphSpec,
    state: SchedulerState,
    as_node: str | None,
) -> str:
    """解析 / 推断 ``as_node``（镜像上游 ``main.py:1875-1935``）。"""
    if as_node is not None:
        if as_node not in spec.nodes:
            raise InvalidUpdateError(
                (), message=f"Node {as_node} does not exist"
            )
        return as_node

    if len(spec.nodes) == 1:
        return next(iter(spec.nodes))

    last_seen_by_node = sorted(
        (version, node_name)
        for node_name, seen in state.versions_seen.items()
        if node_name in spec.nodes
        for version in seen.values()
    )
    if last_seen_by_node:
        if len(last_seen_by_node) == 1:
            return last_seen_by_node[0][1]
        if last_seen_by_node[-1][0] != last_seen_by_node[-2][0]:
            return last_seen_by_node[-1][1]

    raise InvalidUpdateError(
        (), message="Ambiguous update, specify as_node"
    )
