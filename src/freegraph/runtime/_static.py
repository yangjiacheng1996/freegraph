# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **静态中断点**（``interrupt_before`` / ``interrupt_after``）

**契约权威**：``specs/b13f1-static-interrupt-recursion-limit/contracts/
static-interrupt-contract.md``（§1 归一 / 校验 · §7 防重复触发）。

本模块只承载**纯函数**：常量、归一 / 校验、命中判定、ack 水位。它不 import
``superstep``（避免循环依赖），也不做任何 I/O / 环境变量 / 网络访问。

**本模块私有** ⇒ 不进 ``freegraph.runtime.__all__``。
"""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping, Sequence
from typing import Any

__all__: list[str] = []

#: 静态挂起的两类标记（写入检查点 metadata）。
STATIC_BEFORE = "static_before"
STATIC_AFTER = "static_after"

_START_MARKER = "__start__"
_END_MARKER = "__end__"
_ALL_MARKER = "*"


def _node_names(nodes: Mapping[str, Any] | Iterable[str]) -> tuple[str, ...]:
    """取节点表的**保序**节点名序列。"""
    if isinstance(nodes, Mapping):
        return tuple(nodes)
    return tuple(nodes)


def normalize_static_points(
    value: str | Sequence[str] | None,
    nodes: Mapping[str, Any] | Iterable[str],
    field_name: str,
) -> tuple[str, ...]:
    """把 ``GraphSpec`` 的静态断点字段归一为 ``tuple[str, ...]``。

    **失败信号**（与 ``superstep-contract.md`` V-22…V-25 逐字同款）：

    * 裸值：裸 ``"*"`` 合法并展开为**全部可执行节点**（排除 ``__start__`` /
      ``__end__``）；其余裸字符串（含空串 / 哨兵）⇒ ``TypeError``（V-22）；
    * ``None`` ⇒ ``TypeError``（V-22）；
    * 非 ``str`` / ``Sequence``（``Mapping`` / ``set`` 等）⇒ ``TypeError``（V-22）；
    * 序列元素非 ``str`` ⇒ ``TypeError``（V-22）；空串 ⇒ ``ValueError``（V-23）；
      哨兵 / ``"*"`` ⇒ ``ValueError``（V-24）；未知节点 ⇒ ``ValueError``（V-25）。

    重复节点名去重（保序）；空序列 = 关闭。
    """
    names = _node_names(nodes)
    known = set(names)

    if isinstance(value, str):
        if value == _ALL_MARKER:
            return tuple(
                name
                for name in names
                if name not in (_START_MARKER, _END_MARKER)
            )
        raise TypeError(
            f"{field_name} must be '*' or a sequence of node names, "
            f"got bare string {value!r} (V-22)"
        )

    if value is None:
        raise TypeError(f"{field_name} must not be None (V-22)")

    if not isinstance(value, Sequence):
        raise TypeError(
            f"{field_name} must be '*' or a sequence of node names, "
            f"got {type(value).__name__} (V-22)"
        )

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(
                f"{field_name} elements must be str, got {type(item).__name__} (V-22)"
            )
        if item == "":
            raise ValueError(f"{field_name} must not contain an empty string (V-23)")
        if item in (_START_MARKER, _END_MARKER, _ALL_MARKER):
            raise ValueError(
                f"{field_name} element {item!r} is not a suspendable node name (V-24)"
            )
        if item not in known:
            raise ValueError(
                f"{field_name} element {item!r} is not in the node table (V-25)"
            )
        if item not in normalized:
            normalized.append(item)
    return tuple(normalized)


def static_hit(targets: Iterable[str], configured: Container[str]) -> bool:
    """本轮目标中是否有任一命中静态断点集合。"""
    return any(target in configured for target in targets)


def build_static_ack(state: Any) -> dict[str, Any]:
    """记录挂起时的**通道版本水位**（防重复触发）。"""
    return {"channel_versions": dict(state.channel_versions)}


def static_allowed(ack: Mapping[str, Any] | None, state: Any) -> bool:
    """自上次静态挂起以来**是否出现过通道版本推进**。

    * ``ack is None`` ⇒ 首次运行，允许触发；
    * 否则对 **ack 键 ∪ 当前键** 逐个比较 ⇒ 新通道视为 0 ⇒ 只有任何通道版本
      严格变大才允许再次触发（无推进 ⇒ 抑制，防「恢复即再挂起」）。
    """
    if ack is None:
        return True
    previous = ack.get("channel_versions", {}) if isinstance(ack, Mapping) else {}
    current = state.channel_versions
    return any(
        current.get(key, 0) > previous.get(key, 0)
        for key in set(previous) | set(current)
    )
