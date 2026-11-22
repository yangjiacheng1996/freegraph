# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L4 持久化层 · **读侧载体** —— 属 **B14F1**。

本模块只定义 :class:`CheckpointTuple`：`MemorySaver.get_tuple` / `MemorySaver.list`
返回的**恰好三个公开字段**载体。它**不**提供上游的 ``.config`` / ``.checkpoint`` /
``.metadata`` 别名（B10F1 的跨 feature 契约）。

**依赖纪律**（L4）：只依赖 L1 ``freegraph.contracts`` + 标准库；MUST NOT import
L2 / L3 / L5；零第三方依赖、零环境变量、零出站。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from freegraph.contracts.types import StateSnapshot

__all__ = ["CheckpointTuple"]


@dataclass(frozen=True, slots=True)
class CheckpointTuple:
    """**检查点读侧载体**（B14F1 · 恰好三个公开字段）。

    ================ =========================================== ==========================
    字段             类型                                        语义
    ================ =========================================== ==========================
    ``snapshot``     ``StateSnapshot``                           L1 的 8 字段快照
    ``pending_writes`` ``tuple[tuple[str, str, Any], ...]``       ``(task_id, channel, value)``
    ``scheduler``    ``dict[str, Any]``                          调度账本（纯数据）
    ================ =========================================== ==========================

    不新增上游 ``CheckpointTuple`` 的 ``.config`` / ``.checkpoint`` / ``.metadata``
    别名；形态由 B10F1 ``checkpoint-contract.md`` §2 冻结。
    """

    snapshot: StateSnapshot
    pending_writes: tuple[tuple[str, str, Any], ...]
    scheduler: dict[str, Any]
