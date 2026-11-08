# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**解析契约**的守卫测试 —— B4F1（tasks T047 / T048）。

覆盖：

* **T047**（SC-005 · FR-010 · FR-011）—— 不可变 · 可比较 · 投影可
  JSON 序列化且**不含内存地址** · 两个产物类型**显式不可哈希**；
* **T048**（SC-007 · SC-011 · FR-013）—— **零副作用**三断言
  （``sys.modules`` 增量 / 环境变量读取 / 出站连接）+ **import 期**的
  第三方模块断言。

⚠️ **子进程要求**（SC-007 · tasks T003）：``sys.modules`` 增量、环境变量
读取次数、出站连接次数三断言**必须在子进程**执行 —— 测试进程自身已导入
pytest ⇒ 同进程 ``sys.modules`` 不可用（沿用 B1F1 / B3F1 的既有口径）。

⚠️ **import 期断言亦必须在子进程**（SC-011 的字面口径）：测试进程已被
``test_typed_dict_variants.py`` 在**收集期** import ``typing_extensions``
⇒ 进程内断言**必假红**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

import ast
import dataclasses
import json
import operator
import re
import tomllib
from pathlib import Path
from typing import Annotated, TypedDict

import pytest

from freegraph.runtime import ChannelSpec, SchemaSpec, parse_state_schema

#: 仓库根目录（纪律复核的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: 署名头（**逐字** · 宪法原则 X · 门禁 G30 的判定基准）。
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 本 feature **新建**的源文件（署名头 + docstring 复核的扫描域）。
NEW_SOURCE_FILES = (
    "src/freegraph/runtime/__init__.py",
    "src/freegraph/runtime/errors.py",
    "src/freegraph/runtime/reducer.py",
    "src/freegraph/runtime/schema.py",
    "tests/runtime/__init__.py",
    "tests/runtime/conftest.py",
    "tests/runtime/test_binary_criterion.py",
    "tests/runtime/test_future_annotations.py",
    "tests/runtime/test_parse_contract.py",
    "tests/runtime/test_schema_parse.py",
    "tests/runtime/test_typed_dict_variants.py",
)

#: 上层模块（**L3 / L4 / L5**）⇒ L2 MUST NOT import 它们（FR-014 · ARCH-1）。
UPPER_LAYER_MODULES = ("_stategraph", "persistence", "observability", "app")

#: 模块级 lambda（``__qualname__`` == ``"<lambda>"``）⇒ 投影标识**无地址**。
module_level_lambda = lambda a, b: a  # noqa: E731 —— 夹具形态


class CallableReducer:
    """可调用实例（``__call__(self, a, b)``）⇒ 投影标识取**其类型**的路径。"""

    def __call__(self, a, b):  # noqa: ANN001 —— 夹具形态
        return a


class MessagesSchema(TypedDict):
    """被测 schema（带归约器 + 不带归约器各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


# ── T047 · 契约守卫（不可变 / 可比较 / 投影 / 不可哈希）───────────────────


def test_channel_spec_is_immutable() -> None:
    """I-7 · FR-010：改属性抛 ``FrozenInstanceError``。"""
    channel = parse_state_schema(MessagesSchema).channels["messages"]

    with pytest.raises(dataclasses.FrozenInstanceError):
        channel.key = "other"  # type: ignore[misc]


def test_schema_spec_channels_mapping_is_read_only() -> None:
    """I-7 · FR-010：``channels`` 写操作抛 ``TypeError``（结构性不可变）。"""
    spec = parse_state_schema(MessagesSchema)

    with pytest.raises(TypeError):
        spec.channels["x"] = None  # type: ignore[index]


def test_schema_spec_fields_are_immutable() -> None:
    """I-7：``SchemaSpec`` 的字段同样不可改。"""
    spec = parse_state_schema(MessagesSchema)

    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.keys = ("other",)  # type: ignore[misc]


def test_same_schema_parsed_twice_is_equal() -> None:
    """SC-005：同一 schema 两次解析**相等**。"""
    assert parse_state_schema(MessagesSchema) == parse_state_schema(MessagesSchema)


def test_content_identical_schemas_with_different_names_are_equal() -> None:
    """SC-005 的字面口径：差异源 MUST 取自**产物内容**。

    两个**内容相同、仅类名不同**的 ``TypedDict`` 解析结果**必然相等**
    ⇒ 若把「类名不同」当差异源，此条会**假红**。
    """

    class SchemaA(TypedDict):
        value: int

    class SchemaB(TypedDict):
        value: int

    assert parse_state_schema(SchemaA) == parse_state_schema(SchemaB)


def test_schemas_with_different_content_are_not_equal() -> None:
    """SC-005：键集合 / ``value_type`` / ``reducer`` 任一不同 ⇒ 结果**不等**。"""

    class Base(TypedDict):
        value: int

    class OtherType(TypedDict):
        value: str

    class OtherKey(TypedDict):
        other: int

    class OtherReducer(TypedDict):
        value: Annotated[list, operator.add]

    baseline = parse_state_schema(Base)

    assert baseline != parse_state_schema(OtherType)
    assert baseline != parse_state_schema(OtherKey)
    assert baseline != parse_state_schema(OtherReducer)


def test_projection_is_json_serialisable_and_address_free() -> None:
    """SC-005 · FR-011：投影可 JSON 序列化 · **不含内存地址形态**。"""
    spec = parse_state_schema(MessagesSchema)

    payload = json.dumps(spec.to_dict(), ensure_ascii=False)

    assert json.loads(payload) == spec.to_dict()
    assert "0x" not in payload


def test_projection_is_deterministic() -> None:
    """SC-005 · I-9：两次投影**逐字一致**。"""
    first = parse_state_schema(MessagesSchema).to_dict()
    second = parse_state_schema(MessagesSchema).to_dict()

    assert first == second
    assert json.dumps(first, ensure_ascii=False) == json.dumps(
        second, ensure_ascii=False
    )


def test_projection_contains_the_readable_reducer_identifier() -> None:
    """FR-011 · research D-06：归约器标识 = 4 级规则（不是 ``repr`` 原文）。"""
    spec = parse_state_schema(MessagesSchema)
    channels = {entry["key"]: entry for entry in spec.to_dict()["channels"]}

    assert channels["messages"]["reducer"].endswith("operator.add")
    assert channels["llm_calls"]["reducer"] is None


def test_lambda_reducer_identifier_has_no_memory_address() -> None:
    """FR-011 ④ · 澄清 Q10：lambda 的标识**无内存地址**。"""

    class LambdaSchema(TypedDict):
        messages: Annotated[list, module_level_lambda]

    spec = parse_state_schema(LambdaSchema)
    payload = json.dumps(spec.to_dict(), ensure_ascii=False)

    assert "0x" not in payload
    assert payload.count("<lambda>") == 1


def test_callable_instance_identifier_uses_its_type_path() -> None:
    """FR-011 ②：可调用实例的标识取**其类型**的模块名 + 限定名。"""
    instance = CallableReducer()

    class InstanceSchema(TypedDict):
        messages: Annotated[list, instance]

    spec = parse_state_schema(InstanceSchema)
    channels = {entry["key"]: entry for entry in spec.to_dict()["channels"]}

    assert channels["messages"]["reducer"].endswith(".CallableReducer")
    assert "0x" not in channels["messages"]["reducer"]


def test_products_are_explicitly_unhashable() -> None:
    """I-8 · research D-01 / D-02：两个产物类型**显式不可哈希**。"""
    spec = parse_state_schema(MessagesSchema)
    channel = spec.channels["messages"]

    assert isinstance(channel, ChannelSpec)
    assert isinstance(spec, SchemaSpec)

    with pytest.raises(TypeError):
        hash(channel)

    with pytest.raises(TypeError):
        hash(spec)


# ── T048 · 零副作用（子进程 · SC-007 · SC-011 · FR-013）──────────────────

_ZERO_SIDE_EFFECT_SOURCE = '''
import json
import operator
from typing import Annotated, TypedDict

import freegraph.runtime
from freegraph.runtime import parse_state_schema

calls = []


def reducer(current, new):
    calls.append(1)
    return current


class Schema(TypedDict):
    messages: Annotated[list, reducer]


before = snapshot_modules()
spec = parse_state_schema(Schema)

payload = {
    "new_non_stdlib": non_stdlib_delta(before),
    "reducer_calls": len(calls),
    "reducer_is_same": spec.channels["messages"].reducer is reducer,
    "third_party": third_party_modules(),
}
payload["__counters__"] = dict(COUNTERS)
print(json.dumps(payload))
'''


def test_parsing_has_no_side_effects(run_in_subprocess) -> None:
    """SC-007 · FR-013：解析**零副作用**。

    * ``sys.modules`` 增量的**非标准库**条目数 **== 0**；
    * **环境变量读取次数 == 0**（三条读取路径全覆盖）；
    * **出站连接次数 == 0**（两个入口全覆盖）；
    * 归约器**调用次数 == 0**（SC-009）。
    """
    result = run_in_subprocess(_ZERO_SIDE_EFFECT_SOURCE)

    assert result["new_non_stdlib"] == []
    assert result["env_reads"] == 0
    assert result["egress"] == 0
    assert result["reducer_calls"] == 0
    assert result["reducer_is_same"] is True


def test_importing_the_runtime_pulls_no_third_party_modules(
    run_in_subprocess,
) -> None:
    """SC-011：``import freegraph.runtime`` 之后 ``sys.modules`` 中的
    ``pydantic`` / ``typing_extensions`` / ``langchain*`` / ``langgraph*`` /
    ``langsmith`` 的**条目数 == 0**。

    ⚠️ **MUST 在子进程内执行** —— 测试进程已被 ``test_typed_dict_variants.py``
    在收集期 import ``typing_extensions`` ⇒ 进程内断言**必假红**。
    """
    source = '''
import json

import freegraph.runtime

payload = {"third_party": third_party_modules()}
payload["__counters__"] = dict(COUNTERS)
print(json.dumps(payload))
'''
    result = run_in_subprocess(source)

    assert result["third_party"] == []
    assert result["env_reads"] == 0
    assert result["egress"] == 0


# ── T049 / T050 / T051 / T055 / T056 · 纪律复核（可机读断言）──────────────


def _public_symbols(relative_path: str) -> list[str]:
    """从源码里取 ``__all__`` 的字面内容（**不 import** ⇒ 零副作用）。"""
    path = REPO_ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    raise AssertionError(f"{relative_path} 未定义 __all__")


def _dependency_text(sections: object) -> str:
    """把一段依赖声明摊平成**文本**（便于统计包名出现次数）。"""
    if isinstance(sections, dict):
        return " ".join(_dependency_text(value) for value in sections.values())
    if isinstance(sections, (list, tuple)):
        return " ".join(str(item) for item in sections)
    return str(sections)


def test_dependency_declarations_contain_no_upstream_package() -> None:
    """T049 · FR-016 ② · SC-004：**三处**依赖声明中零 ``langgraph``。

    ⚠️ MUST 按 **TOML 解析**三处位置取样（``dependencies`` /
    ``[project.optional-dependencies]`` / ``[dependency-groups]``），
    MUST NOT 对文件全文扫描（``keywords`` 等**非依赖字段**本就含
    ``"langgraph"`` 作检索词）。
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})

    text = " ".join(
        [
            _dependency_text(project.get("dependencies", [])),
            _dependency_text(project.get("optional-dependencies", {})),
            _dependency_text(data.get("dependency-groups", {})),
        ]
    ).lower()

    assert "langgraph" not in text
    assert "langchain" not in text
    assert "langsmith" not in text
    assert "typing_extensions" not in text
    assert "typing-extensions" not in text


def test_ci_workflow_never_installs_langgraph() -> None:
    """T049 · FR-016 ③ · SC-004：CI 作业内 ``langgraph`` 安装次数 **== 0**。"""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert workflow.lower().count("langgraph") == 0


def test_public_api_surface_is_unchanged() -> None:
    """T049 · SC-015 · FR-015：契约层仍 **18** 个 · 门面仍 **7** 个符号。"""
    assert len(_public_symbols("src/freegraph/contracts/__init__.py")) == 18
    assert len(_public_symbols("src/freegraph/graph.py")) == 7


def test_runtime_package_is_registered_as_l2_in_the_layer_registry() -> None:
    """T050 · FR-014：层注册表**零改动**（``src/freegraph/runtime/`` = L2）。"""
    registry = (
        REPO_ROOT
        / "specs"
        / "b3f1-scaffold-ci-gates"
        / "contracts"
        / "layer-registry.md"
    ).read_text(encoding="utf-8")

    assert re.search(
        r"\|\s*`src/freegraph/runtime/`\s*\|\s*`L2`\s*\|", registry
    ), "层注册表未把 src/freegraph/runtime/ 登记为 L2"


def test_runtime_package_has_no_edge_to_upper_layers() -> None:
    """T050 · SC-012 · FR-014：L2 → L3 / L4 / L5 的边数 **== 0**。"""
    runtime_dir = REPO_ROOT / "src" / "freegraph" / "runtime"

    for path in sorted(runtime_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        for name in imported:
            for upper in UPPER_LAYER_MODULES:
                assert f"freegraph.{upper}" not in name, (
                    f"{path.name} 引入了上层模块 {name}"
                )


def test_gate_numbering_is_unchanged() -> None:
    """T050 · SC-012：门禁编号总数仍为 **30** 且**连续**（G1–G30）。"""
    contract = (
        REPO_ROOT
        / "specs"
        / "b3f1-scaffold-ci-gates"
        / "contracts"
        / "architecture-gates.md"
    ).read_text(encoding="utf-8")
    overview = re.search(r"^##\s*0\..*?(?=^##\s|\Z)", contract, re.S | re.M)
    assert overview, "architecture-gates.md 缺少「## 0. 门禁总览」章节"

    identifiers = re.findall(r"\|\s*\*\*G(\d+)\*\*\s*\|", overview.group(0))

    assert identifiers == [str(number) for number in range(1, 31)]


def test_new_source_files_carry_signature_header_and_leading_docstring() -> None:
    """T051 · FR-019 · SC-012：署名头覆盖率 **== 100%** + docstring 为首个语句。"""
    for relative_path in NEW_SOURCE_FILES:
        path = REPO_ROOT / relative_path
        assert path.is_file(), f"缺文件：{relative_path}"

        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == SIGNATURE_HEADER, f"{relative_path} 缺署名头"

        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), f"{relative_path} 缺模块 docstring"
        assert isinstance(tree.body[0], ast.Expr) and isinstance(
            tree.body[0].value, ast.Constant
        ), f"{relative_path} 的模块 docstring 不是首个语句"


def test_compat_matrix_has_no_new_row_for_this_feature() -> None:
    """T055 · SC-015：兼容矩阵**零新增行**（行数不变 ⇒ 双向防漂移）。

    矩阵的 freegraph 符号集合 MUST 恒等于「契约层 18 个 + 门面 7 个」
    ⇒ 本 feature（L2 内部 API）**不新增**任何行。
    """
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = re.search(
        r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", readme, re.S | re.M
    )
    assert section, "README.md 缺少「## API 兼容矩阵」章节"

    names = {
        match.group(1)
        for match in re.finditer(
            r"^\|\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*\|", section.group(1), re.M
        )
    }
    expected = set(_public_symbols("src/freegraph/contracts/__init__.py")) | set(
        _public_symbols("src/freegraph/graph.py")
    )

    assert names == expected, (
        f"兼容矩阵的符号集合与「契约层 18 + 门面 7」不一致："
        f"多出 {sorted(names - expected)} · 缺少 {sorted(expected - names)}"
    )


def test_third_party_notices_needs_no_new_entry() -> None:
    """T056 · FR-019 · 原则 X：本 feature 零新增第三方依赖 ⇒ **无需新增登记**。"""
    notices = (REPO_ROOT / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
    section = re.search(r"^##\s*2\..*?(?=^##\s|\Z)", notices, re.S | re.M)
    assert section, "THIRD_PARTY_NOTICES 缺少「## 2. 第三方运行时依赖」章节"

    rows = [
        line.strip()
        for line in section.group(0).splitlines()
        if line.strip().startswith("|")
        and not re.match(r"^\|[\s\-|:]+\|$", line.strip())
        and not line.strip().startswith("| 包 ")
        and "（暂无条目）" not in line
    ]

    assert rows == [], f"第三方运行时依赖表应无数据行，实得：{rows}"
