# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **状态读取** —— 属 **B5F2**。

本模块是「**状态读取**」的**唯一实现点**（spec FR-001 · SC-012）⇒ 全仓
**无第三个**读取入口。两个入口：

* :func:`read_channels` —— **稀疏读**：只返回「**当前有值**」的通道；
* :func:`local_read` —— 「**当前值 + 本任务本次写入**」的视图（``fresh=True``）。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/read-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立一套口径。

**设计要点**（逐条附来源）：

* **稀疏判据 = ``Channel.is_available()``**（**恒不抛错**）⇒ MUST **NOT** 以
  捕获异常驱动控制流（契约 §2.1 · parity **P-01**）；
* **结果恒为新建的普通 ``dict``**（``type(result) is dict``）· 值**按引用**
  （MUST **NOT** 深拷贝 —— 深拷贝会破坏对象身份且对不可拷贝对象会失败）·
  key **顺序** == 入参映射顺序（契约 §2.1 · §4 **I-1…I-4**）；
* **两个稀疏入口共享同一处实现**（``read_channels`` 与
  ``local_read(..., fresh=False)`` 的结果 **MUST 逐字相等** —— 契约 §4 **I-11**）；
* **fresh 读用「副本法」**：``copy.copy(channel)`` ⇒ 在**副本**上
  ``update`` ⇒ 从**副本**读 ⇒ **丢弃**副本 ⇒ 通道的**绑定与可用性判定
  零污染**（契约 §3.3 · §4 **I-5**）。

**依赖纪律**（FR-022 · L2）：本模块只依赖**标准库**（``collections.abc`` ·
``copy``）；MUST NOT import ``langchain*`` / ``langgraph*`` / ``langsmith`` /
``pydantic`` / ``typing_extensions``；MUST **零出站**、零文件 I/O、
零环境变量读取。

**依赖方向**（Structure Decision）：本模块只依赖**同层**的
:mod:`freegraph.runtime.channel`（B5F1 冻结的四个操作 + 一个判定）
⇒ 通道层与读取层**物理分离** ⇒ B5F1 的 ``Channel`` **冻结面零改动**。
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from .channel import Channel
from .errors import EmptyChannelError, InvalidChannelUpdateError

__all__ = [
    "local_read",
    "read_channels",
]


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    """校验入参**是映射** ⇒ 非映射时抛内置 ``TypeError``（**显式失败**）。

    契约 §1.1：「两个入口的 ``channels`` / ``writes`` 入参 MUST 是**映射**
    （``Mapping``）⇒ 入参**非映射**时 MUST 抛 ``TypeError``」
    ⇒ **不静默降级**。
    """
    if not isinstance(value, Mapping):
        raise TypeError(
            f"{name} must be a Mapping, got {type(value).__name__}"
        )
    return value


def _safe_len(values: Any) -> int:
    """取写入序列的长度（**不可取长**时按 **1** 计）。

    仅用于给 :class:`InvalidChannelUpdateError` 的 ``received_count`` 赋值
    ⇒ 错误对象 **MUST NOT** 携带用户写入的**值本身**（B5F1 FR-017 ⑥）。
    """
    try:
        return len(values)
    except TypeError:
        return 1


def _sparse_read(
    channels: Mapping[str, Channel],
    *,
    skip_empty: bool,
) -> dict[str, Any]:
    """**稀疏读**的**唯一实现点**（契约 §2.1 · §4 **I-1…I-4**）。

    * 判据 = ``is_available()``（**恒不抛错** ⇒ MUST NOT 以捕获异常驱动控制流）；
    * ``skip_empty=True`` ⇒ 无值通道的 key **MUST NOT** 出现在结果中；
    * ``skip_empty=False`` ⇒ 读到无值通道 ⇒ 抛 ``EmptyChannelError``
      （其 ``key`` 指向那个 key · 契约 §2.3）⇒ MUST **NOT** 以 ``None``
      冒充「有值」；
    * 结果 = **新建**的普通 ``dict`` · 值**按引用** · key **保序**。
    """
    result: dict[str, Any] = {}
    for key, channel in channels.items():
        if channel.is_available():
            result[key] = channel.get()
        elif not skip_empty:
            raise EmptyChannelError(key)
    return result


def _fresh_read(
    channels: Mapping[str, Channel],
    writes: Mapping[str, Sequence[Any]],
) -> dict[str, Any]:
    """**fresh 读**的**唯一实现点**（契约 §3.2 · §3.3 · §4 **I-5**）。

    * **副本法**：``copy.copy(channel)`` ⇒ 在**副本**上 ``update(writes[key])``
      ⇒ 从**副本**读 ⇒ **丢弃**副本 ⇒ 原通道的**绑定与可用性判定零污染**；
    * 合并 MUST **复用** ``Channel.update()``（MUST **NOT** 在读取层另写一份
      归约逻辑 · 裁定 4）；
    * 待写入的**未知 key** ⇒ 抛**既有的** ``InvalidChannelUpdateError``
      （MUST **NOT** 新增错误类型）。
    """
    for key in writes:
        if key not in channels:
            raise InvalidChannelUpdateError(
                key,
                received_count=_safe_len(writes[key]),
                expected_count=1,
            )
    # ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游 ``langgraph/pregel/_algo.py:209-215``）：
    # 上游对**每一个**通道都 ``copy()`` 一份、再 ``update(updated[k])``（无写入者 ⇒ ``update([])``）
    # ⇒ **路由型**通道的副本被 ``update([])`` **清空**（上游 ``ephemeral_value.py:56-61``）
    # ⇒ 它在 fresh 视图里**缺席**（实测：上游 fresh 视图 = ``{'a': 2}`` · 路由通道不在其中）。
    # ⇒ freegraph 原先「只给**有写入**的通道建副本」⇒ 路由通道**被保留** ⇒ 与上游**不同款**
    # ⇒ 本次**照抄上游**（每个通道都建副本）。
    result: dict[str, Any] = {}
    for key, channel in channels.items():
        merged = copy.copy(channel)
        merged.update(writes.get(key, ()))
        if merged.is_available():
            result[key] = merged.get()
    return result


def read_channels(
    channels: Mapping[str, Channel],
    *,
    skip_empty: bool = True,
) -> dict[str, Any]:
    """**稀疏读** —— 只返回「**当前有值**」的通道（契约 §2）。

    **签名**（**逐字冻结** · 契约 §1）::

        read_channels(channels: Mapping[str, Channel], *, skip_empty: bool = True)
            -> dict[str, Any]

    * 结果 MUST **只含「当前有值」的通道**的 key —— **无值通道的 key MUST NOT
      出现在结果中**（**C4** · 验收判据 **A1 / A2**）；
    * 「**值为 ``None``**」的通道**出现**在结果里（值为 ``None``）⇒
      「值为 ``None``」≠「无值」（契约 §2.2 · **I-10**）；
    * 结果 MUST 是**新建**的**普通 ``dict``**（``type(result) is dict``）·
      值**按引用**（**不深拷贝**）· key **顺序** == 入参映射顺序；
    * ``skip_empty=False`` ⇒ 读到无值通道 ⇒ 抛 ``EmptyChannelError``。

    ⚠️ **MUST NOT** 做 schema 校验（那是 **B4F1** 的职责）⇒ 映射里有
    **不在 schema 里**的 key 时，本入口**照常读取**。
    """
    _require_mapping(channels, "channels")
    return _sparse_read(channels, skip_empty=skip_empty)


def local_read(
    channels: Mapping[str, Channel],
    writes: Mapping[str, Sequence[Any]],
    *,
    fresh: bool = False,
) -> dict[str, Any]:
    """**当前值 + 本任务本次写入**的视图（契约 §3）。

    **签名**（**逐字冻结** · 契约 §1）::

        local_read(channels: Mapping[str, Channel],
                   writes: Mapping[str, Sequence[Any]],
                   *, fresh: bool = False) -> dict[str, Any]

    * ``fresh=False``（**缺省**）⇒ 视图 = **只含通道当前值**（稀疏口径与
      :func:`read_channels` **一致**）⇒ ⚠️ **两个稀疏入口的结果 MUST 逐字
      相等**（key 集合相同 + key 顺序相同 + 逐 key 值**同一对象**）——
      契约 §4 **I-11** · spec **FR-038** / **SC-033**；
    * ``fresh=True`` ⇒ 视图 = **当前值 + 本任务本次写入**（合并后的视图）
      ⇒ 本次写入 MUST 按通道**自身的**写入规则合并（MUST **NOT** 在读取层
      另写一份归约逻辑）；
    * ⚠️ **零污染**（契约 §3.3）：MUST **NOT** 改变任何通道的**绑定与可用性
      判定** —— 读取前后每个通道的 ``is_available()`` 的**结果**与 ``get()``
      的**取值** MUST **不变**。

    ⚠️ **已知面**（契约 §3.3 · research **D-10** / **DR-4**）：副本与原通道
    **浅共享值对象** ⇒ **就地修改型**归约器会**改写原通道的值对象**
    ⇒ 该情形 **MUST NOT** 计入「零污染」判据（作用域只覆盖**绑定与可用性
    判定**）⇒ **MUST NOT** 由读取层修复（**深拷贝**会破坏对象身份语义）。
    """
    _require_mapping(channels, "channels")
    _require_mapping(writes, "writes")
    if fresh:
        return _fresh_read(channels, writes)
    return _sparse_read(channels, skip_empty=True)
