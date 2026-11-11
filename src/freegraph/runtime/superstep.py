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
from typing import Any

from freegraph.contracts.errors import GraphRecursionError, InvalidUpdateError
from freegraph.contracts.types import Command

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

#: **触发源标识的第一个空间** = **通道触发源**（契约 §3.1 · 裁定 3）。
_CHANNEL_SOURCE = "c"

#: **触发源标识的第二个空间** = **边触发源**（契约 §3.1 · 裁定 3）。
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

    * ``subscribes`` —— 该节点**订阅**的通道 key：**既管触发判定、也管入参内容**
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
        if source not in spec.nodes:
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
    for key in node.subscribes:
        sources.append((_CHANNEL_SOURCE, key))
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


def _view_channel(spec: GraphSpec, state: SchedulerState, key: str) -> int:
    """**首次查看**某通道 ⇒ 若它**已有值**，把它的写入版本记为 **1**。

    （裁定 21 · research **D-01** · 裁定 31：「查看」的操作点 = **触发判定阶段
    枚举该节点的订阅通道时** ⇒ 必然早于任何写入 ⇒ 版本号**唯一确定**。）

    * 通道**已有值** ⇒ 版本 **1**（「有值」即算已写过一次）；
    * 通道**无值** ⇒ 版本 **0**（基值 · 裁定 34）⇒ 该通道**已被查看过**
      ⇒ 之后调用方的直接写入 **不**进版本推进路径 ⇒ MUST **不**成为触发依据。

    ⚠️ 版本记在**调度状态**里，MUST NOT 记进通道对象（B5F1 的四个只读属性是
    **冻结面** · 裁定 21 · research **C-2**）。
    """
    if key not in state.channel_versions:
        state.channel_versions[key] = 1 if spec.channels[key].is_available() else 0
    return state.channel_versions[key]


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

    * **通道触发源** —— ``has_value(channel) ∧ version > seen``；
      **无值**的通道触发源**不计入**（MUST NOT 读成「节点订阅集整体有值」——
      那个读法会让 C4 的节点边界用例**物理不可成立**）；
    * **边触发源** —— **无「值」概念** ⇒ 判定式 = ``version > seen``。
    """
    for kind, ident in sources:
        if kind == _CHANNEL_SOURCE:
            _view_channel(spec, state, ident)
    seen = state.versions_seen.get(node_name, {})
    for kind, ident in sources:
        if kind == _CHANNEL_SOURCE:
            if not spec.channels[ident].is_available():
                continue
            version = state.channel_versions.get(ident, 0)
        else:
            version = state.node_versions.get(ident, 0)
        if version > seen.get((kind, ident), 0):
            return True
    return False


def _determine_triggers(spec: GraphSpec, state: SchedulerState) -> list[str]:
    """**触发判定**（阶段 ①）⇒ 被触发的节点名（**按节点表顺序**）。

    ⚠️ 调度器 MUST NOT 重排节点表（FR-013）⇒ 触发集合 MUST 按**节点表顺序**
    产出（契约 §4）。
    """
    triggered: list[str] = []
    for node_name, node in spec.nodes.items():
        sources = _trigger_sources(spec, state, node_name, node)
        if _is_triggered(spec, state, node_name, node, sources):
            triggered.append(node_name)
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
        if kind == _CHANNEL_SOURCE:
            seen[(kind, ident)] = state.channel_versions.get(ident, 0)
        else:
            seen[(kind, ident)] = state.node_versions.get(ident, 0)


def _node_input(spec: GraphSpec, node: NodeSpec) -> dict[str, Any]:
    """构造一个节点的**入参**（阶段 ② · FR-008 · 裁定 2 · 裁定 26）。

    * 入参 MUST 由 **B5F2 的稀疏读原语**产出 ⇒ 复用
      :func:`freegraph.runtime.read_channels`（MUST NOT 在调度层另写一份）；
    * 子映射 MUST 按「**通道映射的顺序**」构造（**不是**订阅声明的顺序）
      ⇒ 入参的 key 顺序与**整张状态表**的 key 顺序**天然一致**；
    * 结果只含「订阅集 ∩ 有值集」⇒ **无值通道的 key MUST NOT** 出现在入参中
      （**C4**）。
    """
    subset = {
        key: channel for key, channel in spec.channels.items() if key in node.subscribes
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
    update = command.update
    if update is None:
        writes: dict[str, tuple[Any, ...]] = {}
    elif isinstance(update, dict):
        writes = {key: (value,) for key, value in update.items()}
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


def _execute_node(
    spec: GraphSpec,
    state: SchedulerState,
    node_name: str,
    node: NodeSpec,
    node_input: dict[str, Any],
) -> dict[str, tuple[Any, ...]]:
    """**执行**一个节点（阶段 ③ · FR-009 · FR-013 · FR-015 · FR-001）。

    * 按**节点表顺序**串行执行；
    * 节点抛出的异常 MUST **原样**向上传播（**不**包装 · **不**吞掉）；
    * 返回值 MUST 是 ``dict`` / ``Command`` / ``list[Command | dict]`` 之一
      （**FR-001**）⇒ 其它类型（含 ``None``）⇒ **显式失败**（内置
      ``TypeError`` · **V-9**）；
    * 返回值经 :func:`_normalize_node_result` **归一** ⇒ 待写入交给**既有的**
      :func:`_collect_writes` / :func:`_merge_writes`（MUST NOT 另写合并路径）；
    * 节点**执行成功**后 ⇒ 其**执行版本** +1（边触发源的版本）；
    * 节点**执行成功**后 ⇒ **动态边表**登记本次的跳转目标（**整体替换** ·
      含**空集** ⇒ 旧的 ``goto`` 目标被清空 · FR-009）。
    """
    result = node.run(node_input)
    normalized = _normalize_node_result(result, spec.nodes)
    state.dynamic_edges[node_name] = normalized["gotos"]
    state.node_versions[node_name] = state.node_versions.get(node_name, 0) + 1
    return normalized["writes"]


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
    """把待写入**按通道分组**（值按**节点表顺序**排列 · 契约 §5.1）。"""
    grouped: dict[str, list[Any]] = {}
    for node_name in spec.nodes:
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


def _reject_multi_writes(spec: GraphSpec, grouped: dict[str, list[Any]]) -> None:
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
        if len(values) > 1 and spec.channels[key].reducer is None:
            raise InvalidChannelUpdateError(
                key, received_count=len(values), expected_count=1
            )


def _snapshot_channel(channel: Channel) -> tuple[bool, Any]:
    """取一个通道的**快照**（值 / 有无值）—— 合并**首次写入之前**（契约 §5.4）。"""
    if channel.is_available():
        return True, channel.get()
    return False, None


def _rollback(spec: GraphSpec, snapshots: dict[str, tuple[bool, Any]]) -> None:
    """**逐通道回滚**（契约 §5.4 · 裁定 29）。

    * 回滚顺序 MUST 与合并顺序一致（按**通道映射顺序**）；
    * 快照**有值** ⇒ ``clear()`` + ``update([快照值])``（**不套**归约器
      ⇒ 逐字还原）；
    * 快照**无值** ⇒ **只** ``clear()``（无值快照**不是**一个可写回的值）。
    """
    for key, (has_value, value) in snapshots.items():
        channel = spec.channels[key]
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
    _reject_unknown_keys(grouped, spec.channels)
    _reject_multi_writes(spec, grouped)
    snapshots = {
        key: _snapshot_channel(spec.channels[key])
        for key in spec.channels
        if key in grouped
    }
    written: set[str] = set()
    try:
        for key, channel in spec.channels.items():
            values = grouped.get(key)
            if values is None:
                continue
            if channel.update(values):
                written.add(key)
    except Exception:
        _rollback(spec, snapshots)
        raise
    for key in written:
        state.channel_versions[key] = state.channel_versions.get(key, 0) + 1
    return written


def _clear_step_end(spec: GraphSpec, written: set[str]) -> None:
    """**步末清空**（阶段 ⑤ 的收尾 · FR-014 · 裁定 10 · 裁定 33）。

    * **只**对**路由型**通道调 ``clear()``（覆盖型 / 归约型 MUST **保留**其值）；
    * **且只清「本轮未被写入的」**路由型通道 ⇒ 本轮写过的路由型通道的值
      **存活到下一轮**（⇒ B8F1 的条件边路由读得到「本节点本次写入」）；
    * **清空不是写入** ⇒ 通道版本 MUST **不**推进；
    * 「路由型」MUST 以 ``isinstance(channel, EphemeralValue)`` 判定
      ⇒ MUST NOT 用「``reducer is None``」等**启发式**（FR-014 ⚠️）。
    """
    for key, channel in spec.channels.items():
        if isinstance(channel, EphemeralValue) and key not in written:
            channel.clear()


def _run_round(
    spec: GraphSpec,
    state: SchedulerState,
    triggered: list[str],
) -> tuple[list[str], dict[str, dict[str, tuple[Any, ...]]]]:
    """跑**一轮** super-step 的**五个阶段**（FR-001 · 契约 §4）。

    ① **触发判定**已由调用方完成 ⇒ 本函数负责 ② 任务准备 · ③ 任务执行 ·
    ④ 写入收集 · ⑤ 写入合并（含步末清空）。

    ⚠️ **阶段 ② MUST 在阶段 ③ 之前**完成（契约 §4 的顺序固定）⇒ 全部节点的
    入参与「已消费版本」都在**任何节点执行之前**确定 ⇒ 一个节点的执行**不**
    影响另一个节点的入参（FR-006 · C8 fresh 读的基础）。
    """
    tasks: list[tuple[str, NodeSpec, dict[str, Any]]] = []
    for node_name in triggered:
        node = spec.nodes[node_name]
        sources = _trigger_sources(spec, state, node_name, node)
        node_input = _node_input(spec, node)
        _consume_versions(state, node_name, sources)
        tasks.append((node_name, node, node_input))
    executed: list[str] = []
    results: dict[str, dict[str, tuple[Any, ...]]] = {}
    for node_name, node, node_input in tasks:
        results[node_name] = _execute_node(spec, state, node_name, node, node_input)
        executed.append(node_name)
    pending = _collect_writes(executed, results)
    written = _merge_writes(spec, state, pending)
    _clear_step_end(spec, written)
    return executed, pending


def _sparse_state(spec: GraphSpec) -> dict[str, Any]:
    """取本轮**结束**时的**稀疏**通道状态（只含**当前有值**的通道）。"""
    return read_channels(spec.channels)


def run_super_step(spec: GraphSpec, state: SchedulerState) -> SuperStepResult:
    """**单轮入口** —— 跑**一轮** super-step（五阶段 · 顺序固定）。

    **签名**（**逐字冻结** · 契约 §1）::

        run_super_step(spec: GraphSpec, state: SchedulerState) -> SuperStepResult

    * 调度状态 **MUST 显式接收**（裁定 27）⇒ 与多轮入口的「MAY 省略」相对；
    * ``steps`` **恒为 1**（裁定 34 · SC-001 ③）；
    * 跑完一轮后**同样**执行**步末清空**（裁定 33）⇒ 两个入口的语义一致。
    """
    triggered = _determine_triggers(spec, state)
    executed: list[str] = []
    pending: dict[str, dict[str, tuple[Any, ...]]] = {}
    if triggered:
        executed, pending = _run_round(spec, state, triggered)
        state.step += 1
    return SuperStepResult(
        state=_sparse_state(spec),
        executed=tuple(executed),
        node_writes=pending,
        steps=1,
    )


def run_super_steps(
    spec: GraphSpec,
    state: SchedulerState | None = None,
    *,
    max_steps: int = 25,
) -> SuperStepResult:
    """**多轮入口** —— 反复跑 super-step 直到**收敛**或**触到步数上限**。

    **签名**（**逐字冻结** · 契约 §1）::

        run_super_steps(
            spec: GraphSpec, state: SchedulerState | None = None, *, max_steps: int = 25
        ) -> SuperStepResult

    * ``state`` —— 缺省新建一个 ⇒ 该次调用**内部自洽**、**不**继承此前任何
      调用的消费记录（裁定 27 · FR-004）⇒ 两个入口的「已消费版本」**不串扰**；
    * ``max_steps`` —— 步数上限，**缺省 25**（裁定 24 · 与上游
      ``DEFAULT_RECURSION_LIMIT`` 逐字一致）⇒ 达到上限且仍有待执行任务 ⇒ 抛
      ``GraphRecursionError``（FR-011）。

    ⚠️ **上限计「执行轮」**（真正执行了节点的轮数）⇒ **空轮不计入上限**；
    判定顺序 = ① 先判「任务集合为空 ⇒ 立即终止」② 再判「执行轮数 == 上限
    **且**下一轮任务集非空 ⇒ 抛错」（裁定 30 的判定顺序）。
    """
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
        round_executed, round_pending = _run_round(spec, scheduler_state, triggered)
        executed.extend(round_executed)
        for node_name, writes in round_pending.items():
            bucket = pending.setdefault(node_name, {})
            for key, values in writes.items():
                bucket[key] = bucket.get(key, ()) + values
        scheduler_state.step += 1
    return SuperStepResult(
        state=_sparse_state(spec),
        executed=tuple(executed),
        node_writes=pending,
        steps=steps,
    )
