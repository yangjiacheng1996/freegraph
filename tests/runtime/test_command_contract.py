# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**契约守卫**的用例 —— 属 **B9F1**（tasks T031）。

⚠️ **触发模型**（上游对齐 · 2026-11-12）：触发源**恒为边**（上游
``branch:to:<node>`` · ``langgraph/graph/state.py:1531-1532``）⇒ ``subscribes``
只决定「读哪些通道」（上游 ``:1534``）⇒ 每张图 MUST 有**入口边**
``{"__start__": (首节点,)}``（上游 ``add_edge(START, "a")`` 的同款写法）。

**契约权威**：``specs/b9f1-command-primitive/contracts/command-contract.md``
（``<!-- authority: yes -->``）⇒ 本文件 MUST **解析**该契约并**逐条**断言
§9 的 **I-1…I-14**（MUST NOT 只测行为而不校验契约文本）。

**逐条绑定**的机制（防「判据与实现**同源即自证**」）：

* **契约文本**是「**有哪些不变量**」的**唯一权威** ⇒ 本文件**解析** §9 的
  不变量编号集合；
* **编号 → 断言**的绑定写在 ``INVARIANT_TESTS`` 里 ⇒ 每条不变量**恰好**对应
  一个**真实断言**的测试函数；
* 参数化的守卫用例断言「**契约里的每条不变量都有绑定**」且「**每条绑定都
  指向一个真实存在的测试函数**」⇒ 契约新增一条不变量而没人断言 ⇒ **变红**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import operator
import re
from pathlib import Path
from typing import Any

import pytest

from freegraph.contracts import Command
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

#: 仓库根目录（契约文件的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **命令契约**的唯一权威文件（``<!-- authority: yes -->``）。
COMMAND_CONTRACT_PATH = (
    REPO_ROOT
    / "specs"
    / "b9f1-command-primitive"
    / "contracts"
    / "command-contract.md"
)

#: 契约 §9 冻结的**不变量编号集合**（**逐条** · I-1…I-14）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 15))

#: **编号 → 断言**的绑定表（每条不变量**恰好**一个**真实断言**）。
INVARIANT_TESTS: dict[str, str] = {
    "I-1": "test_i1_only_three_return_forms_are_accepted",
    "I-2": "test_i2_the_three_forms_share_one_merge_path",
    "I-3": "test_i3_the_command_update_is_attributed_to_the_source_node",
    "I-4": "test_i4_the_list_writes_are_merged_in_list_order",
    "I-5": "test_i5_every_list_goto_becomes_its_own_edge",
    "I-6": "test_i6_the_dynamic_edges_are_replaced_wholesale",
    "I-7": "test_i7_the_target_is_triggered_only_in_the_next_round",
    "I-8": "test_i8_the_target_runs_without_any_valued_channel",
    "I-9": "test_i9_the_target_input_equals_the_sparse_read",
    "I-10": "test_i10_the_target_reads_the_source_update",
    "I-11": "test_i11_the_dynamic_and_static_edges_are_superposed",
    "I-12": "test_i12_end_neither_jumps_nor_terminates",
    "I-13": "test_i13_the_empty_slots_and_lists_are_no_ops",
    "I-14": "test_i14_the_result_object_has_exactly_four_fields",
}


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
    return [part.strip() for part in parts]


def _is_separator(cells: list[str]) -> bool:
    """判定是否表格的**分隔行**。"""
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _contract_invariants() -> list[str]:
    """**解析**命令契约 §9 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(
        COMMAND_CONTRACT_PATH.read_text(encoding="utf-8"), "## 9."
    ):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


def _channels() -> dict[str, Channel]:
    """构造通道状态：归约型（``messages``）+ 覆盖型（``count`` / ``seed``）。

    ⚠️ ``seed`` 的**初值**只作**入参**（``subscribes`` 只决定「读哪些通道」·
    上游 ``langgraph/graph/state.py:1534``）⇒ **不再**是触发源。
    """
    return {
        "messages": BinaryOperatorAggregate("messages", list, operator.add),
        "count": LastValue("count", int),
        "seed": LastValue("seed", int),
    }


#: **入口哨兵**（上游 ``START`` 的值 · ``langgraph/constants.py:30``）——
#: 触发源**恒为边**（上游 ``branch:to:<node>`` · ``langgraph/graph/state.py:1531``）
#: ⇒ 每张图 MUST 有**入口边** ``{"__start__": (首节点,)}``（上游
#: ``add_edge(START, "a")`` 的同款写法 · ``langgraph/graph/state.py:321``）。
_START = "__start__"


def _never(state: dict[str, Any]) -> dict[str, Any]:
    """**入口哨兵**的节点函数 —— 恒**不被调用**（哨兵无入边 ⇒ 永不被触发）。"""
    raise AssertionError("入口哨兵 __start__ 恒不被执行")


#: **入口哨兵节点**（上游 ``START`` **伪节点**）—— 恒**不被执行**。
_SENTINEL = NodeSpec(subscribes=(), run=_never)


def _graph(
    channels: dict[str, Channel],
    nodes: dict[str, NodeSpec],
    edges: dict[str, tuple[str, ...]],
) -> GraphSpec:
    """组装图规格 —— **注入**入口哨兵节点（``edges`` MUST 已含**入口边**）。

    ⚠️ 边的**源** MUST 在节点表里（V-2）⇒ 入口边的**源**（``__start__``）由
    **哨兵节点**承载（上游的 ``START`` 亦是图里的**伪节点**）。
    """
    return GraphSpec(
        channels=channels,
        nodes={_START: _SENTINEL, **nodes},
        edges=edges,
    )


def _run_returning(result: Any) -> Any:
    """跑一个**只返回** ``result`` 的单节点图（靠**入口边**起跑）。"""
    channels = _channels()
    channels["seed"].update([1])
    spec = _graph(
        channels=channels,
        nodes={"writer": NodeSpec(subscribes=("seed",), run=lambda state: result)},
        edges={_START: ("writer",)},
    )
    return run_super_step(spec, SchedulerState())


# ── 守卫用例（契约文本 ↔ 断言的绑定）──────────────────────────────────────


def test_the_contract_declares_exactly_the_expected_invariants() -> None:
    """契约 §9 的不变量编号集合 == **I-1…I-14**（**逐条**）。"""
    assert _contract_invariants() == list(EXPECTED_INVARIANTS)


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_contract_invariant_has_a_bound_assertion(invariant: str) -> None:
    """契约里的每条不变量**都有**一个绑定（守卫用例**真**存在）。"""
    assert invariant in INVARIANT_TESTS


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_binding_points_to_a_real_test_function(invariant: str) -> None:
    """每条绑定都**指向一个真实存在的测试函数**。"""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"), filename=__file__)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert INVARIANT_TESTS[invariant] in functions


# ── I-1…I-14 的**逐条**断言 ───────────────────────────────────────────────


def test_i1_only_three_return_forms_are_accepted() -> None:
    """**I-1**：返回值**只有三种合法形态**（``dict`` / ``Command`` / 列表）。

    ⚠️ **2026-11-12 上游对齐 P3**：**``None`` 也是合法形态**（**无写入**）
    —— 上游 ``langgraph/graph/state.py:1459-1460`` 的 ``if input is None: return None``
    ⇒ 非法形态的样例**换成** ``123``（``None`` 已被上游合法化）。
    """
    for valid in ({"messages": ["x"]}, Command(update={"messages": ["x"]}),
                  [Command(update={"messages": ["x"]})]):
        assert _run_returning(valid).executed == ("writer",)

    with pytest.raises(TypeError):
        _run_returning(123)


def test_a_node_returning_none_is_a_no_op_like_upstream() -> None:
    """**上游同款**：节点返回 ``None`` ⇒ **无写入**（不是错误）。

    ⚠️ **2026-11-12 上游对齐 P3** · 上游 ``langgraph/graph/state.py:1459-1460``。
    """
    result = _run_returning(None)

    assert result.executed == ("writer",)
    assert result.state["messages"] == []
    assert result.node_writes == {"writer": {}}


def test_i2_the_three_forms_share_one_merge_path() -> None:
    """**I-2**：三形态归一后**共用同一条合并路径** ⇒ 结果**逐项相等**。"""
    plain = _run_returning({"messages": ["b"]})
    command = _run_returning(Command(update={"messages": ["b"]}))
    listed = _run_returning([Command(update={"messages": ["b"]})])

    assert plain.state["messages"] == command.state["messages"] == listed.state["messages"]


def test_i3_the_command_update_is_attributed_to_the_source_node() -> None:
    """**I-3**：``Command.update`` 归**源节点**（``node_writes`` 的 key 集合）。"""
    result = _run_returning(Command(update={"messages": ["x"]}))

    assert set(result.node_writes) == {"writer"}


def test_i4_the_list_writes_are_merged_in_list_order() -> None:
    """**I-4**：列表写入**按列表顺序**合并（与「按序逐条写入」逐元素相等）。"""
    result = _run_returning(
        [
            Command(update={"messages": ["first"]}),
            Command(update={"messages": ["second"]}),
        ]
    )

    assert result.state["messages"] == ["first", "second"]


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_i5_every_list_goto_becomes_its_own_edge(max_concurrency: int | None) -> None:
    """**I-5**：列表里每条 ``goto`` **各自成边** ⇒ 全部目标**都**被执行。
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> list[Command]:
        executed.append("writer")
        return [Command(goto="one"), Command(goto="two")]

    def one(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("one")
        return {}

    def two(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("two")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "writer": NodeSpec(subscribes=("seed",), run=writer),
            "one": NodeSpec(subscribes=(), run=one),
            "two": NodeSpec(subscribes=(), run=two),
        },
        edges={_START: ("writer",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["writer", "one", "two"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['one', 'two', 'writer']
        assert len(executed) == 3


def test_i6_the_dynamic_edges_are_replaced_wholesale() -> None:
    """**I-6**：再次执行无 ``goto`` ⇒ 旧目标**不再**被触发（**整体替换**）。

    ⚠️ **上游同款**（上游对齐 · 2026-11-12）：触发源**恒为边** ⇒ 源节点的
    **再次执行**必须由**显式边**驱动（本例：静态边 ``z → x``）⇒ 旧目标被清空
    的证据 = ``z`` 在 ``x`` 的**第二次**执行之后**不再**被触发 ⇒ 执行序列里
    ``z`` **只出现一次**（若动态边**未**被整体替换 ⇒ ``z`` 会**再**被执行一次）。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []
    calls = {"count": 0}

    def writer(state: dict[str, Any]) -> Any:
        calls["count"] += 1
        executed.append(f"x#{calls['count']}")
        if calls["count"] == 1:
            return Command(goto="z", update={"count": 2})
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed", "count"), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",), "z": ("x",)},
    )

    run_super_steps(spec)

    assert executed == ["x#1", "z", "x#2"]


def test_i7_the_target_is_triggered_only_in_the_next_round() -> None:
    """**I-7**：``goto`` 目标**下一轮**才被触发（同轮内**未**被执行）。"""
    channels = _channels()
    channels["seed"].update([1])
    state = SchedulerState()
    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=lambda state: Command(goto="z")),
            "z": NodeSpec(subscribes=(), run=lambda state: {}),
        },
        edges={_START: ("x",)},
    )

    first = run_super_step(spec, state)
    second = run_super_step(spec, state)

    assert first.executed == ("x",)
    assert second.executed == ("z",)


def test_i8_the_target_runs_without_any_valued_channel() -> None:
    """**I-8**：``goto`` 目标**无「有值」门槛**（订阅通道无值仍被执行）。

    ⚠️ **上游同款**：边触发源**没有**「值」概念 ⇒ 判定式**只有**版本比较
    ⇒ 目标**不**因「订阅通道无值」而被挡下。
    """
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    assert captured == [{}]


def test_i9_the_target_input_equals_the_sparse_read() -> None:
    """**I-9**：目标入参 == **正常稀疏读**的结果（与 ``read_channels`` 逐字相等）。"""
    from freegraph.runtime import read_channels

    channels = _channels()
    channels["seed"].update([1])
    channels["count"].update([7])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z")

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count", "messages"), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    sub_mapping = {
        key: channel for key, channel in channels.items() if key in ("count", "messages")
    }
    assert captured[0] == read_channels(sub_mapping)


def test_i10_the_target_reads_the_source_update() -> None:
    """**I-10**：目标**读得到**源节点本次 ``update`` 的内容。"""
    channels = _channels()
    channels["seed"].update([1])
    captured: list[dict[str, Any]] = []

    def writer(state: dict[str, Any]) -> Command:
        return Command(goto="z", update={"count": 5})

    def z(state: dict[str, Any]) -> dict[str, Any]:
        captured.append(state)
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "z": NodeSpec(subscribes=("count",), run=z),
        },
        edges={_START: ("x",)},
    )

    run_super_steps(spec)

    assert captured[0]["count"] == 5


@pytest.mark.parametrize("max_concurrency", [1, None], ids=["serial", "concurrent"])
def test_i11_the_dynamic_and_static_edges_are_superposed(max_concurrency: int | None) -> None:
    """**I-11**：动态边与静态边**叠加**（两个目标**都**被触发）。
    ⚠️ **B12F1（T069）**：本用例断言「用户侧副作用的**同轮完成顺序**」⇒
    并发下该顺序**不再确定** ⇒ **拆分而不删** —— ① **串行模式**
    （``max_concurrency=1``）**保留原逐字顺序断言**（**一条不删**）·
    ② **并发模式**（缺省）断言**顺序无关但有力**的性质
    （**元素多重集相等** + **次数相等**）⇒ **MUST NOT** 写成「跑过了就行」的弱断言。
    """
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="z")

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    def z(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("z")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
            "z": NodeSpec(subscribes=(), run=z),
        },
        edges={_START: ("x",), "x": ("y",)},
    )

    run_super_steps(spec, max_concurrency=max_concurrency)

    if max_concurrency == 1:
        # ⚠️ **串行模式**：**原逐字**顺序断言（**一条不删**）
        assert executed == ["x", "y", "z"]
    else:
        # ⚠️ **并发模式**：**顺序无关**但**有力**（元素多重集相等 + 次数相等）
        assert sorted(executed) == ['x', 'y', 'z']
        assert len(executed) == 3


def test_i12_end_neither_jumps_nor_terminates() -> None:
    """**I-12**：``END`` **不跳转、不终止**（静态边目标仍被执行 + 更新生效）。"""
    channels = _channels()
    channels["seed"].update([1])
    executed: list[str] = []

    def writer(state: dict[str, Any]) -> Command:
        executed.append("x")
        return Command(goto="__end__", update={"messages": ["via-command"]})

    def y(state: dict[str, Any]) -> dict[str, Any]:
        executed.append("y")
        return {}

    spec = _graph(
        channels=channels,
        nodes={
            "x": NodeSpec(subscribes=("seed",), run=writer),
            "y": NodeSpec(subscribes=(), run=y),
        },
        edges={_START: ("x",), "x": ("y",)},
    )

    result = run_super_steps(spec)

    assert executed == ["x", "y"]
    assert result.state["messages"] == ["via-command"]


def test_i13_the_empty_slots_and_lists_are_no_ops() -> None:
    """**I-13**：空槽位 = **无操作**（零写入 + 零跳转 + 计入执行记录）。

    ⚠️ **2026-11-12 上游对齐 P3**：**空列表不再是「无操作」** ⇒ **显式失败** ——
    上游的判据是 ``isinstance(input,(list,tuple)) and input and any(...)``
    ⇒ **空列表落 ``else``** ⇒ 抛 ``InvalidUpdateError("Expected dict, got []")``
    （上游 ``langgraph/graph/state.py:1488-1492``）。
    ⇒ freegraph 抛内置 ``TypeError``（**类型不同 · 语义等价**）。
    """
    for empty in (Command(update={}), Command(goto=()), Command(goto=(), update={})):
        result = _run_returning(empty)
        assert result.executed == ("writer",)
        assert result.state["messages"] == []
        assert result.node_writes == {"writer": {}}

    with pytest.raises(TypeError):
        _run_returning([])


def test_i14_the_result_object_has_exactly_four_fields() -> None:
    """**I-14**：结果对象**四字段**（字段数断言）。"""
    from dataclasses import fields

    from freegraph.runtime import SuperStepResult

    assert len(fields(SuperStepResult)) == 4


# ── 上游同款（2026-11-12 上游对齐 P3）──────────────────────────────────────


def test_the_update_accepts_a_list_of_two_tuples_like_upstream() -> None:
    """``Command.update`` MUST 接受 **list/tuple of 2-tuples**（**上游同款**）。

    ⚠️ **2026-11-12 上游对齐 P3**：上游 ``langgraph/types.py:836-840``
    ⇒ 元素**必须是 tuple** · 键**必须是 str** ⇒ 逐条照抄（含「列表元素不算」的细节）。
    """
    from_list = _run_returning(Command(update=[("messages", ["x"])]))
    assert from_list.state["messages"] == ["x"]

    from_tuple = _run_returning(Command(update=(("messages", ["y"]),)))
    assert from_tuple.state["messages"] == ["y"]

    # **元素必须是 tuple** ⇒ 列表元素**不算**（上游同款）
    with pytest.raises(TypeError):
        _run_returning(Command(update=[["messages", ["z"]]]))  # type: ignore[arg-type]


def test_a_command_to_the_parent_graph_fails_like_upstream() -> None:
    """``Command(graph=Command.PARENT)`` MUST **显式失败**（**上游同款**）。

    ⚠️ **2026-11-12 上游对齐 P3**：上游 ``langgraph/graph/state.py:1761-1762``
    抛 ``ParentCommand``（上游 ``errors.py:129-133``）⇒ freegraph 抛内置
    ``NotImplementedError``（**类型不同 · 语义等价（都失败）**）。
    """
    with pytest.raises(NotImplementedError):
        _run_returning(Command(graph=Command.PARENT))
