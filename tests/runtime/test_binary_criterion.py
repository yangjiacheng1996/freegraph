# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**二元性判定表逐条比对** —— B4F1 的 A2 判据（SC-004 · FR-016）。

判据的**唯一权威** =
``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``
（``<!-- authority: yes -->``）—— 本文件**解析该 Markdown 表格**取样
（沿用既有门禁 **G25** 解析 ``layer-registry.md`` 的同构手法 ·
research D-03）⇒ **判据与用例天然分离**（改判据必然改测试同提交可见）
⇒ **MUST NOT** 在本文件里另抄一份表。

**覆盖面下限的独立断言**（否则删表行仍绿）：

* §2 的行数 **== 16**（FR-016 ①-a）；
* §3 的行数 **== 2**（FR-016 ①-b）；
* §2 / §3 的「输入」列的**每个名字**都能在 §4 夹具清单中找到
  （求值命名空间**逐名一致**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

import operator
from typing import Annotated, Any, TypedDict

import pytest

from freegraph.runtime import InvalidSchemaError, parse_state_schema
from runtime.conftest import (
    BINARY_CRITERION_ROW_COUNT,
    CRITERION_NAMESPACE,
    CRITERION_ROWS,
    CRITERION_TABLES,
    EXTRACTION_CRITERION_ROW_COUNT,
    resolve_criterion_input,
)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """把判定表的**每一行**变成一条独立用例（逐条比对）。"""
    if "criterion_row" in metafunc.fixturenames:
        metafunc.parametrize(
            "criterion_row",
            CRITERION_ROWS,
            ids=[f"{row['index']}-{row['form']}" for row in CRITERION_ROWS],
        )


def _evaluate(expression: str) -> Any:
    """按**名字**求值判定表「输入」列的表达式（求值路径**只有一套**）。"""
    return resolve_criterion_input(expression)


def _schema_with(annotation: Any) -> Any:
    """构造一份只含单个 key ``probe`` 的 schema（函数式 ``TypedDict``）。"""
    return TypedDict("_Single", {"probe": annotation})  # type: ignore[misc]


# ── 覆盖面下限（独立断言 · 否则删表行仍绿）───────────────────────────────


def test_binary_criterion_covers_sixteen_forms() -> None:
    """FR-016 ①-a：§2 的行数 **== 16**。"""
    assert len(CRITERION_TABLES["binary"]) == BINARY_CRITERION_ROW_COUNT


def test_extraction_criterion_covers_two_forms() -> None:
    """FR-016 ①-b：§3 的行数 **== 2**。"""
    assert len(CRITERION_TABLES["extraction"]) == EXTRACTION_CRITERION_ROW_COUNT


def test_every_criterion_row_carries_an_upstream_source() -> None:
    """SC-004：每条用例 MUST 带来源 `路径:行号` ⇒ **无来源项数 == 0**。"""
    missing = [row["index"] for row in CRITERION_ROWS if not row["upstream"]]
    assert missing == [], f"判定表存在无来源的行：{missing}"

    malformed = [
        row["index"]
        for row in CRITERION_ROWS
        if ":" not in row["upstream"] or not row["upstream"].startswith("langgraph/")
    ]
    assert malformed == [], f"判定表存在来源格式不合的行：{malformed}"


def test_every_input_name_exists_in_the_fixture_list() -> None:
    """SC-004「缺失条数 == 0」：§2 / §3 的每个输入名 MUST 在 §4 中找到。"""
    fixture_names = {row["name"] for row in CRITERION_TABLES["fixtures"]}
    missing = [
        (row["index"], row["input"])
        for row in CRITERION_ROWS
        if row["input"] not in fixture_names
    ]
    assert missing == [], f"判定表的输入名不在 §4 夹具清单中：{missing}"


def test_namespace_matches_the_fixture_list_name_by_name() -> None:
    """求值命名空间 MUST 与 §4 夹具清单**逐名一致**（夹具只有一套）。"""
    fixture_names = {row["name"] for row in CRITERION_TABLES["fixtures"]}
    assert set(CRITERION_NAMESPACE) == fixture_names
    assert len(CRITERION_NAMESPACE) == len(fixture_names)


# ── 逐条比对（判定结果 · 接受 / 拒绝）────────────────────────────────────


def test_criterion_row_matches_the_implementation(criterion_row: dict[str, str]) -> None:
    """逐条比对：判定结果 MUST 与权威表**逐条一致**（一致率 == 100%）。

    * §2 的行 ⇒ 「末位候选是否被判为二元归约器」（接受 / 拒绝）；
    * §3 的行 ⇒ 「元数据末位非 callable ⇒ 无归约器」/「多条目只认末位」。
    """
    expression = criterion_row["input"]
    expected = criterion_row["expected"]
    candidate = _evaluate(expression)
    label = f"{criterion_row['index']}（{criterion_row['form']}）"

    if criterion_row["index"].startswith("E-"):
        # §3 · 归约器**提取**形态 —— 输入是**元数据元组**。
        annotation = Annotated[list, *candidate]
        channel = parse_state_schema(_schema_with(annotation)).channels["probe"]
        if "无归约器" in expected:
            assert channel.reducer is None, f"{label}：应无归约器"
            assert channel.has_reducer is False
            assert channel.semantics == "overwrite"
        else:
            assert channel.reducer is operator.add, f"{label}：只认末位"
            assert channel.semantics == "reduce"
        return

    # §2 · 二元性判定形态 —— 输入是「末位候选」。
    annotation = Annotated[list, candidate]
    if expected.strip() == "接受":
        channel = parse_state_schema(_schema_with(annotation)).channels["probe"]
        assert channel.reducer is candidate, f"{label}：期望接受，却未接受"
        assert channel.semantics == "reduce"
    else:
        with pytest.raises(InvalidSchemaError) as excinfo:
            parse_state_schema(_schema_with(annotation))
        assert excinfo.value.reason == "reducer_not_binary", (
            f"{label}：期望拒绝，却接受了"
        )
        assert excinfo.value.key == "probe"
