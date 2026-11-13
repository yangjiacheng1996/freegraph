# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**多源汇合边（AND / 屏障）**的用例 —— 属 **B7F4**。

覆盖的判定：

* **A1** —— 多源边**可表达**（``edges={("a", "b"): ("c",)}`` ⇒ 构造**成功**）·
  不变量 **M-1**；
* **A2** —— **屏障语义正确**：目标**严格晚于**所有源（**M-2**）· **组内全**
  （只满足一个源时目标**不**执行）· 屏障**不齐** ⇒ 静默等待（**M-3**）·
  屏障**后齐** ⇒ 目标**再执行一次**（**M-5**）· **组间任一**（**M-8**）；
* **A8** —— 多源边的**形态校验**（**V-16** / **V-2** / 边键**类型**非法）。

⚠️ **本文件是 B7F4 的**新文件** ⇒ 既有冻结断言文件（``tests/runtime/`` 的
**10 个**）**逐字未变**（**R-9** · 澄清轮 **C-Q5** 的机械判据）⇒ ⇒ 「一条不删」
以「**原文件内容逐字未变**」**机械可证**。

⚠️ **断言口径**（裁定 13）：``executed`` 的口径 = **节点名序**（B12F1 已落地）⇒
两个屏障源的**执行先后不确定** ⇒ ⇒ 断言 MUST 用「**目标的位置晚于源**」的
**位置比较** ⇒ **MUST NOT** 断言两个源**彼此**的先后。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.contracts.errors import GraphRecursionError
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


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30`）。
#:
#: ⚠️ 它**无入边** ⇒ **永不执行**（永不进 ``executed``）⇒ 它只作「入口边」的**源**。
#: ⚠️ 与 B7F1 的既有夹具**同款**（沿用 ``tests/runtime/test_superstep_trigger.py``）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


def _recorder(calls: list[str], name: str) -> Any:
    """造一个「**记录自己的名字**」的节点函数。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(name)
        return {}

    return _run


def _nodes(calls: list[str], names: tuple[str, ...]) -> dict[str, NodeSpec]:
    """造一组「**只记录名字**」的节点（``subscribes`` 为空 ⇒ 不依赖通道值）。"""
    nodes: dict[str, NodeSpec] = {"__start__": _ENTRY}
    for name in names:
        nodes[name] = NodeSpec(subscribes=(), run=_recorder(calls, name))
    return nodes


# ── T020 · 多源边可表达（A1 · FR-001 · M-1）───────────────────────────────


def test_a_multi_source_edge_can_be_expressed() -> None:
    """**A1** · FR-001 · **M-1**：多源边**可表达** ⇒ 构造**成功**（不抛错）。

    ⚠️ **兼容扩展**：单源边的写法**逐字不变**（``edges={"a": ("c",)}``）⇒
    既有调用方**零改动**。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
    )

    assert spec.edges[("a", "b")] == ("c",)


# ── T021 · 屏障目标严格晚于所有源（A2 · FR-003 · M-2）─────────────────────


def test_the_barrier_target_runs_strictly_after_every_source() -> None:
    """**A2** · FR-003 · **M-2**：屏障目标的执行**严格晚于**所有源。

    ⚠️ **位置比较**（裁定 13）：并发下两个源的**执行先后不确定** ⇒ ⇒
    **MUST NOT** 断言 ``a`` 与 ``b`` 彼此的先后 ⇒ ⇒ 只断言「``c`` 的位置
    **晚于** ``a`` 与 ``b``」。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
    )

    result = run_super_steps(spec, SchedulerState())
    executed = list(result.executed)

    assert executed.count("c") == 1
    assert executed.index("c") > executed.index("a")
    assert executed.index("c") > executed.index("b")


# ── T022 · 两源同一轮触发 ⇒ 屏障在下一轮才触发（DR-8）─────────────────────


def test_the_barrier_arms_only_in_the_round_after_its_sources_ran() -> None:
    """research **DR-8**：两个源**同一轮**被触发 ⇒ 屏障在**下一轮**才满足。

    ⚠️ 与普通边**同款**（源节点的执行版本在**轮末**推进）⇒ ⇒ **零特殊处理**。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert first.executed == ("a", "b")
    assert "c" not in first.executed
    assert second.executed == ("c",)


# ── T023 · 组内全（只满足一个源 ⇒ 目标不执行）（A2 · FR-003 · M-2）────────


def test_the_barrier_target_does_not_run_while_only_one_source_is_satisfied() -> None:
    """**A2** · FR-003 · **M-2**：**组内全** ⇒ 只满足**一个**源时目标**不**执行。

    ⚠️ ``b`` **永不可达**（无入边 ⇒ 永不执行 ⇒ 执行版本**恒为 0**）⇒
    屏障组 ``{"a", "b"}`` **不齐** ⇒ ⇒ ``c`` **不**执行。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a",), ("a", "b"): ("c",)},
    )

    result = run_super_steps(spec, SchedulerState())

    assert result.executed == ("a",)
    assert "c" not in result.executed


# ── T030 · 屏障不齐 ⇒ 目标执行计数 == 0（A2 · FR-004 · M-3）──────────────


def test_an_unsatisfied_barrier_keeps_its_target_from_running_at_all() -> None:
    """**A2** · FR-004 · **M-3**：屏障**不齐** ⇒ 目标执行计数 == **0**。

    ⚠️ 上游 **E-2** 同款（上游的屏障不齐 ⇒ 目标**从未执行**且**不报错**）。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a",), ("a", "b"): ("c",)},
    )

    result = run_super_steps(spec, SchedulerState())

    assert calls.count("c") == 0
    assert result.executed.count("c") == 0


# ── T031 · 屏障不齐时整张图正常收敛（A2 · M-3）────────────────────────────


def test_the_graph_converges_normally_while_a_barrier_stays_unsatisfied() -> None:
    """**A2** · **M-3**：屏障**不齐** ⇒ 图**正常收敛**（**不抛错**）。

    ⚠️ **无「屏障未齐」类错误** ⇒ 屏障的语义是「**静默等待**」⇒ 图在**还有
    任务可跑**时**不**终止、在**没有**任务可跑时**正常**终止。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a",), ("a", "b"): ("c",)},
    )

    result = run_super_steps(spec, SchedulerState())

    assert result.steps <= 3
    assert result.executed == ("a",)


# ── T032 · 屏障后齐 ⇒ 目标再执行一次（A2 · FR-004 · M-5）─────────────────


def test_the_barrier_target_runs_again_once_the_barrier_becomes_satisfied() -> None:
    """**A2** · FR-004 · **M-5**：屏障**后齐** ⇒ 目标**再执行一次**（不被吞掉）。

    ⚠️ 上游 **E-5** 同款（上游基线 = ``['a', 'b', 'c', 'd', 'c']``）⇒
    ⇒ 上游**只消费本次读到的通道** ⇒ 未满足的组**不被记账**。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c", "d")),
        edges={
            "__start__": ("a", "b"),
            "a": ("c",),
            "b": ("d",),
            ("b", "d"): ("c",),
        },
    )

    result = run_super_steps(spec, SchedulerState())

    assert calls.count("c") == 2
    assert list(result.executed) == ["a", "b", "c", "d", "c"]


# ── T033 · 组间任一（A2 · FR-003 · M-8）────────────────────────────────────


def test_a_satisfied_single_source_edge_still_triggers_the_barrier_target() -> None:
    """**A2** · FR-003 · **M-8**：**组间任一** ⇒ 单源边满足时目标**仍被触发**。

    ⚠️ 上游 **E-3** 同款（上游基线 = ``['a', 'b', 'c']``）⇒ ⇒ 一个节点同时有
    「单源入边」与「多源入边」时，**任一**入边满足即触发 ⇒ ⇒
    **不是**「所有源都跑过才触发」。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c", "d")),
        edges={"__start__": ("a", "b"), "a": ("c",), ("b", "d"): ("c",)},
    )

    result = run_super_steps(spec, SchedulerState())

    assert calls.count("c") == 1
    assert list(result.executed) == ["a", "b", "c"]


# ── T034 · 源不订阅任何通道 ⇒ 照样算「跑过」（FR-003 · M-7）────────────────


def test_a_source_that_subscribes_nothing_still_satisfies_the_barrier() -> None:
    """FR-003 · **M-7**：源的「**跑过**」与「**写了什么**」**无关** ⇒
    ⇒ 不订阅任何通道的源**照样**满足屏障 ⇒ ⇒ ``seen`` **逐源各一条**。

    ⚠️ **M-7** 的判定口径 = ``versions_seen[N]`` 的**键集合** ⇒ 屏障组
    ``{"a", "b"}`` 满足后 ⇒ 两个源**各记一条**。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},
    )
    state = SchedulerState()

    run_super_steps(spec, state)

    assert calls.count("c") == 1
    assert set(state.versions_seen["c"]) == {("e", "a"), ("e", "b")}


# ── T039 · 同一轮内至多触发一次（A2 · SC-003 · M-4）──────────────────────


def test_the_barrier_target_is_triggered_at_most_once_per_round() -> None:
    """**SC-003** · **M-4**：屏障目标在**单轮** ``executed`` 里**至多出现一次**。

    ⚠️ 同一张图上**同时**存在单源入边与多源入边 ⇒ 两组**同时**满足 ⇒ ⇒
    目标在**同一轮**仍**只**被触发**一次**。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), "a": ("c",), ("a", "b"): ("c",)},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert first.executed.count("c") <= 1
    assert second.executed.count("c") <= 1
    assert calls.count("c") == 1


# ── T086 · 元组内重复源 ⇒ 构造成功且等价单源口径（裁定 2 · DR-4）──────────


def test_a_duplicated_source_inside_the_tuple_behaves_like_a_single_source() -> None:
    """裁定 2 · research **DR-4** · 契约 §2.3：``("a", "a")`` ⇒ **去重保序** ⇒
    ⇒ 等价**单源口径** ⇒ ⇒ 构造**成功**（**MUST NOT** 报错）。

    ⚠️ 上游 ``NamedBarrierValue(str, set(starts))`` 天然去重 ⇒ **照抄** ⇒
    ⇒ **不是**「比上游更严」。
    """
    calls: list[str] = []

    duplicated = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "c")),
        edges={"__start__": ("a",), ("a", "a"): ("c",)},
    )
    single = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "c")),
        edges={"__start__": ("a",), "a": ("c",)},
    )

    duplicated_result = run_super_steps(duplicated, SchedulerState())
    single_result = run_super_steps(single, SchedulerState())

    assert list(duplicated_result.executed) == list(single_result.executed)
    assert duplicated_result.state == single_result.state


# ── T087 · 环图 ⇒ 屏障照常判定（research DR-9 · 契约 §6）──────────────────


def test_a_cyclic_graph_keeps_evaluating_the_barrier_until_the_step_limit() -> None:
    """research **DR-9** · 契约 §6：屏障目标**自己也是某个源的祖先** ⇒
    ⇒ 屏障**照常判定** ⇒ ⇒ 收敛由**既有步数上限**兜底 ⇒ ⇒
    ⇒ **MUST NOT** 抛「环检测」类异常（**不新增**失败信号）。

    ⚠️ ``c`` 既是屏障的**目标**又是 ``a`` / ``b`` 的**源** ⇒ 图**真的**成环 ⇒
    ⇒ 唯一可观察的失败信号 MUST 是**既有**的 ``GraphRecursionError``（步数上限）
    ⇒ ⇒ **MUST NOT** 出现任何「环检测」类的**新**异常。
    """
    calls: list[str] = []

    spec = GraphSpec(
        channels=_channels(),
        nodes=_nodes(calls, ("a", "b", "c")),
        edges={"__start__": ("a", "b"), ("a", "b"): ("c",), "c": ("a", "b")},
    )

    with pytest.raises(GraphRecursionError):
        run_super_steps(spec, SchedulerState(), max_steps=5)

    # ⚠️ 屏障**照常判定** ⇒ 目标在步数上限之前**确实**执行过 ⇒ ⇒
    # ⇒ 「环」**没有**让屏障失效（也**没有**引入新的失败信号）。
    assert calls.count("c") >= 1


# ── T037 · 多源边的形态校验（A8 · X-02 / X-04 · FR-021）────────────────────


def _shape_spec(edges: Any, nodes: dict[str, NodeSpec] | None = None) -> GraphSpec:
    """造一张「**只用于构造期校验**」的图规格。"""
    return GraphSpec(
        channels=_channels(),
        nodes=nodes if nodes is not None else _nodes([], ("a", "b", "c", "d")),
        edges=edges,
    )


def test_an_empty_multi_source_edge_is_rejected_at_construction_time() -> None:
    """**A8** · **X-02**：**空**的多源边 ⇒ 内置 ``ValueError``（**V-16**）。

    ⚠️ 上游 **E-6** ⇒ 上游**静默**（目标**从未执行**且**不报错**）⇒ ⇒
    freegraph **比上游更严** ⇒ ⇒ 失败信号**显式**。
    """
    with pytest.raises(ValueError):
        _shape_spec({(): ("c",)})


def test_a_multi_source_edge_containing_the_entry_marker_is_rejected() -> None:
    """**A8** · **V-16**：多源边的元组**含 `__start__`** ⇒ 内置 ``ValueError``。

    ⚠️ 上游 **E-7** 同族（上游 ``ValueError: Need to add_node '__start__' first``）。
    """
    with pytest.raises(ValueError):
        _shape_spec({("__start__", "b"): ("c",)})


@pytest.mark.parametrize("targets", [(), ("c", "d")])
def test_a_multi_source_edge_must_have_exactly_one_target(targets: tuple[str, ...]) -> None:
    """**A8** · **V-16**：多源边的**目标数 ≠ 1** ⇒ 内置 ``ValueError``。

    ⚠️ 上游 ``add_edge(starts, end)`` 只有**一个** ``end`` ⇒ **形态照抄**。
    """
    with pytest.raises(ValueError):
        _shape_spec({("a", "b"): targets})


def test_a_multi_source_edge_targeting_the_terminal_marker_is_rejected() -> None:
    """**A8** · **X-04**：多源边的**目标为 `__end__`** ⇒ 内置 ``ValueError``。

    ⚠️ 上游 **E-9** ⇒ 上游**被接受但静默 no-op** ⇒ ⇒ freegraph **比上游更严**。
    """
    with pytest.raises(ValueError):
        _shape_spec({("a", "b"): ("__end__",)})


def test_a_multi_source_edge_with_a_missing_source_names_the_missing_source() -> None:
    """**A8** · **V-2** 同族：多源边含**不存在的源** ⇒ 内置 ``ValueError`` 且
    **点名**该源。

    ⚠️ 上游 **E-8** 同族（上游 ``ValueError: Need to add_node 'a' first``）。
    ⚠️ **MUST NOT** 断言消息的**逐字文本** ⇒ ⇒ 只断言**异常类型**与**点名**。
    """
    with pytest.raises(ValueError) as excinfo:
        _shape_spec({("a", "zz"): ("c",)})

    assert "zz" in str(excinfo.value)


def test_a_multi_source_edge_with_a_missing_target_names_the_missing_target() -> None:
    """**A8** · **V-2** 同族（澄清轮 **C-Q18**）：多源边的**目标不在节点表** ⇒
    内置 ``ValueError`` 且**点名**该目标。

    ⚠️ **归 `V-2`**（语义校验族）⇒ ⇒ **NOT** `V-16`（形态校验族）。
    """
    with pytest.raises(ValueError) as excinfo:
        _shape_spec({("a", "b"): ("nope",)})

    assert "nope" in str(excinfo.value)


def test_an_edge_key_of_an_illegal_type_is_rejected_with_a_type_error() -> None:
    """**A8** · **FR-021** · 裁定 17：边键**既非 `str` 亦非 `tuple`** ⇒
    内置 **`TypeError`**。

    ⚠️ 上游 **E-10** 同族（上游 ``TypeError: 'int' object is not iterable``）⇒
    ⇒ **零新增错误类型**（类型问题 ⇒ ``TypeError``；语义问题 ⇒ ``ValueError``）。
    """
    with pytest.raises(TypeError):
        _shape_spec({123: ("c",)})
