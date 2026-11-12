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

from collections.abc import Callable, Container, Sequence
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from freegraph.contracts.errors import GraphInterrupt, GraphRecursionError, InvalidUpdateError
from freegraph.contracts.types import Command, Interrupt

from ._concurrency import (
    _TaskOutcome,
    _resolve_cap,
    attach_failure_notes,
    run_tasks_concurrently,
)
from .channel import Channel, EphemeralValue
from .errors import InvalidChannelUpdateError
from .read import read_channels

__all__ = [
    "GraphSpec",
    "NodeSpec",
    "SchedulerState",
    "SuperStepResult",
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
            edges: dict[str, tuple[str, ...]],
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
    * ``conditional_edges`` —— **预留**的「条件边」字段（裁定 25）·
      本轮**恒为空**；**非空 ⇒ 显式失败**（FR-033）· 缺省值 MUST 用
      **工厂语义**实现（``default_factory``）⇒ MUST NOT 用字面可变默认值。

    **校验**（契约 §2.1 / §2.1.1）MUST 在**构造时**执行 ⇒ 即刻显式失败。

    **不可变**（data-model §1）⇒ **字段**不可改写；但 ``channels`` 的**内容**
    仍可被调用方增补（FR-034）。
    """

    channels: dict[str, Channel]
    nodes: dict[str, NodeSpec]
    edges: dict[str, tuple[str, ...]]
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
    if spec.conditional_edges:
        raise ValueError(
            "GraphSpec.conditional_edges must stay empty in this feature (V-8)"
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


def _trigger_sources(
    spec: GraphSpec,
    state: SchedulerState,
    node_name: str,
    node: NodeSpec,
) -> list[tuple[str, str]]:
    """枚举一个节点的**全部**触发源（契约 §3.1 · FR-002）。

    * **通道触发源** —— ``("c", 通道 key)``：节点订阅的每个通道；
    * **边触发源** —— ``("e", 源节点名)``：每条指向该节点的边的**源**节点。

    ⚠️ **两个标识空间 MUST 分离** ⇒ 避免「通道 key 与节点名同名」时互相覆盖
    （裁定 3）。

    ⚠️ **静态边与动态边同处「边」空间**（裁定 1 · FR-002）⇒ 两者**叠加**
    （FR-008）⇒ 同一对 (源, 目标) 只枚举**一次**（SC-007：「一轮内至多触发
    一次」）⇒ 本函数对触发源**去重**（**保序**）。

    ⚠️ **动态边的存在性**由**动态边表**决定（源节点 → 其**最近一次执行**给出
    的跳转目标）⇒ 源节点再次执行且**不**给 ``goto`` ⇒ 旧目标**从本枚举中
    消失** ⇒ 该目标**不再**被触发（FR-009 · 裁定 2）。

    ⚠️ **版本口径**：边触发源的版本 = **源节点的执行版本**（每执行成功一次
    +1）⇒ 静态边与动态边**同款**（契约 §5）⇒ 配合 ``seen`` 记录 ⇒
    「动态边**只影响下一轮**」（FR-002）。
    """
    sources: list[tuple[str, str]] = []
    for source, targets in spec.edges.items():
        if node_name in targets:
            sources.append((_EDGE_SOURCE, source))
    for source, targets in state.dynamic_edges.items():
        if node_name in targets:
            sources.append((_EDGE_SOURCE, source))
    deduplicated: list[tuple[str, str]] = []
    for source in sources:
        if source not in deduplicated:
            deduplicated.append(source)
    return deduplicated



def _is_triggered(
    spec: GraphSpec,
    state: SchedulerState,
    node_name: str,
    node: NodeSpec,
    sources: list[tuple[str, str]],
) -> bool:
    """判定一个节点本轮**是否被触发**（契约 §3.2 · 裁定 28）。

    判定式（**逐字**）::

        ∃ 触发源 s ∈ sources(N) : has_value(s) ∧ version(s) > seen(N)[s]

    * **触发源恒为边**（**上游对齐 P1-0-2 · 2026-11-12**）：判定式 = ``version > seen``
      ⇒ 边触发源**无「值」概念**（源节点的执行版本本身即「发生过执行」的信号）。
      ⚠️ 原先还有「通道触发源」空间（``("c", key)``）⇒ **已删除**（上游同款 ·
      `langgraph/graph/state.py:1531-1532`）⇒ 节点**订阅**的通道**不再**是触发源
      ⇒ 「节点写自己订阅的通道」**不再**自触发。
    """
    seen = state.versions_seen.get(node_name, {})
    for kind, ident in sources:
        version = _source_version(state, ident)
        if version > seen.get((kind, ident), 0):
            return True
    return False


def _determine_triggers(spec: GraphSpec, state: SchedulerState) -> list[str]:
    """**触发判定**（阶段 ①）⇒ 被触发的节点名（**按节点名序**）。

    ⚠️ 调度器 MUST NOT 重排节点表（FR-013）⇒ 触发集合 MUST 按**节点名序**
    产出（契约 §4）。
    """
    triggered: list[str] = []
    for node_name, node in spec.nodes.items():
        sources = _trigger_sources(spec, state, node_name, node)
        if _is_triggered(spec, state, node_name, node, sources):
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
    sources: list[tuple[str, str]],
) -> None:
    """**消费**一个节点的**全部**触发源的当前版本（阶段 ② · 裁定 16 · T056）。

    * 节点被**准备执行**时 ⇒ ``seen(N)[s] = version(s)``（对**全部**触发源）；
    * ⇒ **同一版本的同一触发源 MUST NOT 重复触发同一节点**（FR-004）；
    * ⇒ 一个触发源的推进 MUST **不**掩盖另一个触发源的推进（FR-003 · SC-003）。

    ⚠️ **消费时点 = plan（任务准备）阶段** —— 与上游的 apply 阶段**不同**
    ⇒ 登记为 **DR-1**（已知边界 · 只登记 · 不改判据）。
    """
    seen = state.versions_seen.setdefault(node_name, {})
    for kind, ident in sources:
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
        sources = _trigger_sources(spec, state, node_name, node)
        node_input = _node_input(spec, state, node)
        _consume_versions(state, node_name, sources)
        tasks.append((node_name, node, node_input))

    # ── ③ 并发执行（线程池 · 每轮新建 + 关闭 ⇒ 零悬挂线程 · FR-018） ──
    started: list[str] = []

    def _bind(
        node_name: str, fn: Callable[[], dict[str, Any]]
    ) -> Callable[[], dict[str, Any]]:
        def _inner() -> dict[str, Any]:
            started.append(node_name)  # ⚠️ list.append 在 CPython 下是原子的
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
