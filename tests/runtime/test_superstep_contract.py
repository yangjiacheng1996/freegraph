# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**调度契约**的守卫测试 —— 属 **B7F1**（tasks T045）。

**契约权威**：``specs/b7f1-superstep-loop/contracts/superstep-contract.md``
（``<!-- authority: yes -->``）⇒ 本文件 MUST **解析**该契约并**逐条**断言
§7 的 **I-1…I-15**（MUST NOT 只测行为而不校验契约文本）。

**逐条绑定**的机制（防「判据与实现同源 ⇒ 自证」）：

* **契约文本**是「**有哪些不变量**」的**唯一权威** ⇒ 本文件**解析** §7 的
  不变量编号集合；
* **编号 → 断言**的绑定写在 ``INVARIANT_TESTS`` 里 ⇒ 每条不变量**恰好**对应
  一个**真实断言**的测试函数；
* 参数化的守卫用例断言「**契约里的每条不变量都有绑定**」且「**每条绑定都
  指向一个真实存在的测试函数**」⇒ 契约新增一条不变量而没人断言 ⇒ **变红**。

⚠️ **2026-11-12 · 上游对齐（P1-0-2）**：契约 §3 已整节重写为「**纯边触发** +
``__start__`` 入口」⇒ 本文件的夹具一律带**入口边**
（``edges={"__start__": ("首节点",)}``）⇒ ``subscribes`` **只**决定「读哪些通道」
⇒ **I-3 / I-4** 的措辞已与契约同步（**边触发源**口径 / **无入边**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import operator
import re
from pathlib import Path
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
    run_super_step,
)

#: 仓库根目录（契约文件的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **调度契约**的唯一权威文件（``<!-- authority: yes -->``）。
SUPERSTEP_CONTRACT_PATH = (
    REPO_ROOT
    / "specs"
    / "b7f1-superstep-loop"
    / "contracts"
    / "superstep-contract.md"
)

#: 契约 §7 冻结的**不变量编号集合**（**逐条** · I-1…I-15）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 17))

#: **编号 → 断言**的绑定表（每条不变量**恰好**一个**真实断言**的测试函数）。
INVARIANT_TESTS: dict[str, str] = {
    "I-1": "test_i1_node_input_is_a_plain_dict_with_only_the_available_subscriptions",
    "I-2": "test_i2_node_input_equals_the_sparse_read_of_the_sub_mapping",
    "I-3": "test_i3_the_same_version_never_triggers_the_same_node_twice",
    "I-4": "test_i4_an_untriggered_node_never_runs",
    "I-5": "test_i5_two_nodes_writing_the_reducing_channel_are_concatenated",
    "I-6": "test_i6_two_nodes_writing_the_overwriting_channel_fail_explicitly",
    "I-7": "test_i7_an_unknown_key_fails_explicitly_with_all_unknown_keys",
    "I-8": "test_i8_the_official_value_is_not_rewritten_during_execution",
    "I-9": "test_i9_a_failed_round_leaves_every_channel_unchanged",
    "I-10": "test_i10_only_unwritten_routing_channels_are_cleared",
    "I-11": "test_i11_repeating_the_same_spec_yields_equal_results",
    "I-12": "test_i12_the_report_order_follows_the_node_name_order",
    "I-13": "test_i13_two_independent_scheduler_states_give_equal_results",
    "I-14": "test_i14_a_non_empty_conditional_edges_field_fails_explicitly",
    "I-15": "test_i15_a_node_exception_propagates_as_the_very_same_object",
    "I-16": "test_i16_the_same_spec_runs_concurrently_without_interference",
}


# ── 契约解析（**唯一权威** = 契约文本）────────────────────────────────────


def _contract_text() -> str:
    """读取调度契约权威文件的全文。"""
    return SUPERSTEP_CONTRACT_PATH.read_text(encoding="utf-8")


def _table_cells(line: str) -> list[str]:
    """把一行 Markdown 表格拆成单元格（去首尾空单元格 · 去空白）。"""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = stripped.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [cell.strip() for cell in parts]


def _is_separator(cells: list[str]) -> bool:
    """判定是否表格的**分隔行**。"""
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _section_body(text: str, heading: str) -> list[str]:
    """取出某个 ``## `` 小节的正文行（**不含**小节标题本身）。"""
    collected: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(heading)
            continue
        if inside:
            collected.append(line)
    return collected


def _contract_invariants() -> list[str]:
    """**解析**契约 §7 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(_contract_text(), "## 7."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


# ── 守卫 · 契约与绑定**双向齐全**（防「新增不变量而没人断言」）──────────


def test_the_contract_declares_exactly_the_expected_invariants() -> None:
    """契约 §7 的不变量编号集合 == 期望集合（**逐条** · I-1…I-15）。"""
    assert _contract_invariants() == list(EXPECTED_INVARIANTS)


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_contract_invariant_has_a_binding(invariant: str) -> None:
    """契约里的**每条**不变量都有**编号 → 断言**的绑定。"""
    assert invariant in INVARIANT_TESTS


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_binding_points_to_a_real_test_function(invariant: str) -> None:
    """**每条**绑定都指向一个**真实存在**的测试函数。"""
    name = INVARIANT_TESTS[invariant]
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert name in functions


# ── 共享夹具 ────────────────────────────────────────────────────────────


def _channels() -> dict[str, Channel]:
    """构造通道状态：**覆盖型** + **归约型** + **路由型**。"""
    return {
        "count": LastValue("count", int),
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "route": EphemeralValue("route", str),
    }


class _CountingEphemeral(EphemeralValue):
    """**计数路由型**通道（``isinstance(channel, EphemeralValue)`` 仍成立）。"""

    def __init__(self, key: str, value_type: Any, guard: bool = True) -> None:
        super().__init__(key, value_type, guard)
        self.clear_calls = 0

    def clear(self) -> bool:
        self.clear_calls += 1
        return super().clear()

    def update(self, values):  # type: ignore[no-untyped-def]
        """计入「**空序列**写入」—— 上游同款的**步末清空**口径。"""
        if not values:
            self.clear_calls += 1
        return super().update(values)


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


# ── I-1 · 节点入参是普通 dict 且只含「订阅集 ∩ 有值集」───────────────────


def test_i1_node_input_is_a_plain_dict_with_only_the_available_subscriptions() -> None:
    """**I-1**：入参 MUST 是**普通 `dict`**且只含「订阅集 ∩ 有值集」。"""
    channels = _channels()
    channels["count"].update([3])
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("count", "messages"), run=node),
        },
        edges={"__start__": ("reader",)},
    )

    run_super_step(spec, SchedulerState())

    node_input = captured[0]
    assert type(node_input) is dict
    assert set(node_input) == {"count", "messages"}


# ── I-2 · 入参由 B5F2 的稀疏读产出（子映射按通道映射顺序）───────────────


def test_i2_node_input_equals_the_sparse_read_of_the_sub_mapping() -> None:
    """**I-2**：入参 MUST 等于 ``read_channels(子映射)`` 的结果（**逐字相等**）。"""
    from freegraph.runtime import read_channels

    channels = _channels()
    channels["count"].update([3])
    captured: list[dict[str, Any]] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("messages", "count"), run=node),
        },
        edges={"__start__": ("reader",)},
    )

    run_super_step(spec, SchedulerState())

    sub_mapping = {
        key: channel
        for key, channel in channels.items()
        if key in ("messages", "count")
    }
    expected = read_channels(sub_mapping)
    node_input = captured[0]
    assert list(node_input) == list(expected)
    for key, value in expected.items():
        assert node_input[key] is value


# ── I-3 · 同一版本不重复触发同一节点 ────────────────────────────────────


def test_i3_the_same_version_never_triggers_the_same_node_twice() -> None:
    """**I-3**：同一版本 MUST NOT 重复触发同一节点（**边触发源**口径 · 契约 §3）。

    ⚠️ **上游同款**：入口哨兵的版本**恒为 1** ⇒ 入口节点**只在第 1 轮**被触发
    一次 ⇒ 第 2 轮**不**重复触发。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("node",)},
    )
    state = SchedulerState()

    run_super_step(spec, state)
    run_super_step(spec, state)

    assert calls == ["node"]


# ── I-4 · 未被触发的节点执行次数 == 0 ───────────────────────────────────


def test_i4_an_untriggered_node_never_runs() -> None:
    """**I-4**：**无入边**（且非入口节点）的节点执行次数 == **0**。

    ⚠️ **上游同款**：触发源**恒为边** ⇒ 该节点**订阅了有值通道**却**无入边**
    ⇒ ``sources(N)`` 为空 ⇒ **永不**执行。
    """
    channels = _channels()
    channels["count"].update([1])
    calls: list[str] = []

    def node(state: dict[str, Any]) -> dict[str, Any]:
        calls.append("node")
        return {}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count",), run=node),
        },
        edges={},
    )

    result = run_super_step(spec, SchedulerState())

    assert calls == []
    assert result.executed == ()


# ── I-5 · 同轮双写归约通道 == 两次写入的归约结果 ───────────────────────


def test_i5_two_nodes_writing_the_reducing_channel_are_concatenated() -> None:
    """**I-5**：同轮双写归约通道 ⇒ 结果 == 两次写入的**归约结果**。"""
    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(
                subscribes=("count",), run=lambda state: {"messages": ["a"]}
            ),
            "b": NodeSpec(
                subscribes=("count",), run=lambda state: {"messages": ["b"]}
            ),
        },
        edges={"__start__": ("a", "b")},
    )

    result = run_super_step(spec, SchedulerState())

    assert result.state["messages"] == operator.add(["a"], ["b"])


# ── I-6 · 同轮双写覆盖型 ⇒ 显式失败 ─────────────────────────────────────


def test_i6_two_nodes_writing_the_overwriting_channel_fail_explicitly() -> None:
    """**I-6**：同轮双写**覆盖型**通道 ⇒ **显式失败**。"""
    from freegraph.runtime import InvalidChannelUpdateError

    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(subscribes=("count",), run=lambda state: {"count": 1}),
            "b": NodeSpec(subscribes=("count",), run=lambda state: {"count": 2}),
        },
        edges={"__start__": ("a", "b")},
    )

    with pytest.raises(InvalidChannelUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value.key == "count"


# ── I-7 · 未知 key ⇒ 显式失败且 invalid_keys 完整 ───────────────────────


def test_i7_an_unknown_key_fails_explicitly_with_all_unknown_keys() -> None:
    """**I-7**：未知 key ⇒ **显式失败**且 ``invalid_keys`` == **实际未知 key 集合**。"""
    from freegraph.contracts import InvalidUpdateError

    channels = _channels()
    channels["count"].update([0])
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(
                subscribes=("count",),
                run=lambda state: {"count": 1, "ghost_a": 2, "ghost_b": 3},
            ),
        },
        edges={"__start__": ("a",)},
    )

    with pytest.raises(InvalidUpdateError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert set(excinfo.value.invalid_keys) == {"ghost_a", "ghost_b"}


# ── I-8 · 执行期间通道的正式值不被改写 ─────────────────────────────────


def test_i8_the_official_value_is_not_rewritten_during_execution() -> None:
    """**I-8**：执行期间通道的**正式值** MUST NOT 被改写。"""
    channels = _channels()
    channels["count"].update([1])
    seen: list[Any] = []

    def reader(state: dict[str, Any]) -> dict[str, Any]:
        seen.append(channels["count"].get())
        return {}

    def writer(state: dict[str, Any]) -> dict[str, Any]:
        return {"count": 99}

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "reader": NodeSpec(subscribes=("count",), run=reader),
            "writer": NodeSpec(subscribes=("count",), run=writer),
        },
        edges={"__start__": ("reader", "writer")},
    )

    run_super_step(spec, SchedulerState())

    assert seen == [1]


# ── I-9 · 一轮出错 ⇒ 全部通道的值与本轮开始前逐字相等 ──────────────────


def test_i9_a_failed_round_leaves_every_channel_unchanged() -> None:
    """**I-9**：一轮出错 ⇒ **全部**通道的值与**本轮开始前**逐字相等。"""
    from freegraph.runtime import InvalidChannelUpdateError

    channels = _channels()
    channels["count"].update([1])
    before = {
        key: (channel.get() if channel.is_available() else None)
        for key, channel in channels.items()
    }

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "a": NodeSpec(subscribes=("count",), run=lambda state: {"count": 1}),
            "b": NodeSpec(subscribes=("count",), run=lambda state: {"count": 2}),
        },
        edges={"__start__": ("a", "b")},
    )

    with pytest.raises(InvalidChannelUpdateError):
        run_super_step(spec, SchedulerState())

    after = {
        key: (channel.get() if channel.is_available() else None)
        for key, channel in channels.items()
    }
    assert after == before


# ── I-10 · 步末只清「本轮未被写入的」路由型通道 ───────────────────────


def test_i10_only_unwritten_routing_channels_are_cleared() -> None:
    """**I-10**：步末 MUST NOT 清「本轮写过的」路由型通道；MUST 清「未写的」。

    ⚠️ **2026-11-12 · 上游对齐 P2-a**：步末清空的**机制**改为上游同款的
    ``update(EMPTY_SEQ)``（上游 ``langgraph/pregel/_algo.py:326-333``）⇒ 计数口径
    改为「**空序列**写入」的次数；且**只有**「仍有值」的通道会被通知
    （上游同款：``if channels[chan].is_available() and chan not in updated_channels``）
    ⇒ **无值**的路由通道**不**产生调用（**可观察状态**一致：空 ⇒ 空）。
    """
    channels = _channels()
    route = _CountingEphemeral("route", str)
    channels["route"] = route
    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "writer": NodeSpec(
                subscribes=("count",), run=lambda state: {"count": 1}
            ),
        },
        edges={"__start__": ("writer",)},
    )
    channels["count"].update([1])

    state = SchedulerState()
    run_super_step(spec, state)

    # ⚠️ 观测**本次运行**的通道实例（上游同款 · P2-b）
    run_route = state.channels["route"]
    # 路由通道**无值** ⇒ 上游口径下**不**被通知（调用次数 == 0）
    assert run_route.clear_calls == 0

    # **模板**带上值 ⇒ **新建的运行期实例**继承它 ⇒ 本轮**未**写入 ⇒ 被通知一次（**清空**）
    route.update(["x"])
    state2 = SchedulerState()
    run_super_step(spec, state2)
    assert state2.channels["route"].clear_calls == 1
    assert state2.channels["route"].is_available() is False


# ── I-11 · 重复执行 ⇒ 状态与执行序列逐项相等 ───────────────────────────


def test_i11_repeating_the_same_spec_yields_equal_results() -> None:
    """**I-11**：重复执行 ⇒ 合并后状态与执行序列**逐项相等**。"""
    results = []
    for _ in range(3):
        channels = _channels()
        channels["count"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={
                "__start__": _ENTRY,
                "node": NodeSpec(subscribes=("count",), run=lambda state: {}),
            },
            edges={"__start__": ("node",)},
        )
        result = run_super_step(spec, SchedulerState())
        results.append((result.state, result.executed))

    assert results[0] == results[1] == results[2]


# ── I-12 · 节点表顺序 == 执行顺序 ───────────────────────────────────────


def test_i12_the_report_order_follows_the_node_name_order() -> None:
    """**I-12**：**报告顺序** MUST == **节点名序**（**上游同款** · `_algo.py:482`）。

    ⚠️ **2026-11-13 · B12F1 回溯修订 T-8**：原措辞「执行顺序 MUST == **节点表顺序**」⇒
    ① **P2-c** 已把口径改为**节点名序**；② **并发**下「**执行**的时间先后」**不确定**
    ⇒ ⇒ 本条只承诺「**报告**顺序（`executed` 的口径）」⇒ ⇒ **执行时序 MUST NOT**
    作为任何可观察顺序的判据（**拆分而不删** · 顺序承诺本身不撤销）。
    """
    def make(name: str) -> Any:
        def run(state: dict[str, Any]) -> dict[str, Any]:
            return {}

        return run

    def build(order: tuple[str, ...]) -> tuple[str, ...]:
        channels = _channels()
        channels["count"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={
                "__start__": _ENTRY,
                **{
                    name: NodeSpec(subscribes=("count",), run=make(name))
                    for name in order
                },
            },
            edges={"__start__": order},
        )
        return run_super_step(spec, SchedulerState()).executed

    # ⚠️ **上游同款**（2026-11-12 P2-c）：执行顺序 = **节点名序**
    # （上游 ``langgraph/pregel/_algo.py:482``）⇒ **重排节点表不改变**执行序列
    assert build(("zeta", "alpha")) == ("alpha", "zeta")
    assert build(("alpha", "zeta")) == ("alpha", "zeta")


# ── I-13 · 同一份规格可安全跑两次 ──────────────────────────────────────


def test_i13_two_independent_scheduler_states_give_equal_results() -> None:
    """**I-13**：同一份规格可**安全跑两次**（调度状态由调用方持有）。"""
    def build() -> Any:
        channels = _channels()
        channels["count"].update([1])
        spec = GraphSpec(
            channels=channels,
            nodes={
                "__start__": _ENTRY,
                "node": NodeSpec(subscribes=("count",), run=lambda state: {}),
            },
            edges={"__start__": ("node",)},
        )
        return run_super_step(spec, SchedulerState())

    assert build().state == build().state
    assert build().executed == build().executed


# ── I-14 · 「条件边」字段恒空；非空即失败 ──────────────────────────────


def test_i14_a_non_empty_conditional_edges_field_fails_explicitly() -> None:
    """**I-14**：「条件边」字段 MUST **恒为空**；非空 ⇒ **显式失败**。"""
    with pytest.raises(ValueError):
        GraphSpec(
            channels=_channels(),
            nodes={"reader": NodeSpec(subscribes=(), run=lambda state: {})},
            edges={},
            conditional_edges={"reader": ("other",)},
        )


# ── I-15 · 节点异常原样传播 ────────────────────────────────────────────


def test_i15_a_node_exception_propagates_as_the_very_same_object() -> None:
    """**I-15**：节点异常 MUST **原样**传播（异常对象 ``is`` 同一）。"""
    channels = _channels()
    channels["count"].update([1])
    boom = RuntimeError("boom")

    def node(state: dict[str, Any]) -> dict[str, Any]:
        raise boom

    spec = GraphSpec(
        channels=channels,
        nodes={
            "__start__": _ENTRY,
            "node": NodeSpec(subscribes=("count",), run=node),
        },
        edges={"__start__": ("node",)},
    )

    with pytest.raises(RuntimeError) as excinfo:
        run_super_step(spec, SchedulerState())

    assert excinfo.value is boom


# ── I-16 · 运行期的通道值住在调度状态里（上游同款 · 多会话隔离）──────────────


def test_i16_the_same_spec_runs_concurrently_without_interference() -> None:
    """**I-16**：**运行期的通道值** MUST 住在**调度状态**的 ``channels`` 里 ⇒
    **同一份图规格可并发跑多次而互不干扰**（**上游同款** · P2-b）。

    ⚠️ **P2-b 之前**通道值住在**图规格**里 ⇒ 第二次运行会**累积**上次的值
    （审计的 **X-6**）⇒ 本用例是该缺陷的**回归防线**。
    """
    import threading

    def build() -> Any:
        seed = LastValue("seed", int)
        seed.update([1])
        acc = BinaryOperatorAggregate("acc", list, operator.add)
        spec = GraphSpec(
            channels={"seed": seed, "acc": acc},
            nodes={
                "__start__": _ENTRY,
                "writer": NodeSpec(
                    subscribes=("seed",), run=lambda s: {"acc": ["written"]}
                ),
            },
            edges={"__start__": ("writer",)},
        )
        return spec

    # ① 连续两次（两个独立调度状态）⇒ 互不累积
    spec = build()
    first = run_super_step(spec, SchedulerState())
    second = run_super_step(spec, SchedulerState())
    assert first.state["acc"] == ["written"]
    assert second.state["acc"] == ["written"]

    # ② 并发两次 ⇒ 互不干扰
    spec = build()
    outcomes: dict[str, Any] = {}

    def run(tag: str) -> None:
        outcomes[tag] = run_super_step(spec, SchedulerState()).state

    threads = [threading.Thread(target=run, args=(tag,)) for tag in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes["A"]["acc"] == ["written"]
    assert outcomes["B"]["acc"] == ["written"]

    # ③ **模板**不被运行期改写 ⇒ 图规格可反复复用
    assert spec.channels["acc"].get() == []
