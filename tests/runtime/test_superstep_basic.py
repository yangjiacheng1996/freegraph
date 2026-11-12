# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**单 super-step 跑通**的用例 —— 属 **B7F1**（tasks T018 / T019 / T020 / T021）。

覆盖的判定：

* **SC-001** —— 手写图规格跑**一轮** super-step 后状态变更完全符合预期；
  五阶段产物（**执行记录** / **待写入** / **合并后状态** / **轮数**）**逐项可观测**；
* **SC-004** —— **无入边**的节点执行次数 == **0**；
* **SC-009 / SC-013** —— 节点入参是**普通 `dict`**且只含「订阅集 ∩ 有值集」；
* **SC-015** —— 图规格校验与返回值校验的**四条显式失败路径**（校验规则 **V-1…V-4**）；
* **SC-020** —— 节点异常**原样**传播；
* **SC-025** —— 「条件边」字段**恒空**；非空即**显式失败**。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：触发源**恒为边**（上游 ``branch:to:<node>``
· ``langgraph/graph/state.py:1531-1532``）⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点",)}` · 上游 ``add_edge(START, "a")``）⇒
``subscribes`` **只**决定「读哪些通道」（上游 ``langgraph/graph/state.py:1534``），
**不再**是触发源。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import operator
from typing import Any

import pytest

from freegraph.runtime.channel import MISSING
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


#: **入口哨兵节点**（上游 ``START`` 同款 · ``langgraph/constants.py:30``）。
#:
#: ⚠️ 它**无入边** ⇒ **永不执行**（永不进 ``executed``）⇒ 它只作「入口边」的**源**。
#:
#: ⚠️ **为什么它 MUST 在节点表里** —— ``GraphSpec`` 的校验规则 **V-2** 要求
#: 「边的**源** MUST 在节点表里」⇒ 入口边 ``edges={"__start__": ("首节点",)}``
#: 的源 ``__start__`` 也 MUST 在节点表里（上游的 ``START`` 是**编译期**补进去的
#: 伪节点 · ``langgraph/graph/state.py:321`` ⇒ freegraph 在**手写图规格**层面
#: 用「节点表里的一个哨兵节点」表达**同款**语义）。
_ENTRY = NodeSpec(subscribes=(), run=lambda state: {})


class _ProbeChannel(Channel):
    """**探针通道** —— 记录 ``update`` / ``clear`` 的调用次数。

    ⚠️ 只**观察**、**不改变**语义（委托给内部通道）⇒ 用例可以用它断言
    「执行期间通道的**正式值**被改写的次数 == 0」（SC-008）。
    """


    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（**上游同款** · ``langgraph/channels/base.py:60-65``
        的 ``from_checkpoint`` 是**抽象方法** ⇒ 第三方自定义通道**必须**自己实现）。

        ⚠️ 本夹具的构造签名带第三个参数（``inner``）⇒ 子类的 ``from_checkpoint``
        MUST 与其**构造签名自洽**（上游同款约束）。"""
        empty = type(self)(self._key, self._value_type, self._inner)
        if checkpoint is not MISSING:
            empty._value = checkpoint
        return empty
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


def test_an_entry_node_runs_exactly_once_and_the_state_merges() -> None:
    """**SC-001**：**入口边**指向的节点执行**恰好一次**；合并后状态符合预期。

    ⚠️ 触发源**恒为边**（上游同款）⇒ 本用例的节点由**入口边**
    （``edges={"__start__": ("writer",)}``）触发 ⇒ 它**恰好**在**第 1 轮**执行一次。

    ⚠️ 初始值由**调用方在跑之前**直接写通道对象（**初始化写入豁免** · 裁定 31）
    ⇒ 该值是**入参**（读得到），**不**是触发依据。
    """
    channels = _reducer_channels()
    channels["messages"].update([["seed"]])
    calls: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(state)
        return {"messages": ["written"], "count": 7}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("messages",), run=node),
        },
        edges={"__start__": ("writer",)},
    )

    result = run_super_step(spec, SchedulerState())

    assert len(calls) == 1
    assert result.executed == ("writer",)
    assert result.state["messages"] == ["seed", "written"]
    assert result.state["count"] == 7


def test_a_node_without_an_incoming_edge_does_not_run() -> None:
    """**SC-004**：**无入边**的节点执行次数 == **0**（上游同款）。

    ⚠️ 触发源**恒为边**（上游 ``branch:to:<node>``）⇒ 「订阅了某个通道」
    **不是**触发依据 ⇒ 没有入边 ⇒ ``sources(N)`` 为空 ⇒ **永不**执行。

    ⚠️ 图里另有一个**入口节点**（由**入口边**触发）⇒ 图确实「跑起来了」⇒
    被断言的「无入边」节点**一次都没跑**（不是「整张图都没跑」的空洞断言）。
    """
    channels = _plain_channels()
    calls: list[dict[str, Any]] = []
    executed: list[str] = []

    def entry(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("entry")
        return {}

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(state)
        return {"count": 1}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "entry": NodeSpec(subscribes=(), run=entry),
            "writer": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("entry",)},
    )

    result = run_super_step(spec, SchedulerState())

    assert calls == []
    assert executed == ["entry"]
    assert result.executed == ("entry",)
    assert result.state == {}


def test_a_subscriber_without_an_incoming_edge_never_runs() -> None:
    """**SC-004** · **上游同款**：**订阅了有值通道**却**无入边**的节点 ⇒ **永不执行**。

    ⚠️ 这是「纯边触发」与旧「通道触发」的可观察分界：节点 ``reader`` **订阅**了
    通道 ``log``，而 ``log`` 在第 1 轮里被 ``writer`` 写出了值 ⇒ 旧模型会执行
    ``reader``（并自触发循环）⇒ **纯边触发**下 ``reader`` **无入边** ⇒
    ``ran == ["writer"]``（上游 ``langgraph`` 的**同款**结果）。
    """
    channels = _plain_channels()
    channels["log"] = LastValue("log", str)
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("writer")
        return {"log": "written"}

    def reader(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("reader")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=writer),
            "reader": NodeSpec(subscribes=("log",), run=reader),
        },
        edges={"__start__": ("writer",)},
    )

    result = run_super_steps(spec)

    assert executed == ["writer"]
    assert result.executed == ("writer",)
    assert result.state["log"] == "written"


def test_a_node_updates_only_the_keys_it_returns() -> None:
    """**SC-001**：节点返回的**部分状态**只更新返回的 key（未返回的保持不变）。"""
    channels = _plain_channels()
    channels["count"].update([3])
    channels["other"].update(["kept"])

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=lambda state: {"count": 4}),
        },
        edges={"__start__": ("writer",)},
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
            "__start__": _ENTRY,
            "source": NodeSpec(subscribes=("count",), run=source),
            "target": NodeSpec(subscribes=("other",), run=target),
        },
        edges={"__start__": ("source",), "source": ("target",)},
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
            "__start__": _ENTRY,
            "writer": NodeSpec(
                subscribes=("messages",), run=lambda state: {"messages": ["more"]}
            ),
        },
        edges={"__start__": ("writer",)},
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
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("count", "other"), run=node),
        },
        edges={"__start__": ("reader",)},
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
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("other", "count"), run=node),
        },
        edges={"__start__": ("reader",)},
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
    """**V-4**：节点返回值**不是 `dict`** ⇒ 运行期抛内置 ``TypeError``。

    ⚠️ **2026-11-12 上游对齐 P3**：``None`` **已合法**（**无写入**）⇒ 非法样例里去掉它。
    """
    channels = _plain_channels()
    channels["count"].update([1])

    for bad in (42, "text", ["not", "a", "dict"]):
        spec = GraphSpec(
            channels=channels,
            nodes={
                "__start__": _ENTRY,
                "writer": NodeSpec(subscribes=("count",), run=lambda state: bad),
            },
            edges={"__start__": ("writer",)},
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
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("count",), run=reader),
            "writer": NodeSpec(subscribes=("count",), run=writer),
        },
        edges={"__start__": ("reader", "writer")},
    )

    state = SchedulerState()
    result = run_super_step(spec, state)

    assert seen == [1, 0]
    # ⚠️ 观测**本次运行**的通道实例（上游同款 · P2-b）⇒ 而非图规格里的**模板**
    assert state.channels["count"].get() == 99
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
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("writer",)},
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


def test_a_value_written_before_the_run_is_visible_to_the_entry_node() -> None:
    """**SC-003**：跑**之前**由调用方直接写通道对象 ⇒ 入口节点**读得到**该初始值。

    ⚠️ **上游同款**：触发源**恒为边** ⇒ 跑之前的直接写入**不是**触发依据
    （旧口径的「有值即版本 1 ⇒ 订阅者被触发」**已删除**）⇒ 节点**只**由**入口边**
    触发；该直接写入**不进**版本推进路径（裁定 31）⇒ 该通道的写入版本仍为
    **基值 0**。
    """
    channels = _plain_channels()
    executed: list[str] = []
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("writer")
        captured.append(dict(state))
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("writer",)},
    )
    state = SchedulerState()

    channels["count"].update([1])
    result = run_super_step(spec, state)

    assert executed == ["writer"]
    assert result.executed == ("writer",)
    assert captured[0] == {"count": 1}
    # 跑之前的直接写入**不进**版本推进路径 ⇒ 该通道的写入版本仍为**基值 0**。
    assert state.channel_versions.get("count", 0) == 0


def test_a_value_written_after_the_run_triggers_nothing() -> None:
    """**SC-003**：跑**之后**再直接往通道塞值 ⇒ 调度器**看不见** ⇒ 不触发任何节点。

    ⚠️ 用**同一个**调度状态续跑（裁定 31：「跑之后」的直接写入 MUST NOT 成为
    触发依据）⇒ 入口哨兵的版本**恒为 1** ⇒ 第 2 轮**无**节点被触发。
    """
    channels = _plain_channels()
    executed: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("writer")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("writer",)},
    )
    state = SchedulerState()

    first = run_super_step(spec, state)
    assert executed == ["writer"]
    assert first.executed == ("writer",)

    channels["count"].update([1])
    second = run_super_step(spec, state)

    assert executed == ["writer"]
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
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("count",), run=lambda state: {}),
        },
        edges={"__start__": ("reader",)},
    )

    spec.channels["route"] = EphemeralValue("route", str)
    spec.channels["route"].update(["payload"])

    assert "route" in spec.channels

    state = SchedulerState()
    result = run_super_step(spec, state)

    assert "route" not in result.state
    # ⚠️ 观测**本次运行**的通道实例（上游同款 · P2-b）
    assert state.channels["route"].is_available() is False
