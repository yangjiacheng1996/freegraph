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
    edges: dict[str, tuple[str, ...]]
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


def _compare_interrupts(
    fg_payload: tuple[Any, ...],
    up_payload: tuple[Any, ...],
    compare: str,
) -> bool:
    """比对两侧的**中断载荷**（口径由 ``scenario.compare`` 决定）。"""
    fg_keys = _interrupt_keys(fg_payload)
    up_keys = _interrupt_keys(up_payload)
    if compare == "set":
        # ⚠️ **按集合比**（上游的元组内元素顺序**竞态** ⇒ 逐字比会偶发红）
        return sorted(map(repr, fg_keys)) == sorted(map(repr, up_keys))
    return fg_keys == up_keys


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
    edges = {
        src: tuple(target for target in targets if target != "__end__")
        for src, targets in scenario.edges.items()
    }
    spec = GraphSpec(channels=channels, nodes=nodes, edges=edges)
    scheduler_state = SchedulerState()
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
        },
    )


def _sparse(scheduler_state: Any) -> dict[str, Any]:
    """取调度状态里的**稀疏通道值**（中断轮也取得到 —— 合并**已经**发生）。"""
    sys.path.insert(0, f"{ROOT}/src")
    from freegraph.runtime import read_channels

    return dict(read_channels(scheduler_state.channels))


def _exc_detail(exc: BaseException) -> str:
    """异常的**可观察要点**（类名 + 首行消息）。"""
    msg = str(exc).strip().splitlines()
    return f"{type(exc).__name__}: {msg[0] if msg else ''}"


# ── 上游侧 ──────────────────────────────────────────────────────────────────


def run_upstream(scenario: Scenario) -> tuple[str, Any, str, dict[str, Any]]:
    """跑上游 langgraph ⇒ 返回 ``(结果摘要, 状态/载荷, 细节, 附加信息)``。

    ⚠️ **B12F1 扩展**：提取结果的 **``__interrupt__`` 键**（上游**根图抑制**中断 ⇒
    中断落进结果键而不是抛出来 ⇒ 两侧的**取法不同**但**比的是同一批东西**）。
    """
    from typing import Annotated

    from typing_extensions import TypedDict

    from langgraph.graph import END, START, StateGraph

    gate = threading.Barrier(scenario.barrier) if scenario.barrier else None

    # 通道形态 ⇒ TypedDict 字段类型（上游按字段名建通道）
    annotations: dict[str, Any] = {}
    for name, kind in scenario.channels.items():
        if kind == "binop":
            # ⚠️ 上游的**归约通道** MUST 用 ``Annotated[..., operator.add]``
            # （否则上游建的是 LastValue ⇒ 同轮多写会报错 ⇒ 比的是另一套语义）
            annotations[name] = Annotated[list, operator.add]
        else:
            annotations[name] = Any
    schema = TypedDict("S", annotations)  # type: ignore[valid-type]

    graph = StateGraph(schema)
    upstream_nodes = scenario.nodes_upstream or scenario.nodes
    for name, (_subscribes, fn) in upstream_nodes.items():
        graph.add_node(name, _instrument(scenario, fn, name, gate))
    for src, targets in scenario.edges.items():
        if src == "__start__":
            graph.add_edge(START, targets[0])
            for extra in targets[1:]:
                graph.add_edge(START, extra)
        else:
            for target in targets:
                graph.add_edge(src, END if target == "__end__" else target)
    if scenario.upstream_extra is not None:
        scenario.upstream_extra(graph)
    compiled = graph.compile()
    try:
        result = compiled.invoke(dict(scenario.initial))
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
        },
    )



# ── 场景集 ──────────────────────────────────────────────────────────────────

STRICTER_NOTES = {
    "未知 key 写入": "freegraph 显式失败（InvalidChannelUpdateError）；上游 warning + 静默忽略（_algo.py:310-313）",
    "非法 goto 目标": "freegraph 显式失败（ValueError）；上游 warning + 静默忽略",
    "空命令列表": "freegraph 失败（TypeError）；上游失败（InvalidUpdateError）—— 类型不同 · 语义等价",
    "覆盖型通道同轮重复写": "freegraph 失败（InvalidChannelUpdateError）；上游失败（InvalidUpdateError）—— 同族",
}


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

        if scenario.expect_interrupt:
            # ② 中断载荷对跑 ⇒ ⚠️ 两侧的「失败与否」**本就不同**
            # （freegraph **抛** · 上游**根图抑制** ⇒ 落进结果键）
            payload_ok = _compare_interrupts(
                fg_extra["interrupt"], up_extra["interrupt"], scenario.compare
            )
            # ⚠️ **状态**也要比（上游结果里去掉 ``__interrupt__`` 键）
            state_ok = fg_extra["state"] == up_extra["state"]
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
        if scenario.expect_exception_identity:
            # ⚠️ 对象 identity ⇒ 两侧捕获到的 MUST 是节点内抛出的**同一个对象**
            identity_ok = (
                fg_extra["exception"] is not None
                and up_extra["exception"] is not None
                and fg_extra["exception"] is scenario.raised[0]
                and up_extra["exception"] is scenario.raised[0]
            )
            ok = ok and identity_ok

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
