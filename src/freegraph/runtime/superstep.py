# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **调度内核（super-step）** —— 属 **B7F1**。

本模块是 freegraph 的**调度内核**：super-step 循环 —— 每轮「判定哪些节点被触发
→ 准备任务 → 执行任务 → 收集写入 → 按通道语义合并写入 → 进入下一轮」。

**契约权威**：``specs/b7f1-superstep-loop/contracts/superstep-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立一套口径。

**设计要点**（逐条附来源）：

* **四个类型 + 两个入口**（契约 §1）—— :class:`GraphSpec`（手写图规格）·
  :class:`NodeSpec`（节点规格）· :class:`SchedulerState`（调度状态）·
  :class:`SuperStepResult`（单轮结果）· :func:`run_super_step`（单轮入口）·
  :func:`run_super_steps`（多轮入口）；**名字与语义逐字冻结**（跨 feature 契约）；
* **校验在构造时执行**（裁定 32）—— 图规格的**四条显式失败路径**
  （**V-1** 订阅不存在的通道 · **V-2** 边的端点不在节点表 · **V-3** 节点表为空 ·
  **V-8** 条件边字段非空）MUST **即刻**显式失败，MUST NOT 推迟到运行期；
* **版本由调度器维护**（裁定 21 · research **D-01**）—— 版本记在
  :class:`SchedulerState` 里，通道对象 **MUST NOT** 新增版本属性
  （B5F1 的四个只读属性是**冻结面**）；
* **「有值」即算已写过一次**（裁定 21）—— 调度器**第一次**查看某通道时若它
  **已有值**，该通道的写入版本记为 **1** ⇒ 调用方在**跑之前**预置的初始值
  MUST 能触发其订阅者（**初始化写入豁免** · 裁定 31）⇒ 而**跑之后**的直接写入
  **不**进版本推进路径 ⇒ MUST **不**成为触发依据；
* **节点入参复用 B5F2 的稀疏读**（裁定 2 · research **D-08**）—— 入参 =
  :func:`freegraph.runtime.read_channels` 的结果 ⇒「稀疏语义」在**调度层**
  **不可能**漂移；子映射 MUST 按「**通道映射的顺序**」构造（裁定 26）；
* **写入合并走批量路径**（裁定 5 · research **D-07**）—— 每个通道**一次**
  ``Channel.update(values)`` ⇒ 归约型按序归约（**不**后写覆盖先写）；
* **步末只清「本轮未被写入的」路由型通道**（裁定 10 · research **D-05**）——
  「路由型」MUST 以 ``isinstance(channel, EphemeralValue)`` 判定
  ⇒ MUST NOT 用「``reducer is None``」等**启发式**（覆盖型与路由型**都**无归约器）；
* **一轮 super-step 是原子的**（裁定 22 · 裁定 29）—— 本轮任何环节出错 ⇒
  本轮产生的**全部**待写入**不**合并 ⇒ 通道的正式值 MUST 保持**本轮开始前**
  的样子（合并前**快照** → 出错**逐通道回滚** · **不套**归约器）。

**依赖纪律**（FR-022 · L2）：本模块只依赖**标准库**与**同层 / 下层**的既有
模块（``channel`` / ``read`` / ``errors`` / L1 的 ``contracts.errors``）
⇒ **零第三方依赖**；MUST NOT import ``langchain*`` / ``langgraph*`` /
``langsmith`` / ``pydantic`` / ``typing_extensions``；MUST **零出站**、
零文件 I/O、零环境变量读取。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from freegraph.contracts.errors import GraphInterrupt, GraphRecursionError, InvalidUpdateError
from freegraph.contracts.types import Command, Interrupt, RunConfig, StateDict

from ._concurrency import (
    _TaskOutcome,
    _resolve_cap,
    attach_failure_notes,
    run_tasks_concurrently,
)
from ._interrupt import (
    bind_run,
    bind_task,
    current_run_table,
    new_run_table,
    prepare_task,
)
from .channel import Channel, EphemeralValue
from .errors import InterruptError, InvalidChannelUpdateError
from .read import read_channels

__all__ = [
    "GraphSpec",
    "InterruptError",
    "InterruptResult",
    "NodeSpec",
    "SchedulerState",
    "SuperStepResult",
    "run_graph",
    "run_super_step",
    "run_super_steps",
]

#: **触发源标识** = **边触发源**（契约 §3.1 · 裁定 3）—— **唯一**的空间。
#:
#: ⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：原先还有「**通道触发源**」空间（``("c", key)``）
#: ⇒ 已**删除**：上游的触发源**恒为边**（``branch:to:<node>`` · 上游
#: ``langgraph/graph/state.py:1531-1532``）⇒ freegraph 改为**纯边触发** ⇒
#: 「节点订阅的通道」**不再**是触发源（``subscribes`` 只决定「读哪些通道」· 上游
#: ``langgraph/graph/state.py:1534``）⇒ **消除**「节点写自己订阅的通道 ⇒ 自触发循环」。
_EDGE_SOURCE = "e"

#: **终止标记**（契约 §3 · 裁定 6）—— 字符串字面量。
#:
#: ⚠️ **L2 MUST NOT import 门面**（L3 · ARCH-1）⇒ 终止标记 MUST 以**字面量**
#: 判定 ⇒ 门面 ``END`` 的值 MUST 与本字面量**逐字相等**（**可自动核对** ·
#: SC-008 第三子句）。
_TERMINAL_MARKER = "__end__"

#: **入口标记**（门面 ``START`` 的值）—— **不是**合法跳转目标（契约 §3 · V-13）。
#:
#: ⚠️ 同上：以**字面量**判定（L2 MUST NOT import 门面）。
_START_MARKER = "__start__"

#: **保留节点名**（契约 §7 · V-14）—— ``Command.PARENT`` 的值。
#:
#: 图规格里出现该名字的节点 MUST **构造期**显式失败（内置 ``ValueError``）⇒
#: 杜绝「用户自建一个叫 ``__parent__`` 的节点 ⇒ ``Command.PARENT`` 跳到它」的
#: **语义歧义**（宪法原则 VIII 的术语纪律）。
_RESERVED_NODE_NAME = Command.PARENT


@dataclass(frozen=True)
class NodeSpec:
    """**节点规格** —— 「订阅哪些通道 → 读 → 写」。

    **构造签名**（**逐字冻结** · 契约 §1）::

        NodeSpec(
            subscribes: tuple[str, ...],
            run: Callable[
                [dict[str, Any]],
                dict[str, Any] | Command | list[Command | dict[str, Any]],
            ],
        )

    * ``subscribes`` —— 该节点**订阅**的通道 key：**只管「读哪些通道」（入参内容）** ——
      **不**再是触发源（**上游对齐 P1-0-2 · 2026-11-12**：上游的触发源**恒为边**
      · `langgraph/graph/state.py:1531-1532`；节点读的状态通道在 `channels=` · `:1534`
      ⇒ **不参与触发**）⇒ 节点**没有入边** ⇒ **永不执行**。
      （裁定 2 ⇒ MUST NOT 存在「订阅了某通道却读不到它的值」的情形）；
    * ``run`` —— 节点函数（**C5**：``f(state: dict) -> dict``）⇒ MUST 可调用；
      其返回值 MUST 是 ``dict`` / ``Command`` / ``list[Command | dict]`` 之一
      （**B9F1** · FR-001 · 裁定 15 / 21）。

    **校验**（契约 §2.2）MUST **显式失败**，MUST NOT 静默忽略。

    **不可变**（data-model §1）⇒ 构造后**不可**改写。

    ⚠️ **返回类型注解的放宽**（**B9F1** · 裁定 11 / 15 · 协变放宽）：
    B7F1 冻结的注解是 ``Callable[[dict[str, Any]], dict[str, Any]]`` ⇒ 本 feature
    把**接受面**放宽为「``dict`` / ``Command`` / **命令列表**」三形态 ⇒
    **构造签名与名字逐字不变**（参数名 / 顺序 / 种类 / 个数均未动）⇒
    B7F2 / B7F3 / B8F1 / B12F1 **零改动**。
    """

    subscribes: tuple[str, ...]
    run: Callable[
        [dict[str, Any]],
        dict[str, Any] | Command | list[Command | dict[str, Any]],
    ]

    def __post_init__(self) -> None:
        """构造期校验（裁定 32）—— ``run`` MUST 可调用（契约 §2.2）。"""
        if not callable(self.run):
            raise TypeError(
                f"NodeSpec.run must be callable, got {type(self.run).__name__}"
            )


@dataclass(frozen=True)
class GraphSpec:
    """**手写图规格** —— 纯数据的图定义（**静态**）。

    **构造签名**（**逐字冻结** · 契约 §1）::

        GraphSpec(
            channels: dict[str, Channel],
            nodes: dict[str, NodeSpec],
            edges: dict[str | tuple[str, ...], tuple[str, ...]],
            *,
            conditional_edges: dict[str, Any] = <空映射>,
        )

    * ``channels`` —— 通道映射（状态本体）· MUST 是**可变** ``dict``
      （FR-034 · **MUST NOT** 用 ``MappingProxyType``）⇒ 调用方 MUST 能在其上
      **增补内部通道**（如路由型通道 · 裁定 23）⇒ 调度器 MUST 在**运行期**
      读取它（MUST NOT 在构造时快照）；
    * ``nodes`` —— **保序**的节点表（``dict`` 的插入顺序 == 同轮执行顺序 ·
      FR-013）· MUST **非空**；
    * ``edges`` —— 边表（源节点名 → 目标节点名序列）· 源 / 目标 MUST **都在**
      ``nodes`` 里；
    * ⚠️ **边表的键类型**（**B7F4** · 兼容扩展 · 契约 §2.1）⇒ ``str``
      （**单源边** · 写法**逐字不变**）**或** ``tuple[str, ...]``
      （**多源边** · AND / 屏障）⇒ ⇒ **单源边的既有调用方零改动**；
    * ``conditional_edges`` —— **预留**的「条件边」字段（裁定 25）·
      本轮**恒为空**；**非空 ⇒ 显式失败**（FR-033）· 缺省值 MUST 用
      **工厂语义**实现（``default_factory``）⇒ MUST NOT 用字面可变默认值。

    **校验**（契约 §2.1 / §2.1.1）MUST 在**构造时**执行 ⇒ 即刻显式失败。

    **不可变**（data-model §1）⇒ **字段**不可改写；但 ``channels`` 的**内容**
    仍可被调用方增补（FR-034）。
    """

    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    conditional_edges: dict[str, Any] = field(default_factory=dict, kw_only=True)

    def __post_init__(self) -> None:
        """构造期校验（裁定 32 · 契约 §2.1.1）—— 四条失败路径逐条唯一。"""
        _validate_graph_spec(self)


@dataclass
class SchedulerState:
    """**调度状态** —— 「已消费版本」+ 轮次计数（**由调用方持有**）。

    **构造签名**（**逐字冻结** · 契约 §1）::

        SchedulerState()

    * ``versions_seen`` —— **节点名 → {触发源 → 已消费版本}**；触发源标识 MUST
      用**两个空间**：``("c", 通道 key)`` / ``("e", 源节点名)``
      ⇒ 避免「通道 key 与节点名同名」时互相覆盖（裁定 3）；
    * ``step`` —— **执行轮**计数（**不含**空轮）—— 即 FR-011 的上限计数口径
      ⇒ MUST NOT 与 :attr:`SuperStepResult.steps`（含空轮）混用（裁定 34）；
    * ``channel_versions`` —— **通道 key → 写入版本**（**每通道独立** ·
      research **D-03**）· 通道**成功写入**时 +1（清空**不是**写入 ⇒ 不推进）；
    * ``node_versions`` —— **节点名 → 执行版本**（边触发源的版本）· 节点
      **执行成功**时 +1；
    * ``dynamic_edges`` —— **动态边表**（**B9F1** · 裁定 12 · 澄清轮第 2 次
      **Q5** 发起者拍板）—— **源节点名 → 其最近一次执行的跳转目标序列**
      （**保序** · 去重）⇒ 源节点**再次执行**时**整体替换**（含**空集**）
      ⇒ 旧的 ``goto`` 目标被清空（FR-009 · 裁定 2）。

    ⚠️ **可变**（data-model §1）—— 调用方持有 ⇒ 同一份图规格可**安全跑多次**
    （FR-004 · 裁定 16）⇒ 两个入口的「已消费版本」**不串扰**。

    ⚠️ **带缺省字段的扩展**（**B9F1** · 登记项 **R-3 ①** · 裁定 12）：
    ``dynamic_edges`` 用**工厂语义**实现（``default_factory=dict``）⇒
    MUST NOT 用字面可变默认值（dataclass 会抛 ``ValueError: mutable default``
    · **实测**）⇒ ``SchedulerState()`` 的**构造签名与名字逐字不变**
    ⇒ B7F2 / B7F3 / B8F1 / B12F1 **零改动**（FR-016 · SC-015）。
    """

    versions_seen: dict[str, dict[tuple[str, str], int]] = field(default_factory=dict)
    step: int = 0
    channel_versions: dict[str, int] = field(default_factory=dict)
    node_versions: dict[str, int] = field(default_factory=dict)
    dynamic_edges: dict[str, tuple[str, ...]] = field(default_factory=dict)
    channels: dict[str, Channel] = field(default_factory=dict)

    def to_checkpoint(self) -> dict[str, Any]:
        """把**调度账本**编码成**纯数据**（**可 JSON 序列化** · C19 ③）。

        **编码**（契约 §3 · **逐字**）：

        * ``versions_seen`` ⇒ ``{节点名: [[kind, ident, 版本], ...]}``
          （⚠️ 它的 key 是**二元组** ⇒ **JSON 不可直接序列化** ⇒ ⇒ 必须用
          **列表**编码 ⇒ ⇒ 还原时还原成 ``{(kind, ident): 版本}``）；
        * ``channel_versions`` / ``node_versions`` ⇒ **原样**（key 全是字符串）；
        * ``dynamic_edges`` ⇒ ``{节点名: [目标, ...]}``（还原时还原成 **tuple**）。

        ⚠️ ``step`` **不落盘** ⇒ 恢复时**重新计数**（``steps`` 是**本 feature
        产出的结果**的口径 · **不是**持久化状态）⇒ ⇒ **零**「跨运行的步数」
        语义 ⇒ ⇒ 零歧义（契约 §3）。
        ⚠️ ``channels`` **不落盘** ⇒ 通道实例由 ``Channel.from_checkpoint``
        **重建**（现成机制）。

        ⚠️ **只增方法 · 不改字段** ⇒ ⇒ ``SchedulerState()`` 的**构造签名
        逐字不变** ⇒ ⇒ B7F1 冻结面**零破坏**（B12F1 的 ``dynamic_edges`` 就是
        这么加的 · 裁定 12 / R-3 ①）⇒ ⇒ 零 L1 改动。
        """
        return {
            "versions_seen": {
                node_name: [
                    [kind, ident, version]
                    for (kind, ident), version in sorted(seen.items())
                ]
                for node_name, seen in self.versions_seen.items()
            },
            "channel_versions": dict(self.channel_versions),
            "node_versions": dict(self.node_versions),
            "dynamic_edges": {
                node_name: list(targets)
                for node_name, targets in self.dynamic_edges.items()
            },
        }

    @classmethod
    def from_checkpoint(cls, data: Mapping[str, Any]) -> "SchedulerState":
        """按**纯数据**重建**调度账本**（契约 §3 · **逐字**）。

        ⚠️ **还原**与 :meth:`to_checkpoint` **严格互逆**：

        * ``versions_seen`` ⇒ ``{节点名: {(kind, ident): 版本}}``；
        * ``dynamic_edges`` ⇒ ``{节点名: (目标, ...)}``（**tuple**）；
        * ``step`` ⇒ **0**（**不落盘** ⇒ 重新计数）。

        ⚠️ **缺项**（``data`` 里没有某个键）⇒ ⇒ 该项取**空** ⇒ ⇒
        **不**抛异常（**纯数据**载荷的宽容解码 ⇒ ⇒ B14F1 的实现面最小）。
        """
        versions_seen: dict[str, dict[tuple[str, str], int]] = {}
        for node_name, entries in (data.get("versions_seen") or {}).items():
            seen: dict[tuple[str, str], int] = {}
            for entry in entries:
                kind, ident, version = entry
                seen[(kind, ident)] = version
            versions_seen[node_name] = seen
        dynamic_edges: dict[str, tuple[str, ...]] = {
            node_name: tuple(targets)
            for node_name, targets in (data.get("dynamic_edges") or {}).items()
        }
        return cls(
            versions_seen=versions_seen,
            step=0,
            channel_versions=dict(data.get("channel_versions") or {}),
            node_versions=dict(data.get("node_versions") or {}),
            dynamic_edges=dynamic_edges,
        )


@dataclass(frozen=True)
class SuperStepResult:
    """**单轮结果** —— 五阶段产物的**可观测**载体。

    **构造签名**（**逐字冻结** · 契约 §1）::

        SuperStepResult(
            state: dict[str, Any],
            executed: tuple[str, ...],
            node_writes: dict[str, dict[str, tuple[Any, ...]]],
            steps: int,
        )

    * ``state`` —— 本轮**结束**时的**稀疏**通道状态（合并 + 步末清空之后）；
    * ``executed`` —— 执行过的节点名（**按执行顺序**）· 单轮入口 = 本轮 ·
      多轮入口 = **累计**（跨轮按轮次先后拼接 · 裁定 34）；
    * ``node_writes`` —— **按节点分组**的待写入（节点名 → 通道 key → 值序列）
      · 单轮入口 = 本轮 · 多轮入口 = **累计**（同名节点的同一通道按**轮次先后**
      拼接 · **不**按通道重排）⇒ B8F1 的 fresh 读复用前提（FR-006）；
    * ``steps`` —— **实际迭代轮数**（**含**那次发现「任务集为空」的**空轮**）·
      单轮入口**恒为 1**（裁定 34）。

    **不可变**（data-model §1）。
    """

    state: dict[str, Any]
    executed: tuple[str, ...]
    node_writes: dict[str, dict[str, tuple[Any, ...]]]
    steps: int


@dataclass(frozen=True, slots=True)
class InterruptResult:
    """**挂起态**的结果对象 —— **B10F1** · 裁定 2（**四个**字段 · **逐字冻结**）。

    **构造签名**（**逐字冻结** · 契约 §5.1）::

        InterruptResult(
            state: dict[str, Any],
            interrupts: tuple[Interrupt, ...],
            executed: tuple[str, ...],
            steps: int,
        )

    * ``state`` —— **合并后**的稀疏状态（**含**中断前已产生的写入）；
    * ``interrupts`` —— 中断集合（= ``exc.args[0]`` · **元组** · 元素 =
      ``Interrupt``）⇒ ⇒ 元素带 ``.value`` 与 ``.id``（C17 · 裁定 1）；
    * ``executed`` —— **已启动过**的节点名（**含**被中断的 · **节点名序** =
      **升序** · 与 :attr:`SuperStepResult.executed` **同排序口径**）；
    * ``steps`` —— **实际跑过的轮数**（**如实计** · **含**被中断的那轮 ·
      **不含**那个「发现没任务了」的**空轮**）⇒ ⚠️ **与**
      :attr:`SuperStepResult.steps`（**含**空轮 · B7F1 冻结面）**计数口径
      「刻意不同」** ⇒ ⇒ 两者**数值不可直接比较**。

    ⚠️ **MUST NOT** 带「待写入」字段（挂起时那些写入**已合并进** ``state``
    ⇒ 语义不明 · 澄清轮 **Q1**）⇒ ⇒ **四字段**（契约 §5.1）。
    ⚠️ ``__interrupt__`` **不进** ``state``（形态污染 · B12F1 裁定 25 ③）。
    ⚠️ **MUST NOT** 改 :attr:`SuperStepResult` 的**字段数**（**四字段** ·
    B12F1 裁定 25 ②）⇒ ⇒ 挂起态**另立**载体（原则 XII ③ · 既有载体已穷举）。
    """

    state: dict[str, Any]
    interrupts: tuple[Interrupt, ...]
    executed: tuple[str, ...]
    steps: int

    def as_result_dict(self) -> dict[str, Any]:
        """把**挂起态**转成**结果字典**（= ``{**state, "__interrupt__": interrupts}``）。

        ⚠️ **键名逐字** = ``"__interrupt__"``（**上游同款** ·
        ``langgraph/_internal/_constants.py:9``）⇒ ⇒ **同一个常量**既是
        **通道名**又是**结果键名**（原则 XI ②）。
        ⚠️ **值 = 元组**（裁定 1 · 偏离登记 **X-1** · 上游 ``invoke()`` 返回
        **list**）⇒ ⇒ freegraph **统一**为**元组**（与 B12F1 的**中断载荷
        形态**一致 ⇒ **同类项同类承载** · 原则 XII ③）。
        ⚠️ **本 feature 独占**「异常 → ``__interrupt__`` 键」的**转成路径**
        （裁定 10）⇒ ⇒ B7F3 **MUST NOT** 另写（承接 **D-3**）。
        """
        return {**self.state, "__interrupt__": self.interrupts}


def _validate_graph_spec(spec: GraphSpec) -> None:
    """**图规格校验**（契约 §2.1 / §2.1.1）—— 四条失败路径逐条唯一。

    * **V-1**（``subscribes`` 含**不存在**的通道 key）⇒ 内置 ``ValueError``；
    * **V-2**（边的**源 / 目标**不在节点表里）⇒ 内置 ``ValueError``；
    * **V-3**（节点表**为空**）⇒ 内置 ``ValueError``；
    * **V-8**（``conditional_edges`` **非空**）⇒ 内置 ``ValueError``。

    ⚠️ **失败信号 MUST 逐条唯一** ⇒ 「同一场景出现两种异常类型」的出现次数
    MUST == **0**（SC-015）。
    """
    for key, channel in spec.channels.items():
        if not isinstance(key, str):
            raise TypeError(f"GraphSpec channel key must be str, got {type(key).__name__}")
        if not isinstance(channel, Channel):
            raise TypeError(
                f"GraphSpec.channels[{key!r}] must be a Channel instance, "
                f"got {type(channel).__name__}"
            )
    if not spec.nodes:
        raise ValueError("GraphSpec.nodes must not be empty (V-3)")
    for name, node in spec.nodes.items():
        if not isinstance(name, str):
            raise TypeError(f"GraphSpec node name must be str, got {type(name).__name__}")
        if name == _RESERVED_NODE_NAME:
            raise ValueError(
                f"GraphSpec node name {name!r} is reserved for Command.PARENT "
                f"(reserved-name check)"
            )
        if not isinstance(node, NodeSpec):
            raise TypeError(
                f"GraphSpec.nodes[{name!r}] must be a NodeSpec instance, "
                f"got {type(node).__name__}"
            )
        for key in node.subscribes:
            if key not in spec.channels:
                raise ValueError(
                    f"Node {name!r} subscribes to unknown channel {key!r} (V-1)"
                )
    for source, targets in spec.edges.items():
        # ⚠️ **边键分流**（**B7F4** · 契约 §2.2）：``str`` ⇒ 单源边（既有语义
        # **逐字不变**）· ``tuple`` ⇒ **多源边**（AND / 屏障）· 其它类型 ⇒
        # 内置 ``TypeError``（**FR-021** · 上游同族 · 实测 **E-10**）。
        if isinstance(source, str):
            # ⚠️ **入口哨兵豁免**（2026-11-12 · 上游对齐 P1-0-1）：`__start__` 是**图的入口**
            # （上游 `START` 伪节点 · `langgraph/constants.py:30`；入口边写法
            # `add_edge(START, "a")` · `langgraph/graph/state.py:321`）⇒ 它**不必**是节点表里的
            # 一个节点 ⇒ 但**必须**是**合法的边源**（否则图无法起跑）。
            if source not in spec.nodes and source != _START_MARKER:
                raise ValueError(f"Edge source {source!r} is not in the node table (V-2)")
            for target in targets:
                if target not in spec.nodes:
                    raise ValueError(
                        f"Edge target {target!r} is not in the node table (V-2)"
                    )
            continue
        if isinstance(source, tuple):
            _validate_multisource_edge(source, targets, spec)
            continue
        raise TypeError(
            f"GraphSpec edge key must be a str or a tuple of str, "
            f"got {type(source).__name__}"
        )
    if spec.conditional_edges:
        raise ValueError(
            "GraphSpec.conditional_edges must stay empty in this feature (V-8)"
        )


def _validate_multisource_edge(
    source: tuple[str, ...],
    targets: tuple[str, ...],
    spec: GraphSpec,
) -> None:
    """**多源边**的校验（契约 §2.2 · **V-16** 形态 + **V-2** 语义）。

    ⚠️ **校验的优先级**（澄清轮 **C-Q15**）：**形态校验（`V-16`）MUST 先于缺源 /
    缺目标校验（`V-2`）** ⇒ ⇒ 元组同时命中两者时（典型 = 元组含 `__start__`）
    ⇒ **归 `V-16`** ⇒ ⇒ 失败信号仍是内置 `ValueError`（**零新增错误类型**）
    ⇒ ⇒ 差异**只在错误消息**。

    * **V-16**（形态）：元组**非空** · **不含** `__start__` · 目标**恰为一个** ·
      目标 **MUST NOT** 为 `__end__`（**X-04** · 上游静默 no-op · 比上游**更严**）；
    * **V-2**（语义）：**每个**源 MUST 在节点表里（**点名全部**缺失者）·
      **目标** MUST 在节点表里（**点名该目标**）。
    """
    # ── V-16（形态校验 · MUST 先于 V-2）──
    if not source:
        raise ValueError(
            f"Multi-source edge {source!r} must have at least one source (V-16)"
        )
    if _START_MARKER in source:
        raise ValueError(
            f"Multi-source edge {source!r} must not contain the entry marker "
            f"{_START_MARKER!r} (V-16)"
        )
    if len(targets) != 1:
        raise ValueError(
            f"Multi-source edge {source!r} must have exactly one target, "
            f"got {len(targets)} (V-16)"
        )
    target = targets[0]
    if target == _TERMINAL_MARKER:
        raise ValueError(
            f"Multi-source edge {source!r} must not target the terminal marker "
            f"{_TERMINAL_MARKER!r} (V-16)"
        )
    # ── V-2（语义校验族 · 缺源 / 缺目标）──
    missing = [name for name in source if name not in spec.nodes]
    if missing:
        raise ValueError(
            f"Multi-source edge {source!r} has sources not in the node table: "
            f"{missing!r} (V-2)"
        )
    if target not in spec.nodes:
        raise ValueError(
            f"Multi-source edge target {target!r} is not in the node table (V-2)"
        )


def _source_version(state: SchedulerState, ident: str) -> int:
    """一个**边触发源**的版本 = **源节点的执行版本**（每执行成功一次 +1）。

    ⚠️ **入口哨兵**（``__start__``）的版本**恒为 1** —— 它对应上游「入口边只写过一次」
    （上游 ``START`` 常量 · ``langgraph/constants.py:30``；入口边的写法
    ``add_edge(START, "a")`` · ``langgraph/graph/state.py:321``）⇒ 入口节点**只在第 1 轮**
    被触发一次（与上游同款）。
    """
    if ident == _START_MARKER:
        return 1
    return state.node_versions.get(ident, 0)


def _run_channels(spec: GraphSpec, state: SchedulerState) -> dict[str, Channel]:
    """返回**本次运行**使用的通道实例映射（**上游同款** · 2026-11-12 P2-b）。

    ⚠️ **上游模型**（``langgraph/pregel/_checkpoint.py:229-277`` 的
    ``channels_from_checkpoint``）：图规格里的通道是**规格**；**每次运行**从规格**新建**一份
    实例（``channels/base.py:60-65`` 的 ``from_checkpoint``）⇒ 同一张图规格**可并发跑多次**
    而**互不干扰**（多会话隔离 · 上游同款）。

    ⇒ freegraph 的等价落点：**运行期实例由**调度状态**持有**（``SchedulerState.channels``）
    ⇒ **每个调度状态 = 一次运行** ⇒ 不同调度状态之间**完全隔离**
    ⇒ 与 B7F1 的「调度状态**由调用方持有**」（裁定 16）**同源**。
    """
    instances = state.channels
    for key, template in spec.channels.items():
        if key not in instances:
            instances[key] = template.from_checkpoint(template.checkpoint())
    return instances


def _edge_sources(source: str | tuple[str, ...]) -> tuple[str, ...]:
    """一条边的**源节点名序列**（契约 §2.3 · research **DR-4**）。

    * ``str`` ⇒ ``(source,)``（**单源**）；
    * ``tuple`` ⇒ **去重保序**（``("a", "a")`` ⇒ ``("a",)`` ⇒ 等价**单源口径**）⇒
      **不报错**（**上游同款** · 上游 ``NamedBarrierValue(str, set(starts))`` 天然去重）。

    ⚠️ **规范化发生在「触发源枚举」期** ⇒ **不改写**用户的 ``edges``
    ⇒ ``GraphSpec`` 的**字段不可改写**口径（data-model §1）**零破**。
    """
    if isinstance(source, str):
        return (source,)
    sources: list[str] = []
    for item in source:
        if item not in sources:
            sources.append(item)
    return tuple(sources)


def _trigger_groups(
    spec: GraphSpec,
    state: SchedulerState,
    node_name: str,
    node: NodeSpec,
) -> list[tuple[tuple[str, str], ...]]:
    """枚举一个节点的**全部触发源组**（契约 §3.1 · research **DR-3**）。

    * **组** = ``tuple[边触发源, ...]``（成员的元组）⇒ **零新增类型**；
    * **每条入边一个组**（**不是**「每个源一个组」）；
    * **静态边与动态边同处「边」空间**（裁定 1 · FR-002）⇒ 两者**叠加**（FR-008）；
    * **去重**：按**成员集合**（``frozenset``）去重（**保序** ⇒ 先出现者胜出）⇒
      同成员的两条边合成**一组**（research **DR-3**）⇒ ⇒ 与上游「按**节点**去重」
      **同款**（实测 **E-11** · ``_algo.py:476-482``）。

    ⚠️ **动态边的存在性**由**动态边表**决定（源节点 → 其**最近一次执行**给出的
    跳转目标）⇒ 源节点再次执行且**不**给 ``goto`` ⇒ 旧目标**从本枚举中消失**
    ⇒ 该目标**不再**被触发（FR-009 · 裁定 2）⇒ ⇒ **动态边恒为单元素组**
    （**H-3** · B9F1 → B7F4）。
    """
    groups: list[tuple[tuple[str, str], ...]] = []
    for source, targets in spec.edges.items():
        if node_name in targets:
            groups.append(tuple((_EDGE_SOURCE, name) for name in _edge_sources(source)))
    for source, targets in state.dynamic_edges.items():
        if node_name in targets:
            groups.append(((_EDGE_SOURCE, source),))
    deduplicated: list[tuple[tuple[str, str], ...]] = []
    seen_members: set[frozenset[tuple[str, str]]] = set()
    for group in groups:
        members = frozenset(group)
        if members in seen_members:
            continue
        seen_members.add(members)
        deduplicated.append(group)
    return deduplicated


def _satisfied_groups(
    state: SchedulerState,
    node_name: str,
    groups: list[tuple[tuple[str, str], ...]],
) -> list[tuple[tuple[str, str], ...]]:
    """**已满足的组**（契约 §3.2 · research **DR-2**）。

    判定式（**逐字**）::

        ∃ 组 g ∈ groups(N) : ∀ s ∈ g : version(s) > seen(N)[s]

    * **组内全**（AND / 屏障）· **组间任一**（**上游同款** · 实测 **E-3 / E-4**）；
    * **单源口径的退化**：单源边的组是**单元素** ⇒ 上式**逐字退化**为 B7F1 的旧判定式
      「∃ 触发源 s ∈ sources(N) : version(s) > seen(N)[s]」⇒ **既有行为零变化**；
    * **判定与记账共用同一判据**（research **DR-2**）⇒ **不可能漂移**。

    ⚠️ **「无「有值」合取项」**：边触发源**没有**「值」概念（沿用 B7F1 契约 §3.2）⇒
    判定式**只有**版本比较。
    """
    seen = state.versions_seen.get(node_name, {})
    satisfied: list[tuple[tuple[str, str], ...]] = []
    for group in groups:
        if all(
            _source_version(state, ident) > seen.get((kind, ident), 0)
            for kind, ident in group
        ):
            satisfied.append(group)
    return satisfied



def _is_triggered(
    spec: GraphSpec,
    state: SchedulerState,
    node_name: str,
    node: NodeSpec,
    groups: list[tuple[tuple[str, str], ...]],
) -> bool:
    """判定一个节点本轮**是否被触发**（契约 §3.2 · 裁定 28）。

    判定式（**逐字**）::

        ∃ 组 g ∈ groups(N) : ∀ s ∈ g : version(s) > seen(N)[s]

    * **触发源恒为边**（**上游对齐 P1-0-2 · 2026-11-12**）：判定式 = ``version > seen``
      ⇒ 边触发源**无「值」概念**（源节点的执行版本本身即「发生过执行」的信号）。
      ⚠️ 原先还有「通道触发源」空间（``("c", key)``）⇒ **已删除**（上游同款 ·
      `langgraph/graph/state.py:1531-1532`）⇒ 节点**订阅**的通道**不再**是触发源
      ⇒ 「节点写自己订阅的通道」**不再**自触发。
    """
    return bool(_satisfied_groups(state, node_name, groups))


def _determine_triggers(spec: GraphSpec, state: SchedulerState) -> list[str]:
    """**触发判定**（阶段 ①）⇒ 被触发的节点名（**按节点名序**）。

    ⚠️ 调度器 MUST NOT 重排节点表（FR-013）⇒ 触发集合 MUST 按**节点名序**
    产出（契约 §4）。
    """
    triggered: list[str] = []
    for node_name, node in spec.nodes.items():
        groups = _trigger_groups(spec, state, node_name, node)
        if _is_triggered(spec, state, node_name, node, groups):
            triggered.append(node_name)
    # ⚠️ **上游同款**（2026-11-12 · P2-c）：上游把候选节点**按名字排序**
    # （``langgraph/pregel/_algo.py:482`` 的 ``sorted(triggered_nodes)``）⇒
    # 同轮的执行顺序与**同通道的写入顺序**都随之按**节点名**排列
    # （``_algo.py:256`` 的 ``sorted(tasks, key=task_path_str(...))`` ⇒ PULL 路径
    # 即 ``("__pregel_pull", <节点名>)``）⇒ **差分测试**才可能逐项相等。
    # ⇒ 原「节点表（声明）顺序」的承诺（FR-013 · 裁定 9）**已被取代**。
    triggered.sort()
    return triggered


def _consume_versions(
    state: SchedulerState,
    node_name: str,
    groups: list[tuple[tuple[str, str], ...]],
) -> None:
    """**消费**一个节点的**已满足的组**的当前版本（阶段 ② · 裁定 16 · T056）。

    * 节点被**准备执行**时 ⇒ ``seen(N)[s] = version(s)``（**对已满足的组的
      全部成员** · **逐源各一条**）；
    * ⇒ **同一版本的同一触发源 MUST NOT 重复触发同一节点**（FR-004）；
    * ⇒ 一个触发源的推进 MUST **不**掩盖另一个触发源的推进（FR-003 · SC-003）。

    ⚠️ **范围 = 只消费「已满足的组」**（契约 §3.3 · research **DR-2 / DR-11**）⇒
    **未满足的组不记账** ⇒ 屏障**后来齐了仍能再次触发**（**上游同款** · 实测 **E-5**）
    ⇒ ⇒ **单源口径的等价性**：单源组的「已满足」⟺ ``version > seen`` ⇒ 记账后
    ``seen = version``；**未满足** ⇒ ``version ≤ seen`` ⇒ 版本**只增不减** ⇒
    ``version == seen`` ⇒ 旧口径的「记 ``seen = version``」是**同值记账**
    ⇒ **可观察行为零变化** ⇒ **既有断言一条不删**。

    ⚠️ **消费时点 = plan（任务准备）阶段** —— 与上游的 apply 阶段**不同**
    ⇒ 登记为 **DR-1**（已知边界 · 只登记 · 不改判据）。
    """
    seen = state.versions_seen.setdefault(node_name, {})
    for group in groups:
        for kind, ident in group:
            seen[(kind, ident)] = _source_version(state, ident)


def _node_input(
    spec: GraphSpec, state: SchedulerState, node: NodeSpec
) -> dict[str, Any]:
    """构造一个节点的**入参**（阶段 ② · FR-008 · 裁定 2 · 裁定 26）。

    * 入参 MUST 由 **B5F2 的稀疏读原语**产出 ⇒ 复用
      :func:`freegraph.runtime.read_channels`（MUST NOT 在调度层另写一份）；
    * 子映射 MUST 按「**通道映射的顺序**」构造（**不是**订阅声明的顺序）
      ⇒ 入参的 key 顺序与**整张状态表**的 key 顺序**天然一致**；
    * 结果只含「订阅集 ∩ 有值集」⇒ **无值通道的 key MUST NOT** 出现在入参中
      （**C4**）。
    """
    channels = _run_channels(spec, state)
    subset = {
        key: channel for key, channel in channels.items() if key in node.subscribes
    }
    return read_channels(subset)


def _normalize_node_result(
    result: Any,
    node_names: Container[str],
) -> dict[str, Any]:
    """**归一**节点返回值 —— 三形态 → **一种内部形状**（契约 §2）。

    **归一后的统一形状**（内部中间产物 · **不进公开面**）::

        {"writes": dict[str, tuple[Any, ...]], "gotos": tuple[str, ...]}

    * ``writes`` —— **待写入**（每 key 一个**值序列** · 键序 = 归一顺序）；
    * ``gotos`` —— **跳转目标**（**保序去重**）。

    **三种合法形态**（契约 §2 · FR-001）：

    ============================ ==================================== ==========
    形态                         语法                                   归一结果
    ============================ ==================================== ==========
    **部分状态**                 ``dict``                               该 dict 的 items
    **单条命令**                 ``Command``                            ``update`` / ``goto``
    **命令列表**                 ``list[Command | dict]``              按**列表顺序**归入
    ============================ ==================================== ==========

    ⚠️ **归一是唯一的新增概念** ⇒ 三形态归一后**只有一种内部表示** ⇒
    「未知 key 报错」「归约器语义」「批量合并」「原子性」**全部复用 B7F1 的
    同一条路径**（裁定 4 · FR-004）。

    ⚠️ **失败信号**（契约 §7 · V-9…V-11）：

    * **V-9**（返回值形态非法 · 含 ``None``）⇒ 内置 ``TypeError``；
    * **V-10**（命令列表的**元素**类型非法）⇒ 内置 ``TypeError``；
    * **V-11**（``Command.update`` **不是** ``dict``）⇒ 内置 ``TypeError``。

    .. note::
       **骨架期**（Phase 2 ⇒ 各故事落地前）：``Command`` 与**命令列表**两种形态
       **一律**抛 ``NotImplementedError`` ⇒ 各故事的用例 MUST **先写 · 先失败**
       （先红后绿）⇒ 实现由各用户故事**分摊**（T014 / T018）。
    """
    if result is None:
        # ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游 ``graph/state.py:1459-1460``
        # 的 ``if input is None: return None``）⇒ **无写入**（**不是**错误）。
        return {"writes": {}, "gotos": ()}
    if isinstance(result, dict):
        return {
            "writes": {key: (value,) for key, value in result.items()},
            "gotos": (),
        }
    if isinstance(result, Command):
        return _normalize_command(result, node_names)
    if isinstance(result, list):
        return _normalize_command_list(result, node_names)
    raise TypeError(
        f"Node result must be a dict, a Command or a list of them, "
        f"got {type(result).__name__} (V-9)"
    )


def _normalize_command(
    command: Command,
    node_names: Container[str],
) -> dict[str, Any]:
    """**归一**单条命令（契约 §2 · FR-003 · FR-004 · FR-010）。

    * ``update`` —— ``None`` ⇒ **无写入**（该位**未提供**）；``dict`` ⇒ 逐 key
      归入待写入（**空** ``dict`` ⇒ **无写入** · 该位**不产生动作**）；
      **其它类型** ⇒ 内置 ``TypeError``（**V-11** · FR-010）；
    * ``goto`` ⇒ 交由 :func:`_parse_goto_targets` 解析（契约 §3）；
    * ``resume`` —— 本 feature **只接受**、**不产生任何效果**（FR-011 ·
      恢复语义归 **B10F1**）。

    ⚠️ **跳转与更新互不排斥**（FR-003）⇒ 两者**同时**归一进同一份结果 ⇒
    「只生效其一」的现象**物理不可能**发生。
    """
    if command.graph == Command.PARENT:
        # ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游 ``graph/state.py:1761-1762``
        # 抛 ``ParentCommand`` · 上游 ``errors.py:129-133``）⇒ **失败**而非静默。
        # ⇒ freegraph **无子图** ⇒ 抛 ``NotImplementedError``（与 ``goto=PARENT`` 的
        # **V-14** 同一口径：合法但本版未实现）⇒ **异常类型与上游不同 · 语义等价**。
        raise NotImplementedError(
            "Command.graph == Command.PARENT ('__parent__') is not supported "
            "in this version: 子图属 v2 能力（跨层传播归 C26 · v2）(V-14)"
        )
    update = command.update
    if update is None:
        writes: dict[str, tuple[Any, ...]] = {}
    elif isinstance(update, dict):
        writes = {key: (value,) for key, value in update.items()}
    elif isinstance(update, (list, tuple)) and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
        for item in update
    ):
        # ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游 ``langgraph/types.py:836-840``）：
        # 上游接受 **list/tuple of 2-tuples**（元素**必须是 tuple** · 键**必须是 str**）
        # ⇒ 逐条照抄（含「列表元素不算」的细节）。
        writes = {key: (value,) for key, value in update}
    else:
        raise TypeError(
            f"Command.update must be a dict or None, got {type(update).__name__} (V-11)"
        )
    return {"writes": writes, "gotos": _parse_goto_targets(command.goto, node_names)}


def _normalize_command_list(
    commands: list[Any],
    node_names: Container[str],
) -> dict[str, Any]:
    """**归一**命令列表（契约 §2 · FR-001 · FR-004 · 裁定 15）。

    * 元素 MUST 是 ``Command`` 或 ``dict`` ⇒ 其它类型 ⇒ 内置 ``TypeError``
      （**V-10**）；
    * 各元素的写入按**列表顺序**归入**同一份**待写入 ⇒ 归约型通道按该顺序
      归约（与上游 ``_get_updates`` 的 ``updates.extend(...)`` **逐字一致**）
      ⇒ **MUST NOT** 让「后一条命令覆盖前一条」（**值序列** ⇒ 同 key 的多个值
      **依次入列**）；
    * 各条命令的 ``goto`` 各自成边 ⇒ **并集**（**保序去重**）；
    * **空列表** ⇒ **明确无操作**（零写入 + 零跳转）。
    """
    if not commands:
        # ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游 ``graph/state.py:1488-1492``）：
        # 上游的判据是 ``isinstance(input,(list,tuple)) and input and any(...)``
        # ⇒ **空列表落 ``else``** ⇒ 抛 ``InvalidUpdateError("Expected dict, got []")``
        # ⇒ freegraph 原先「空列表 = 无操作」⇒ **更宽** ⇒ 本次**照抄上游**（改为失败）。
        raise TypeError(
            "Node result must be a dict, a Command or a list of them, "
            "got an empty list (V-9)"
        )
    writes: dict[str, tuple[Any, ...]] = {}
    gotos: list[str] = []
    for element in commands:
        if isinstance(element, Command):
            part = _normalize_command(element, node_names)
        elif isinstance(element, dict):
            part = {
                "writes": {key: (value,) for key, value in element.items()},
                "gotos": (),
            }
        else:
            raise TypeError(
                f"Command list elements must be a Command or a dict, "
                f"got {type(element).__name__} (V-10)"
            )
        for key, values in part["writes"].items():
            writes[key] = writes.get(key, ()) + tuple(values)
        for target in part["gotos"]:
            if target not in gotos:
                gotos.append(target)
    return {"writes": writes, "gotos": tuple(gotos)}


def _parse_goto_targets(
    goto: Any,
    node_names: Container[str],
) -> tuple[str, ...]:
    """**解析** ``Command.goto`` ⇒ 跳转目标（契约 §3 · FR-007）。

    ================================ ==================================== ==========
    输入                             解析结果                              说明
    ================================ ==================================== ==========
    ``None``                         无跳转                                该位**未提供**
    ``str``（**先判**）              **一个**目标                           见下
    ``Sequence[str]``（非空）        **多个**目标（**保序去重**）            每条各自成边
    ``Sequence[str]``（空）          无跳转                                该位不产生动作
    终止标记 ``"__end__"``           无跳转                                该位不产生动作
    ``Command.PARENT``               **显式失败**                          ``NotImplementedError``
    其它 ``str``                     **显式失败**                          ``ValueError``
    其它类型 / 序列含非 ``str``      **显式失败**                          ``TypeError``
    ================================ ==================================== ==========

    ⚠️ **``str`` MUST 先判**（``str`` 本身也是 ``Sequence[str]`` ⇒ 顺序判断会
    把它拆成字符序列 —— L1 docstring 逐字点名）。

    ⚠️ **终止标记以字面量判定**（L2 **MUST NOT** import 门面 · ARCH-1）⇒
    门面 ``END`` 的值 MUST 与该字面量**逐字相等**（**可自动核对** · 裁定 6）。

    ⚠️ **失败信号 MUST 分开**（裁定 7 · 澄清轮第 2 次 **Q2**）：

    * **V-12**（形态非法）⇒ 内置 ``TypeError``；
    * **V-13**（目标不在节点表 / 空串 / ``START``）⇒ 内置 ``ValueError``
      （**点名目标**）；
    * **V-14**（``goto == Command.PARENT``）⇒ 内置 ``NotImplementedError``
      （**点名 ``__parent__``** + 「子图属 v2 能力」）⇒ 「**写错了**」与
      「**合法但未实现**」**可区分**。

    ⚠️ **形态校验先于语义校验**：序列里**任一**元素**不是** ``str`` ⇒ 先抛
    ``TypeError``（V-12）⇒ 再逐个做**目标**校验 ⇒ 「序列含非 ``str``」**恒**是
    **类型错误**（与 spec Edge Cases 的逐字口径一致）。
    """
    if goto is None:
        return ()
    if isinstance(goto, str):
        return _parse_goto_target(goto, node_names)
    if isinstance(goto, Sequence):
        items = list(goto)
        for item in items:
            if not isinstance(item, str):
                raise TypeError(
                    f"Command.goto sequence items must be str, "
                    f"got {type(item).__name__} (V-12)"
                )
        targets: list[str] = []
        for item in items:
            for target in _parse_goto_target(item, node_names):
                if target not in targets:
                    targets.append(target)
        return tuple(targets)
    raise TypeError(
        f"Command.goto must be a str or a sequence of str, "
        f"got {type(goto).__name__} (V-12)"
    )


def _parse_goto_target(
    target: str,
    node_names: Container[str],
) -> tuple[str, ...]:
    """**解析**单个跳转目标（契约 §3 · FR-007 · V-13 / V-14）。

    * ``Command.PARENT`` ⇒ 内置 ``NotImplementedError``（**V-14**）；
    * 终止标记 ⇒ **无跳转**（该位不产生动作）；
    * 空串 / ``START`` / 不在节点表 ⇒ 内置 ``ValueError``（**V-13** ·
      **点名目标**）。
    """
    if target == _RESERVED_NODE_NAME:
        raise NotImplementedError(
            "Command.goto target '__parent__' (Command.PARENT) is not supported "
            "in this version: 子图属 v2 能力（跨层传播归 C26 · v2）(V-14)"
        )
    if target == _TERMINAL_MARKER:
        return ()
    if not target or target == _START_MARKER or target not in node_names:
        raise ValueError(
            f"Command.goto target {target!r} is not a node in the graph (V-13)"
        )
    return (target,)


def _execute_node_pure(
    spec: GraphSpec,
    node: NodeSpec,
    node_input: dict[str, Any],
) -> dict[str, Any]:
    """**纯执行**一个节点（阶段 ③ · FR-009 · FR-013 · FR-015 · FR-001）。

    * 只调 ``node.run`` + :func:`_normalize_node_result` **归一**
      ⇒ **零共享状态写**（并发执行的前提 · FR-010 · 裁定 11）；
    * 节点抛出的异常 MUST **原样**向上传播（**不**包装 · **不**吞掉）
      ⇒ ``caught is raised_by_node`` 成立（B7F1 契约 **I-15** 不破）；
    * 返回值 MUST 是 ``dict`` / ``Command`` / ``list[Command | dict]`` 之一
      （**FR-001**）⇒ 其它类型（含 ``None``）⇒ **显式失败**（内置
      ``TypeError`` · **V-9**）；
    * 返回值经 :func:`_normalize_node_result` **归一** ⇒ 待写入交给**既有的**
      :func:`_collect_writes` / :func:`_merge_writes`（MUST NOT 另写合并路径）；
    * ⚠️ **本函数 MUST NOT** 触碰 ``SchedulerState`` ⇒ 落回由
      :func:`_commit_outcome` 在**轮末**统一做（阶段 ③′）。
    """
    result = node.run(node_input)
    return _normalize_node_result(result, spec.nodes)


def _commit_outcome(
    state: SchedulerState,
    node_name: str,
    outcome: _TaskOutcome,
) -> None:
    """把一个**成功完成**的节点的结果**落回**调度状态（阶段 ③′ · FR-010 · 裁定 11）。

    * ``state.node_versions[node_name]`` **+1**（边触发源的版本）；
    * ``state.dynamic_edges[node_name]`` **整体替换**（含**空集** ⇒ 旧的 ``goto``
      目标被清空 · FR-009）；
    * ⚠️ **轮末**才落回 ⇒ 出错轮**一个都不落回** ⇒ 消除「值没合并、版本却推进了」的
      **幽灵触发**（FR-010 · SC-008 · 裁定 11）。
    """
    state.dynamic_edges[node_name] = outcome.gotos
    state.node_versions[node_name] = state.node_versions.get(node_name, 0) + 1


def _collect_writes(
    executed: list[str],
    results: dict[str, dict[str, tuple[Any, ...]]],
) -> dict[str, dict[str, tuple[Any, ...]]]:
    """**收集待写入**（阶段 ④ · FR-006）。

    * 产出**待写入**并**按节点分组**保留（节点名 → 通道 key → 值序列）
      ⇒ B8F1 的 fresh 读复用前提；
    * **``Command.update`` 的写入归到**返回该命令的那个节点**名下（裁定 16 ·
      SC-022）⇒ **归一**已在**执行阶段**完成 ⇒ 本阶段**只收集**、**不**写入；
    * 执行期间通道的**正式值 MUST NOT** 被改写 ⇒ 本阶段**只收集**、**不**写入。
    """
    pending: dict[str, dict[str, tuple[Any, ...]]] = {}
    for node_name in executed:
        writes = pending.setdefault(node_name, {})
        for key, values in results[node_name].items():
            writes[key] = writes.get(key, ()) + tuple(values)
    return pending


def _group_writes(
    spec: GraphSpec,
    pending: dict[str, dict[str, tuple[Any, ...]]],
) -> dict[str, list[Any]]:
    """把待写入**按通道分组**（值按**节点名序**排列 · 契约 §5.1）。"""
    grouped: dict[str, list[Any]] = {}
    # ⚠️ **上游同款**（P2-c）：同通道的写入顺序 = **节点名序**（上游
    # ``langgraph/pregel/_algo.py:256``）⇒ 合并顺序**可复现**且与上游**逐项相等**。
    for node_name in sorted(spec.nodes):
        writes = pending.get(node_name)
        if not writes:
            continue
        for key, values in writes.items():
            grouped.setdefault(key, []).extend(values)
    return grouped


def _reject_unknown_keys(grouped: dict[str, list[Any]], channels: dict[str, Channel]) -> None:
    """**未知 key 校验**（FR-007 · C6 · 校验规则 **V-5**）。

    * 待写入中出现**通道映射之外**的 key ⇒ 抛 ``InvalidUpdateError``
      （**L1 契约层已冻结**）；
    * 其 ``invalid_keys`` MUST 列出**全部**未知 key；
    * MUST 在**任何写入被合并之前**完成 ⇒ 一轮内同时命中多类错误时**只抛第一个**
      （契约 §5.1 的固定校验顺序）。
    """
    unknown = [key for key in grouped if key not in channels]
    if unknown:
        raise InvalidUpdateError(unknown)


def _reject_multi_writes(
    channels: dict[str, Channel], grouped: dict[str, list[Any]]
) -> None:
    """**覆盖型多写**校验（FR-005 ② · 校验规则 **V-6**）。

    * 一轮内同一通道收到**多于一个**值且该通道是**单值语义** ⇒ 抛
      ``InvalidChannelUpdateError``（**B5F1 既有类型** · **零新增错误类型**）
      ⇒ 其 ``key`` 字段 MUST 指向该通道；
    * MUST **先检测后写入** ⇒ 抛错时该通道的值**不变**；
    * MUST 在**任何写入被合并之前**完成 ⇒ 整轮原子（契约 §5.1 的固定校验顺序）。

    ⚠️ 「单值语义」的判定 = 该通道**没有归约器**（B5F1 的通道契约：只有
    **归约型**通道能接受一次写入里的多个值）—— 与 FR-014 冻结的**路由型**
    判定（``isinstance(channel, EphemeralValue)``）**是两种不同的判定**。
    """
    for key, values in grouped.items():
        if len(values) > 1 and channels[key].reducer is None:
            raise InvalidChannelUpdateError(
                key, received_count=len(values), expected_count=1
            )


def _snapshot_channel(channel: Channel) -> tuple[bool, Any]:
    """取一个通道的**快照**（值 / 有无值）—— 合并**首次写入之前**（契约 §5.4）。"""
    if channel.is_available():
        return True, channel.get()
    return False, None


def _rollback(
    channels: dict[str, Channel], snapshots: dict[str, tuple[bool, Any]]
) -> None:
    """**逐通道回滚**（契约 §5.4 · 裁定 29）。

    * 回滚顺序 MUST 与合并顺序一致（按**通道映射顺序**）；
    * 快照**有值** ⇒ ``clear()`` + ``update([快照值])``（**不套**归约器
      ⇒ 逐字还原）；
    * 快照**无值** ⇒ **只** ``clear()``（无值快照**不是**一个可写回的值）。
    """
    for key, (has_value, value) in snapshots.items():
        channel = channels[key]
        channel.clear()
        if has_value:
            channel.update([value])


def _merge_writes(
    spec: GraphSpec,
    state: SchedulerState,
    pending: dict[str, dict[str, tuple[Any, ...]]],
) -> set[str]:
    """**写入合并**（阶段 ⑤ · FR-005 · FR-032 · 契约 §5）。

    * **批量** ⇒ 每个通道**一次** ``Channel.update(values)``（MUST NOT 逐次调用
      ⇒ 归约型**不**退化成「后写覆盖先写」）；
    * 合并顺序 MUST 按**通道映射顺序** ⇒ 合并与回滚**可复现**；
    * **全部合并成功后**才对「写入了值」的通道各 **+1**（FR-002 ⚠️）⇒ 本轮出错
      ⇒ **一个通道的版本都不推进**（与值的回滚**同进同退**）；
    * 返回「本轮写入了值」的通道集合（``update()`` 返回**真**）。
    """
    grouped = _group_writes(spec, pending)
    channels = _run_channels(spec, state)
    _reject_unknown_keys(grouped, channels)
    _reject_multi_writes(channels, grouped)
    snapshots = {
        key: _snapshot_channel(channels[key])
        for key in channels
        if key in grouped
    }
    written: set[str] = set()
    try:
        for key, channel in channels.items():
            values = grouped.get(key)
            if values is None:
                continue
            if channel.update(values):
                written.add(key)
    except Exception:
        _rollback(channels, snapshots)
        raise
    for key in written:
        state.channel_versions[key] = state.channel_versions.get(key, 0) + 1
    return written


def _clear_step_end(
    spec: GraphSpec, state: SchedulerState, written: set[str]
) -> None:
    """**步末清空**（阶段 ⑤ 的收尾 · FR-014 · 裁定 10 · 裁定 33）。

    * **只**对**路由型**通道调 ``clear()``（覆盖型 / 归约型 MUST **保留**其值）；
    * **且只清「本轮未被写入的」**路由型通道 ⇒ 本轮写过的路由型通道的值
      **存活到下一轮**（⇒ B8F1 的条件边路由读得到「本节点本次写入」）；
    * **清空不是写入** ⇒ 通道版本 MUST **不**推进；
    * 「路由型」MUST 以 ``isinstance(channel, EphemeralValue)`` 判定
      ⇒ MUST NOT 用「``reducer is None``」等**启发式**（FR-014 ⚠️）。
    """
    # ⚠️ **上游同款**（2026-11-12 · P2-a）：上游对「本步**未**更新**且**仍有值**」的通道
    # 调 ``update(EMPTY_SEQ)``（上游 ``langgraph/pregel/_algo.py:326-333``）⇒
    #   * **路由型** ⇒ ``EphemeralValue.update([])`` ⇒ **清空**（上游
    #     ``langgraph/channels/ephemeral_value.py:56-61``）
    #   * **覆盖型 / 归约型** ⇒ ``update([])`` ⇒ **no-op**（值保留；上游
    #     ``last_value.py:57-58`` · ``binop.py:124-125``）
    # ⇒ 与 freegraph 原先「只对路由型调 ``clear()``」的**可观察语义等价**，但**机制**与上游**逐字同款**
    # ⇒ 自研的 ``clear()`` **不再是**调度层的写入口。
    for key, channel in _run_channels(spec, state).items():
        if key in written:
            continue
        if not channel.is_available():
            continue
        channel.update([])


def _run_round(
    spec: GraphSpec,
    state: SchedulerState,
    triggered: list[str],
    *,
    max_concurrency: int | None = None,
) -> tuple[list[str], dict[str, dict[str, tuple[Any, ...]]]]:
    """跑**一轮** super-step 的**七个阶段**（契约 §3 · FR-001）。

    ① **触发判定**已由调用方完成 ⇒ 本函数负责 ② 任务准备 · ③ **并发执行** ·
    ③′ **判定与落回** · ④ 写入收集 · ⑤ 写入合并（含步末清空）· ⑥ **收尾**。

    ⚠️ **阶段 ② MUST 在阶段 ③ 之前**完成（契约 §4 的顺序固定）⇒ 全部节点的
    入参与「已消费版本」都在**任何节点执行之前**确定 ⇒ 一个节点的执行**不**
    影响另一个节点的入参（FR-006 · C8 fresh 读的基础）。

    ⚠️ **阶段 ⑥ 是唯一的「抛出」点**（真实异常与中断**都**在 ⑥ 抛）⇒
    阶段 ③′ **只做判定与落回**、**不抛任何异常**（契约 §3）。
    """
    # ── ② 任务准备（入参在**任何节点执行前**固定 · FR-011） ──
    tasks: list[tuple[str, NodeSpec, dict[str, Any]]] = []
    for node_name in triggered:
        node = spec.nodes[node_name]
        groups = _trigger_groups(spec, state, node_name, node)
        satisfied = _satisfied_groups(state, node_name, groups)
        node_input = _node_input(spec, state, node)
        _consume_versions(state, node_name, satisfied)
        tasks.append((node_name, node, node_input))

    # ── ③ 并发执行（线程池 · 每轮新建 + 关闭 ⇒ 零悬挂线程 · FR-018） ──
    started: list[str] = []

    # ⚠️ **运行级**现场表 MUST 在**主线程**读出（**工作线程不继承**
    # ``contextvars`` · **实测**）⇒ ⇒ 在**闭包外**取一次 ⇒ ⇒ 工作线程
    # 显式拿到它（**B10F1** · 契约 §3 · 运行级行）。
    run_table = current_run_table()

    def _bind(
        node_name: str, fn: Callable[[], dict[str, Any]]
    ) -> Callable[[], dict[str, Any]]:
        def _inner() -> dict[str, Any]:
            started.append(node_name)  # ⚠️ list.append 在 CPython 下是原子的
            # ⚠️ **B10F1**：**任务级**现场（``interrupt()`` 的运行期上下文）
            # MUST 在**节点执行**期间挂上 ⇒ ⇒ 复原用 ``reset(token)``
            # ⇒ ⇒ 线程池**复用线程**时**零脏状态**（契约 §3 · 任务级行）。
            with bind_task(node_name, run_table):
                return fn()

        return _inner

    cap = _resolve_cap(len(tasks), max_concurrency)
    outcomes = run_tasks_concurrently(
        [
            (node_name, _bind(node_name, partial(_execute_node_pure, spec, node, node_input)))
            for node_name, node, node_input in tasks
        ],
        cap=cap,
    )
    # ⚠️ **被取消**的任务**从未被启动** ⇒ 不产出结果槽 ⇒ MUST NOT 出现在
    # ``executed`` 里（FR-009 · 裁定 22）⇒ 用「实际启动过的节点名」对齐结果槽。
    by_name: dict[str, _TaskOutcome] = dict(zip(sorted(started), outcomes))

    # ── ③′ 判定与落回（**不抛任何异常** · 契约 §3 / §5） ──
    error = _first_error(by_name)
    interrupts = _collect_interrupts(by_name)
    interrupted = {name for name, outcome in by_name.items() if outcome.interrupts}
    snapshot_versions = dict(state.node_versions)
    snapshot_edges = dict(state.dynamic_edges)
    if error is None:
        # 成功节点**照常落回**（**节点名序**）· 被中断节点**不**落回（它**没完成**）
        for node_name in sorted(by_name):
            if node_name in interrupted:
                continue
            _commit_outcome(state, node_name, by_name[node_name])
    # ⚠️ **出错轮**：**不落回**任何调度状态（整轮原子 · FR-010 · SC-008）

    # ── ④ 写入收集（按节点分组 · 零改动） ──
    succeeded = [
        name
        for name in sorted(by_name)
        if name not in interrupted and by_name[name].error is None
    ]
    pending = _collect_writes(succeeded, {name: by_name[name].writes for name in succeeded})

    # ── ⑤ 写入合并（**出错轮不进入**本阶段 ⇒ 一个都不合并 · X-3） ──
    if error is None:
        try:
            written = _merge_writes(spec, state, pending)
        except BaseException:
            # ⚠️ **合并阶段出错** ⇒ 调度状态也**不落回**（FR-010：任何环节出错 ⇒
            # 执行版本与跳转目标都不推进 ⇒ 无「值没合并、版本却推进」的幽灵触发）
            _restore_scheduler_versions(state, snapshot_versions, snapshot_edges)
            raise
        _clear_step_end(spec, state, written)

    # ── ⑥ 收尾（**唯一的「抛出」点**） ──
    executed = tuple(sorted(by_name))
    if error is not None:
        # ⚠️ **其余并发失败**以**附注**记录（固定格式 · 三样齐全 · V-15）
        attach_failure_notes(error, [(name, by_name[name]) for name in sorted(by_name)])
        # ⚠️ **真实异常优先** ⇒ 中断元组**随之丢弃**（上游同款 · FR-014 · X-4）
        raise error
    if interrupts:
        # ⚠️ **先合并、后抛** ⇒ 用户接住异常后从调度状态读到的**已是合并后**的值
        raise GraphInterrupt(interrupts)
    return list(executed), pending


def _first_error(by_name: dict[str, _TaskOutcome]) -> BaseException | None:
    """取「**节点名序**最靠前」的失败节点的异常（**原对象** · FR-003 · X-1）。

    ⚠️ MUST **NOT** 依赖「谁先跑完」（完成时刻的竞态）⇒ **确定性** ⇒
    ⚠️ **比上游更严**（上游从 ``done`` **集合** ``pop()`` ⇒ 竞态 · 实测 26/24）
    ⇒ 偏离登记 **X-1**。
    """
    for node_name in sorted(by_name):
        error = by_name[node_name].error
        if error is not None:
            return error
    return None


def _collect_interrupts(by_name: dict[str, _TaskOutcome]) -> tuple[Interrupt, ...]:
    """收集本轮**全部**节点的 ``GraphInterrupt`` 载荷（**元素** · **节点名序**）。

    * 元素 = 该节点 ``GraphInterrupt.args[0]``（≡ ``payload``）的**元素**
      （``Interrupt`` 对象 · **原样**）⇒ ⚠️ MUST **NOT** 是 ``payload`` **本身**
      （那是元组 ⇒ 嵌套元组 ⇒ 元素**没有** ``.value`` / ``.id``）（裁定 7）；
    * 顺序 = **节点名序** ⇒ ⚠️ **比上游更严**（上游顺序**竞态** · 实测 199/1）
      ⇒ 偏离登记 **X-7**；
    * 一个节点**至多**贡献一个中断（上游同款）⇒ 元组长度 == 本轮中断的节点数。
    """
    collected: list[Interrupt] = []
    for node_name in sorted(by_name):
        collected.extend(by_name[node_name].interrupts)
    return tuple(collected)


def _restore_scheduler_versions(
    state: SchedulerState,
    snapshot_versions: dict[str, int],
    snapshot_edges: dict[str, tuple[str, ...]],
) -> None:
    """把**本轮已落回**的调度状态**回退**（合并阶段出错时 · FR-010）。

    * 恢复 ``node_versions`` 与 ``dynamic_edges`` 到**轮初**的快照
      ⇒ 「值没合并、版本却推进了」的**幽灵触发**被消除；
    * ⚠️ 「**已消费版本**」（``state.versions_seen``）**不回滚** ⇒
      **上游同款**（上游的「已消费」记录同样**不**回滚）⇒ ⇒ MUST **NOT** 实现成
      「自研的版本回滚」（那会落在宪法原则 XI 的「必须自研区」之外 · FR-010 的
      「已消费版本不回滚」补记段）。
    """
    state.node_versions.clear()
    state.node_versions.update(snapshot_versions)
    state.dynamic_edges.clear()
    state.dynamic_edges.update(snapshot_edges)


def _sparse_state(spec: GraphSpec, state: SchedulerState) -> dict[str, Any]:
    """取本轮**结束**时的**稀疏**通道状态（只含**当前有值**的通道）。"""
    return read_channels(_run_channels(spec, state))


def _validate_max_concurrency(max_concurrency: int | None) -> None:
    """校验 ``max_concurrency`` 的取值（**入口即失败** · FR-017 · V-18）。

    * 必须是 ``int`` 或 ``None`` ⇒ 否则内置 ``TypeError``；
    * ``int`` MUST **≥ 1** ⇒ 否则内置 ``ValueError``；
    * 两者都 MUST **点名该参数**；
    * ⚠️ **校验时机 = 入口** ⇒ 即**一进门就报错** ⇒ **哪怕本轮没有任何节点要跑**
      也 MUST 报错（**上游同款** · 标准库线程池在**构造时**校验 ``max_workers``）
      ⇒ ⇒ 「零节点的一轮 MUST NOT 创建任何线程」（FR-001）**与之不冲突**
      （**不建池** ≠ **不校验参数**）；
    * ⚠️ ``bool`` 是 ``int`` 的子类 ⇒ 上游 ``ThreadPoolExecutor(max_workers=True)``
      **照单全收**（当作 1）⇒ freegraph **同款** ⇒ MUST **NOT** 单独把 ``bool``
      拒之门外。
    """
    if max_concurrency is None:
        return
    if not isinstance(max_concurrency, int):
        raise TypeError(
            f"max_concurrency must be an int or None, "
            f"got {type(max_concurrency).__name__}"
        )
    if max_concurrency < 1:
        raise ValueError(f"max_concurrency must be >= 1, got {max_concurrency!r}")


def run_super_step(
    spec: GraphSpec,
    state: SchedulerState,
    *,
    max_concurrency: int | None = None,
) -> SuperStepResult:
    """**单轮入口** —— 跑**一轮** super-step（七个阶段 · 顺序固定）。

    **签名**（**逐字冻结** · 契约 §1）::

        run_super_step(
            spec: GraphSpec, state: SchedulerState, *, max_concurrency: int | None = None
        ) -> SuperStepResult

    * 调度状态 **MUST 显式接收**（裁定 27）⇒ 与多轮入口的「MAY 省略」相对；
    * ``steps`` **恒为 1**（裁定 34 · SC-001 ③）；
    * 跑完一轮后**同样**执行**步末清空**（裁定 33）⇒ 两个入口的语义一致；
    * ``max_concurrency`` —— **keyword-only** · **兼容扩展**（带缺省值 ⇒ 既有调用方
      零改动）· **上游同名同义**（``RunnableConfig["max_concurrency"]``）
      ⇒ 缺省上限 ``min(32, cpu+4)``（**上游同款**）· 显式 ``N`` ⇒ 实际并发度
      ``min(本轮任务数, N)``（**N 不被 32 再夹**）· ``N = 1`` ⇒ **串行基线**
      （FR-017 · 裁定 2 / 18）。
    """
    _validate_max_concurrency(max_concurrency)
    triggered = _determine_triggers(spec, state)
    executed: list[str] = []
    pending: dict[str, dict[str, tuple[Any, ...]]] = {}
    if triggered:
        executed, pending = _run_round(
            spec, state, triggered, max_concurrency=max_concurrency
        )
        state.step += 1
    return SuperStepResult(
        state=_sparse_state(spec, state),
        executed=tuple(executed),
        node_writes=pending,
        steps=1,
    )


def run_super_steps(
    spec: GraphSpec,
    state: SchedulerState | None = None,
    *,
    max_steps: int = 10007,
    max_concurrency: int | None = None,
) -> SuperStepResult:
    """**多轮入口** —— 反复跑 super-step 直到**收敛**或**触到步数上限**。

    **签名**（**逐字冻结** · 契约 §1）::

        run_super_steps(
            spec: GraphSpec,
            state: SchedulerState | None = None,
            *,
            max_steps: int = 10007,
            max_concurrency: int | None = None,
        ) -> SuperStepResult

    * ``state`` —— 缺省新建一个 ⇒ 该次调用**内部自洽**、**不**继承此前任何
      调用的消费记录（裁定 27 · FR-004）⇒ 两个入口的「已消费版本」**不串扰**；
    * ``max_steps`` —— 步数上限，**缺省 10007**（**上游同款** · 上游
      ``langgraph/_internal/_config.py:32`` 的 ``DEFAULT_RECURSION_LIMIT = 10007``
      —— ⚠️ 上游可由环境变量 ``LANGGRAPH_DEFAULT_RECURSION_LIMIT`` 覆盖，freegraph
      **MUST NOT** 读环境变量（零环境变量红线）⇒ **硬编码** 10007；裁定 24 原写的
      「缺省 25 · 与上游一致」是**事实错误** ⇒ 本次订正）
      ``DEFAULT_RECURSION_LIMIT`` 逐字一致）⇒ 达到上限且仍有待执行任务 ⇒ 抛
      ``GraphRecursionError``（FR-011）；
    * ``max_concurrency`` —— **keyword-only** · 与单轮入口**同名同义**
      （FR-017 · 裁定 2 / 18）。

    ⚠️ **上限计「执行轮」**（真正执行了节点的轮数）⇒ **空轮不计入上限**；
    判定顺序 = ① 先判「任务集合为空 ⇒ 立即终止」② 再判「执行轮数 == 上限
    **且**下一轮任务集非空 ⇒ 抛错」（裁定 30 的判定顺序）。
    """
    _validate_max_concurrency(max_concurrency)
    scheduler_state = state if state is not None else SchedulerState()
    executed: list[str] = []
    pending: dict[str, dict[str, tuple[Any, ...]]] = {}
    steps = 0
    while True:
        triggered = _determine_triggers(spec, scheduler_state)
        steps += 1
        if not triggered:
            break
        if scheduler_state.step >= max_steps:
            raise GraphRecursionError(
                recursion_limit=max_steps, current_step=scheduler_state.step
            )
        round_executed, round_pending = _run_round(
            spec, scheduler_state, triggered, max_concurrency=max_concurrency
        )
        executed.extend(round_executed)
        for node_name, writes in round_pending.items():
            bucket = pending.setdefault(node_name, {})
            for key, values in writes.items():
                bucket[key] = bucket.get(key, ()) + values
        scheduler_state.step += 1
    return SuperStepResult(
        state=_sparse_state(spec, scheduler_state),
        executed=tuple(executed),
        node_writes=pending,
        steps=steps,
    )


# ── B10F1 · 图级入口（``run_graph``）与检查点接缝 ─────────────────────────


#: **保留通道名**（**上游同款 · 逐字**）—— ``__interrupt__``（中断留痕）/
#: ``__resume__``（恢复值）⇒ ⇒ 同一批常量也用作**结果字典的键名**
#: （上游用**同一个**常量 · 原则 XI ②）。
_INTERRUPT_CHANNEL = "__interrupt__"
_RESUME_CHANNEL = "__resume__"


def _pending_interrupts(
    pending_writes: Sequence[Any],
) -> dict[str, Interrupt]:
    """从 **pending writes** 里取该会话的**挂起中断集合**（契约 §6.2 第 2 步）。

    * ``pending_writes`` 的元素 = ``(task_id, channel, value)`` **三元组**
      （**上游同款** · DR-09）⇒ ⇒ 只取 ``channel == "__interrupt__"`` 的那些；
    * ``value`` = 该节点的中断载荷**元组** ⇒ ⇒ 取**首个**元素
      （一个节点**至多**贡献一个中断 · **上游同款**）；
    * ``task_id`` = **节点名**（freegraph 取舍 · DR-09）⇒ ⇒ 返回
      ``{节点名: Interrupt}``。
    """
    found: dict[str, Interrupt] = {}
    for entry in pending_writes or ():
        task_id, channel, value = entry
        if channel != _INTERRUPT_CHANNEL:
            continue
        items = tuple(value) if isinstance(value, (tuple, list)) else (value,)
        if items:
            found[task_id] = items[0]
    return found


def _pending_resume_values(
    pending_writes: Sequence[Any], node_name: str
) -> list[Any]:
    """取该节点**已累积**的恢复值序列（``__resume__`` 通道 · **上游同款**）。

    * ⚠️ **上游同款**（实测 E-17 / E-18）：任务自己的 ``__resume__`` 待写入
      装的是**累积列表** ⇒ ⇒ 第 ``index`` 次 ``interrupt()`` 取
      ``resume[index]`` ⇒ ⇒ **更早的**恢复值会被**复用**（E-18）；
    * ⚠️ **同一节点的多个** ``__resume__`` 待写入 ⇒ ⇒ **最后一个**胜
      （上游的 saver 对**同一任务 + 同一通道**是**覆盖**语义 ⇒ 只有一条）。
    """
    values: list[Any] = []
    for entry in pending_writes or ():
        task_id, channel, value = entry
        if channel != _RESUME_CHANNEL or task_id != node_name:
            continue
        values = list(value) if isinstance(value, (tuple, list)) else [value]
    return values


def _restore_scheduler(state: SchedulerState, data: Mapping[str, Any]) -> None:
    """按**调度账本****就地**重建调度状态（契约 §6.2 第 4 步 · H-5 ⑤）。

    * ⚠️ **就地**重建 ⇒ ⇒ 调用方持有的那一份 :class:`SchedulerState`
      **就是**本轮真正在用的那一份 ⇒ ⇒ 「调度状态由调用方持有」的既有口径
      **不破**（裁定 27）；
    * ⚠️ ``step`` **重新计数**（**不落盘** · 契约 §3）。
    """
    restored = SchedulerState.from_checkpoint(data or {})
    state.versions_seen.clear()
    state.versions_seen.update(restored.versions_seen)
    state.step = restored.step
    state.channel_versions.clear()
    state.channel_versions.update(restored.channel_versions)
    state.node_versions.clear()
    state.node_versions.update(restored.node_versions)
    state.dynamic_edges.clear()
    state.dynamic_edges.update(restored.dynamic_edges)


def _restore_channels(
    spec: GraphSpec, state: SchedulerState, values: Mapping[str, Any]
) -> None:
    """按**快照的稀疏状态**重建**通道实例**（契约 §6.2 第 4 步）。

    * **有值**的通道 ⇒ ``template.from_checkpoint(值)``（**现成** · 零新增）；
    * **无值**的通道 ⇒ ``template.from_checkpoint(template.checkpoint())``
      ⇒ ⇒ 保留模板的**初始值**（**不**凭空造值 · 与 B7F1 的
      ``_run_channels`` **同款**）。
    """
    instances: dict[str, Channel] = {}
    for key, template in spec.channels.items():
        if key in values:
            instances[key] = template.from_checkpoint(values[key])
        else:
            instances[key] = template.from_checkpoint(template.checkpoint())
    state.channels = instances


def _apply_input_writes(
    spec: GraphSpec, state: SchedulerState, values: Mapping[str, Any]
) -> set[str]:
    """把**图输入**按**通道写入**叠加上去（spec FR-013 末两行）。

    * **覆盖型通道 ⇒ 覆盖** · **归约型通道 ⇒ 追加** ⇒ ⇒ **复用** B5F1 的
      ``Channel.update``（每通道**一次** · 值序列 = **单元素**）
      ⇒ ⇒ **MUST NOT** 另写一条叠加路径（spec FR-013 末行）；
    * ⚠️ **未知 key** ⇒ 抛 ``InvalidUpdateError``（**L1 契约层已冻结** ·
      C6）⇒ ⇒ 与节点写入的失败信号**同款**；
    * ⚠️ **通道版本推进**（写入成功者 +1）⇒ ⇒ **下游**的**边触发**据此推进
      ⇒ ⇒ 触发判定与首次运行**同款**。
    """
    channels = _run_channels(spec, state)
    grouped = {key: [value] for key, value in values.items()}
    _reject_unknown_keys(grouped, channels)
    written: set[str] = set()
    for key, channel in channels.items():
        if key not in grouped:
            continue
        if channel.update(grouped[key]):
            written.add(key)
    for key in written:
        state.channel_versions[key] = state.channel_versions.get(key, 0) + 1
    return written


def _reset_entry_triggers(spec: GraphSpec, state: SchedulerState) -> None:
    """让**入口节点**在「会话连续 + 状态字典输入」时**重新触发**（上游同款）。

    ⚠️ **上游的机制**（**实测 E-26 ②**）：输入写入 ⇒ 上游的 ``__input__``
    通道版本推进 ⇒ ``__start__`` 节点**重跑** ⇒ 它**重写**各入口节点的
    ``branch:to:<节点>`` 通道 ⇒ ⇒ 入口节点的「已消费版本」**落后** ⇒ ⇒
    **重新触发** ⇒ ⇒ 其后继**级联**重跑。

    ⇒ freegraph 的等价落点（**纯边触发**模型 · **上游同款**）：把入口边
    （``__start__``）的**已消费版本**归零 ⇒ ⇒ 入口节点**重新触发**
    （``version > seen``）⇒ ⇒ 入口节点的**执行版本**推进 ⇒ ⇒ 其后继
    （**边**触发）**级联**重跑。

    ⇒ ⚠️ **只**归零**入口边**的已消费版本 ⇒ ⇒ **其它**触发源**不受影响**
    ⇒ ⇒ **与上游同款**（上游也只重写入口节点的 branch 通道）。
    """
    for source, targets in spec.edges.items():
        if source != _START_MARKER:
            continue
        for target in targets:
            seen = state.versions_seen.get(target)
            if seen is None:
                continue
            seen.pop((_EDGE_SOURCE, _START_MARKER), None)


def _suspend_metadata(
    next_nodes: Sequence[str],
    interrupts: Sequence[Interrupt],
    scheduler: Mapping[str, Any],
) -> dict[str, Any]:
    """产出**挂起时**写给 checkpointer 的 **metadata**（契约 §4 的写侧载荷）。

    * ``next`` —— **下一步要执行的节点名**（= 被中断的节点）⇒ ⇒ B14F1 据此
      复原 ``StateSnapshot.next``；
    * ``interrupts`` —— **本步**的中断集合 ⇒ ⇒ B14F1 据此复原
      ``StateSnapshot.interrupts``；
    * ``tasks`` —— **本步**的任务列表（v1 **恒空** · B15F1 之前无任务对象）；
    * ``scheduler`` —— **调度账本**（纯数据）⇒ ⇒ B14F1 据此复原
      ``get_tuple`` 返回值的 ``.scheduler``（契约 §2 / §3）。

    ⚠️ **纯数据**（可 JSON 序列化 · C19 ③）⇒ ⇒ B14F1 **只**需原样存取
    ⇒ ⇒ **零**耦合（契约 §3 末尾）。
    """
    return {
        "next": tuple(next_nodes),
        "interrupts": tuple(interrupts),
        "tasks": (),
        "scheduler": dict(scheduler),
    }


def _resume_target_nodes(
    snapshot: Any, interrupts: Mapping[str, Interrupt]
) -> tuple[str, ...]:
    """取**恢复轮**要**显式**跑的节点名（契约 §6.2 第 4 步 ④a）。

    * 优先取 ``StateSnapshot.next``（**上游同款** · 按 checkpoint 的 ``next``
      重建 · **不走**触发判定）⇒ ⇒ **不**重复触发；
    * **兜底**：快照没有 ``next`` ⇒ ⇒ 取**挂起中断**的节点名（**升序**）。
    """
    declared = tuple(getattr(snapshot, "next", ()) or ())
    if declared:
        return declared
    return tuple(sorted(interrupts))


def _run_graph_loop(
    spec: GraphSpec,
    state: SchedulerState,
    table: Mapping[str, Any],
    run_config: RunConfig,
    *,
    checkpointer: Any | None,
    first_round: Sequence[str] | None,
    max_steps: int,
    max_concurrency: int | None,
) -> SuperStepResult | InterruptResult:
    """跑**多轮** ⇒ **完成**（``SuperStepResult``）或**挂起**（``InterruptResult``）。

    * ``first_round`` —— **显式**指定的首轮节点（**不走**触发判定）⇒ ⇒
      恢复轮（``.snapshot.next``）与会话连续轮（``input=None``）**同款**；
    * ⚠️ **轮数口径**：``SuperStepResult.steps`` **含**那个「发现没任务了」的
      **空轮**（B7F1 冻结面）⇒ ⇒ 挂起时**没有**空轮 ⇒ ⇒ 两者的 ``steps``
      **计数口径刻意不同**（裁定 2 ③ · 不可直接比较）。
    """
    executed: list[str] = []
    pending: dict[str, dict[str, tuple[Any, ...]]] = {}
    steps = 0
    triggered: list[str] | None = list(first_round) if first_round is not None else None
    while True:
        if triggered is None:
            triggered = _determine_triggers(spec, state)
        steps += 1
        if not triggered:
            break
        if state.step >= max_steps:
            raise GraphRecursionError(
                recursion_limit=max_steps, current_step=state.step
            )
        try:
            round_executed, round_pending = _run_round(
                spec, state, triggered, max_concurrency=max_concurrency
            )
        except GraphInterrupt as exc:
            result = _suspend(spec, state, table, exc, steps=steps)
            if checkpointer is not None:
                # ⚠️ **挂起时** MUST **写**快照 + **待写入**（FR-012）⇒ ⇒
                # 挂起态**可被再次恢复**（闭环**可重复** · SC-013）。
                _write_suspend(
                    run_config,
                    checkpointer,
                    state,
                    result.state,
                    _produced_interrupts(table, result.interrupts),
                    result.interrupts,
                )
            return result
        executed.extend(round_executed)
        for node_name, writes in round_pending.items():
            bucket = pending.setdefault(node_name, {})
            for key, values in writes.items():
                bucket[key] = bucket.get(key, ()) + tuple(values)
        state.step += 1
        triggered = None
    return SuperStepResult(
        state=_sparse_state(spec, state),
        executed=tuple(executed),
        node_writes=pending,
        steps=steps,
    )


def _suspend(
    spec: GraphSpec,
    state: SchedulerState,
    table: Mapping[str, Any],
    exc: GraphInterrupt,
    *,
    steps: int,
) -> InterruptResult:
    """把**接住的** ``GraphInterrupt`` 转成**挂起态**结果（裁定 1 / 裁定 2）。

    * ``exc.args[0]`` = **元组**（上游同款）⇒ ⇒ 元素 = ``Interrupt``；
    * ⚠️ **真异常优先**（裁定 11）—— 真异常**在** ``_run_round`` 的阶段 ⑥
      **先于**中断抛出 ⇒ ⇒ 中断元组**被丢弃** ⇒ ⇒ 本函数**只**在
      **没有**真异常时被调用；
    * ⚠️ **MUST NOT** 另写一条中断收集路径（FR-004）⇒ ⇒ 直接复用 B12F1 的
      **合并抛出**语义。
    """
    interrupts = tuple(exc.args[0]) if exc.args else ()
    return InterruptResult(
        state=_sparse_state(spec, state),
        interrupts=interrupts,
        executed=tuple(sorted(table)),
        steps=steps,
    )


def _produced_interrupts(
    table: Mapping[str, Any], interrupts: Sequence[Interrupt]
) -> dict[str, Interrupt]:
    """取「**本轮**产生的」中断（按节点 · 契约 §6.2 写侧的粒度）。

    * ⚠️ **身份判定**（``is``）—— 运行级现场表里每个节点的 ``existing``
      **要么**是「**先前**挂起时的中断载荷」（**恢复路径**预置）**要么**是
      「**本轮**产生的载荷」（``interrupt()`` 挂起时写回）⇒ ⇒ 只有后者在
      **本轮**的合并元组里 ⇒ ⇒ 用**身份**判定**零歧义**；
    * ⇒ ⇒ **被恢复但**未**再次挂起**的节点**不**出现在写侧 ⇒ ⇒ 它的
      「先前载荷」**不**被当成新留痕 ✓。
    """
    produced: dict[str, Interrupt] = {}
    for node_name, scratchpad in table.items():
        payload = getattr(scratchpad, "existing", None)
        if payload is None:
            continue
        for item in interrupts:
            if item is payload:
                produced[node_name] = payload
                break
    return produced


def _write_suspend(
    run_config: RunConfig,
    checkpointer: Any,
    state: SchedulerState,
    values: Mapping[str, Any],
    produced: Mapping[str, Interrupt],
    all_interrupts: Sequence[Interrupt],
) -> None:
    """**挂起时**的**写侧**（契约 §4 · FR-012 · T041）。

    * ``put`` 写**快照**（``values`` = 该步合并后的**稀疏状态**）⇒
      ``metadata`` 携带「下一步要执行的节点名 / 本步的中断 / 调度账本」
      ⇒ ⇒ B14F1 据此复原 ``StateSnapshot`` 与 ``.scheduler``（契约 §2 / §3）；
    * ``put_writes`` 逐节点写**中断留痕**（通道名 ``__interrupt__`` ·
      载荷 = 该节点的**中断载荷元组**）⇒ ⇒ 挂起态**可被再次恢复**
      （闭环**可重复** · FR-012 / SC-013）；
    * ⚠️ **关键字名逐字**：``values`` / ``metadata`` / ``writes`` /
      ``task_id`` / ``task_path``（契约 §4 冻结）。
    """
    checkpointer.put(
        run_config,
        values=dict(values),
        metadata=_suspend_metadata(
            tuple(sorted(produced)),
            all_interrupts,
            state.to_checkpoint(),
        ),
    )
    for node_name, payload in produced.items():
        checkpointer.put_writes(
            run_config,
            writes=[(_INTERRUPT_CHANNEL, (payload,))],
            task_id=node_name,
            task_path=node_name,
        )


def run_graph(
    spec: GraphSpec,
    input: StateDict | Command | None = None,
    *,
    state: SchedulerState | None = None,
    checkpointer: Any | None = None,
    config: RunConfig | None = None,
    max_steps: int = 10007,
    max_concurrency: int | None = None,
) -> SuperStepResult | InterruptResult:
    """**图级入口** —— 首次运行 / 恢复（B10F1 · 裁定 10 · 契约 §2）。

    **签名**（**逐字冻结** · 契约 §2）::

        run_graph(
            spec: GraphSpec,
            input: StateDict | Command | None = None,
            *,
            state: SchedulerState | None = None,
            checkpointer: Checkpointer | None = None,
            config: RunConfig | None = None,
            max_steps: int = 10007,
            max_concurrency: int | None = None,
        ) -> SuperStepResult | InterruptResult

    * ⚠️ **既有入口一字不动**（B7F1 冻结面）⇒ ⇒ ``run_super_step`` /
      ``run_super_steps`` 的**签名与返回类型零改动**⇒ ⇒ 本入口是**图级**的
      **另立**入口（**不是**替代关系）；
    * ⚠️ **返回联合类型** ⇒ 「挂起」与「跑完」**两种结束方式可区分**
      （B12F1 裁定 24 ②）⇒ ⇒ 门面层再归一成 dict（B7F3 · 承接 **D-3**）。

    **两条路径**（spec FR-013 · 裁定 4）：

    ① **输入是 ``Command``** ⇒ **恢复**路径 ⇒ 判定顺序逐字见 **裁定 4**：
    ② ``resume`` 未提供 ⇒ ``resume_value_required`` · ③ 未挂 checkpointer ⇒
    ``checkpointer_required`` · ④ 该会话没有挂起中断 ⇒
    ``no_pending_interrupt`` · ⑤ 单值 + 多挂起 ⇒ ``ambiguous_resume`` ·
    ⑥ 「按 id 的映射」⇒ 逐个恢复 · ⑦ 「非 map 的 dict」⇒ 普通恢复值（**多挂起**
    ⇒ 回到 ⑤）· ⑧ ``resume`` 与 ``update`` **并存** ⇒ 两者各走各的通道；
    ② **输入不是 ``Command``** ⇒ **首次运行**路径（**不**要求 checkpointer、
    **不**触发恢复）⇒ ⚠️ 该 ``thread_id`` **已有历史快照** ⇒ ⇒ **会话连续**
    （**续跑** · **上游同款** · 实测 E-26）⇒ ⇒ ``input=None`` ⇒ **不**写任何
    通道 ⇒ **只有被中断的节点**重跑 ⇒ ``.id`` **逐字不变**；``input=StateDict``
    ⇒ 先读 ``.snapshot.values``、再把 ``input`` **按通道写入**叠加上去 ⇒ ⇒
    **``.id`` 可变**。
    """
    _validate_max_concurrency(max_concurrency)
    scheduler_state = state if state is not None else SchedulerState()
    run_config = config if config is not None else RunConfig()
    table = new_run_table()
    with bind_run(table):
        if isinstance(input, Command):
            return _resume_graph(
                spec,
                input,
                scheduler_state,
                run_config,
                table,
                checkpointer=checkpointer,
                max_steps=max_steps,
                max_concurrency=max_concurrency,
            )
        return _first_graph(
            spec,
            input,
            scheduler_state,
            run_config,
            table,
            checkpointer=checkpointer,
            max_steps=max_steps,
            max_concurrency=max_concurrency,
        )


def _first_graph(
    spec: GraphSpec,
    input: StateDict | None,
    state: SchedulerState,
    run_config: RunConfig,
    table: Mapping[str, Any],
    *,
    checkpointer: Any | None,
    max_steps: int,
    max_concurrency: int | None,
) -> SuperStepResult | InterruptResult:
    """**首次运行路径**（输入**不是** ``Command`` · spec FR-013 末两行）。"""
    history = None
    if checkpointer is not None:
        history = checkpointer.get_tuple(run_config)
    if history is None:
        # ⚠️ **全新会话** ⇒ 直接按输入写入通道 ⇒ ⇒ 入口节点由 ``__start__``
        # 边触发（**纯边触发**模型 · 上游同款）。
        if isinstance(input, dict):
            _apply_input_writes(spec, state, input)
        return _run_graph_loop(
            spec,
            state,
            table,
            run_config,
            checkpointer=checkpointer,
            first_round=None,
            max_steps=max_steps,
            max_concurrency=max_concurrency,
        )

    # ⚠️ **会话连续**（**续跑** · **上游同款** · 实测 E-26）
    snapshot = history.snapshot
    pending_writes = history.pending_writes
    _restore_scheduler(state, history.scheduler)
    _restore_channels(spec, state, snapshot.values)
    interrupts = _pending_interrupts(pending_writes)
    if input is None:
        # ⚠️ **不**写任何通道 ⇒ ⇒ **只有被中断的节点**重跑（其它节点**不**重跑）
        # ⇒ ⇒ 结果与挂起时**完全相同** ⇒ ⇒ `.id` **逐字不变**（**上游同款** ·
        # 实测 E-15 / E-26 ① · 补记 **F-1**）⇒ ⇒ **不**消费 `__resume__`。
        for node_name, payload in interrupts.items():
            prepare_task(table, node_name, resume=[], existing=payload)
        return _run_graph_loop(
            spec,
            state,
            table,
            run_config,
            checkpointer=checkpointer,
            first_round=_resume_target_nodes(snapshot, interrupts),
            max_steps=max_steps,
            max_concurrency=max_concurrency,
        )
    # ⚠️ **状态字典**输入 ⇒ 先读 `.snapshot.values`（已恢复）⇒ 再把 `input`
    # **按通道写入**叠加上去 ⇒ ⇒ 写通道 ⇒ 通道版本推进 ⇒ **订阅节点重新触发**
    # ⇒ ⇒ 被触及的节点**重跑**（**上游同款** · 实测 E-26 ②）⇒ ⇒ `.id` **可变**。
    _apply_input_writes(spec, state, input)
    _reset_entry_triggers(spec, state)
    return _run_graph_loop(
        spec,
        state,
        table,
        run_config,
        checkpointer=checkpointer,
        first_round=None,
        max_steps=max_steps,
        max_concurrency=max_concurrency,
    )


def _resume_graph(
    spec: GraphSpec,
    input: Command,
    state: SchedulerState,
    run_config: RunConfig,
    table: Mapping[str, Any],
    *,
    checkpointer: Any | None,
    max_steps: int,
    max_concurrency: int | None,
) -> SuperStepResult | InterruptResult:
    """**恢复路径**（输入**是** ``Command`` · spec FR-013 / 裁定 4）。"""
    resume_value = input.resume
    # ⚠️ **② 先于 ③**（**上游同款** · 实测 E-25a / E-25b）—— 上游的
    # checkpointer 检查**在** `if resume is not None` **之内** ⇒ ⇒
    # `resume=None` 时**根本不触达** ⇒ ⇒ 先判「未提供恢复值」。
    if resume_value is None:
        raise InterruptError(reason=InterruptError.REASON_RESUME_VALUE_REQUIRED)
    if checkpointer is None:
        raise InterruptError(reason=InterruptError.REASON_CHECKPOINTER_REQUIRED)
    history = checkpointer.get_tuple(run_config)
    if history is None:
        raise InterruptError(reason=InterruptError.REASON_NO_PENDING_INTERRUPT)
    snapshot = history.snapshot
    pending_writes = history.pending_writes
    interrupts = _pending_interrupts(pending_writes)
    if not interrupts:
        raise InterruptError(reason=InterruptError.REASON_NO_PENDING_INTERRUPT)

    interrupt_ids = {payload.id for payload in interrupts.values()}
    per_node: dict[str, Any] = {}
    if isinstance(resume_value, dict) and all(
        key in interrupt_ids for key in resume_value
    ):
        # ⚠️ **⑥「按 id 的映射」**（**上游同款** · 偏离登记 **X-3**）——
        # 「全部 key 都是**当前挂起中断的 id**」⇒ ⇒ 命中即按 id 逐个恢复
        # （**未被指定的仍挂起**）⇒ ⇒ **map 的「值」原样投递**（**标量即可** ·
        # 上游 `_algo.py:1313-1314`）⇒ ⇒ 该值 = 该节点**下一个**
        # `interrupt()` 的恢复值（**不是**「节点内全部中断值的列表」）。
        # ⚠️ **空 dict** ⇒ 「全部 key 都是 id」**真空为真** ⇒ 归本分支 ⇒
        # 恢复**零个** ⇒ 全部**仍挂起**（**不**报错 · spec FR-013 的空 dict 行）。
        for key, value in resume_value.items():
            for node_name, payload in interrupts.items():
                if payload.id == key:
                    per_node[node_name] = value
    elif len(interrupts) > 1:
        # ⚠️ **⑤ / ⑦** —— 单值（或「非 map 的 dict」）+ **多个**挂起中断 ⇒
        # **无法确定恢复哪一个** ⇒ ⇒ `ambiguous_resume`（**上游同款** ·
        # 实测 E-12 / E-19 / E-20）。
        raise InterruptError(reason=InterruptError.REASON_AMBIGUOUS_RESUME)
    else:
        # ⚠️ **普通恢复值**（**仅当**挂起中断数 == 1 时有效）⇒ ⇒ 用它恢复
        # 那**一个**挂起中断。
        per_node[next(iter(interrupts))] = resume_value

    # ⚠️ **⑧「resume 与 update 并存」** ⇒ ⇒ 两者**各走各的通道**
    # （**上游同款** · 补记 **F-2**）⇒ ⇒ `update` 走**通道写入**、
    # `resume` 走**恢复通道**⇒ ⇒ 两者**互不排斥**。
    # ⚠️ **顺序**：**先**恢复调度状态 + 通道实例 ⇒ ⇒ **再**写 `update`
    # ⇒ ⇒ 否则写入会被「按快照重建通道」**覆盖掉**。
    _restore_scheduler(state, history.scheduler)
    _restore_channels(spec, state, snapshot.values)
    if input.update:
        _apply_input_writes(spec, state, input.update)

    targets = _resume_target_nodes(snapshot, interrupts)
    for node_name in targets:
        previous = _pending_resume_values(pending_writes, node_name)
        accumulated = list(previous)
        if node_name in per_node:
            accumulated.append(per_node[node_name])
            # ⚠️ **恢复值先落 pending writes 再执行**（**上游同款** · DR-10 ②）
            # ⇒ ⇒ 「恢复」与「首次运行」**共用同一条执行路径** ⇒ ⇒ 零分支。
            checkpointer.put_writes(
                run_config,
                writes=[(_RESUME_CHANNEL, accumulated)],
                task_id=node_name,
                task_path=node_name,
            )
        prepare_task(
            table,
            node_name,
            resume=accumulated,
            existing=interrupts.get(node_name),
        )
    return _run_graph_loop(
        spec,
        state,
        table,
        run_config,
        checkpointer=checkpointer,
        first_round=targets,
        max_steps=max_steps,
        max_concurrency=max_concurrency,
    )
