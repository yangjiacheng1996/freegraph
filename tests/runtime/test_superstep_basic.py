# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**单 super-step 跑通**的用例 —— 属 **B7F1**（tasks T018 / T019 / T020 / T021）。

覆盖的判定：

* **SC-001** —— 手写图规格跑**一轮** super-step 后状态变更完全符合预期；
  五阶段产物（**执行记录** / **待写入** / **合并后状态** / **轮数**）**逐项可观测**；
* **SC-004** —— 订阅**无值**通道的节点执行次数 == **0**；
* **SC-009 / SC-013** —— 节点入参是**普通 `dict`**且只含「订阅集 ∩ 有值集」；
* **SC-015** —— 图规格校验与返回值校验的**四条显式失败路径**（校验规则 **V-1…V-4**）；
* **SC-020** —— 节点异常**原样**传播；
* **SC-025** —— 「条件边」字段**恒空**；非空即**显式失败**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.runtime import (
    BinaryOperatorAggregate,
    Channel,
    EphemeralValue,
    GraphSpec,
    LastValue,
    NodeSpec,
    SchedulerState,
    SuperStepResult,
    read_channels,
    run_super_step,
    run_super_steps,
)


def _reducer_channels() -> dict[str, Channel]:
    """构造通道状态：**归约型**（``messages``）+ **覆盖型**（``count``）。

    ⚠️ 归约型通道在构造时**推导**出空值（``[]``）⇒ 它**一开始就有值**
    ⇒ 「无值通道」的用例 MUST 用**覆盖型**通道（见 ``_plain_channels``）。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
    }


def _plain_channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型**两个（构造后**都无值**）。"""
    return {
        "count": LastValue("count", int),
        "other": LastValue("other", str),
    }


class _ProbeChannel(Channel):
    """**探针通道** —— 记录 ``update`` / ``clear`` 的调用次数。

    ⚠️ 只**观察**、**不改变**语义（委托给内部通道）⇒ 用例可以用它断言
    「执行期间通道的**正式值**被改写的次数 == 0」（SC-008）。
    """

    def __init__(self, key: str, value_type: Any, inner: Channel) -> None:
        super().__init__(key, value_type)
        self._inner = inner
        self.update_calls = 0
        self.clear_calls = 0

    def update(self, values: Any) -> bool:
        self.update_calls += 1
        return self._inner.update(values)

    def get(self) -> Any:
        return self._inner.get()

    def is_available(self) -> bool:
        return self._inner.is_available()

    def clear(self) -> bool:
        self.clear_calls += 1
        return self._inner.clear()


# ── T018 · 一轮 super-step 跑通（SC-001 / SC-004）──────────────────────


def test_a_subscribed_node_runs_exactly_once_and_the_state_merges() -> None:
    """**SC-001**：订阅**有值**通道的节点执行**恰好一次**；合并后状态符合预期。

    ⚠️ 初始值由**调用方在跑之前**直接写通道对象（**初始化写入豁免** · 裁定 31）。
    """
    channels = _reducer_channels()
    channels["messages"].update([["seed"]])
    calls: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(state)
        return {"messages": ["written"], "count": 7}

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("messages",), run=node)},
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert len(calls) == 1
    assert result.executed == ("writer",)
    assert result.state["messages"] == ["seed", "written"]
    assert result.state["count"] == 7


def test_a_node_subscribing_an_empty_channel_does_not_run() -> None:
    """**SC-004**：订阅**无值**通道的节点执行次数 == **0**。"""
    calls: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(state)
        return {"count": 1}

    spec = GraphSpec(
        channels=_plain_channels(),
        nodes={"writer": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert calls == []
    assert result.executed == ()
    assert result.state == {}


def test_a_node_updates_only_the_keys_it_returns() -> None:
    """**SC-001**：节点返回的**部分状态**只更新返回的 key（未返回的保持不变）。"""
    channels = _plain_channels()
    channels["count"].update([3])
    channels["other"].update(["kept"])

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("count",), run=lambda state: {"count": 4})},
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.state["other"] == "kept"
    assert result.state["count"] == 4


# ── T019 · 边触发源在下一轮生效（SC-001）────────────────────────────────


def test_an_edge_target_is_scheduled_in_the_next_round() -> None:
    """**SC-001**：源节点在第 1 轮执行完毕 ⇒ 目标节点在**第 2 轮**被调度执行。"""
    channels = _plain_channels()
    channels["count"].update([1])
    executed: list[str] = []

    def source(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("source")
        return {"other": "from-source"}

    def target(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("target")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "source": NodeSpec(subscribes=("count",), run=source),
            "target": NodeSpec(subscribes=("other",), run=target),
        },
        edges={"source": ("target",)},
    )

    result = run_super_steps(spec)

    assert executed == ["source", "target"]
    assert result.executed == ("source", "target")


# ── T020 · 五阶段产物逐项可观测（SC-001）───────────────────────────────


def test_the_five_phase_products_are_all_observable() -> None:
    """**SC-001**：**执行记录** / **待写入** / **合并后状态** / **轮数**逐项可观测。

    ⚠️ **待写入** = 节点返回的**原始**写入值（**合并前**）⇒ 归约型通道上
    记的是 ``(["more"],)`` 而**不是**合并后的结果（FR-006 · B8F1 的复用前提）。
    """
    channels = _reducer_channels()
    channels["messages"].update([["seed"]])

    spec = GraphSpec(
        channels=channels,
        nodes={
            "writer": NodeSpec(
                subscribes=("messages",), run=lambda state: {"messages": ["more"]}
            )
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert isinstance(result, SuperStepResult)
    assert result.executed == ("writer",)
    assert result.node_writes == {"writer": {"messages": (["more"],)}}
    assert result.state["messages"] == ["seed", "more"]
    assert result.steps == 1


# ── T021 · 节点入参（SC-009 / SC-013）───────────────────────────────────


def test_the_node_input_is_a_plain_dict_with_only_the_available_subscriptions() -> None:
    """**SC-009 / SC-013**：入参是**普通 `dict`**且只含「订阅集 ∩ 有值集」。"""
    channels = _plain_channels()
    channels["count"].update([3])
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"reader": NodeSpec(subscribes=("count", "other"), run=node)},
        edges={},
    )

    run_super_step(spec, SchedulerState())

    assert len(captured) == 1
    node_input = captured[0]
    assert type(node_input) is dict
    assert set(node_input) == {"count"}
    assert "other" not in node_input
    assert node_input.get("other", "default") == "default"


def test_the_node_input_equals_the_sparse_read_of_the_sub_mapping() -> None:
    """**SC-013**：入参 == ``read_channels(子映射)`` 的结果（**逐字相等**）。

    ⚠️ 子映射 MUST 按「**通道映射的顺序**」构造（裁定 26）⇒ 入参的 key 顺序
    与**整张状态表**的 key 顺序**天然一致**。
    """
    channels = _plain_channels()
    channels["count"].update([5])
    channels["other"].update(["x"])
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"reader": NodeSpec(subscribes=("other", "count"), run=node)},
        edges={},
    )

    run_super_step(spec, SchedulerState())

    sub_mapping = {
        key: channel for key, channel in channels.items() if key in ("other", "count")
    }
    expected = read_channels(sub_mapping)
    node_input = captured[0]
    assert list(node_input) == list(expected)
    for key, value in expected.items():
        assert node_input[key] is value


# ── T057 · 四条显式失败路径（SC-015）────────────────────────────────────


def test_subscribing_an_unknown_channel_fails_at_construction_time() -> None:
    """**V-1**：订阅**不存在**的通道 key ⇒ **构造时**抛内置 ``ValueError``。"""
    with pytest.raises(ValueError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={"reader": NodeSpec(subscribes=("nope",), run=lambda state: {})},
            edges={},
        )


def test_an_edge_pointing_outside_the_node_table_fails_at_construction_time() -> None:
    """**V-2**：边的**源 / 目标**不在节点表里 ⇒ **构造时**抛内置 ``ValueError``。"""
    with pytest.raises(ValueError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={"reader": ("ghost",)},
        )
    with pytest.raises(ValueError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={"ghost": ("reader",)},
        )


def test_an_empty_node_table_fails_at_construction_time() -> None:
    """**V-3**：图规格**没有任何节点** ⇒ **构造时**抛内置 ``ValueError``。"""
    with pytest.raises(ValueError):
        GraphSpec(channels=_plain_channels(), nodes={}, edges={})


def test_a_node_returning_a_non_dict_fails_at_runtime() -> None:
    """**V-4**：节点返回值**不是 `dict`**（含 ``None``）⇒ 运行期抛内置 ``TypeError``。"""
    channels = _plain_channels()
    channels["count"].update([1])

    for bad in (None, 42, "text", ["not", "a", "dict"]):
        spec = GraphSpec(
            channels=channels,
            nodes={"writer": NodeSpec(subscribes=("count",), run=lambda state: bad)},
            edges={},
        )
        with pytest.raises(TypeError):
            run_super_step(spec, SchedulerState())


# ── T057 · 图规格的**类型**校验（契约 §2.1 / §2.2）───────────────────────


def test_a_non_callable_node_function_fails_at_construction_time() -> None:
    """契约 §2.2：节点函数 **MUST 可调用** ⇒ **构造时**抛内置 ``TypeError``。"""
    with pytest.raises(TypeError):
        NodeSpec(subscribes=("count",), run="not-callable")  # type: ignore[arg-type]


def test_a_non_channel_channel_value_fails_at_construction_time() -> None:
    """契约 §2.1：通道映射的**值** MUST 是 ``Channel`` 实例 ⇒ 显式失败。"""
    with pytest.raises(TypeError):
        GraphSpec(
            channels={"count": "not-a-channel"},  # type: ignore[dict-item]
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
        )


def test_a_non_str_channel_key_fails_at_construction_time() -> None:
    """契约 §2.1：通道映射的 **key** MUST 是 ``str`` ⇒ 显式失败。"""
    with pytest.raises(TypeError):
        GraphSpec(
            channels={7: LastValue("count", int)},  # type: ignore[dict-item]
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
        )


def test_a_non_node_spec_node_value_fails_at_construction_time() -> None:
    """契约 §2.1：节点表的**值** MUST 是 ``NodeSpec`` 实例 ⇒ 显式失败。"""
    with pytest.raises(TypeError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={"reader": "not-a-node-spec"},  # type: ignore[dict-item]
            edges={},
        )


def test_a_non_str_node_name_fails_at_construction_time() -> None:
    """契约 §2.1：**节点名** MUST 是 ``str`` ⇒ 显式失败。"""
    with pytest.raises(TypeError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={7: NodeSpec(subscribes=(), run=lambda state: {})},  # type: ignore[dict-item]
            edges={},
        )


# ── T058 · 待写入隔离（SC-008）──────────────────────────────────────────


def test_a_node_does_not_see_another_nodes_write_of_the_same_round() -> None:
    """**SC-008**：节点读**不到**同轮其它节点的写入；正式值在执行期间**不变**。"""
    inner = LastValue("count", int)
    inner.update([1])
    probe = _ProbeChannel("count", int, inner)
    seen: list[Any] = []

    def reader(state: dict[str, Any]) -> dict[str, Any]:
        seen.append(probe.get())
        seen.append(probe.update_calls)
        return {}

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 99}

    spec = GraphSpec(
        channels={"count": probe},
        nodes={
            "reader": NodeSpec(subscribes=("count",), run=reader),
            "writer": NodeSpec(subscribes=("count",), run=writer),
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert seen == [1, 0]
    assert probe.get() == 99
    assert result.state["count"] == 99


# ── T059 · 节点异常原样传播（SC-020）────────────────────────────────────


def test_a_node_exception_propagates_as_the_very_same_object() -> None:
    """**SC-020**：节点抛出的异常**原样**传播（类型与身份均不变）。"""
    channels = _plain_channels()
    channels["count"].update([1])
    boom = RuntimeError("boom")

    def node(state: dict[str, Any]) -> dict[str, Any]:
        raise boom

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )

    with pytest.raises(RuntimeError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value is boom


# ── T060 · 条件边字段恒空（SC-025）──────────────────────────────────────


def test_a_non_empty_conditional_edges_field_fails_explicitly() -> None:
    """**SC-025**：「条件边」字段**非空** ⇒ **显式失败**（内置 ``ValueError``）。"""
    with pytest.raises(ValueError):
        GraphSpec(
            channels=_plain_channels(),
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
            conditional_edges={"reader": ("other",)},
        )


def test_the_delivered_specs_keep_the_conditional_edges_field_empty() -> None:
    """**SC-025**：本 feature 交付的规格中该字段**恒空**（非空的用例数 == 0）。"""
    spec = GraphSpec(
        channels=_plain_channels(),
        nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
        edges={},
    )

    assert spec.conditional_edges == {}


# ── T063 · 初始化写入豁免的两条边界（SC-003）────────────────────────────


def test_a_value_written_before_the_run_triggers_its_subscriber() -> None:
    """**SC-003**：跑**之前**由调用方直接写通道对象 ⇒ 订阅者**被触发**（版本 == 1）。"""
    channels = _plain_channels()
    executed: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("writer")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )
    state = SchedulerState()

    channels["count"].update([1])
    result = run_super_step(spec, state)

    assert executed == ["writer"]
    assert result.executed == ("writer",)
    assert state.channel_versions["count"] == 1


def test_a_value_written_after_the_run_triggers_nothing() -> None:
    """**SC-003**：跑**之后**再直接往通道塞值 ⇒ 调度器**看不见** ⇒ 不触发任何节点。

    ⚠️ 用**同一个**调度状态续跑（裁定 31：「跑之后」的直接写入 MUST NOT 成为
    触发依据）。
    """
    channels = _plain_channels()
    executed: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("writer")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("count",), run=node)},
        edges={},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    assert executed == []
    assert first.executed == ()

    channels["count"].update([1])
    second = run_super_step(spec, state)

    assert executed == []
    assert second.executed == ()


# ── T065 · 通道映射是可变映射（SC-015）──────────────────────────────────


def test_the_channel_mapping_can_be_augmented_after_construction() -> None:
    """**SC-015**：`GraphSpec.channels` 是**可变**映射 ⇒ 可**增补**内部通道。

    ① 增补**不抛错**；② 增补后的通道**参与步末清空范围判定**（路由型 ⇒ 步末被清）；
    ③ 增补后的通道**能被调度器看见**。
    """
    channels = _plain_channels()
    channels["count"].update([1])
    spec = GraphSpec(
        channels=channels,
        nodes={"reader": NodeSpec(subscribes=("count",), run=lambda state: {})},
        edges={},
    )

    spec.channels["route"] = EphemeralValue("route", str)
    spec.channels["route"].update(["payload"])

    assert "route" in spec.channels

    result = run_super_step(spec, SchedulerState())

    assert "route" not in result.state
    assert spec.channels["route"].is_available() is False
