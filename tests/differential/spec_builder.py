# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**图规格**的前置校验与 ``TypedDict`` 构造 —— 属 **B5F2**（tasks T009 / T019）。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/differential-fixture.md``
§2（图规格的形态）与 §5（**不进入**比对的范围）。

**图规格的形态**（**纯数据** · 不携带 ``TypedDict`` 类）：

======================  ======================================================
字段                    约束
======================  ======================================================
``schema``             ``{key: (value_type, reducer | None)}``（**纯数据**）
``schema_typed``       运行时动态构造的 ``TypedDict``（**一个**）⇒ 两侧消费**同一个对象**
``nodes``              ``[(节点名, 节点函数)]``（**有序** · 线性单链）
``initial_input``      ``dict``（按「**一次写入**」进通道）
``conditional_edges``  **恒空**（本 feature）⇒ 非空即**显式失败**
``model_factory``      **恒空**（本 feature）⇒ 非空即**显式失败**
======================  ======================================================

**三条纪律**：

* **MUST NOT** 用 ``exec`` / 动态求值构造 schema（FR-033）⇒ 用
  ``typing.TypedDict("名称", {...})`` 的**函数式**写法；
* **两侧 MUST 消费同一个 ``TypedDict`` 对象**（FR-033 · 裁定 21）⇒
  ``schema_typed`` 由 :func:`build_graph_spec` **构造一次**并放进图规格；
* **模型工厂钩子恒空**（FR-036 · 裁定 26）⇒ 非空即**显式失败**
  ⇒ MUST **NOT** 自行实现 fake 注入（那归 **B25F1**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Annotated, Any, Callable, Mapping, Sequence, TypedDict

from freegraph.runtime import parse_state_schema

__all__ = [
    "NO_VALUE_TYPE",
    "GraphSpec",
    "GraphSpecError",
    "build_graph_spec",
    "build_schema_typed",
    "check_node_output",
    "validate_graph_spec",
]


class GraphSpecError(ValueError):
    """图规格的**显式失败**信号（**测试侧** · 不进内核）。

    ⚠️ 这是**测试侧**的错误类型（不属于 ``freegraph.runtime.errors`` 的
    冻结面）⇒ **零新增内核错误类型**（I-9）。
    """


#: 「**缺少值类型**」的哨兵（字段描述的 ``value_type`` 取它 ⇒ **显式失败**）。
NO_VALUE_TYPE = object()


@dataclass(frozen=True)
class GraphSpec:
    """**图规格**（**纯数据** · 契约 §2）。

    字段：

    * ``name`` —— 图规格的名字（**动态构造的 ``TypedDict`` 用它**）；
    * ``schema`` —— **字段描述**：``{key: (value_type, reducer | None)}``；
    * ``schema_typed`` —— 运行时动态构造的 ``TypedDict``（**一个**）⇒
      **两侧消费同一个对象**；
    * ``nodes`` —— ``[(节点名, 节点函数)]``（**有序** · 线性单链）；
    * ``initial_input`` —— 初始输入（按「**一次写入**」进通道）；
    * ``conditional_edges`` —— **恒空**（本 feature · 预留字段）；
    * ``model_factory`` —— **恒空**（本 feature · 预留的「模型工厂」钩子）。
    """

    name: str
    schema: Mapping[str, tuple[Any, Callable[..., Any] | None]]
    nodes: tuple[tuple[str, Callable[[dict], dict]], ...]
    initial_input: Mapping[str, Any]
    conditional_edges: tuple[Any, ...] = ()
    model_factory: Any = None
    schema_typed: type | None = None


def _hook_is_empty(value: Any) -> bool:
    """判定「**预留钩子**」是否**恒空**。

    **恒空** = ``None``（**规范写法**）**或**空的定长容器
    （``()`` / ``[]`` / ``{}`` / ``set()``）⇒ 非空 ⇒ **显式失败**。
    """
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) == 0
    return False


def validate_graph_spec(spec: GraphSpec) -> None:
    """**图规格的前置校验**（**不依赖 schema 的那部分** · 契约 §2 / §5）。

    * ``nodes`` MUST **非空**；
    * **节点名 MUST 唯一**；
    * ``conditional_edges`` MUST **为空** ⇒ 非空即**显式失败**（裁定 15）——
      MUST **NOT** 静默忽略；
    * ``model_factory`` MUST **恒空** ⇒ 非空即**显式失败**（FR-036 · 裁定 26）——
      MUST **NOT** 静默忽略 · MUST **NOT** 自行实现 fake 注入。

    ⚠️ **节点函数 MUST 是确定性且零网络的** —— 那是**人工审查**项
    （契约 §5 · SC-017）⇒ 本函数**只**做**可判定**的那部分。
    """
    if not spec.nodes:
        raise GraphSpecError("图规格的 nodes MUST 非空")

    names = [name for name, _ in spec.nodes]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise GraphSpecError(f"节点名 MUST 唯一 —— 重复：{duplicates}")

    if spec.conditional_edges:
        raise GraphSpecError(
            "本 feature 的 conditional_edges MUST 恒空（预留字段）—— "
            f"实得：{spec.conditional_edges!r}"
        )

    if not _hook_is_empty(spec.model_factory):
        raise GraphSpecError(
            "本 feature 的 model_factory MUST 恒空（预留钩子 · fake 注入归 B25F1）"
        )


def _unpack_description(key: str, description: Any) -> tuple[Any, Any]:
    """拆开字段描述 ⇒ ``(value_type, reducer)``（**形状不符 ⇒ 显式失败**）。"""
    if not isinstance(description, tuple) or len(description) != 2:
        raise GraphSpecError(
            f"字段 {key!r} 的描述 MUST 是 (value_type, reducer) 二元组 —— "
            f"实得：{description!r}"
        )
    return description[0], description[1]


def build_schema_typed(spec: GraphSpec) -> type:
    """**动态构造**一个真的 ``TypedDict``（**函数式**写法 · MUST NOT 用 ``exec``）。

    * 有归约器的字段 ⇒ ``Annotated[value_type, reducer]``；
    * 无归约器的字段 ⇒ ``value_type``；
    * **缺少值类型**的字段 ⇒ **显式失败**（构造不出 ``TypedDict``
      ⇒ 两边都拼不出图 · 契约 §5 的 **V-7**）。

    ⚠️ 两侧 MUST 消费**同一个对象** ⇒ 本函数由 :func:`build_graph_spec`
    **只调用一次**，产物放进 ``schema_typed``。
    """
    fields: dict[str, Any] = {}
    for key, description in spec.schema.items():
        value_type, reducer = _unpack_description(key, description)
        if value_type is NO_VALUE_TYPE:
            raise GraphSpecError(f"字段 {key!r} 的描述缺少值类型")
        fields[key] = (
            Annotated[value_type, reducer] if reducer is not None else value_type
        )
    return TypedDict(spec.name, fields)


def build_graph_spec(
    *,
    name: str,
    schema: Mapping[str, tuple[Any, Callable[..., Any] | None]],
    nodes: Sequence[tuple[str, Callable[[dict], dict]]],
    initial_input: Mapping[str, Any],
    conditional_edges: Sequence[Any] = (),
    model_factory: Any = None,
) -> GraphSpec:
    """**构造**一份图规格（**前置校验** + **动态构造** ``TypedDict``）。

    步骤：

    ① **前置校验**（不依赖 schema 的那部分 · :func:`validate_graph_spec`）；
    ② **动态构造** ``TypedDict``（**一个** · :func:`build_schema_typed`）；
    ③ **依赖 schema 的校验**：

       * 字段描述里的**值类型无法被 B4F1 解析** ⇒ **显式失败**
         （MUST **NOT** 静默跳过该字段）⇒ 错误**向上传播**；
       * **初始输入**含 schema 之外的 key ⇒ **显式失败**
         （MUST **NOT** 静默丢弃 · MUST **NOT** 塞进「未知通道」）。

    ⚠️ ③ 的**运行时**子情形（节点返回 schema 之外的 key · 初始值与归约器
    不兼容）由 :func:`check_node_output` 与驱动器承担。
    """
    spec = GraphSpec(
        name=name,
        schema=dict(schema),
        nodes=tuple(nodes),
        initial_input=dict(initial_input),
        conditional_edges=tuple(conditional_edges),
        model_factory=model_factory,
    )
    validate_graph_spec(spec)

    schema_typed = build_schema_typed(spec)
    # ③ 字段描述里的值类型无法被 B4F1 解析 ⇒ 错误**向上传播**（显式失败）。
    parse_state_schema(schema_typed)

    unknown = sorted(set(spec.initial_input) - set(spec.schema))
    if unknown:
        raise GraphSpecError(
            f"初始输入含 schema 之外的 key：{unknown} —— MUST 显式失败"
            "（MUST NOT 静默丢弃）"
        )

    return replace(spec, schema_typed=schema_typed)


def check_node_output(
    spec: GraphSpec,
    node_name: str,
    output: Any,
) -> Mapping[str, Any]:
    """**校验**一个节点的返回值（**依赖 schema 的那部分** · 裁定 15 / DR-2）。

    * 返回值 MUST 是**映射**（``None`` 视为「无更新」）；
    * 返回的 key MUST **全在** schema 里 ⇒ 否则**显式失败**
      （MUST **NOT** 静默接受 schema 之外的 key）。

    ⚠️ 上游对未知 key **静默丢弃** ⇒ 两侧**不等价地失败** ⇒ 该场景
    **不进入**差分比对（契约 §5）⇒ 由 freegraph 的**单元测试独占断言**。
    """
    if output is None:
        return {}
    if not isinstance(output, Mapping):
        raise GraphSpecError(
            f"节点 {node_name!r} 的返回值 MUST 是映射 —— 实得：{type(output).__name__}"
        )
    unknown = sorted(set(output) - set(spec.schema))
    if unknown:
        raise GraphSpecError(
            f"节点 {node_name!r} 返回了 schema 之外的 key：{unknown}"
            " —— MUST 显式失败"
        )
    return output
