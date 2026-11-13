#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""**差分探针** —— freegraph ↔ langgraph 上游的**同场景对跑**（**测试侧**）。

为什么需要它
------------
本仓库的权威判据是「**上游 langgraph 是唯一权威**」（见
``harness/proposals/主路线.md``）。但截至 2026-11-12，仓库里的 8 个
``harness/verification/*/acceptance.py`` **全部只验 freegraph 自身**的契约 ——
它们证明「freegraph 符合自己的 spec」，**不能**证明「freegraph 与上游同款」。

⇒ 于是出现了一个结构性盲区：**spec 与上游分叉了，验收脚本仍然是绿的。**
（这不是假想：B4F1 的「只接受 ``TypedDict``」、B5F2 的 fresh 视图保留路由通道、
B9F1 的「空列表 = 无操作」三处分叉，都是在 P3 回改**之前**长期保持绿色的。）

本脚本把「**同场景 · 两边跑 · 比可观察结果**」变成可重复执行的检查：

* **上游侧**：用**已安装的** ``langgraph``（``StateGraph`` · ``compile().invoke()``）
  —— 只在**开发期**使用，不进发行面；
* **freegraph 侧**：用 ``freegraph.runtime`` 的 ``GraphSpec`` / ``run_super_steps``；
* **比对三件事**：① **执行的节点序列** ② **最终状态** ③ **异常族**
  （成功 / 失败 · 不比对异常**类名** —— 两边本就不该同名）。

每个场景带一条**判词**：

* ``SAME`` —— **必须逐字一致**（不一致 ⇒ **判据失败** ⇒ 退出码 1）；
* ``STRICTER`` —— freegraph **刻意更严**（失败信号更硬）⇒ 允许「上游成功、freegraph 失败」，
  但**必须**在 ``STRICTER_NOTES`` 里写明理由；
* ``DIFF`` —— **已知且已登记**的行为差异（不是更严，而是语义不同）。

用法
----
    python harness/scripts/diff_parity.py            # 全跑 · 退出码 0 = 全部符合判词
    python harness/scripts/diff_parity.py -v         # 附带打印两边的原始结果
    python harness/scripts/diff_parity.py -k 命令     # 只跑名字含「命令」的场景
"""
from __future__ import annotations

import operator
import os
import pathlib
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

ROOT = str(pathlib.Path(__file__).resolve().parents[2])

#: 「不覆盖场景自带取值」的哨兵（**B12F1** 引入）。
_UNSET: Any = object()

# ── 场景模型 ────────────────────────────────────────────────────────────────


@dataclass
class Scenario:
    """一个**同场景对跑**的用例。"""

    name: str
    #: 通道形态：``name -> "last" | "binop" | "ephemeral"``
    channels: dict[str, str]
    #: 初始状态（**通道初值**）
    initial: dict[str, Any]
    #: 节点：``name -> (订阅的通道, 函数)``
    nodes: dict[str, tuple[tuple[str, ...], Callable[[dict[str, Any]], Any]]]
    #: 静态边：``源 -> 目标们``（``__start__`` 是入口）
    #:
    #: ⚠️ **2026-11-13 · B7F4**：键类型放宽为 ``str | tuple[str, ...]`` ——
    #: ``str`` 键 = **单源边**（写法**逐字不变**）· ``tuple`` 键 = **多源边**
    #: （AND / 屏障）⇒ ⇒ **既有 30 个场景逐字不变**（**FR-018** · 裁定 12）。
    edges: dict[str | tuple[str, ...], tuple[str, ...]]
    #: 上游侧的**节点函数**（默认同 ``nodes``）—— 两边原语不同类时用
    nodes_upstream: dict[str, tuple[tuple[str, ...], Callable[[dict[str, Any]], Any]]] | None = None
    #: 节点执行顺序记录（两侧共用一个列表 ⇒ 跑完清空）
    calls: list[str] = field(default_factory=list)
    #: 判词：``SAME`` | ``STRICTER`` | ``DIFF``
    verdict: str = "SAME"
    #: ``STRICTER`` / ``DIFF`` 的理由（``STRICTER`` **必须**有）
    note: str = ""
    #: 上游侧的**额外声明**（如 ``add_conditional_edges``）—— 自由图侧不需要
    upstream_extra: Callable[[Any], None] | None = None

    # ── B12F1 扩展（**全部可选** · 缺省 ⇒ 既有 15 个场景的行为与判词**逐字不变**）──

    #: ``max_concurrency``（**透传给 freegraph 侧**的 ``run_super_steps``）
    #: —— **上游同名同义**（``RunnableConfig["max_concurrency"]``）
    max_concurrency: int | None = None
    #: 比较口径：``exact``（默认 · 逐字相等）· ``set``（集合相等 · 顺序无关）
    #: · ``order``（顺序相等）
    compare: str = "exact"
    #: **屏障**夹具的**参与方数**（``0`` = 不用屏障）⇒ 串行执行会**死锁 / 超时**
    #: ⇒ 屏障被放行即「**真并发**」的证明
    barrier: int = 0
    #: 记录**执行时间窗**（⇒ 判定「重叠时长 > 0」）
    time_window: bool = False
    #: 节点**执行时间窗**（``节点名 -> [(起, 止), ...]``）⇒ 由 ``run_*`` 填充
    windows: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    #: 期望捕获 ``GraphInterrupt``（⇒ 从异常的 ``args[0]`` 取载荷）
    expect_interrupt: bool = False
    #: 节点函数抛出的**异常对象**（⇒ 判定「对象 identity 逐字一致」· D-02）
    raised: list[BaseException] = field(default_factory=list)
    #: **freegraph 侧专用**判定器（``(ok, detail)``）⇒ 供「**freegraph 内部对照**」
    #: 场景使用（并发 == 串行 · 多会话隔离 · 并发度上限 · 确定性 …）
    fg_only: Callable[["Scenario"], tuple[bool, str]] | None = None
    #: 比对两侧「**实际被启动了哪些节点**」的**集合**（⇒ 端到端的取消语义 · D-03）
    compare_started: bool = False
    #: 比对两侧捕获到的**异常对象 identity**（⇒ D-02）
    expect_exception_identity: bool = False

    # ── B7F4 扩展（**全部可选** · 缺省 ⇒ 既有 30 个场景的行为与判词**逐字不变**）──

    #: **期望 freegraph 侧在构造期失败**（⇒ **D-22 / D-25 / D-26 / D-28**）
    fg_construct_error: bool = False
    #: **期望上游侧在构造期失败**（⇒ **D-22 / D-28**）⇒ ⇒ 可表达「**两侧都失败**」
    #: 与「**一侧失败一侧不失败**」两种形态（research **DR-7** · **FR-018**）。
    up_construct_error: bool = False
    #: **期望两侧抛出的异常类型名**（**两侧同名** · 如 ``"TypeError"``）⇒
    #: 缺省 ⇒ **不比对**异常类型（既有口径：只比「成功 / 失败」）。
    expect_exception_type: str = ""

    # ── B10F1 扩展（**全部可选** · 缺省 ⇒ 既有 43 个场景的行为与判词**逐字不变**）──

    #: **第二次输入**（⇒ **两段式**跑法：第一次 ⇒ 挂起；第二次 ⇒ 以该输入恢复）
    #: —— 缺省 ``_UNSET`` ⇒ **单段式**（既有口径**逐字不变**）。
    resume_input: Any = _UNSET
    #: **期望 freegraph 侧「挂起」**（⇒ 返回 ``InterruptResult`` ⇒ 中断载荷从
    #: **结果**取，而**不是**从**异常**取）⇒ ⇒ 判据形态与 ``expect_interrupt``
    #: **不同**（freegraph **不**抛 · 上游**根图抑制** ⇒ 落进结果键）。
    fg_suspends: bool = False
    #: **上游侧挂 checkpointer**（⇒ ``compile(checkpointer=InMemorySaver())``）
    #: —— 恢复路径**必须**挂 checkpointer（**上游同款** · **实测 E-3**）。
    upstream_checkpointer: bool = False
    #: **freegraph 侧不挂 checkpointer**（⇒ 恢复时**必须**显式失败 · DI-04）
    #: —— 缺省 ⇒ 挂**桩**（本 feature **不**实现 saver · FR-019）。
    fg_no_checkpointer: bool = False
    #: 比对两侧「**节点被执行的次数**」（⇒ ``len(calls)``）⇒ 供「**从节点起点
    #: 重跑**」这类**次数**判据使用（DI-03 · **上游同款** · 实测 E-8）。
    compare_call_counts: bool = False

    def clear(self) -> None:
        self.calls.clear()
        self.windows.clear()


# ── 夹具装置（B12F1 扩展）────────────────────────────────────────────────────


def _instrument(
    scenario: Scenario,
    fn: Callable[[dict[str, Any]], Any],
    node_name: str,
    gate: threading.Barrier | None,
) -> Callable[[dict[str, Any]], Any]:
    """给节点函数装上**屏障**与**执行时间窗**夹具（B12F1 扩展）。

    * **屏障**（``scenario.barrier`` > 0）⇒ 节点在**进入**时等在 ``Barrier`` 上
      ⇒ 串行执行会**死锁 / 超时** ⇒ 屏障被放行即「**真并发**」的证明
      （SC-001 · I-1 · 不变量判定用**屏障放行**而非墙钟耗时 ⇒ CI 不假红）；
    * **时间窗**（``scenario.time_window``）⇒ 记录每个节点的 ``(起, 止)``
      ⇒ 判定「重叠时长 > 0」。
    """
    if gate is None and not scenario.time_window:
        return fn

    def _wrapped(state: dict[str, Any]) -> Any:
        if gate is not None:
            gate.wait(timeout=30)
        start = time.monotonic()
        try:
            return fn(state)
        finally:
            if scenario.time_window:
                scenario.windows.setdefault(node_name, []).append((start, time.monotonic()))

    return _wrapped


def _interrupt_payload(exc: BaseException) -> tuple[Any, ...]:
    """从一个异常里取「**中断载荷**」（``GraphInterrupt.args[0]`` 的**元素**）。

    ⚠️ 非 ``GraphInterrupt`` ⇒ 返回**空元组**。
    ⚠️ 取的是 ``args[0]`` 的**元素**（``Interrupt`` 对象）⇒ **不是** ``payload``
    本身（那是元组 ⇒ 嵌套元组 ⇒ 元素**没有** ``.value`` / ``.id``）（裁定 7）。
    """
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.contracts.errors import GraphInterrupt

    if isinstance(exc, GraphInterrupt):
        payload = exc.args[0] if exc.args else ()
        return tuple(payload)
    return ()


def _interrupt_keys(payload: tuple[Any, ...]) -> list[tuple[Any, Any]]:
    """把中断载荷转成**可比较**的 ``(value, id)`` 序列。

    ⚠️ 两侧的 ``Interrupt`` **类不同**（freegraph 的 L1 vs 上游的）⇒ **比值**，不比类。
    """
    return [(getattr(item, "value", None), getattr(item, "id", None)) for item in payload]


#: **``.id`` 的形态**（**上游同款** · 实测 **E-9**）—— 32 位十六进制。
#:
#: ⚠️ 两侧的 ``.id`` **逐字不同**（上游 ``xxh3_128`` vs freegraph ``blake2b-128``
#: ⇒ 偏离登记 **X-4**）⇒ ⇒ **比形态**，**不**比具体值（research **DR-12**）。
_ID_SHAPE = re.compile(r"^[0-9a-f]{32}$")


def _compare_interrupts(
    fg_payload: tuple[Any, ...],
    up_payload: tuple[Any, ...],
    compare: str,
) -> bool:
    """比对两侧的**中断载荷**（口径由 ``scenario.compare`` 决定）。

    ⚠️ **``"interrupt-shape"``**（**B10F1** · research **DR-12**）⇒ ⇒
    ① ``.value`` **逐字相等**（**集合**口径 ⇒ **不**比顺序 —— 上游的合并顺序
    **是竞态**）⇒ ② 两侧的 ``.id`` **都**匹配 **32 位十六进制**的**形态**
    ⇒ ⇒ **不**比具体值（算法不同 · 偏离登记 **X-4**）。
    """
    fg_keys = _interrupt_keys(fg_payload)
    up_keys = _interrupt_keys(up_payload)
    if compare == "interrupt-shape":
        fg_values = sorted(repr(value) for value, _ in fg_keys)
        up_values = sorted(repr(value) for value, _ in up_keys)
        if fg_values != up_values:
            return False
        return all(
            _ID_SHAPE.match(str(identifier or ""))
            for _, identifier in (*fg_keys, *up_keys)
        )
    if compare == "set":
        # ⚠️ **按集合比**（上游的元组内元素顺序**竞态** ⇒ 逐字比会偶发红）
        return sorted(map(repr, fg_keys)) == sorted(map(repr, up_keys))
    return fg_keys == up_keys


# ── B10F1 · 探针内的**桩** checkpointer（self-contained）───────────────────


class _ProbeCheckpointer:
    """**桩** checkpointer —— 只存**最小**载荷（探针自足 · 不依赖其它模块）。

    ⚠️ **探针自足** ⇒ ⇒ **不** import ``tests.runtime``（探针可作脚本独立运行
    ⇒ ``python harness/scripts/diff_parity.py``）。
    """

    def __init__(self) -> None:
        self.snapshot: dict[str, Any] | None = None
        self.pending: list[tuple[str, str, Any]] = []

    def get_tuple(self, config: Any) -> Any:
        """取回**最新**快照（**查不到** ⇒ ``None``）。"""
        if self.snapshot is None:
            return None
        values, metadata = self.snapshot
        return _ProbeTuple(
            values=values,
            metadata=metadata,
            pending=tuple(self.pending),
        )

    def put(
        self,
        config: Any,
        values: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**快照**。"""
        self.snapshot = (dict(values or {}), dict(metadata or {}))

    def put_writes(
        self,
        config: Any,
        writes: Any = None,
        task_id: Any = None,
        task_path: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**待写入数据**（同一任务 + 同一通道 ⇒ **覆盖**）。"""
        for channel, value in writes or ():
            for index, entry in enumerate(self.pending):
                if entry[0] == task_id and entry[1] == channel:
                    self.pending[index] = (task_id, channel, value)
                    break
            else:
                self.pending.append((task_id, channel, value))


class _ProbeTuple:
    """``get_tuple`` 的返回值 —— **三个具名属性**（契约 §2）。"""

    def __init__(
        self,
        values: dict[str, Any],
        metadata: dict[str, Any],
        pending: tuple[tuple[str, str, Any], ...],
    ) -> None:
        self.values = values
        self.metadata = metadata
        self.pending = pending

    @property
    def snapshot(self) -> Any:
        """**快照**（L1 的 ``StateSnapshot`` 形态 · 探针只取用到的字段）。"""
        return _ProbeSnapshot(self.values, self.metadata)

    @property
    def pending_writes(self) -> tuple[tuple[str, str, Any], ...]:
        """**待写入**。"""
        return self.pending

    @property
    def scheduler(self) -> dict[str, Any]:
        """**调度账本**。"""
        return dict(self.metadata.get("scheduler", {}))


class _ProbeSnapshot:
    """``StateSnapshot`` 的**探针替身**（只带探针用到的字段）。"""

    def __init__(self, values: dict[str, Any], metadata: dict[str, Any]) -> None:
        self.values = values
        self.next = tuple(metadata.get("next", ()))
        self.interrupts = tuple(metadata.get("interrupts", ()))
        self.tasks = tuple(metadata.get("tasks", ()))


# ── freegraph 侧 ────────────────────────────────────────────────────────────


def run_freegraph(
    scenario: Scenario,
    *,
    max_concurrency: Any = _UNSET,
) -> tuple[str, Any, str, dict[str, Any]]:
    """跑 freegraph ⇒ 返回 ``(结果摘要, 状态/载荷, 细节, 附加信息)``。

    ⚠️ **B12F1 扩展**：``max_concurrency`` 可**覆盖**场景自带的取值（⇒ 供
    「**并发 == 串行**」这类**内部对照**场景使用）· 捕获**异常对象**（供
    「对象 identity」判定）· 捕获 ``GraphInterrupt`` 的**载荷**。
    """
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.contracts import Command  # noqa: F401  （供场景使用）
    from freegraph.runtime import (
        BinaryOperatorAggregate,
        EphemeralValue,
        GraphSpec,
        LastValue,
        NodeSpec,
        SchedulerState,
        run_super_steps,
    )

    cap = scenario.max_concurrency if max_concurrency is _UNSET else max_concurrency
    gate = threading.Barrier(scenario.barrier) if scenario.barrier else None

    channels: dict[str, Any] = {}
    for name, kind in scenario.channels.items():
        if kind == "last":
            channels[name] = LastValue(name, object)
        elif kind == "binop":
            channels[name] = BinaryOperatorAggregate(name, list, operator.add)
        elif kind == "ephemeral":
            channels[name] = EphemeralValue(name, object)
        else:  # pragma: no cover - 场景写错
            raise ValueError(f"未知通道形态：{kind}")

    # **播种初值**（两侧初态必须一致，否则比的是「初态」而不是「行为」）
    for name, value in scenario.initial.items():
        channel = channels.get(name)
        if channel is None:
            continue
        # ⚠️ 播种 MUST 与「节点写一个值」**同款** ⇒ 归约通道的**首写直存**
        # （上游 ``binop.py:126-128`` 同款）⇒ 不可多包一层
        channel.update([value])

    nodes: dict[str, Any] = {}
    for name, (subscribes, fn) in scenario.nodes.items():
        nodes[name] = NodeSpec(
            subscribes=subscribes, run=_instrument(scenario, fn, name, gate)
        )

    # 自由图侧的 ``__end__`` 只作 **goto 目标**；边到 ``__end__`` 会被校验拒绝
    # ⇒ 「**无出边**」即「终止」，与上游「边到 END」**同义** ⇒ 对跑时归一
    # ⚠️ **2026-11-13 · B7F4**：**只剥除「单源键」的** ``__end__`` 目标 ⇒ ⇒
    # **多源键**的 ``__end__`` 目标**穿透**到 ``GraphSpec`` 构造期 ⇒ ⇒
    # freegraph 的「多源边 → ``__end__`` ⇒ 构造期显式失败」（**V-16** · **X-04**）
    # 在差分夹具里**可判定**（**否则该分支永远不可达** ⇒ **D-25 落空**）⇒ ⇒
    # 「**边到 ``__end__`` 即终止**」的既有语义**逐字不变**。
    edges = {
        src: (
            tuple(target for target in targets if target != "__end__")
            if isinstance(src, str)
            else tuple(targets)
        )
        for src, targets in scenario.edges.items()
    }
    try:
        spec = GraphSpec(channels=channels, nodes=nodes, edges=edges)
    except Exception as exc:  # noqa: BLE001
        # ⚠️ **构造期失败**（**B7F4**）⇒ 与「运行期失败」**区分**记录
        return (
            "ERROR",
            f"{type(exc).__name__}",
            _exc_detail(exc),
            {
                "exception": exc,
                "interrupt": (),
                "calls": list(scenario.calls),
                "state": {},
                "stage": "construct",
            },
        )
    scheduler_state = SchedulerState()
    if scenario.resume_input is not _UNSET or scenario.fg_suspends:
        # ⚠️ **B10F1**：**图级入口**（``run_graph``）—— 恢复路径**必须**经由
        # checkpointer（**上游同款**）⇒ ⇒ **两段式**跑法（第一次 ⇒ 挂起；
        # 第二次 ⇒ 以 ``resume_input`` 恢复）⇒ ⇒ 比**恢复后**的结果。
        return _run_freegraph_graph(scenario, spec, channels)
    try:
        result = run_super_steps(spec, scheduler_state, max_concurrency=cap)
    except Exception as exc:  # noqa: BLE001
        return (
            "ERROR",
            f"{type(exc).__name__}",
            _exc_detail(exc),
            {
                "exception": exc,
                "interrupt": _interrupt_payload(exc),
                "calls": list(scenario.calls),
                "state": _sparse(scheduler_state),
                "stage": "run",
            },
        )
    return (
        "OK",
        dict(result.state),
        f"executed={list(result.executed)}",
        {
            "exception": None,
            "interrupt": (),
            "calls": list(scenario.calls),
            "state": dict(result.state),
            "stage": "ok",
        },
    )


def _run_freegraph_graph(
    scenario: Scenario, spec: Any, channels: dict[str, Any]
) -> tuple[str, Any, str, dict[str, Any]]:
    """**图级入口**的两段式跑法（**B10F1** · DI-01…DI-08）。

    * 第一次 ⇒ 以 ``scenario.initial`` 起跑 ⇒ ⇒ **挂起**时返回
      ``InterruptResult``（**不**抛）⇒ ⇒ 中断载荷从**结果**取；
    * 第二次 ⇒ 以 ``scenario.resume_input`` 恢复 ⇒ ⇒ 比**恢复后**的结果。
    """
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.contracts.types import RunConfig
    from freegraph.runtime import run_graph

    stub = _ProbeCheckpointer()
    config = RunConfig(thread_id="diff")
    # ⚠️ **DI-04**：**不挂** checkpointer ⇒ ⇒ 恢复**必须**显式失败
    # （**上游同款** · **实测 E-3**）⇒ ⇒ 两侧**都**失败 ⇒ ⇒ 判词 **STRICTER**。
    saver = None if scenario.fg_no_checkpointer else stub
    initial = dict(scenario.initial) if scenario.initial else None
    try:
        first = run_graph(spec, initial, checkpointer=saver, config=config)
    except Exception as exc:  # noqa: BLE001
        return (
            "ERROR",
            f"{type(exc).__name__}",
            _exc_detail(exc),
            {
                "exception": exc,
                "interrupt": (),
                "calls": list(scenario.calls),
                "state": {},
                "stage": "run",
            },
        )
    if scenario.resume_input is not _UNSET:
        try:
            result = run_graph(
                spec,
                _as_command(scenario.resume_input),
                checkpointer=saver,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            return (
                "ERROR",
                f"{type(exc).__name__}",
                _exc_detail(exc),
                {
                    "exception": exc,
                    "interrupt": (),
                    "calls": list(scenario.calls),
                    "state": {},
                    "stage": "run",
                },
            )
        payload = tuple(getattr(result, "interrupts", ()) or ())
        state = dict(getattr(result, "state", {}) or {})
    else:
        payload = tuple(getattr(first, "interrupts", ()) or ())
        state = dict(getattr(first, "state", {}) or {})
    return (
        "OK",
        state,
        f"executed={list(getattr(first, 'executed', ()))}",
        {
            "exception": None,
            "interrupt": payload,
            "calls": list(scenario.calls),
            "state": state,
            "stage": "ok",
        },
    )


def _as_command(value: Any) -> Any:
    """把「第二次输入」归一成 ``Command``（**两侧同款**）。"""
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.contracts.types import Command

    if isinstance(value, Command):
        return value
    return Command(resume=value)


def _sparse(scheduler_state: Any) -> dict[str, Any]:
    """取调度状态里的**稀疏通道值**（中断轮也取得到 —— 合并**已经**发生）。"""
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.runtime import read_channels

    return dict(read_channels(scheduler_state.channels))


def _exc_detail(exc: BaseException) -> str:
    """异常的**可观察要点**（类名 + 首行消息）。"""
    msg = str(exc).strip().splitlines()
    return f"{type(exc).__name__}: {msg[0] if msg else ''}"


def _as_upstream_command(value: Any) -> Any:
    """把「第二次输入」归一成上游的 ``Command``（**两侧同款**）。"""
    from langgraph.types import Command

    if isinstance(value, Command):
        return value
    return Command(resume=value)


# ── 上游侧 ──────────────────────────────────────────────────────────────────


def run_upstream(scenario: Scenario) -> tuple[str, Any, str, dict[str, Any]]:
    """跑上游 langgraph ⇒ 返回 ``(结果摘要, 状态/载荷, 细节, 附加信息)``。

    ⚠️ **B12F1 扩展**：提取结果的 **``__interrupt__`` 键**（上游**根图抑制**中断 ⇒
    中断落进结果键而不是抛出来 ⇒ 两侧的**取法不同**但**比的是同一批东西**）。
    """
    from typing import Annotated

    from typing_extensions import TypedDict

    from langgraph.channels.ephemeral_value import EphemeralValue
    from langgraph.graph import END, START, StateGraph

    gate = threading.Barrier(scenario.barrier) if scenario.barrier else None

    # 通道形态 ⇒ TypedDict 字段类型（上游按字段名建通道）
    annotations: dict[str, Any] = {}
    for name, kind in scenario.channels.items():
        if kind == "binop":
            # ⚠️ 上游的**归约通道** MUST 用 ``Annotated[..., operator.add]``
            # （否则上游建的是 LastValue ⇒ 同轮多写会报错 ⇒ 比的是另一套语义）
            annotations[name] = Annotated[list, operator.add]
        elif kind == "ephemeral":
            # ⚠️ **2026-11-13 · B7F4**：上游的**路由型通道** MUST 显式声明
            # ``Annotated[Any, EphemeralValue]``（上游 ``graph/state.py:1892-1900``
            # 的 ``_is_field_channel``）⇒ ⇒ 裸 ``Any`` 建的是 **LastValue**
            # ⇒ ⇒ 「ephemeral」这一维**只在两侧都真的是路由型**时才有意义。
            annotations[name] = Annotated[Any, EphemeralValue]
        else:
            annotations[name] = Any
    schema = TypedDict("S", annotations)  # type: ignore[valid-type]

    graph = StateGraph(schema)
    upstream_nodes = scenario.nodes_upstream or scenario.nodes
    try:
        for name, (_subscribes, fn) in upstream_nodes.items():
            graph.add_node(name, _instrument(scenario, fn, name, gate))
        for src, targets in scenario.edges.items():
            if isinstance(src, tuple):
                # ⚠️ **上游的真实形态**（research **DR-7**）：多源边 ⇒
                # ``add_edge(list(starts), target)``（上游 ``graph/state.py:928``
                # 的 ``add_edge`` · ``:969`` 的 ``for start in start_key:``）⇒
                # ⇒ 上游建的**正是**一条 join 屏障通道（``:1560-1575`）⇒
                # ⇒ 比的**确实是**「上游同款」的屏障语义。
                graph.add_edge(
                    list(src), END if targets[0] == "__end__" else targets[0]
                )
            elif src == "__start__":
                graph.add_edge(START, targets[0])
                for extra in targets[1:]:
                    graph.add_edge(START, extra)
            else:
                for target in targets:
                    graph.add_edge(src, END if target == "__end__" else target)
        if scenario.upstream_extra is not None:
            scenario.upstream_extra(graph)
        # ⚠️ **B10F1**：恢复路径**必须**挂 checkpointer（**上游同款** · 实测 E-3）
        # ⇒ ⇒ 上游侧**挂** ``InMemorySaver``（**上游的形状**）⇒ ⇒ 两段式可比。
        if scenario.upstream_checkpointer:
            from langgraph.checkpoint.memory import InMemorySaver

            compiled = graph.compile(checkpointer=InMemorySaver())
        else:
            compiled = graph.compile()
    except Exception as exc:  # noqa: BLE001
        # ⚠️ **构造期失败**（**B7F4**）⇒ 与「运行期失败」**区分**记录
        return (
            "ERROR",
            f"{type(exc).__name__}",
            _exc_detail(exc),
            {
                "exception": exc,
                "interrupt": (),
                "calls": list(scenario.calls),
                "state": {},
                "stage": "construct",
            },
        )
    try:
        # ⚠️ **B10F1**：挂了 checkpointer ⇒ 上游**必须**带 ``thread_id``
        # （上游 ``Checkpointer requires one or more of the following
        # 'configurable' keys`` · ``thread_id``）⇒ ⇒ 两侧**同一会话**。
        up_config = (
            {"configurable": {"thread_id": "diff"}}
            if scenario.upstream_checkpointer
            else None
        )
        result = compiled.invoke(dict(scenario.initial), up_config)
        if scenario.resume_input is not _UNSET:
            # ⚠️ **两段式**（**B10F1**）：第二次 ⇒ 以 ``resume_input`` 恢复
            result = compiled.invoke(
                _as_upstream_command(scenario.resume_input), up_config
            )
    except Exception as exc:  # noqa: BLE001
        return (
            "ERROR",
            f"{type(exc).__name__}",
            _exc_detail(exc),
            {
                "exception": exc,
                "interrupt": (),
                "calls": list(scenario.calls),
                "state": {},
                "stage": "run",
            },
        )
    interrupt = tuple(result.get("__interrupt__", ()) or ())
    return (
        "OK",
        dict(result),
        f"executed={scenario.calls!r}",
        {
            "exception": None,
            "interrupt": interrupt,
            "calls": list(scenario.calls),
            "state": {k: v for k, v in dict(result).items() if k != "__interrupt__"},
            "stage": "ok",
        },
    )



# ── 场景集 ──────────────────────────────────────────────────────────────────

STRICTER_NOTES = {
    "未知 key 写入": "freegraph 显式失败（InvalidChannelUpdateError）；上游 warning + 静默忽略（_algo.py:310-313）",
    "非法 goto 目标": "freegraph 显式失败（ValueError）；上游 warning + 静默忽略",
    "空命令列表": "freegraph 失败（TypeError）；上游失败（InvalidUpdateError）—— 类型不同 · 语义等价",
    "覆盖型通道同轮重复写": "freegraph 失败（InvalidChannelUpdateError）；上游失败（InvalidUpdateError）—— 同族",
}


# ── B7F4 · D-24 的参数化空间（**H-6** · 立项书 §4.2 S5 ③ 的最小增量）─────────

#: **屏障形态**（单源 / 多源）。
D24_BARRIER_SHAPES: tuple[str, ...] = ("single", "multi")

#: **通道类型**（``last`` / ``binop`` / ``ephemeral``）。
D24_CHANNEL_KINDS: tuple[str, ...] = ("last", "binop", "ephemeral")

#: **源可达性**（全可达 / 缺一源）。
D24_REACHABILITIES: tuple[str, ...] = ("all-reachable", "one-unreachable")

#: 各**通道类型**的**初始值**与**写入值**（⇒ 两侧的类型**逐字对齐**）。
_D24_SEED_AND_WRITE: dict[str, tuple[Any, Any]] = {
    "last": (0, 1),
    "binop": ([], None),
    "ephemeral": ("", None),
}


def d24_parameter_space() -> list[tuple[str, str, str]]:
    """**D-24** 的参数化取值空间（**屏障形态 × 通道类型 × 源可达性**）。

    ⚠️ **只铺「屏障维度」的最小增量**（research **DR-6** · 承接 **H-6**）⇒ ⇒
    **MUST NOT** 一次性铺开立项书 §4.2 **S5 ③** 的**全量**枚举（reducer × 通道
    的全组合）⇒ ⇒ 归后续 feature（**M-13**）。
    """
    return [
        (shape, kind, reach)
        for shape in D24_BARRIER_SHAPES
        for kind in D24_CHANNEL_KINDS
        for reach in D24_REACHABILITIES
    ]


def d24_scenario(shape: str, kind: str, reach: str) -> Scenario:
    """构造**一个** **D-24** 的参数化场景（屏障形态 × 通道类型 × 源可达性）。

    * **拓扑刻意「一轮一个节点」** ⇒ ⇒ **覆盖型**（``last``）通道**不会**遇到
      「同轮多写」⇒ ⇒ 三种通道形态**可比**；
    * **两个通道**：``value``（**形态随参数变**）+ ``trace``（**恒为归约型** ⇒
      **节点序列**逐字可观测）；
    * **源可达性**：``one-unreachable`` ⇒ 屏障的**某个源**不可达 ⇒ ⇒ 屏障
      **不齐** ⇒ ⇒ 目标**不执行**（**上游同款** · 实测 **E-2**）。
    """
    seed, write = _D24_SEED_AND_WRITE[kind]
    calls: list[str] = []

    def _make(name: str) -> Any:
        def _run(state: dict[str, Any]) -> dict[str, Any]:
            calls.append(name)
            payload = [name] if kind == "binop" else write
            return {"value": payload, "trace": [name]}

        return _run

    if shape == "single":
        node_names = ("a", "b", "c")
        edges: dict[Any, tuple[str, ...]] = {
            "__start__": ("a",),
            "a": ("b",),
            "b": ("c",),
        }
    else:
        node_names = ("a", "b", "d", "c")
        edges = {
            "__start__": ("a",),
            "a": ("b",),
            "b": ("d",),
            ("b", "d"): ("c",),
        }
    if reach == "one-unreachable":
        # ⚠️ 让屏障的**某个源**不可达 ⇒ ⇒ 屏障**不齐** ⇒ ⇒ 目标**不执行**。
        edges = {k: v for k, v in edges.items() if k != "b"}

    return Scenario(
        name=f"D-24 · 参数化 · {shape} × {kind} × {reach}",
        channels={"value": kind, "trace": "binop"},
        initial={"value": seed, "trace": []},
        nodes={name: ((), _make(name)) for name in node_names},
        edges=edges,
        calls=calls,
        verdict="SAME",
    )


def _scenarios() -> list[Scenario]:
    """全部场景。"""
    out: list[Scenario] = []

    # ① 线性两跳：静态边 + 归约通道
    calls: list[str] = []

    def a(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("a")
        return {"messages": ["a"]}

    def b(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("b")
        return {"messages": ["b"]}

    out.append(
        Scenario(
            name="线性两跳 · 静态边 · 归约通道",
            channels={"messages": "binop"},
            initial={"messages": ["seed"]},
            nodes={"a": (("messages",), a), "b": (("messages",), b)},
            edges={"__start__": ("a",), "a": ("b",), "b": ("__end__",)},
            calls=calls,
        )
    )

    # ② 扇出：同一轮两个节点都写归约通道
    calls2: list[str] = []

    def fan1(state: dict[str, Any]) -> dict[str, Any]:
        calls2.append("fan1")
        return {"messages": ["x"]}

    def fan2(state: dict[str, Any]) -> dict[str, Any]:
        calls2.append("fan2")
        return {"messages": ["y"]}

    out.append(
        Scenario(
            name="扇出 · 同一轮两个节点写同一归约通道",
            channels={"messages": "binop"},
            initial={"messages": ["seed"]},
            nodes={"fan1": (("messages",), fan1), "fan2": (("messages",), fan2)},
            edges={"__start__": ("fan1", "fan2")},
            calls=calls2,
        )
    )

    # ③ 覆盖型通道：两个节点同轮写同一个覆盖通道
    calls3: list[str] = []

    def over1(state: dict[str, Any]) -> dict[str, Any]:
        calls3.append("over1")
        return {"count": 1}

    def over2(state: dict[str, Any]) -> dict[str, Any]:
        calls3.append("over2")
        return {"count": 2}

    out.append(
        Scenario(
            name="覆盖型通道 · 同轮重复写",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"over1": (("count",), over1), "over2": (("count",), over2)},
            edges={"__start__": ("over1", "over2")},
            calls=calls3,
            note="两边**都失败**（上游 InvalidUpdateError / freegraph InvalidChannelUpdateError）—— 异常**类名**不同 · **失败语义同款**",
        )
    )

    # ④ 未知 key 写入
    calls4: list[str] = []

    def ghost(state: dict[str, Any]) -> dict[str, Any]:
        calls4.append("ghost")
        return {"ghost": 1}

    out.append(
        Scenario(
            name="未知 key 写入",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"ghost": (("count",), ghost)},
            edges={"__start__": ("ghost",)},
            calls=calls4,
            verdict="STRICTER",
            note=STRICTER_NOTES["未知 key 写入"],
        )
    )

    # ⑤ 节点返回 None（上游同款：无写入）
    calls5: list[str] = []

    def none_node(state: dict[str, Any]) -> Any:
        calls5.append("none_node")
        return None

    out.append(
        Scenario(
            name="节点返回 None · 无写入",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"none_node": (("count",), none_node)},
            edges={"__start__": ("none_node",)},
            calls=calls5,
        )
    )

    # ⑥ 节点返回空 dict（无写入）
    calls6: list[str] = []

    def empty_node(state: dict[str, Any]) -> dict[str, Any]:
        calls6.append("empty_node")
        return {}

    out.append(
        Scenario(
            name="节点返回空 dict · 无写入",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"empty_node": (("count",), empty_node)},
            edges={"__start__": ("empty_node",)},
            calls=calls6,
        )
    )

    # ⑦ END 语义：END 不终止整张图（静态边照走）
    calls7: list[str] = []

    def to_end(state: dict[str, Any]) -> dict[str, Any]:
        calls7.append("to_end")
        return {"count": 1}

    def after(state: dict[str, Any]) -> dict[str, Any]:
        calls7.append("after")
        return {"count": 2}

    out.append(
        Scenario(
            name="END · 不终止整张图（静态边照走）",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"to_end": (("count",), to_end), "after": (("count",), after)},
            edges={"__start__": ("to_end",), "to_end": ("__end__",)},
            calls=calls7,
            note="自由图侧的 ``__end__`` 只作 **goto 目标**；边到 ``__end__`` 会被校验拒绝 ⇒ 本场景两侧用「**无出边**」表达终止",
        )
    )

    # ⑧ 覆盖型通道的「无写入」节点不触发下游（订阅集有值才跑）
    calls8: list[str] = []

    def quiet(state: dict[str, Any]) -> dict[str, Any]:
        calls8.append("quiet")
        return {}

    out.append(
        Scenario(
            name="无写入节点 · 下游不触发",
            channels={"count": "last", "other": "last"},
            initial={"count": 0},
            nodes={"quiet": (("other",), quiet)},
            edges={"__start__": ("quiet",)},
            calls=calls8,
        )
    )

    # ⑨ Command 的 goto（动态边）—— 上游需声明式目标，自由图用 Command
    calls9: list[str] = []

    def router_fg(state: dict[str, Any]) -> Any:
        calls9.append("router")
        from freegraph.contracts import Command as FgCommand

        return FgCommand(goto="left")

    def router_up(state: dict[str, Any]) -> Any:
        calls9.append("router")
        from langgraph.types import Command as UpCommand

        return UpCommand(goto="left")

    def left_fg(state: dict[str, Any]) -> dict[str, Any]:
        calls9.append("left")
        return {"count": 9}

    def left_up(state: dict[str, Any]) -> dict[str, Any]:
        calls9.append("left")
        return {"count": 9}

    def declare_conditional(graph: Any) -> None:
        from langgraph.graph import END

        graph.add_conditional_edges("router", lambda state: ["left"], ["left"])

    out.append(
        Scenario(
            name="Command.goto · 动态跳转",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={
                "router": (("count",), router_fg),
                "left": (("count",), left_fg),
            },
            nodes_upstream={
                "router": (("count",), router_up),
                "left": (("count",), left_up),
            },
            edges={"__start__": ("router",)},
            calls=calls9,
            upstream_extra=declare_conditional,
            verdict="DIFF",
            note="上游 Command.goto 需**声明式**目标（`add_conditional_edges`）；自由图用**边触发源** ⇒ 机制不同 · 语义同款",
        )
    )


    # ⑩ Command(update=...) 的写入（两边同款）
    calls10: list[str] = []

    def cmd_fg(state: dict[str, Any]) -> Any:
        calls10.append("cmd")
        from freegraph.contracts import Command as FgCommand

        return FgCommand(update={"messages": ["via-command"]})

    def cmd_up(state: dict[str, Any]) -> Any:
        calls10.append("cmd")
        from langgraph.types import Command as UpCommand

        return UpCommand(update={"messages": ["via-command"]})

    out.append(
        Scenario(
            name="Command.update · 写入",
            channels={"messages": "binop"},
            initial={"messages": ["seed"]},
            nodes={"cmd": (("messages",), cmd_fg)},
            nodes_upstream={"cmd": (("messages",), cmd_up)},
            edges={"__start__": ("cmd",)},
            calls=calls10,
        )
    )

    # ⑪ 混合通道 · 三跳链（归约 + 覆盖）
    calls11: list[str] = []

    def m1(state: dict[str, Any]) -> dict[str, Any]:
        calls11.append("m1")
        return {"messages": ["m1"], "count": 1}

    def m2(state: dict[str, Any]) -> dict[str, Any]:
        calls11.append("m2")
        return {"messages": ["m2"]}

    def m3(state: dict[str, Any]) -> dict[str, Any]:
        calls11.append("m3")
        return {"messages": ["m3"], "count": 3}

    out.append(
        Scenario(
            name="混合通道 · 三跳链",
            channels={"messages": "binop", "count": "last"},
            initial={"messages": ["seed"], "count": 0},
            nodes={
                "m1": (("messages", "count"), m1),
                "m2": (("messages", "count"), m2),
                "m3": (("messages", "count"), m3),
            },
            edges={"__start__": ("m1",), "m1": ("m2",), "m2": ("m3",)},
            calls=calls11,
        )
    )

    # ⑫ 环路（递归上限命中）
    calls12: list[str] = []

    def loop(state: dict[str, Any]) -> dict[str, Any]:
        calls12.append("loop")
        return {"count": state.get("count", 0) + 1}

    out.append(
        Scenario(
            name="环路 · 递归上限命中",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"loop": (("count",), loop)},
            edges={"__start__": ("loop",), "loop": ("loop",)},
            calls=calls12,
            verdict="DIFF",
            note="上游命中 ``GraphRecursionError``（recursion_limit 默认 25）⇒ freegraph 命中的是**自己的**上限（10007）⇒ 上限值不同 · **失败语义同款**（都失败）",
        )
    )

    # ⑬ 节点抛错（异常传播）
    calls13: list[str] = []

    def boom(state: dict[str, Any]) -> dict[str, Any]:
        calls13.append("boom")
        raise RuntimeError("boom")

    out.append(
        Scenario(
            name="节点抛错 · 异常传播",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"boom": (("count",), boom)},
            edges={"__start__": ("boom",)},
            calls=calls13,
        )
    )

    # ⑭ 中间节点无写入 · 链继续
    calls14: list[str] = []

    def h1(state: dict[str, Any]) -> dict[str, Any]:
        calls14.append("h1")
        return {"count": 1}

    def h2(state: dict[str, Any]) -> dict[str, Any]:
        calls14.append("h2")
        return {}

    def h3(state: dict[str, Any]) -> dict[str, Any]:
        calls14.append("h3")
        return {"count": 3}

    out.append(
        Scenario(
            name="中间节点无写入 · 链继续",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={
                "h1": (("count",), h1),
                "h2": (("count",), h2),
                "h3": (("count",), h3),
            },
            edges={"__start__": ("h1",), "h1": ("h2",), "h2": ("h3",)},
            calls=calls14,
        )
    )

    # ⑮ 覆盖型通道：下游读到上游的**新值**
    calls15: list[str] = []
    seen: list[Any] = []

    def r1(state: dict[str, Any]) -> dict[str, Any]:
        calls15.append("r1")
        return {"count": 42}

    def r2(state: dict[str, Any]) -> dict[str, Any]:
        calls15.append("r2")
        seen.append(state.get("count"))
        return {}

    out.append(
        Scenario(
            name="覆盖型通道 · 下游读到新值",
            channels={"count": "last"},
            initial={"count": 0},
            nodes={"r1": (("count",), r1), "r2": (("count",), r2)},
            edges={"__start__": ("r1",), "r1": ("r2",)},
            calls=calls15,
        )
    )

    # ══════════════════════════════════════════════════════════════════════════
    # B12F1 · 差分场景组（D-01 … D-15）
    #
    # ⚠️ **判词纪律**（spec FR-026 · 澄清轮 Q13 / Q18）：
    # * **上游自身不确定**的场景（**D-13** · **D-15**）MUST **NOT** 逐字比对两侧
    #   ⇒ MUST 拆成「freegraph 一侧**重复跑 ≥ 3 次每次同一个**」+「上游一侧**只断言
    #   也在同一批里**」⇒ ⇒ 差分门禁 **MUST NOT** 偶发红；
    # * **STRICTER** MUST 写明理由；**DIFF** MUST 写明理由。
    # ══════════════════════════════════════════════════════════════════════════

    # ── D-01 · 并发重叠（**SAME**）──────────────────────────────────────────
    d01_calls: list[str] = []

    def d01_left(state: dict[str, Any]) -> dict[str, Any]:
        d01_calls.append("left")
        return {"messages": ["left"]}

    def d01_right(state: dict[str, Any]) -> dict[str, Any]:
        d01_calls.append("right")
        return {"messages": ["right"]}

    out.append(
        Scenario(
            name="D-01 · 并发重叠（两个节点真同时在跑）",
            channels={"messages": "binop"},
            initial={},
            nodes={"left": (("messages",), d01_left), "right": (("messages",), d01_right)},
            edges={"__start__": ("left", "right")},
            calls=d01_calls,
            barrier=2,
            time_window=True,
            verdict="SAME",
            note="两侧都用**线程池**跑同轮节点 ⇒ 屏障**两侧都被放行** ⇒ 执行时间窗**重叠 > 0**",
        )
    )

    # ── D-02 · 首个异常的对象 identity 与消息（**SAME**）────────────────────
    d02_raised: list[BaseException] = []
    # ⚠️ 异常对象 MUST 在节点函数**外**创建 ⇒ 两侧抛的是**同一个**对象 ⇒ identity 可判
    d02_error = ValueError("boom")

    def d02_bad(state: dict[str, Any]) -> dict[str, Any]:
        d02_raised.append(d02_error)
        raise d02_error

    out.append(
        Scenario(
            name="D-02 · 首个异常的对象 identity 与消息",
            channels={"count": "last"},
            initial={},
            nodes={"bad": (("count",), d02_bad)},
            edges={"__start__": ("bad",)},
            raised=d02_raised,
            expect_exception_identity=True,
            verdict="SAME",
            note="两侧捕获到的异常 MUST 是节点内抛出的**同一个对象**（``is``）⇒ 类型 / 消息逐字一致",
        )
    )

    # ── D-03 · 取消语义（**SAME** · 端到端集合比对）──────────────────────────
    d03_calls: list[str] = []

    def d03_ok1(state: dict[str, Any]) -> dict[str, Any]:
        d03_calls.append("ok1")
        return {"messages": ["ok1"]}

    def d03_ok2(state: dict[str, Any]) -> dict[str, Any]:
        d03_calls.append("ok2")
        return {"messages": ["ok2"]}

    def d03_fail(state: dict[str, Any]) -> dict[str, Any]:
        d03_calls.append("fail")
        raise ValueError("boom")

    out.append(
        Scenario(
            name="D-03 · 取消语义（端到端：最后实际被启动了哪些节点）",
            channels={"messages": "binop"},
            initial={},
            nodes={
                "ok1": (("messages",), d03_ok1),
                "ok2": (("messages",), d03_ok2),
                "fail": (("messages",), d03_fail),
            },
            edges={"__start__": ("ok1", "ok2", "fail")},
            calls=d03_calls,
            barrier=3,
            compare_started=True,
            verdict="SAME",
            note="**端到端**只比「最后实际被启动了哪些节点」的**集合**（**不**比『取消与否』）"
            "⇒ ⚠️ **机制级**（尚未启动的任务其 ``cancel()`` → ``True``）由**单元夹具**承担"
            "（``tests/runtime/test_superstep_errors.py`` · 契约 §11 **I-17**）⇒ **不在**本探针内做",
        )
    )

    # ── D-04 · 中断合并成一个异常且载荷为元组（**SAME**）────────────────────
    def d04_fg(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.errors import GraphInterrupt as FgGraphInterrupt
        from freegraph.contracts.types import Interrupt as FgInterrupt

        raise FgGraphInterrupt((FgInterrupt(value="approve-A", id="a"),))

    def d04_up(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.errors import GraphInterrupt as UpGraphInterrupt
        from langgraph.types import Interrupt as UpInterrupt

        raise UpGraphInterrupt((UpInterrupt("approve-A", id="a"),))

    out.append(
        Scenario(
            name="D-04 · 中断合并成一个异常且载荷为元组",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), d04_fg)},
            nodes_upstream={"ask": (("count",), d04_up)},
            edges={"__start__": ("ask",)},
            expect_interrupt=True,
            compare="set",
            verdict="SAME",
            note="freegraph 从**异常**的 ``args[0]`` 取 · 上游从**结果键** ``__interrupt__`` 取"
            "⇒ 比的是**同一批东西** ⇒ ⚠️ 按**集合**比（上游的元组内元素顺序**竞态**）",
        )
    )

    # ── D-05 · 中断节点的写入被丢弃 / 其它节点照常合并（**SAME**）────────────
    def d05_fg_ask(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.errors import GraphInterrupt as FgGraphInterrupt
        from freegraph.contracts.types import Interrupt as FgInterrupt

        raise FgGraphInterrupt((FgInterrupt(value="approve", id="ask"),))

    def d05_up_ask(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.errors import GraphInterrupt as UpGraphInterrupt
        from langgraph.types import Interrupt as UpInterrupt

        raise UpGraphInterrupt((UpInterrupt("approve", id="ask"),))

    def d05_writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["written"]}

    out.append(
        Scenario(
            name="D-05 · 中断节点的写入被丢弃 / 其它节点照常合并",
            channels={"messages": "binop"},
            initial={},
            nodes={
                "ask": (("messages",), d05_fg_ask),
                "writer": (("messages",), d05_writer),
            },
            nodes_upstream={
                "ask": (("messages",), d05_up_ask),
                "writer": (("messages",), d05_writer),
            },
            edges={"__start__": ("ask", "writer")},
            expect_interrupt=True,
            compare="set",
            verdict="SAME",
            note="**中断不是「出错」** ⇒ 同轮**其它**节点的写入**照常合并** ⇒ 两侧的最终状态逐字相等",
        )
    )

    # ── D-06 · 并发 == 串行（**SAME** · freegraph 内部对照）──────────────────
    def d06_writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    def _d06_judge(scenario: Scenario) -> tuple[bool, str]:
        concurrent = run_freegraph(scenario)
        serial = run_freegraph(scenario, max_concurrency=1)
        if concurrent[0] != "OK" or serial[0] != "OK":
            return False, f"并发侧={concurrent[0]} · 串行侧={serial[0]}"
        same_state = concurrent[1] == serial[1]
        same_writes = concurrent[3]["state"] == serial[3]["state"]
        return (same_state and same_writes), (
            f"并发状态={concurrent[1]} · 串行状态={serial[1]}"
        )

    out.append(
        Scenario(
            name="D-06 · 并发 == 串行（同一规格）",
            channels={"messages": "binop"},
            initial={},
            nodes={"left": (("messages",), d06_writer), "right": (("messages",), d06_writer)},
            edges={"__start__": ("left", "right")},
            fg_only=_d06_judge,
            verdict="SAME",
            note="**同一份规格**在**缺省**与 ``max_concurrency=1`` 两种模式下 ⇒ 状态与待写入**逐项相等**",
        )
    )

    # ── D-07 · 同轮顺序 = 节点名序（**SAME**）──────────────────────────────
    def d07_a(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["a"]}

    def d07_z(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["z"]}

    def _d07_judge(scenario: Scenario) -> tuple[bool, str]:
        fg_kind, fg_state, _, fg_extra = run_freegraph(scenario)
        if fg_kind != "OK":
            return False, f"freegraph 侧={fg_kind}"
        # ⚠️ **节点表声明顺序**与**名字顺序**相反 ⇒ 执行序列 MUST 是**节点名序**
        order_ok = list(fg_extra["state"]["messages"]) == ["a", "z"]
        up_kind, up_state, _, _ = run_upstream(scenario)
        upstream_ok = up_kind == "OK" and list(up_state.get("messages", [])) == ["a", "z"]
        return (order_ok and upstream_ok), (
            f"freegraph={fg_extra['state']} · upstream={up_state}"
        )

    out.append(
        Scenario(
            name="D-07 · 同轮顺序 = 节点名序",
            channels={"messages": "binop"},
            initial={},
            nodes={"z_node": (("messages",), d07_z), "a_node": (("messages",), d07_a)},
            edges={"__start__": ("z_node", "a_node")},
            fg_only=_d07_judge,
            verdict="SAME",
            note="**节点表声明顺序**与**名字顺序**相反 ⇒ 合并顺序 MUST 是**节点名序**"
            "（**上游同款** · ``_algo.py:482`` 的 ``sorted(triggered_nodes)``）",
        )
    )

    # ── D-08 · 归约通道的合并顺序（**SAME**）────────────────────────────────
    def d08_left(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["left"]}

    def d08_right(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["right"]}

    def _d08_judge(scenario: Scenario) -> tuple[bool, str]:
        fg_kind, _, _, fg_extra = run_freegraph(scenario)
        up_kind, up_state, _, _ = run_upstream(scenario)
        if fg_kind != "OK" or up_kind != "OK":
            return False, f"freegraph={fg_kind} · upstream={up_kind}"
        fg_order = list(fg_extra["state"].get("messages", []))
        up_order = list(up_state.get("messages", []))
        return (fg_order == up_order == ["left", "right"]), (
            f"freegraph={fg_order} · upstream={up_order}"
        )

    out.append(
        Scenario(
            name="D-08 · 归约通道的合并顺序",
            channels={"messages": "binop"},
            initial={},
            nodes={"left": (("messages",), d08_left), "right": (("messages",), d08_right)},
            edges={"__start__": ("left", "right")},
            fg_only=_d08_judge,
            verdict="SAME",
            note="**非交换归约器**下同一通道的元素顺序 MUST == **节点名序** ⇒ 两侧逐项相等",
        )
    )

    # ── D-09 · 异常优先于中断（**SAME**）───────────────────────────────────
    def d09_fg_boom(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom")

    def d09_fg_ask(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.errors import GraphInterrupt as FgGraphInterrupt
        from freegraph.contracts.types import Interrupt as FgInterrupt

        raise FgGraphInterrupt((FgInterrupt(value="approve", id="ask"),))

    def d09_up_ask(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.errors import GraphInterrupt as UpGraphInterrupt
        from langgraph.types import Interrupt as UpInterrupt

        raise UpGraphInterrupt((UpInterrupt("approve", id="ask"),))

    out.append(
        Scenario(
            name="D-09 · 异常优先于中断",
            channels={"count": "last"},
            initial={},
            nodes={
                "boom": (("count",), d09_fg_boom),
                "ask": (("count",), d09_fg_ask),
            },
            nodes_upstream={
                "boom": (("count",), d09_fg_boom),
                "ask": (("count",), d09_up_ask),
            },
            edges={"__start__": ("boom", "ask")},
            verdict="SAME",
            note="同现时 MUST 抛**真实异常** ⇒ 中断**不掩盖**失败（**上游同款**）",
        )
    )

    # ── D-10 · 多会话隔离（**SAME** · freegraph 内部对照）────────────────────
    def d10_writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    def _d10_judge(scenario: Scenario) -> tuple[bool, str]:
        first = run_freegraph(scenario)
        second = run_freegraph(scenario)
        if first[0] != "OK" or second[0] != "OK":
            return False, f"第一次={first[0]} · 第二次={second[0]}"
        same = first[1] == second[1]
        no_accumulate = list(first[1].get("messages", [])) == ["x"]
        return (same and no_accumulate), (
            f"第一次={first[1]} · 第二次={second[1]}"
        )

    out.append(
        Scenario(
            name="D-10 · 多会话隔离（同一规格连续跑两次不累积）",
            channels={"messages": "binop"},
            initial={},
            nodes={"writer": (("messages",), d10_writer)},
            edges={"__start__": ("writer",)},
            fg_only=_d10_judge,
            verdict="SAME",
            note="每次运行从规格**新建**通道实例 ⇒ 连续两次**不累积**（**上游同款** · P2-b 已落地）",
        )
    )

    # ── D-11 · 并发度缺省的上限（**SAME** · freegraph 内部对照）──────────────
    def _d11_judge(scenario: Scenario) -> tuple[bool, str]:
        cap = min(32, (os.cpu_count() or 1) + 4)
        kind, _, _, extra = run_freegraph(scenario)
        if kind != "OK":
            return False, f"freegraph 侧={kind}"
        # ⚠️ 全部节点各跑 **1** 次（超出上限者**排队**而不是被丢弃）
        once = all(len(v) == 1 for v in scenario.windows.values())
        return once, f"节点数={len(scenario.windows)} · 缺省上限={cap}"

    d11_nodes: dict[str, tuple[tuple[str, ...], Callable[[dict[str, Any]], Any]]] = {}
    for _i in range(20):

        def _d11_node(state: dict[str, Any], _i: int = _i) -> dict[str, Any]:
            time.sleep(0.03)
            return {"messages": [f"n{_i}"]}

        d11_nodes[f"n{_i:02d}"] = (("messages",), _d11_node)

    out.append(
        Scenario(
            name="D-11 · 并发度缺省的上限（超出者排队）",
            channels={"messages": "binop"},
            initial={},
            nodes=d11_nodes,
            edges={"__start__": tuple(f"n{i:02d}" for i in range(20))},
            time_window=True,
            fg_only=_d11_judge,
            verdict="SAME",
            note="缺省上限 = ``min(32, cpu+4)``（**上游同款**）⇒ 超出者**排队**（不是被丢弃）"
            "⇒ 全部节点各执行 **1** 次",
        )
    )

    # ── D-12 · goto 不互相吞并（**SAME**）───────────────────────────────────
    def d12_fg_left(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.types import Command as FgCommand

        return FgCommand(goto="t_left")

    def d12_fg_right(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.types import Command as FgCommand

        return FgCommand(goto="t_right")

    def d12_up_left(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.types import Command as UpCommand

        return UpCommand(goto="t_left")

    def d12_up_right(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.types import Command as UpCommand

        return UpCommand(goto="t_right")

    def d12_sink(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["sink"]}

    out.append(
        Scenario(
            name="D-12 · goto 不互相吞并",
            channels={"messages": "binop"},
            initial={},
            nodes={
                "left": (("messages",), d12_fg_left),
                "right": (("messages",), d12_fg_right),
                "t_left": (("messages",), d12_sink),
                "t_right": (("messages",), d12_sink),
            },
            nodes_upstream={
                "left": (("messages",), d12_up_left),
                "right": (("messages",), d12_up_right),
                "t_left": (("messages",), d12_sink),
                "t_right": (("messages",), d12_sink),
            },
            edges={"__start__": ("left", "right")},
            verdict="SAME",
            note="同轮多个节点各自的 ``goto`` 目标 MUST **全部**被触发（**不互相吞并**）",
        )
    )

    # ── D-13 · 首个异常的选取（**STRICTER**）────────────────────────────────
    def d13_a(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom-a")

    def d13_z(state: dict[str, Any]) -> dict[str, Any]:
        raise KeyError("boom-z")

    def _d13_judge(scenario: Scenario) -> tuple[bool, str]:
        # ① freegraph 一侧：重复跑 **≥ 3** 次**每次抛出同一个异常**
        seen: list[str] = []
        for _ in range(3):
            kind, _, _, extra = run_freegraph(scenario)
            seen.append(type(extra["exception"]).__name__ if extra["exception"] else "NONE")
        deterministic = len(set(seen)) == 1
        # ② 上游一侧：**只断言**也在同几个失败节点之中（**不**逐字比对）
        up_kind, _, _, up_extra = run_upstream(scenario)
        up_name = type(up_extra["exception"]).__name__ if up_extra["exception"] else "NONE"
        upstream_ok = up_name in {"ValueError", "KeyError"}
        return (deterministic and upstream_ok), (
            f"freegraph 三次={seen} · upstream={up_name}"
        )

    out.append(
        Scenario(
            name="D-13 · 首个异常的选取（确定性）",
            channels={"count": "last"},
            initial={},
            nodes={"a_fail": (("count",), d13_a), "z_fail": (("count",), d13_z)},
            edges={"__start__": ("a_fail", "z_fail")},
            barrier=2,
            fg_only=_d13_judge,
            verdict="STRICTER",
            note="freegraph 取「**节点名序**最靠前」者 ⇒ **确定**（重复 ≥ 3 次恒定）；"
            "上游从 ``done`` **集合** ``pop()`` ⇒ **自身不确定**（实测 50 次 ⇒ 26/24）"
            "⇒ ⇒ **比上游更严**（必须自研区 ②）",
        )
    )

    # ── D-14 · 其余失败的可见性（**STRICTER**）──────────────────────────────
    def d14_a(state: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("boom-a")

    def d14_z(state: dict[str, Any]) -> dict[str, Any]:
        raise KeyError("boom-z")

    def _d14_judge(scenario: Scenario) -> tuple[bool, str]:
        _, _, _, fg_extra = run_freegraph(scenario)
        _, _, _, up_extra = run_upstream(scenario)
        fg_notes = getattr(fg_extra["exception"], "__notes__", [])
        up_notes = getattr(up_extra["exception"], "__notes__", [])
        # ⚠️ 上游 **1.2.11** 也会给「**抛出的那个**」加一条 note（``During task with name ...``）
        # ⇒ ⇒ 判据 MUST 是「**除了抛出的那个之外** ⇒ 还有没有别的失败被暴露出来」：
        # * freegraph：抛出的**恒是**「a_fail」（**节点名序**最靠前）⇒ 它的附注 MUST
        #   指向**另一个**失败节点「z_fail」⇒ ⇒ **另一个失败被暴露**；
        # * 上游：它的 note 指向**它自己抛出的那个** ⇒ ⇒ **另一个失败始终不可见**。
        failing = ("a_fail", "z_fail")

        def _covered(notes: list[str]) -> int:
            return sum(1 for name in failing if any(name in note for note in notes))

        fg_raised = type(fg_extra["exception"]).__name__ if fg_extra["exception"] else "NONE"
        fg_other_visible = (
            fg_raised == "ValueError"
            and any("z_fail" in note for note in fg_notes)
            and not any("a_fail" in note for note in fg_notes)
        )
        up_covered = _covered(up_notes)
        upstream_ok = up_covered <= 1
        return (fg_other_visible and upstream_ok), (
            f"freegraph 抛={fg_raised} 附注={fg_notes} · "
            f"upstream 附注={up_notes}（覆盖 {up_covered} 个失败节点）"
        )

    out.append(
        Scenario(
            name="D-14 · 其余失败的可见性（附注）",
            channels={"count": "last"},
            initial={},
            nodes={"a_fail": (("count",), d14_a), "z_fail": (("count",), d14_z)},
            edges={"__start__": ("a_fail", "z_fail")},
            barrier=2,
            fg_only=_d14_judge,
            verdict="STRICTER",
            note="上游把其余异常只落 checkpoint 的 ``ERROR`` 通道 ⇒ **调用方看不到**；"
            "freegraph 以**附注**记录 ⇒ 失败信号**更严**（必须自研区 ②）",
        )
    )

    # ── D-15 · 中断元组内元素顺序（**STRICTER**）───────────────────────────
    def d15_fg_a(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.errors import GraphInterrupt as FgGraphInterrupt
        from freegraph.contracts.types import Interrupt as FgInterrupt

        raise FgGraphInterrupt((FgInterrupt(value="approve-A", id="a"),))

    def d15_fg_z(state: dict[str, Any]) -> dict[str, Any]:
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.contracts.errors import GraphInterrupt as FgGraphInterrupt
        from freegraph.contracts.types import Interrupt as FgInterrupt

        raise FgGraphInterrupt((FgInterrupt(value="approve-Z", id="z"),))

    def d15_up_a(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.errors import GraphInterrupt as UpGraphInterrupt
        from langgraph.types import Interrupt as UpInterrupt

        raise UpGraphInterrupt((UpInterrupt("approve-A", id="a"),))

    def d15_up_z(state: dict[str, Any]) -> dict[str, Any]:
        from langgraph.errors import GraphInterrupt as UpGraphInterrupt
        from langgraph.types import Interrupt as UpInterrupt

        raise UpGraphInterrupt((UpInterrupt("approve-Z", id="z"),))

    def _d15_judge(scenario: Scenario) -> tuple[bool, str]:
        # ① freegraph 一侧：重复跑 **≥ 3** 次**元素顺序逐项相同**
        orders: list[tuple[str, ...]] = []
        for _ in range(3):
            _, _, _, extra = run_freegraph(scenario)
            orders.append(
                tuple(getattr(i, "id", "") for i in extra["interrupt"])
            )
        deterministic = len(set(orders)) == 1 and orders[0] == ("a", "z")
        # ② 上游一侧：**只断言元素集合相同**（**不**比顺序 —— 上游顺序**竞态**）
        _, _, _, up_extra = run_upstream(scenario)
        up_set = sorted(getattr(i, "id", "") for i in up_extra["interrupt"])
        upstream_ok = up_set == ["a", "z"]
        return (deterministic and upstream_ok), (
            f"freegraph 三次={orders} · upstream 集合={up_set}"
        )

    out.append(
        Scenario(
            name="D-15 · 中断元组内元素顺序（确定性）",
            channels={"count": "last"},
            initial={},
            nodes={"a_ask": (("count",), d15_fg_a), "z_ask": (("count",), d15_fg_z)},
            nodes_upstream={"a_ask": (("count",), d15_up_a), "z_ask": (("count",), d15_up_z)},
            edges={"__start__": ("a_ask", "z_ask")},
            barrier=2,
            fg_only=_d15_judge,
            verdict="STRICTER",
            note="freegraph 取「**节点名序**」⇒ **确定**；上游从 ``done`` **集合** ``pop()`` "
            "⇒ 顺序**竞态**（实测 200 次 ⇒ 199/1）⇒ ⇒ **比上游更严**（必须自研区 ②）"
            "⇒ ⚠️ 上游侧**只断言集合相同**（**不**逐字比顺序 ⇒ 差分门禁不偶发红）",
        )
    )

    # ── B7F4 · 多源汇合边（AND / 屏障）的差分场景组（D-16…D-28）────────────
    def _msgs_node(name: str) -> Any:
        def _run(state: dict[str, Any]) -> dict[str, Any]:
            return {"msgs": [name]}

        return _run

    def _msgs_nodes(*names: str) -> dict[str, tuple[tuple[str, ...], Any]]:
        return {name: (("msgs",), _msgs_node(name)) for name in names}

    # ── D-16 · 标准屏障（上游 E-1 · **SAME**）───────────────────────────────
    out.append(
        Scenario(
            name="D-16 · 标准屏障（两源皆可达）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
            verdict="SAME",
            note="上游 E-1 基线 ``{'msgs': ['a','b','c']}`` ⇒ 屏障目标**严格晚于**所有源",
        )
    )

    # ── D-17 · 屏障不齐（上游 E-2 · **SAME**）───────────────────────────────
    out.append(
        Scenario(
            name="D-17 · 屏障不齐（一个源永不可达）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c", "d"),
            edges={"__start__": ("a", "b"), ("b", "d"): ("c",)},
            verdict="SAME",
            note="上游 E-2 基线 ``{'msgs': ['a','b']}`` ⇒ 屏障**不齐** ⇒ 目标**从不执行**且**不报错**",
        )
    )

    # ── D-18 · 单源边 + 不齐的屏障边并存（上游 E-3 · **SAME**）───────────────
    out.append(
        Scenario(
            name="D-18 · 单源边 + 不齐的屏障边并存（组间任一）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c", "d"),
            edges={"__start__": ("a", "b"), "a": ("c",), ("b", "d"): ("c",)},
            verdict="SAME",
            note="上游 E-3 基线 ``{'msgs': ['a','b','c']}`` ⇒ **组间任一** ⇒ 单源边满足即触发",
        )
    )

    # ── D-19 · 屏障后齐（上游 E-5 · **SAME**）───────────────────────────────
    out.append(
        Scenario(
            name="D-19 · 屏障后齐（目标再执行一次）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c", "d"),
            edges={
                "__start__": ("a", "b"),
                "a": ("c",),
                "b": ("d",),
                ("b", "d"): ("c",),
            },
            verdict="SAME",
            note="上游 E-5 基线 ``{'msgs': ['a','b','c','d','c']}`` ⇒ 未满足的组**不被记账** ⇒ 目标**再执行一次**",
        )
    )

    # ── D-20 · 屏障的并发无关性（**SAME** · freegraph 内部对照）──────────────
    def _d20_judge(scenario: Scenario) -> tuple[bool, str]:
        concurrent = run_freegraph(scenario)
        serial = run_freegraph(scenario, max_concurrency=1)
        if concurrent[0] != "OK" or serial[0] != "OK":
            return False, f"并发侧={concurrent[0]} · 串行侧={serial[0]}"
        same_state = concurrent[1] == serial[1]
        same_writes = concurrent[3]["state"] == serial[3]["state"]
        return (same_state and same_writes), (
            f"并发状态={concurrent[1]} · 串行状态={serial[1]}"
        )

    out.append(
        Scenario(
            name="D-20 · 屏障的并发无关性（并发档 == 串行档）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
            fg_only=_d20_judge,
            verdict="SAME",
            note="**同一份规格**在**并发档**与 ``max_concurrency=1`` **串行档** ⇒ 最终状态 + 待写入序列**逐字相等**"
            "⇒ ⇒ 屏障语义**与并发无关**（裁定 13）",
        )
    )

    # ── D-21 · 两条屏障并存（其中一条不齐）（上游 E-4 · **SAME**）─────────────
    out.append(
        Scenario(
            name="D-21 · 两条屏障并存（其中一条不齐）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c", "d", "e"),
            edges={
                "__start__": ("a", "b", "d"),
                ("a", "b"): ("c",),
                ("d", "e"): ("c",),
            },
            verdict="SAME",
            note="上游 E-4 基线 ``{'msgs': ['a','b','d','c']}`` ⇒ **先齐的那条生效** ⇒ 再次确认「组间任一」",
        )
    )

    # ── D-22 · 缺源的多源边（上游 E-8 · 两侧都构造期失败 · **SAME**）─────────
    out.append(
        Scenario(
            name="D-22 · 缺源的多源边（两侧都构造期失败）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "c"),
            edges={"__start__": ("a",), ("a", "zz"): ("c",)},
            fg_construct_error=True,
            up_construct_error=True,
            verdict="SAME",
            note="上游 E-8（``ValueError: Need to add_node 'zz' first``）⇒ freegraph 的 **V-2** 同族"
            "⇒ ⇒ **失败与否**一致 ⇒ 判词 = **SAME**",
        )
    )

    # ── D-23 · 元组顺序无关（**SAME** · freegraph 内部对照）──────────────────
    def _d23_judge(scenario: Scenario) -> tuple[bool, str]:
        def _run_with(key: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
            scenario.edges = {key: ("c",)}
            scenario.clear()
            _, _, _, extra = run_freegraph(scenario)
            return dict(extra["state"]), list(extra["state"].get("msgs", []))

        state_ab, order_ab = _run_with(("a", "b"))
        state_ba, order_ba = _run_with(("b", "a"))
        ok = state_ab == state_ba and order_ab == order_ba
        return ok, (
            f"('a','b') ⇒ state={state_ab} order={order_ab} · "
            f"('b','a') ⇒ state={state_ba} order={order_ba}"
        )

    out.append(
        Scenario(
            name="D-23 · 元组顺序无关（('a','b') == ('b','a')）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
            fg_only=_d23_judge,
            verdict="SAME",
            note="**组内合取无序**（语义点 **P-14**）⇒ 两种书写顺序的**节点序列 + 最终状态**逐字相等",
        )
    )

    # ── D-24 · 参数化（屏障形态 × 通道类型 × 源可达性）（**SAME**）────────────
    def _d24_judge(scenario: Scenario) -> tuple[bool, str]:
        failures: list[str] = []
        for shape, kind, reach in d24_parameter_space():
            sub = d24_scenario(shape, kind, reach)
            fg_kind, fg_state, _, _ = run_freegraph(sub)
            sub.clear()
            up_kind, up_state, _, _ = run_upstream(sub)
            if fg_kind != up_kind or (fg_kind == "OK" and fg_state != up_state):
                failures.append(
                    f"{shape}/{kind}/{reach}：freegraph={fg_kind} {fg_state} · upstream={up_kind} {up_state}"
                )
        return (not failures), (
            f"{len(d24_parameter_space())} 组参数化场景全绿"
            if not failures
            else "；".join(failures)
        )

    out.append(
        Scenario(
            name="D-24 · 参数化（屏障形态 × 通道类型 × 源可达性）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
            fg_only=_d24_judge,
            verdict="SAME",
            note="**H-6** · 立项书 §4.2 **S5 ③** 的**最小增量**（承接条款）⇒ "
            "**屏障形态 × 通道类型 × 源可达性** ⇒ **MUST NOT** 一次性铺开全量枚举",
        )
    )

    # ── D-25 · 多源边指向 __end__（上游 E-9 · **STRICTER** · X-04）───────────
    out.append(
        Scenario(
            name="D-25 · 多源边指向 __end__（上游静默 no-op）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("__end__",)},
            fg_construct_error=True,
            verdict="STRICTER",
            note="上游 E-9：``add_edge(['a','b'], END)`` ⇒ **被接受但静默 no-op**"
            "（``graph/state.py:1560`` 的 ``elif end != END:`` ⇒ 不建 join 通道）⇒ "
            "freegraph **构造期显式失败**（内置 ``ValueError`` · **V-16**）⇒ **比上游更严**（**X-04**）",
        )
    )

    # ── D-26 · 空的多源边（上游 E-6 · **STRICTER** · X-02）────────────────────
    out.append(
        Scenario(
            name="D-26 · 空的多源边（上游静默）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), (): ("c",)},
            fg_construct_error=True,
            verdict="STRICTER",
            note="上游 E-6：``add_edge([], 'c')`` ⇒ **被接受但静默**（目标**从未执行**且**不报错**）⇒ "
            "freegraph **构造期显式失败**（内置 ``ValueError`` · **V-16**）⇒ **比上游更严**（**X-02**）",
        )
    )

    # ── D-27 · 两条同成员不同序的多源边并存（上游 E-11 · **SAME**）────────────
    out.append(
        Scenario(
            name="D-27 · 两条同成员不同序的多源边并存（目标只触发 1 次）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a", "b", "c"),
            edges={"__start__": ("a", "b"), ("a", "b"): ("c",), ("b", "a"): ("c",)},
            verdict="SAME",
            note="上游 E-11 基线 ``{'msgs': ['a','b','c']}`` ⇒ 上游按**节点**去重"
            "（``pregel/_algo.py:476-482`` 的 ``triggered_nodes: set[str]``）⇒ "
            "freegraph 的「按**成员集合**去重」**与上游同款** ⇒ 行为面**零分叉**",
        )
    )

    # ── D-28 · 边键类型非法（上游 E-10 · 两侧均抛 TypeError · **SAME**）───────
    out.append(
        Scenario(
            name="D-28 · 边键类型非法（两侧均抛内置 TypeError）",
            channels={"msgs": "binop"},
            initial={"msgs": []},
            nodes=_msgs_nodes("a"),
            edges={"__start__": ("a",), 123: ("a",)},
            fg_construct_error=True,
            up_construct_error=True,
            expect_exception_type="TypeError",
            verdict="SAME",
            note="上游 E-10：``add_edge(123, 'a')`` ⇒ ``TypeError: 'int' object is not iterable``"
            "（锚点 ``graph/state.py:969`` 的 ``for start in start_key:``）⇒ "
            "freegraph 用内置 ``TypeError`` ⇒ **同族** ⇒ 语义点 **P-16** = **SAME**",
        )
    )

    # ── B10F1 · DI-01…DI-08（中断 / 恢复 · **DI-** 前缀 · 与既有 D-xx **不重号**）──
    #
    # ⚠️ **DI-** 前缀的由来（spec §下游承接条款的「编号消歧」）：探针内**已有**
    # B12F1 的 ``D-01…D-15`` 与 B7F4 的 ``D-16…D-28`` ⇒ ⇒ 本 feature 的
    # **差分场景**改用 ``DI-``（interrupt-diff）⇒ ⇒ **同一文件内三套编号互不
    # 重号** ⇒ ⇒ **既有场景名逐字不动**。

    def _fg_interrupt(value: str) -> Any:
        """freegraph 侧的 ``interrupt()``（**开发期** · 不进发行面）。"""
        sys.path.insert(0, f"{ROOT}/src")
        from freegraph.graph import interrupt as fg_interrupt

        return fg_interrupt(value)

    def _up_interrupt(value: str) -> Any:
        """上游侧的 ``interrupt()``（**开发期** · 不进发行面）。"""
        from langgraph.types import interrupt as up_interrupt

        return up_interrupt(value)

    # ── DI-01 · 单节点中断 ⇒ 结果含 ``__interrupt__``（元素带 .value / .id）──
    def _di01_fg(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve?")
        return {"count": 1}

    def _di01_up(state: dict[str, Any]) -> Any:
        _up_interrupt("approve?")
        return {"count": 1}

    out.append(
        Scenario(
            name="DI-01 · 单节点中断 ⇒ 结果含 __interrupt__（元素带 .value / .id）",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), _di01_fg)},
            nodes_upstream={"ask": (("count",), _di01_up)},
            edges={"__start__": ("ask",)},
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            verdict="SAME",
            note="中断载荷：``.value`` **逐字相等** · ``.id`` **只比形态**"
            "（32 位十六进制）⇒ **摘要算法**不同（上游 ``xxh3_128`` vs freegraph "
            "``blake2b-128`` ⇒ 偏离登记 **X-4**）⇒ ⇒ 判据形态同款",
        )
    )

    # ── DI-02 · Command(resume=…) 恢复 ⇒ 跑完且状态含恢复值 ──
    def _di02_fg(state: dict[str, Any]) -> Any:
        answer = _fg_interrupt("approve?")
        return {"count": answer}

    def _di02_up(state: dict[str, Any]) -> Any:
        answer = _up_interrupt("approve?")
        return {"count": answer}

    out.append(
        Scenario(
            name="DI-02 · Command(resume=…) 恢复 ⇒ 跑完且状态含恢复值",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), _di02_fg)},
            nodes_upstream={"ask": (("count",), _di02_up)},
            edges={"__start__": ("ask",)},
            resume_input="yes",
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            verdict="SAME",
            note="**两段式**（第一次 ⇒ 挂起；第二次 ⇒ 恢复）⇒ ⇒ 比**恢复后**的结果"
            "⇒ ⇒ 恢复值落在同一个 key 上 · 两侧**均无** ``__interrupt__``",
        )
    )

    # ── DI-03 · 恢复时节点从头重跑（执行次数两侧都 == 2）──
    di03_calls: list[str] = []

    def _di03_fg(state: dict[str, Any]) -> Any:
        di03_calls.append("ask")
        answer = _fg_interrupt("approve?")
        return {"count": answer}

    def _di03_up(state: dict[str, Any]) -> Any:
        di03_calls.append("ask")
        answer = _up_interrupt("approve?")
        return {"count": answer}

    out.append(
        Scenario(
            name="DI-03 · 恢复时节点从头重跑（执行次数两侧都 == 2）",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), _di03_fg)},
            nodes_upstream={"ask": (("count",), _di03_up)},
            edges={"__start__": ("ask",)},
            calls=di03_calls,
            resume_input="yes",
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            compare_call_counts=True,
            verdict="SAME",
            note="**从节点起点重跑**（**上游同款** · 实测 **E-8**）⇒ ⇒ 两侧的"
            "**执行次数**相等（都 == 2）⇒ ⇒ **不**比较中间态",
        )
    )

    # ── DI-04 · 未挂 checkpointer 时恢复 ⇒ 两侧都失败 ──
    def _di04_fg(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve?")
        return {"count": 1}

    def _di04_up(state: dict[str, Any]) -> Any:
        _up_interrupt("approve?")
        return {"count": 1}

    out.append(
        Scenario(
            name="DI-04 · 未挂 checkpointer 时恢复 ⇒ 失败（STRICTER）",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), _di04_fg)},
            nodes_upstream={"ask": (("count",), _di04_up)},
            edges={"__start__": ("ask",)},
            resume_input="yes",
            fg_no_checkpointer=True,
            compare="interrupt-shape",
            verdict="STRICTER",
            note="**失败信号**更结构化：freegraph 抛 ``InterruptError``"
            "（``.reason == 'checkpointer_required'`` · **L1** 的 ``FreegraphError``"
            "**子类**）⇒ 上游抛内置 ``RuntimeError`` ⇒ ⇒ **类型**不同 · "
            "**消息要点**逐字同款 ⇒ ⇒ 偏离登记 **X-2**（**STRICTER**）"
            "⇒ ⇒ 差分探针**只比「成功 / 失败」**（比对器既有纪律）",
        )
    )

    # ── DI-05 · 中断前的写入不丢失 ──
    def _di05_pre(state: dict[str, Any]) -> Any:
        return {"count": 1}

    def _di05_fg(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve?")
        return {"count": 2}

    def _di05_up(state: dict[str, Any]) -> Any:
        _up_interrupt("approve?")
        return {"count": 2}

    out.append(
        Scenario(
            name="DI-05 · 中断前的写入不丢失（挂起不是回滚）",
            channels={"count": "last"},
            initial={},
            nodes={
                "ask": (("count",), _di05_fg),
                "pre": (("count",), _di05_pre),
            },
            nodes_upstream={
                "ask": (("count",), _di05_up),
                "pre": (("count",), _di05_pre),
            },
            edges={"__start__": ("pre",), "pre": ("ask",)},
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            verdict="SAME",
            note="中断**前**已产生的写入**保留**（**上游同款** · 实测 **E-16**）"
            "⇒ ⇒ 两侧的**最终状态**逐 key 相等",
        )
    )

    # ── DI-06 · 同一节点内两个 interrupt() ⇒ 恢复值按顺序匹配 ──
    def _di06_fg(state: dict[str, Any]) -> Any:
        first = _fg_interrupt("first?")
        second = _fg_interrupt("second?")
        return {"count": f"{first}/{second}"}

    def _di06_up(state: dict[str, Any]) -> Any:
        first = _up_interrupt("first?")
        second = _up_interrupt("second?")
        return {"count": f"{first}/{second}"}

    out.append(
        Scenario(
            name="DI-06 · 同一节点内两个 interrupt() ⇒ 恢复值按顺序匹配",
            channels={"count": "last"},
            initial={},
            nodes={"ask": (("count",), _di06_fg)},
            nodes_upstream={"ask": (("count",), _di06_up)},
            edges={"__start__": ("ask",)},
            resume_input="X",
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            verdict="SAME",
            note="**按节点内顺序**匹配（**上游同款** · 实测 **E-17**）⇒ ⇒ 恢复值"
            "**不足** ⇒ **再次挂起**（载荷变成 ``second?``）⇒ ⇒ 两侧的**载荷**与"
            "**最终状态**逐项相等",
        )
    )

    # ── DI-07 · 跨节点两个挂起中断 ⇒ __interrupt__ 两个元素 ──
    def _di07_fg_a(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve-A")
        return {"count": 1}

    def _di07_fg_b(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve-B")
        return {"count": 1}

    def _di07_up_a(state: dict[str, Any]) -> Any:
        _up_interrupt("approve-A")
        return {"count": 1}

    def _di07_up_b(state: dict[str, Any]) -> Any:
        _up_interrupt("approve-B")
        return {"count": 1}

    out.append(
        Scenario(
            name="DI-07 · 跨节点两个挂起中断 ⇒ __interrupt__ 两个元素",
            channels={"count": "last"},
            initial={},
            nodes={"a": (("count",), _di07_fg_a), "b": (("count",), _di07_fg_b)},
            nodes_upstream={
                "a": (("count",), _di07_up_a),
                "b": (("count",), _di07_up_b),
            },
            edges={"__start__": ("a", "b")},
            fg_suspends=True,
            upstream_checkpointer=True,
            compare="interrupt-shape",
            verdict="SAME",
            note="**集合比较**（元素 ``.value`` 逐个相等）⇒ ⇒ **不**比顺序"
            "（上游的合并顺序**是竞态** · ``pregel/_runner.py:672``）",
        )
    )

    # ── DI-08 · 跨节点多挂起中断 + 单值恢复 ⇒ 失败（STRICTER）──
    def _di08_fg_a(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve-A")
        return {"count": 1}

    def _di08_fg_b(state: dict[str, Any]) -> Any:
        _fg_interrupt("approve-B")
        return {"count": 1}

    def _di08_up_a(state: dict[str, Any]) -> Any:
        _up_interrupt("approve-A")
        return {"count": 1}

    def _di08_up_b(state: dict[str, Any]) -> Any:
        _up_interrupt("approve-B")
        return {"count": 1}

    out.append(
        Scenario(
            name="DI-08 · 跨节点多挂起中断 + 单值恢复 ⇒ 失败（STRICTER）",
            channels={"count": "last"},
            initial={},
            nodes={"a": (("count",), _di08_fg_a), "b": (("count",), _di08_fg_b)},
            nodes_upstream={
                "a": (("count",), _di08_up_a),
                "b": (("count",), _di08_up_b),
            },
            edges={"__start__": ("a", "b")},
            resume_input="A",
            compare="interrupt-shape",
            verdict="STRICTER",
            note="**多个**挂起中断 + **单值**恢复 ⇒ ⇒ 两侧**都失败** ⇒ ⇒ "
            "freegraph 抛 ``InterruptError``（``.reason == 'ambiguous_resume'``）"
            "⇒ 上游抛内置 ``RuntimeError`` ⇒ ⇒ **类型**不同 · **消息要点**同款 ⇒ ⇒ "
            "偏离登记 **X-2**（**STRICTER**）",
        )
    )

    return out


# ── 公开 API（供 pytest / CLI 复用）─────────────────────────────────────────


@dataclass
class ProbeResult:
    """一个场景的对跑结果。"""

    name: str
    verdict: str
    ok: bool
    freegraph_kind: str
    upstream_kind: str
    detail: str


def run_all(keyword: str = "") -> list[ProbeResult]:
    """跑全部场景 ⇒ 返回逐场景结果（**不打印**）。

    ⚠️ **B12F1 扩展**：三种比较口径 ——
    ① **两侧对跑**（默认）⇒ 既有 15 个场景走这条 ⇒ **行为逐字不变**；
    ② **中断载荷**对跑（``expect_interrupt=True``）⇒ freegraph 从**异常**取 ·
    上游从**结果键**取 ⇒ 比**集合**（上游的元组内元素顺序**竞态**）；
    ③ **freegraph 内部对照**（``fg_only``）⇒ 供「并发 == 串行」「多会话隔离」
    「并发度上限」「确定性」这类**不对着上游比**的场景使用。
    """
    results: list[ProbeResult] = []
    for scenario in _scenarios():
        if keyword and keyword not in scenario.name:
            continue
        scenario.clear()

        # ③ freegraph 内部对照（**不对着上游比**）
        if scenario.fg_only is not None:
            ok, detail = scenario.fg_only(scenario)
            results.append(
                ProbeResult(
                    name=scenario.name,
                    verdict=scenario.verdict,
                    ok=ok,
                    freegraph_kind="OK",
                    upstream_kind="OK",
                    detail=detail,
                )
            )
            continue

        fg_kind, fg_state, fg_detail, fg_extra = run_freegraph(scenario)
        scenario.clear()
        up_kind, up_state, up_detail, up_extra = run_upstream(scenario)

        if scenario.expect_interrupt or scenario.fg_suspends:
            # ② 中断载荷对跑 ⇒ ⚠️ 两侧的「失败与否」**本就不同**
            # （freegraph **抛** · 上游**根图抑制** ⇒ 落进结果键）
            # ⚠️ **B10F1**：``fg_suspends`` ⇒ freegraph 侧**返回**
            # ``InterruptResult``（**不**抛）⇒ ⇒ 中断载荷从**结果**取 ⇒ ⇒
            # 两侧**都**是「成功 + 带中断载荷」。
            payload_ok = _compare_interrupts(
                fg_extra["interrupt"], up_extra["interrupt"], scenario.compare
            )
            # ⚠️ **状态**也要比（上游结果里去掉 ``__interrupt__`` 键）
            state_ok = fg_extra["state"] == up_extra["state"]
            if scenario.fg_suspends:
                ok = payload_ok and state_ok and fg_kind == "OK" and up_kind == "OK"
            else:
                ok = payload_ok and state_ok and fg_kind == "ERROR" and up_kind == "OK"
            detail = (
                f"freegraph={fg_kind} {fg_detail} | upstream={up_kind} {up_detail} "
                f"| fg_interrupt={_interrupt_keys(fg_extra['interrupt'])} "
                f"up_interrupt={_interrupt_keys(up_extra['interrupt'])} "
                f"| fg_state={fg_extra['state']} up_state={up_extra['state']}"
            )
            passed = ok if scenario.verdict == "SAME" else bool(scenario.note) and ok
            results.append(
                ProbeResult(
                    name=scenario.name,
                    verdict=scenario.verdict,
                    ok=passed,
                    freegraph_kind=fg_kind,
                    upstream_kind=up_kind,
                    detail=detail,
                )
            )
            continue

        same_kind = fg_kind == up_kind
        if fg_kind == "ERROR" and up_kind == "ERROR":
            # 两边都失败 ⇒ 失败**语义**同款（异常**类名**本就不该同名）
            same_state = True
        else:
            same_state = fg_state == up_state
        ok = same_kind and same_state

        if scenario.compare_started:
            # ⚠️ 端到端的取消语义 ⇒ 比「**实际被启动了哪些节点**」的**集合**
            started_ok = set(fg_extra["calls"]) == set(up_extra["calls"])
            ok = ok and started_ok
        if scenario.compare_call_counts:
            # ⚠️ **B10F1**：「**从节点起点重跑**」⇒ 两侧的**执行次数**必须
            # **相等**（**上游同款** · 实测 **E-8** ⇒ 两侧都 == 2）
            count_ok = len(fg_extra["calls"]) == len(up_extra["calls"])
            ok = ok and count_ok
        if scenario.expect_exception_identity:
            # ⚠️ 对象 identity ⇒ 两侧捕获到的 MUST 是节点内抛出的**同一个对象**
            identity_ok = (
                fg_extra["exception"] is not None
                and up_extra["exception"] is not None
                and fg_extra["exception"] is scenario.raised[0]
                and up_extra["exception"] is scenario.raised[0]
            )
            ok = ok and identity_ok
        if scenario.fg_construct_error:
            # ⚠️ **B7F4**：freegraph 侧 MUST **在构造期**失败（**不是**运行期）
            ok = ok and fg_extra.get("stage") == "construct"
        if scenario.up_construct_error:
            ok = ok and up_extra.get("stage") == "construct"
        if scenario.expect_exception_type:
            # ⚠️ **B7F4**：**类型族**的可判定性（⇒ **D-28**）⇒ 两侧 MUST 抛
            # **同名**的内置异常（**不比对**消息文本）。
            expected = scenario.expect_exception_type
            fg_type = (
                type(fg_extra["exception"]).__name__
                if fg_extra["exception"] is not None
                else ""
            )
            up_type = (
                type(up_extra["exception"]).__name__
                if up_extra["exception"] is not None
                else ""
            )
            ok = ok and fg_type == expected and up_type == expected

        if scenario.verdict == "SAME":
            passed = ok
        elif scenario.verdict == "STRICTER":
            # 允许「上游成功、freegraph 失败」；但「上游失败、freegraph 成功」是漏网
            passed = ok or (fg_kind == "ERROR" and up_kind == "OK")
        else:  # DIFF
            passed = bool(scenario.note)

        detail = f"freegraph={fg_kind} {fg_detail} | upstream={up_kind} {up_detail}"
        results.append(
            ProbeResult(
                name=scenario.name,
                verdict=scenario.verdict,
                ok=passed,
                freegraph_kind=fg_kind,
                upstream_kind=up_kind,
                detail=detail,
            )
        )
    return results
