# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**并发执行**的用例 —— 属 **B12F1**（tasks **T018–T026** · **T048–T057**）。

覆盖的判定：

* **US1**（**A1** · SC-001）—— 同轮两个节点**真的重叠执行**（屏障被放行）
  · 各自**恰好执行 1 次** · 执行序列 == **节点名序** · **零悬挂线程**
  · 并发度**有上限**且与上游同款 · ``max_concurrency`` **入口即校验**；
* **US4**（SC-004 / SC-005 / SC-015 / SC-016 / SC-017 / SC-006）
  —— **并发 == 串行**（同一规格）· **可复现** · 合并顺序 == **节点名序**
  · ``Command`` 的并发语义 · 节点**入参口径** · 执行期**不改正式值**。

⚠️ **判定口径纪律**（data-model §8）：MUST **NOT** 用**墙钟耗时**做判据
（CI 假红）⇒ 判据用「**屏障放行**」「**执行次数**」「**逐项相等**」「**线程计数**」。

⚠️ **依赖纪律**（FR-007 · L2）：本文件**只**用**标准库** + freegraph 自身
⇒ **零第三方依赖**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
import os
import threading
import time
from typing import Any

import pytest

from freegraph.contracts.errors import InvalidUpdateError
from freegraph.contracts.types import Command
from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    run_super_step,
    run_super_steps,
)


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型**（``count``）+ **归约型**（``messages``）。"""
    return {
        "count": LastValue("count", int),
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
    }


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30``）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


def _two_node_spec(
    left: Any, right: Any, *, order: tuple[str, str] = ("left", "right")
) -> GraphSpec:
    """构造「``START`` 扇出到两个节点」的图规格。"""
    nodes = {
        "left": NodeSpec(subscribes=("messages",), run=left),
        "right": NodeSpec(subscribes=("messages",), run=right),
        "__start__": _ENTRY,
    }
    edges = {"__start__": order}
    return GraphSpec(channels=_channels(), nodes=nodes, edges=edges)


# ── US1 · 并行节点不串行化（**A1** · SC-001）────────────────────────────────


def test_two_nodes_in_one_round_really_overlap_in_parallel() -> None:
    """**SC-001**（**A1** · I-1）：同轮两个节点**重叠执行** ⇒ **屏障被放行**。

    ⚠️ 串行执行 ⇒ 第一个节点在屏障上**死等** ⇒ ``BrokenBarrierError`` ⇒
    **测试先失败**（这就是「真并发」的证明）。
    """
    channels = _channels()
    barrier = threading.Barrier(2, timeout=10)
    windows: list[tuple[float, float]] = []

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            start = time.monotonic()
            barrier.wait()  # ⚠️ 串行 ⇒ 死等 ⇒ 超时抛 BrokenBarrierError
            windows.append((start, time.monotonic()))
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    result = run_super_step(spec, SchedulerState())

    assert result.executed == ("left", "right")
    assert len(windows) == 2
    first, second = sorted(windows)
    overlap = min(first[1], second[1]) - max(first[0], second[0])
    assert overlap > 0, f"两节点的执行时间窗未重叠（overlap={overlap}）"


def test_two_nodes_in_one_round_do_not_run_serially_under_parallel() -> None:
    """**SC-001**：「后一个的开始 ≥ 前一个的结束」的出现次数 == **0**。"""
    channels = _channels()
    windows: list[tuple[float, float]] = []
    lock = threading.Lock()

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            start = time.monotonic()
            time.sleep(0.02)
            with lock:
                windows.append((start, time.monotonic()))
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    run_super_step(spec, SchedulerState())

    assert len(windows) == 2
    first, second = sorted(windows)
    assert second[0] < first[1], "后一个的开始 ≥ 前一个的结束 ⇒ 存在串行化"


def test_each_node_runs_exactly_once_under_parallel() -> None:
    """**SC-001**（I-2）：两个节点各自的**副作用计数 == 1**（不是 0 · 也不是 2）。"""
    counts = {"left": 0, "right": 0}
    lock = threading.Lock()

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            with lock:
                counts[name] += 1
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    run_super_step(spec, SchedulerState())

    assert counts == {"left": 1, "right": 1}


def test_executed_follows_the_node_name_order_under_parallel() -> None:
    """**SC-001** / **FR-009**：``executed`` 按**节点名序**排列（**上游同款**）。

    ⇒ **节点表声明顺序**与**名字顺序**相反时，执行序列**不变**。
    """
    def _noop(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    nodes = {
        "zebra": NodeSpec(subscribes=("messages",), run=_noop),
        "alpha": NodeSpec(subscribes=("messages",), run=_noop),
        "__start__": _ENTRY,
    }
    edges = {"__start__": ("zebra", "alpha")}
    spec = GraphSpec(channels=_channels(), nodes=nodes, edges=edges)

    result = run_super_step(spec, SchedulerState())

    assert result.executed == ("alpha", "zebra")


def test_no_hanging_threads_after_a_round() -> None:
    """**SC-025**（I-16）：一轮结束后**仍存活**的执行线程数 == **0**。"""
    before = threading.active_count()

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    spec = _two_node_spec(_fn, _fn)
    run_super_step(spec, SchedulerState())

    assert threading.active_count() == before


def test_thread_count_does_not_grow_over_ten_rounds() -> None:
    """**SC-025**：连续运行 **≥ 10** 轮后进程内线程数**不增长**。"""

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    spec = _two_node_spec(_fn, _fn)
    run_super_step(spec, SchedulerState())  # 预热（让线程池的惰性创建先发生）
    baseline = threading.active_count()
    for _ in range(10):
        run_super_step(spec, SchedulerState())

    assert threading.active_count() == baseline


def test_the_default_concurrency_cap_is_bounded() -> None:
    """**SC-027**：缺省（``max_concurrency=None``）时**同时在跑**的任务数
    **不超过** ``min(32, cpu+4)``；超出者**排队**（不是被丢弃）⇒ 全部节点各跑 1 次。"""
    cap = min(32, (os.cpu_count() or 1) + 4)
    node_count = cap + 8
    active = 0
    max_active = 0
    counts = [0] * node_count
    lock = threading.Lock()

    def make(index: int) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
                counts[index] += 1
            time.sleep(0.05)
            with lock:
                active -= 1
            return {"messages": [f"n{index}"]}

        return _fn

    nodes = {f"n{i}": NodeSpec(subscribes=("messages",), run=make(i)) for i in range(node_count)}
    nodes["__start__"] = _ENTRY
    spec = GraphSpec(
        channels=_channels(), nodes=nodes, edges={"__start__": tuple(f"n{i}" for i in range(node_count))}
    )

    run_super_step(spec, SchedulerState())

    assert max_active <= cap, f"同时在跑 {max_active} > 缺省上限 {cap}"
    assert counts == [1] * node_count, "超出上限的节点被丢弃了（应排队）"


def test_an_explicit_cap_is_not_clamped_to_32() -> None:
    """**SC-027**：显式 ``max_concurrency=N`` ⇒ 实际并发度 == ``min(任务数, N)``。

    ⚠️ **N 不被 32 再夹** ⇒ 用 **N = 40** + **40** 个节点 + **40 方屏障**
    ⇒ 若被夹到 32 ⇒ 屏障**永远等不齐** ⇒ 超时 ⇒ **测试失败**。
    """
    node_count = 40
    barrier = threading.Barrier(node_count, timeout=20)

    def make(index: int) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            barrier.wait()  # ⚠️ 40 个节点**同时**在跑才放行
            return {"messages": [f"n{index}"]}

        return _fn

    nodes = {f"n{i}": NodeSpec(subscribes=("messages",), run=make(i)) for i in range(node_count)}
    nodes["__start__"] = _ENTRY
    spec = GraphSpec(
        channels=_channels(), nodes=nodes, edges={"__start__": tuple(f"n{i}" for i in range(node_count))}
    )

    result = run_super_step(spec, SchedulerState(), max_concurrency=node_count)

    assert len(result.executed) == node_count


def test_invalid_max_concurrency_fails_at_the_entry() -> None:
    """**SC-027**（V-18）：``max_concurrency`` 非法 ⇒ **入口即**显式失败。

    * 类型不符 ⇒ 内置 ``TypeError``（**点名该参数**）；
    * ``< 1`` ⇒ 内置 ``ValueError``（**点名该参数**）。
    """

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": ["x"]}

    spec = _two_node_spec(_fn, _fn)
    state = SchedulerState()

    with pytest.raises(TypeError) as type_error:
        run_super_step(spec, state, max_concurrency="x")  # type: ignore[arg-type]
    assert "max_concurrency" in str(type_error.value)

    with pytest.raises(ValueError) as value_error:
        run_super_step(spec, state, max_concurrency=0)
    assert "max_concurrency" in str(value_error.value)


def test_invalid_max_concurrency_fails_even_with_zero_nodes() -> None:
    """**SC-027**：**本轮没有节点要跑**时传非法值 ⇒ **同样报错**。

    ⚠️ 「**不建池**」≠「**不校验参数**」（FR-001 与 FR-017 **不冲突**）。
    """
    nodes = {"__start__": _ENTRY}
    spec = GraphSpec(channels=_channels(), nodes=nodes, edges={})

    with pytest.raises(TypeError) as type_error:
        run_super_step(spec, SchedulerState(), max_concurrency="x")  # type: ignore[arg-type]
    assert "max_concurrency" in str(type_error.value)

    with pytest.raises(ValueError) as value_error:
        run_super_steps(spec, max_concurrency=0)
    assert "max_concurrency" in str(value_error.value)


def test_a_bool_max_concurrency_is_accepted_as_one() -> None:
    """**SC-027**：``bool`` 是 ``int`` 的子类 ⇒ **照单全收**（当作 1 · **上游同款**）。"""
    counts = {"left": 0, "right": 0}
    lock = threading.Lock()

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            with lock:
                counts[name] += 1
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    result = run_super_step(spec, SchedulerState(), max_concurrency=True)

    assert result.executed == ("left", "right")
    assert counts == {"left": 1, "right": 1}


def test_the_serial_baseline_runs_one_node_at_a_time() -> None:
    """**SC-004**（**串行基线**）：``max_concurrency=1`` ⇒ **逐个执行**（**无重叠**）。"""
    windows: list[tuple[float, float]] = []
    lock = threading.Lock()

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            start = time.monotonic()
            time.sleep(0.02)
            with lock:
                windows.append((start, time.monotonic()))
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    result = run_super_step(spec, SchedulerState(), max_concurrency=1)

    assert result.executed == ("left", "right")
    first, second = sorted(windows)
    assert second[0] >= first[1], "串行模式下仍有重叠 ⇒ 未逐个执行"


# ── US4 · 并发不改变状态的语义（SC-004 / SC-005 / SC-015 / SC-016）──────────


def _non_commutative_spec() -> GraphSpec:
    """一张带**非交换归约器**的图（同轮两个节点写同一归约通道）。"""

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            return {"messages": [name]}

        return _fn

    return _two_node_spec(make("left"), make("right"))


def test_concurrent_and_serial_produce_identical_results() -> None:
    """**SC-004**（I-6）：**并发 == 串行**（**同一规格**）⇒ 状态与待写入**逐项相等**。"""
    concurrent = run_super_step(_non_commutative_spec(), SchedulerState())
    serial = run_super_step(_non_commutative_spec(), SchedulerState(), max_concurrency=1)

    assert dict(concurrent.state) == dict(serial.state)
    assert concurrent.node_writes == serial.node_writes
    assert concurrent.executed == serial.executed


def test_repeated_runs_are_identical() -> None:
    """**SC-005**（I-7）：同一规格重复运行 **≥ 3** 次 ⇒ 状态与执行序列**逐项相等**。"""
    results = [run_super_step(_non_commutative_spec(), SchedulerState()) for _ in range(3)]

    assert all(dict(r.state) == dict(results[0].state) for r in results)
    assert all(r.executed == results[0].executed for r in results)


def test_the_merge_order_of_one_channel_is_the_node_name_order() -> None:
    """**SC-005**（I-8）：同一通道上多个写入的**合并顺序 == 节点名序**。

    ⇒ **非交换归约器**（拼接列表）的结果**可复现**。
    """

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            return {"messages": [name]}

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == ["left", "right"]


def test_goto_targets_do_not_swallow_each_other() -> None:
    """**SC-015**：同轮多个节点各自的 ``goto`` 目标在下一轮**全部**被触发。"""
    triggered: list[str] = []
    lock = threading.Lock()

    def make(name: str, target: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            with lock:
                triggered.append(name)
            return Command(goto=target)

        return _fn

    def sink(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            with lock:
                triggered.append(name)
            return {}

        return _fn

    nodes = {
        "left": NodeSpec(subscribes=("messages",), run=make("left", "t_left")),
        "right": NodeSpec(subscribes=("messages",), run=make("right", "t_right")),
        "t_left": NodeSpec(subscribes=(), run=sink("t_left")),
        "t_right": NodeSpec(subscribes=(), run=sink("t_right")),
        "__start__": _ENTRY,
    }
    spec = GraphSpec(channels=_channels(), nodes=nodes, edges={"__start__": ("left", "right")})

    result = run_super_steps(spec)

    assert "t_left" in triggered
    assert "t_right" in triggered
    assert set(result.executed) >= {"left", "right", "t_left", "t_right"}


def test_command_update_uses_the_same_batch_merge_path() -> None:
    """**SC-015**：``Command.update`` 的写入与普通返回值走**同一条**批量合并路径。

    ⇒ 未知 key 仍抛 ``InvalidUpdateError``（**MUST NOT** 另写一条并发合并路径）。
    """

    def _fn(state: dict[str, Any]) -> Any:
        return Command(update={"unknown_key": 1})

    spec = _two_node_spec(_fn, _fn)

    with pytest.raises(InvalidUpdateError):
        run_super_step(spec, SchedulerState())


def test_the_merge_order_is_node_name_order_times_command_list_order() -> None:
    """**SC-016**：多节点 × 多命令的归并顺序 ==「**节点名序 × 命令列表顺序**」。"""

    def make(name: str) -> Any:
        def _fn(state: dict[str, Any]) -> dict[str, Any]:
            return [Command(update={"messages": [f"{name}-1"]}), Command(update={"messages": [f"{name}-2"]})]

        return _fn

    spec = _two_node_spec(make("left"), make("right"))
    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == ["left-1", "left-2", "right-1", "right-2"]


def test_the_node_input_equals_the_sparse_read_of_the_sub_mapping() -> None:
    """**SC-017**（I-9）：节点收到的入参 == ``read_channels(子映射)`` 的结果
    （**逐字** · 含 **key 顺序**）。"""
    received: list[dict[str, Any]] = []
    lock = threading.Lock()

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            received.append(state)
        return {"messages": ["x"]}

    channels = _channels()
    channels["count"].update([7])
    nodes = {
        "reader": NodeSpec(subscribes=("count", "messages"), run=_fn),
        "__start__": _ENTRY,
    }
    spec = GraphSpec(channels=channels, nodes=nodes, edges={"__start__": ("reader",)})

    run_super_step(spec, SchedulerState())

    assert len(received) == 1
    assert list(received[0]) == ["count", "messages"]
    assert received[0]["count"] == 7


def test_the_node_input_is_not_affected_by_the_other_node_in_the_same_round() -> None:
    """**SC-017**：入参**不受**同轮其它节点产出的影响（全部入参在**任何节点执行前**确定）。"""
    seen: list[dict[str, Any]] = []
    lock = threading.Lock()

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 99}

    def reader(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            seen.append(dict(state))
        return {}

    channels = _channels()
    channels["count"].update([1])
    nodes = {
        "reader": NodeSpec(subscribes=("count",), run=reader),
        "writer": NodeSpec(subscribes=("count",), run=writer),
        "__start__": _ENTRY,
    }
    spec = GraphSpec(channels=channels, nodes=nodes, edges={"__start__": ("reader", "writer")})

    run_super_step(spec, SchedulerState())

    assert seen == [{"count": 1}]


def test_the_official_channel_value_is_not_rewritten_during_execution() -> None:
    """**SC-006**（I-9）：并发执行期间**通道的正式值被改写**的现象 == **0** 次。

    ⇒ 节点执行期间从外部观察到的通道值 == **本轮开始前**的值。
    """
    observed: list[Any] = []
    lock = threading.Lock()

    def _fn(state: dict[str, Any]) -> dict[str, Any]:
        with lock:
            observed.append(state["count"])
        return {"messages": ["x"]}

    channels = _channels()
    channels["count"].update([1])
    nodes = {
        "left": NodeSpec(subscribes=("count",), run=_fn),
        "right": NodeSpec(subscribes=("count",), run=_fn),
        "__start__": _ENTRY,
    }
    spec = GraphSpec(channels=channels, nodes=nodes, edges={"__start__": ("left", "right")})

    run_super_step(spec, SchedulerState())

    assert observed == [1, 1]


def test_two_independent_runs_do_not_interfere() -> None:
    """**SC-026**：两次**独立**的运行（各自新建调度状态）**互不影响**。"""
    spec = _non_commutative_spec()

    first = run_super_steps(spec)
    second = run_super_steps(spec)

    assert dict(first.state) == dict(second.state)
    assert first.executed == second.executed


# ── 结构纪律（**T072** · SC-019 / SC-024 · I-16 的层纪律侧）──────────────────

#: **仓库根**（结构纪律的取证基准）。
_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]

#: **L3 / L4 / L5** 的模块名（**L2 MUST NOT import** ⇒ ARCH-1）。
_UPPER_LAYER_MODULES = ("graph", "cli", "studio", "api")


def _parse_l1_manifest() -> set[str]:
    """解析 **L1 公开符号面清单**（**清单驱动** ⇒ **不硬编码个数**）。"""
    text = (
        _REPO_ROOT
        / "specs"
        / "b2f1-contracts-protocols"
        / "contracts"
        / "public-api.md"
    ).read_text(encoding="utf-8")
    start = text.index("## 0. 公开符号面")
    block = text[start:]
    block = block[block.index("```python") + len("```python") : block.index("```", block.index("```python") + 3)]
    names: set[str] = set()
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("from "):
            continue
        head = stripped.split(",", 1)[0].strip()
        if head and head.isidentifier():
            names.add(head)
    return names


def test_the_public_symbol_faces_are_unchanged() -> None:
    """**SC-019**：L1 **20** / 门面 **7** / ``freegraph.runtime.__all__`` **20** 个符号。

    ⚠️ **清单驱动** ⇒ L1 的断言是「与 ``public-api.md`` §0 的清单**集合相等**」
    ⇒ **不硬编码 18**（⚠️ **2026-11-13 · X1 / R-10**：L1 基线由 18 改为 **20**
    —— **上游对齐批次 P3** 已扩面 ⇒ **本 feature 对 L1 零新增**）。
    """
    import freegraph.contracts as l1
    import freegraph.graph as facade
    import freegraph.runtime as runtime

    manifest = _parse_l1_manifest()
    assert manifest, "L1 公开符号面清单解析为空"
    assert set(l1.__all__) == manifest, "L1 的 `__all__` 与清单**集合不等**"
    assert len(facade.__all__) == 7, f"门面符号面应为 7，实得 {len(facade.__all__)}"
    # ⚠️ **回溯修订 T-1 ②**（**B10F1** · **拆分而不删**）：原判据是「符号数 == 20」
    # ⇒ ⇒ **硬编码数字** ⇒ ⇒ B10F1 **增**了 3 个符号 ⇒ ⇒ **必红** ⇒ ⇒
    # 改为「**与清单集合相等**」⇒ ⇒ **判据零放宽**（仍是「== 某份清单」）。
    from ._runtime_export_manifest import RUNTIME_EXPORT_SYMBOLS

    assert set(runtime.__all__) == RUNTIME_EXPORT_SYMBOLS, (
        f"runtime.__all__ 与清单不等：{set(runtime.__all__) ^ RUNTIME_EXPORT_SYMBOLS}"
    )


def test_the_super_step_result_keeps_its_four_fields() -> None:
    """**SC-019**：``SuperStepResult`` 的**字段数 == 4**（⚠️ **不**新增 ``interrupts``）。

    ⇒ 中断信息**以抛出的方式**交给调用方（**裁定 25**）⇒ 加字段会是**死字段**。
    """
    import dataclasses

    from freegraph.runtime import SuperStepResult

    fields = [f.name for f in dataclasses.fields(SuperStepResult)]
    assert fields == ["state", "executed", "node_writes", "steps"], fields


def test_the_scheduler_state_constructor_signature_is_unchanged() -> None:
    """**SC-019**：``SchedulerState()`` 的**构造签名逐字不变**（**零新增字段**）。

    ⇒ 中断**不落**调度状态（**V-3**）⇒ `SchedulerState()` 的**构造签名与名字逐字不变**。
    """
    import dataclasses
    import inspect

    from freegraph.runtime import SchedulerState

    assert [f.name for f in dataclasses.fields(SchedulerState)] == [
        "versions_seen",
        "step",
        "channel_versions",
        "node_versions",
        "dynamic_edges",
        "channels",
    ]
    # ⚠️ **构造签名逐字不变** = 字段的**名字与顺序**不变，且**全部有缺省值**
    # ⇒ `SchedulerState()` **零参可构造**（既有调用方零改动）
    parameters = list(inspect.signature(SchedulerState).parameters.values())
    assert [p.name for p in parameters] == [
        "versions_seen",
        "step",
        "channel_versions",
        "node_versions",
        "dynamic_edges",
        "channels",
    ]
    assert all(p.default is not inspect.Parameter.empty for p in parameters)
    SchedulerState()  # 零参可构造


def test_the_entry_points_only_gained_a_keyword_only_parameter() -> None:
    """**SC-019**：两个入口的**既有参数**名字 / 顺序 / 语义**一字不动**。

    ⇒ **只**增一个 **keyword-only** 的 ``max_concurrency``（**兼容扩展**）。
    """
    import inspect

    from freegraph.runtime import run_super_step, run_super_steps

    single = inspect.signature(run_super_step).parameters
    assert list(single) == ["spec", "state", "max_concurrency"]
    assert single["max_concurrency"].kind is inspect.Parameter.KEYWORD_ONLY
    assert single["max_concurrency"].default is None

    multi = inspect.signature(run_super_steps).parameters
    assert list(multi) == ["spec", "state", "max_steps", "max_concurrency"]
    assert multi["max_steps"].kind is inspect.Parameter.KEYWORD_ONLY
    assert multi["max_steps"].default == 10007
    assert multi["max_concurrency"].kind is inspect.Parameter.KEYWORD_ONLY
    assert multi["max_concurrency"].default is None


def test_the_runtime_layer_does_not_import_the_upper_layers() -> None:
    """**SC-019**：L2 → L3 / L4 / L5 的依赖边数 == **0**（ARCH-1）。"""
    import ast

    runtime_dir = _REPO_ROOT / "src" / "freegraph" / "runtime"
    edges: list[str] = []
    for path in sorted(runtime_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        for name in imported:
            for upper in _UPPER_LAYER_MODULES:
                if f"freegraph.{upper}" in name:
                    edges.append(f"{path.name} → {name}")
    assert edges == [], edges


def test_the_gate_numbering_is_still_continuous() -> None:
    """**SC-019**：既有门禁编号 **G1–G30** 连续无跳号 · 总数 == **30**。

    ⇒ 本 feature **零新增门禁编号**（**FR-025**）。
    """
    import re

    contract = (
        _REPO_ROOT
        / "specs"
        / "b3f1-scaffold-ci-gates"
        / "contracts"
        / "architecture-gates.md"
    ).read_text(encoding="utf-8")
    overview = re.search(r"^##\s*0\..*?(?=^##\s|\Z)", contract, re.S | re.M)
    assert overview, "architecture-gates.md 缺少「## 0. 门禁总览」章节"
    identifiers = re.findall(r"\|\s*\*\*G(\d+)\*\*\s*\|", overview.group(0))
    assert identifiers == [str(number) for number in range(1, 31)]


# ── 并发执行器的**直接**单元判定（**T073 覆盖率 == 100%** 的补齐）──────────


def test_the_concurrency_executor_creates_no_thread_for_zero_tasks() -> None:
    """**SC-001**：**零节点**的一轮 ⇒ MUST **NOT** 创建任何线程 ⇒ MUST **NOT** 建池。

    ⚠️ 这是并发执行器的**守卫分支**（对外入口永远不会以「零任务」调用它）⇒
    以**直接单元判定**覆盖（契约 §4「零节点」行）。
    """
    from freegraph.runtime import _concurrency

    before = threading.active_count()
    outcomes = _concurrency.run_tasks_concurrently([], cap=4)

    assert outcomes == []
    assert threading.active_count() == before


def test_the_concurrency_cap_is_resolved_as_specified() -> None:
    """**SC-027**：实际并发度 == ``min(本轮任务数, 上限)``。

    * 缺省上限 == ``min(32, cpu+4)``（**上游同款**）；
    * 显式 ``N`` ⇒ **N 不被 32 再夹**。
    """
    from freegraph.runtime import _concurrency

    default_cap = min(32, (os.cpu_count() or 1) + 4)
    assert _concurrency._resolve_cap(0, None) == 0
    assert _concurrency._resolve_cap(3, None) == 3
    assert _concurrency._resolve_cap(1000, None) == default_cap
    assert _concurrency._resolve_cap(1000, 100) == 100
    assert _concurrency._resolve_cap(5, 100) == 5
    assert _concurrency._resolve_cap(5, 1) == 1


# ── 纯净性 · 文档纪律（**SC-018** / **SC-023** / **SC-024**）────────────────

#: **本 feature 的**新 / 改源文件（**署名头**与**上游引用纪律**的取证范围）。
_FEATURE_SOURCES = (
    "src/freegraph/runtime/_concurrency.py",
    "src/freegraph/runtime/superstep.py",
    "tests/runtime/test_superstep_concurrency.py",
    "tests/runtime/test_superstep_errors.py",
    "tests/differential/parity_probe.py",
    "harness/verification/B12F1/acceptance.py",
)


def test_the_concurrency_module_is_pure() -> None:
    """**SC-018** / **SC-023**：并发实现**只用标准库** ⇒ 零环境变量 / 零出站 /
    零文件 I/O；且 **MUST NOT** 越界实现 ``interrupt()`` / ``__interrupt__`` /
    async / ``Send`` / ``recursion_limit`` / checkpoint / 重试 / 超时 /
    **多源汇合边**。"""
    import re as _re

    concurrency = (
        _REPO_ROOT / "src" / "freegraph" / "runtime" / "_concurrency.py"
    ).read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "os.environ",
        "os.getenv",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "open(",
        "async def",
        "await ",
        "Send",
        "recursion_limit",
        "checkpointer",
        "retry",
        "timeout(",
        "__interrupt__",
    ):
        assert forbidden not in concurrency, f"并发模块出现越界构造：{forbidden}"
    # ⚠️ `os.cpu_count()` 是**系统调用**（**非**环境变量）⇒ 允许
    assert _re.search(r"os\.cpu_count\(\)", concurrency), "并发度缺省 MUST 用 os.cpu_count()"

    # ⚠️ **回溯修订 T-1 ⑥**（**B10F1** · **拆分而不删**）：原判据是「源码文本里**含**
    # `NotImplementedError`」⇒ ⇒ 它守的是「`interrupt()` **未接线**」这个
    # **中间态** ⇒ ⇒ B10F1 把 `interrupt()` **接线**后 ⇒ ⇒ **必红**
    # ⇒ ⇒ 改为「`_primitives.py` **只留 `Send`**（**不含** `interrupt` 的
    # **实现体**）」的**源码文本**断言 ⇒ ⇒ **判据零放宽**（**更强**：从
    # 「含某个字符串」定位到「**不含实现体**」本身）⇒ ⇒ 同步本测试的
    # **docstring / 命名**（不再说「归 B10F1」）。
    primitives = (_REPO_ROOT / "src" / "freegraph" / "_primitives.py").read_text(
        encoding="utf-8"
    )
    assert "def interrupt" not in primitives, (
        "_primitives.py 仍带 interrupt 的实现体（**必须**只留 `Send` —— "
        "**跨注册表条目的同层 import** ⇒ 门禁 G25 判红）"
    )


def test_the_new_source_files_carry_signature_header_and_leading_docstring() -> None:
    """**SC-024**（宪法原则 X）：本 feature 的**新 / 改源文件**署名头覆盖率 == **100%**
    且模块 docstring 是**首个语句**。"""
    import ast

    for relative in _FEATURE_SOURCES:
        path = _REPO_ROOT / relative
        assert path.exists(), f"缺失源文件：{relative}"
        text = path.read_text(encoding="utf-8")
        # ⚠️ 允许**首行**是 shebang（``#!/usr/bin/env python3``）⇒ 署名头 MUST 在**前三行**内
        head = "\n".join(text.splitlines()[:3])
        assert "# Copyright (c) 2026 " in head, f"{relative} 缺署名头"
        tree = ast.parse(text)
        assert (
            ast.get_docstring(tree) is not None
        ), f"{relative} 的模块 docstring 缺失或不是首个语句"
        first = tree.body[0]
        assert isinstance(
            first, ast.Expr
        ) and isinstance(first.value, ast.Constant), f"{relative} 的 docstring 不是首个语句"


def test_the_upstream_references_carry_version_and_line_numbers() -> None:
    """**SC-024**（宪法原则 VIII / 原则 XI 的「上游锚点纪律」）：上游引用 MUST 带
    **版本 + `路径:行号`** ⇒ 凭记忆沿用的引用数 == **0**。"""
    import re as _re

    offenders: list[str] = []
    for relative in _FEATURE_SOURCES:
        text = (_REPO_ROOT / relative).read_text(encoding="utf-8")
        for match in _re.finditer(r"(langgraph|langchain_core)/[A-Za-z0-9_./]*\.py", text):
            if not _re.match(r":\d", text[match.end() : match.end() + 4]):
                line = text[: match.start()].count("\n") + 1
                offenders.append(f"{relative}:{line} {match.group(0)}")
    assert offenders == [], offenders
