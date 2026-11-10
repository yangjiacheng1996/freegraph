# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**读取契约**的守卫测试 —— 属 **B5F2**（tasks T028 / T029 / T030）。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/read-contract.md``
（``<!-- authority: yes -->``）⇒ 本文件 MUST **解析**该契约并**逐条**断言
§4 的 **I-1…I-11**（MUST NOT 只测行为而不校验契约文本）。

**逐条绑定**的机制（防「判据与实现同源 ⇒ 自证」）：

* **契约文本**是「**有哪些不变量**」的**唯一权威** ⇒ 本文件**解析** §4 的
  不变量编号集合；
* **编号 → 断言**的绑定写在 ``INVARIANT_TESTS`` 里 ⇒ 每条不变量**恰好**对应
  一个**真实断言**的测试函数；
* 参数化的守卫用例断言「**契约里的每条不变量都有绑定**」且「**每条绑定都
  指向一个真实存在的测试函数**」⇒ 契约新增一条不变量而没人断言 ⇒ **变红**。

另含：

* **签名守卫**（§1）—— 两个入口的**名字 + 签名**与契约文本**逐字一致**；
* **收敛守卫**（FR-001 · SC-012）—— 全仓「状态读取入口」的**实现点数 == 1**；
* **依赖隔离**（FR-018 / FR-020 · SC-008 / SC-010）—— 内核路径对上游的导入
  次数 == **0** · ``Requires-Dist`` **整体为空**；
* **冻结面断言**（FR-021 / FR-026 · SC-011 / SC-029）—— ``freegraph.runtime``
  的 ``__all__`` == **20** · ``freegraph.contracts`` == **18** ·
  ``freegraph.graph`` == **7**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import copy
import importlib.metadata
import inspect
import operator
import re
import tomllib
from pathlib import Path
from typing import Annotated, Any, Callable, TypedDict

import pytest

from freegraph.runtime import build_channels, local_read, parse_state_schema, read_channels

#: 仓库根目录（契约文件与源码树的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **读取契约**的唯一权威文件（``<!-- authority: yes -->``）。
READ_CONTRACT_PATH = (
    REPO_ROOT
    / "specs"
    / "b5f2-sparse-state-read"
    / "contracts"
    / "read-contract.md"
)

#: 契约 §4 冻结的**不变量编号集合**（**逐条** · I-1…I-11）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 12))

#: 契约 §4 之前冻结的**错误类型符号集合**（**零新增错误类型** · I-9）。
EXPECTED_ERROR_SYMBOLS = (
    "EmptyChannelError",
    "InvalidChannelUpdateError",
    "InvalidSchemaError",
    "REASON_ANNOTATION_UNRESOLVABLE",
    "REASON_NOT_A_TYPED_DICT",
    "REASON_REDUCER_NOT_BINARY",
    "SCHEMA_ERROR_REASONS",
)

#: 契约层（``freegraph.contracts``）的**冻结符号数**。
CONTRACT_SYMBOL_COUNT = 18

#: 门面（``freegraph.graph``）的**冻结符号数**。
FACADE_SYMBOL_COUNT = 7

#: L2 内部 API（``freegraph.runtime``）的**导出面**（12 → **14** → **20**）。
RUNTIME_SYMBOL_COUNT = 20


class SampleSchema(TypedDict):
    """被测 schema（**有归约器** + **无归约器** + **无值**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int
    never_written: str


# ── 契约解析（**唯一权威** = 契约文本）────────────────────────────────


def _contract_text() -> str:
    """读取契约权威文件的全文。"""
    return READ_CONTRACT_PATH.read_text(encoding="utf-8")


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
    """**解析**契约 §4 ⇒ 不变量编号列表（**按出现顺序**）。"""
    identifiers: list[str] = []
    for line in _section_body(_contract_text(), "## 4."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


def _contract_entry_signatures() -> dict[str, str]:
    """**解析**契约 §1 ⇒ ``{入口名: 签名文本}``。

    签名文本取自 §1 表格里「入口 1 / 入口 2」两行的**反引号内容**
    ⇒ **逐字**比对的基准是**契约文本**（MUST NOT 在测试里另抄一份）。
    """
    signatures: dict[str, str] = {}
    for line in _section_body(_contract_text(), "## 1."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        if cells[0] not in {"入口 1", "入口 2"}:
            continue
        match = re.search(r"`([^`]+)`", cells[1])
        assert match, f"契约 §1 的 {cells[0]} 行没有反引号包裹的签名"
        text = match.group(1)
        name = text.split("(", 1)[0].strip()
        signatures[name] = text
    return signatures


def _render_annotation(annotation: Any) -> str:
    """把注解渲染成**文本**（``from __future__ import annotations`` ⇒ 字符串注解）。"""
    if annotation is inspect.Parameter.empty:
        return ""
    if isinstance(annotation, str):
        return annotation
    return str(annotation)


def _signature_text(func: Callable[..., Any]) -> str:
    """把函数的签名渲染成**契约同款文本**（供逐字比对）。"""
    signature = inspect.signature(func)
    parts: list[str] = []
    keyword_only_started = False
    for name, parameter in signature.parameters.items():
        if (
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and not keyword_only_started
        ):
            parts.append("*")
            keyword_only_started = True
        annotation = _render_annotation(parameter.annotation)
        text = f"{name}: {annotation}" if annotation else name
        if parameter.default is not inspect.Parameter.empty:
            text += f" = {parameter.default!r}"
        parts.append(text)
    rendered = f"({', '.join(parts)})"
    returns = _render_annotation(signature.return_annotation)
    if returns:
        rendered += f" -> {returns}"
    return rendered


# ── I-1…I-11 · 逐条断言 ───────────────────────────────────────────────


def _sample_channels() -> dict:
    """构造一份手写通道状态（**有归约器** + **无归约器** + **无值**各一）。"""
    channels = build_channels(parse_state_schema(SampleSchema))
    channels["messages"].update([["hi"]])
    return channels


def _binding_snapshot(channels: dict) -> list[tuple[str, bool, object]]:
    """每个通道的「**绑定与可用性判定**」快照（I-5 的作用域）。"""
    snapshot: list[tuple[str, bool, object]] = []
    for key, channel in channels.items():
        available = channel.is_available()
        snapshot.append((key, available, channel.get() if available else None))
    return snapshot


def test_i1_result_key_set_equals_the_available_channel_set() -> None:
    """**I-1**：结果 key 集合 == 「``is_available()`` 为真」的通道 key 集合。"""
    channels = _sample_channels()

    result = read_channels(channels)

    assert set(result) == {
        key for key, channel in channels.items() if channel.is_available()
    }


def test_i2_result_key_order_equals_the_input_mapping_order() -> None:
    """**I-2**：结果 key **顺序** == 入参映射的顺序（过滤后）。"""
    channels = _sample_channels()

    result = read_channels(channels)

    assert list(result) == [key for key in channels if key in result]


def test_i3_result_is_exactly_a_plain_dict() -> None:
    """**I-3**：``type(result) is dict``（类型恒等）。"""
    result = read_channels(_sample_channels())

    assert type(result) is dict


def test_i4_result_values_are_the_same_objects_as_the_channel_values() -> None:
    """**I-4**：结果里的每个值与通道当前值**同一对象**。"""
    channels = _sample_channels()

    result = read_channels(channels)

    for key in result:
        assert result[key] is channels[key].get()


def test_i5_binding_and_availability_are_unchanged_by_reading() -> None:
    """**I-5**：读取**前后**每个通道的**绑定与可用性判定不变**。

    ⚠️ 作用域只覆盖 **``is_available()`` 的结果 + ``get()`` 的取值** ⇒
    「**就地修改型**归约器改写值对象」属**已知面**（MUST **NOT** 计入本条）。
    """
    channels = _sample_channels()
    before = _binding_snapshot(channels)

    read_channels(channels)
    local_read(channels, {}, fresh=False)
    local_read(channels, {"messages": [["new"]]}, fresh=True)

    assert _binding_snapshot(channels) == before


def test_i6_channel_copy_has_no_instance_dict() -> None:
    """**I-6**：副本**无** ``__dict__``（B5F1 的 ``__slots__`` 纪律不被破坏）。"""
    channel = _sample_channels()["messages"]

    duplicate = copy.copy(channel)

    assert not hasattr(duplicate, "__dict__")


def test_i7_channel_copy_keeps_the_very_same_reducer_reference() -> None:
    """**I-7**：副本的归约器与原通道**同一引用**。"""
    channel = _sample_channels()["messages"]

    duplicate = copy.copy(channel)

    assert duplicate.reducer is channel.reducer


def test_i8_reading_layer_has_zero_egress_and_zero_env_reads(
    run_in_subprocess,
) -> None:
    """**I-8**：读取层的出站次数 == **0** · 环境变量读取次数 == **0**。"""
    source = '''
import json

before = snapshot_modules()

import freegraph.runtime.read

payload = {
    "new_non_stdlib": non_stdlib_delta(before),
    "third_party": third_party_modules(),
}
payload["__counters__"] = dict(COUNTERS)
print(json.dumps(payload))
'''
    result = run_in_subprocess(source)

    assert result["new_non_stdlib"] == []
    assert result["third_party"] == []
    assert result["env_reads"] == 0
    assert result["egress"] == 0


def test_i9_the_reading_layer_adds_no_new_error_type() -> None:
    """**I-9**：读取层**不新增**错误类型（``freegraph.runtime.errors`` 的符号集合不变）。"""
    from freegraph.runtime import errors

    assert tuple(errors.__all__) == EXPECTED_ERROR_SYMBOLS

    tree = ast.parse(
        (REPO_ROOT / "src" / "freegraph" / "runtime" / "errors.py").read_text(
            encoding="utf-8"
        )
    )
    error_classes = sorted(
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id == "FreegraphError")
            or (
                isinstance(base, ast.Attribute)
                and base.attr == "FreegraphError"
            )
            for base in node.bases
        )
    )
    assert error_classes == [
        "EmptyChannelError",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
    ]


def test_i10_a_channel_holding_none_is_present_in_the_result() -> None:
    """**I-10**：「**值为 ``None``**」的通道**出现**在结果里。"""
    channels = _sample_channels()
    channels["llm_calls"].update([None])

    result = read_channels(channels)

    assert result["llm_calls"] is None


def test_i11_the_two_sparse_entries_are_byte_identical() -> None:
    """**I-11**：两个稀疏入口的结果**逐字相等**。

    （key 集合**相同** + key **顺序相同** + 逐 key 值**同一对象**。）
    """
    channels = _sample_channels()

    direct = read_channels(channels)
    via_local = local_read(channels, {}, fresh=False)

    assert via_local == direct
    assert list(via_local) == list(direct)
    for key in direct:
        assert via_local[key] is direct[key]


#: **不变量编号 → 断言它的测试函数**（§4 的**逐条**绑定）。
INVARIANT_TESTS: dict[str, Callable[..., Any]] = {
    "I-1": test_i1_result_key_set_equals_the_available_channel_set,
    "I-2": test_i2_result_key_order_equals_the_input_mapping_order,
    "I-3": test_i3_result_is_exactly_a_plain_dict,
    "I-4": test_i4_result_values_are_the_same_objects_as_the_channel_values,
    "I-5": test_i5_binding_and_availability_are_unchanged_by_reading,
    "I-6": test_i6_channel_copy_has_no_instance_dict,
    "I-7": test_i7_channel_copy_keeps_the_very_same_reducer_reference,
    "I-8": test_i8_reading_layer_has_zero_egress_and_zero_env_reads,
    "I-9": test_i9_the_reading_layer_adds_no_new_error_type,
    "I-10": test_i10_a_channel_holding_none_is_present_in_the_result,
    "I-11": test_i11_the_two_sparse_entries_are_byte_identical,
}


# ── 契约守卫（§4 的**逐条**覆盖）──────────────────────────────────────


@pytest.mark.parametrize("invariant", EXPECTED_INVARIANTS)
def test_every_contract_invariant_has_a_bound_assertion(invariant: str) -> None:
    """§4 的**每条**不变量 MUST 有**一条**绑定的断言（FR-027 · 裁定 32 ②）。

    ⇒ 契约新增一条不变量而没人断言 ⇒ **变红**。
    """
    assert invariant in INVARIANT_TESTS, f"契约的不变量 {invariant} 没有绑定断言"


def test_the_contract_declares_exactly_the_expected_invariants() -> None:
    """契约 §4 的不变量编号集合 MUST 与**冻结的**集合**逐条一致**。

    ⇒ 契约被改动（新增 / 删除 / 改编号）而测试未同步 ⇒ **变红**。
    """
    assert tuple(_contract_invariants()) == EXPECTED_INVARIANTS


def test_every_bound_assertion_points_to_a_real_test_function() -> None:
    """每条绑定 MUST 指向一个**真实存在**的测试函数（防「绑定到空壳」）。"""
    for invariant, function in INVARIANT_TESTS.items():
        assert callable(function), f"{invariant} 的绑定不是可调用对象"
        assert function.__name__.startswith("test_"), (
            f"{invariant} 绑定的函数名不是测试函数：{function.__name__}"
        )


def test_every_bound_assertion_is_collected_by_pytest() -> None:
    """每条绑定的断言 MUST **被 pytest 收集**（防「绑定了但没跑」）。"""
    namespace = globals()
    collected = {
        name
        for name in namespace
        if name.startswith("test_") and callable(namespace[name])
    }
    for invariant, function in INVARIANT_TESTS.items():
        assert function.__name__ in collected, (
            f"{invariant} 绑定的断言未被 pytest 收集：{function.__name__}"
        )


# ── §1 · 签名守卫（名字 + 签名**逐字一致**）───────────────────────────


def test_the_two_entry_names_and_signatures_match_the_contract_verbatim() -> None:
    """两个入口的**名字 + 签名** MUST 与契约 §1 **逐字一致**。

    ⇒ 期望值**取自契约文本**（MUST NOT 在测试里另抄一份）⇒ 契约改了签名 ⇒
    本用例**变红**（⇒ 实现 MUST 同步）。
    """
    expected = _contract_entry_signatures()

    assert set(expected) == {"read_channels", "local_read"}
    assert (
        f"{read_channels.__name__}{_signature_text(read_channels)}"
        == expected["read_channels"]
    )
    assert (
        f"{local_read.__name__}{_signature_text(local_read)}"
        == expected["local_read"]
    )
    assert read_channels.__name__ == "read_channels"
    assert local_read.__name__ == "local_read"


# ── T029 · 收敛守卫 + 依赖隔离 ────────────────────────────────────────


def _source_modules() -> list[Path]:
    """列出内核源码树的全部 ``*.py``（按路径排序）。"""
    return sorted((REPO_ROOT / "src" / "freegraph").rglob("*.py"))


def test_the_state_reading_entry_points_have_exactly_one_implementation() -> None:
    """FR-001 · SC-012：状态读取入口的**实现点数 == 1**（一个模块 · 两个函数）。

    ⇒ 全仓**无第三个**读取实现点 ⇒ 「稀疏读」只有**一处**实现。
    """
    definitions: list[str] = []
    for path in _source_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in {"read_channels", "local_read"}:
                    relative = path.relative_to(REPO_ROOT).as_posix()
                    definitions.append(f"{relative}::{node.name}")

    assert sorted(definitions) == [
        "src/freegraph/runtime/read.py::local_read",
        "src/freegraph/runtime/read.py::read_channels",
    ]


def test_the_reading_module_exposes_exactly_the_two_entries() -> None:
    """读取模块的**公开函数**恰为两个入口（⇒ 该模块就是**那一个**实现点）。"""
    path = REPO_ROOT / "src" / "freegraph" / "runtime" / "read.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    public = sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    )

    assert public == ["local_read", "read_channels"]


def test_the_kernel_imports_no_upstream_package() -> None:
    """FR-018 / FR-022：``src/freegraph/**`` 对上游的导入次数 == **0**。

    （``langgraph`` / ``langchain*`` / ``langsmith`` / ``pydantic`` /
    ``typing_extensions`` —— 逐字判定。）
    """
    forbidden = (
        "langgraph",
        "langchain",
        "langsmith",
        "pydantic",
        "typing_extensions",
    )
    offenders: list[str] = []
    for path in _source_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                root = name.split(".")[0]
                if root in forbidden:
                    offenders.append(f"{path.name}:{node.lineno}: {name}")

    assert offenders == []


def test_the_release_metadata_declares_no_requirement_at_all() -> None:
    """判据 **A5** · SC-008：``Requires-Dist`` **整体为空**。"""
    assert importlib.metadata.requires("freegraph") in (None, [])


def test_the_project_declares_no_optional_dependency_extra() -> None:
    """宪法 v1.7.0：v1.0 的 ``pyproject.toml`` MUST **NOT** 含
    ``[project].optional-dependencies``。"""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "optional-dependencies" not in data.get("project", {})


# ── T030 · 冻结面断言 ─────────────────────────────────────────────────


def test_the_runtime_export_surface_holds_twenty_symbols() -> None:
    """FR-023 · SC-016：``freegraph.runtime.__all__`` == **20** 且含两个读取入口。"""
    import freegraph.runtime as runtime

    assert len(runtime.__all__) == RUNTIME_SYMBOL_COUNT
    assert "read_channels" in runtime.__all__
    assert "local_read" in runtime.__all__
    assert set(runtime.__all__) == {
        "BinaryOperatorAggregate",
        "Channel",
        "ChannelSpec",
        "EmptyChannelError",
        "EphemeralValue",
        "GraphSpec",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
        "LastValue",
        "NodeSpec",
        "SchedulerState",
        "SchemaSpec",
        "SuperStepResult",
        "build_channel",
        "build_channels",
        "local_read",
        "parse_state_schema",
        "read_channels",
        "run_super_step",
        "run_super_steps",
    }


def test_the_contract_layer_and_the_facade_symbol_counts_are_unchanged() -> None:
    """FR-026 · SC-011：契约层 **18** 个 · 门面 **7** 个符号**一字不动**。"""
    import freegraph.contracts as contracts
    import freegraph.graph as graph

    assert len(contracts.__all__) == CONTRACT_SYMBOL_COUNT
    assert len(graph.__all__) == FACADE_SYMBOL_COUNT
