# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""状态 schema 解析 + **通道规格**产物 —— B4F1 的主流程。

**输入**：用户提供的**标准 ``TypedDict``** 状态 schema（C1 · FR-001）。
**输出**：不可变的 :class:`SchemaSpec`（保序的 ``channels`` 映射 + ``keys``
序列）—— **每个 key 恰一条** :class:`ChannelSpec`（FR-002 · SC-008）。

**本模块只解析、不执行**：

* 覆盖语义的**执行**归 **B5F1**（``LastValue``）——本模块**只标记**
  ``semantics = "overwrite"``（FR-006 ① · C3）；
* 归约器的**执行**归 **B5F1 / B7F1** ——本模块**从不调用**它
  （FR-013 · SC-009）。

**判定口径**（二元性 / 归约器提取）在
``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``
（**唯一权威**）——实现见同层的 :mod:`freegraph.runtime.reducer`。
"""

from __future__ import annotations

import re
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import (
    Any,
    NoReturn,
    NotRequired,
    Required,
    TypedDict,
    get_type_hints,
    is_typeddict,
)

from .errors import (
    REASON_ANNOTATION_UNRESOLVABLE,
    REASON_NOT_A_STATE_SCHEMA,
    REASON_REDUCER_NOT_BINARY,
    InvalidSchemaError,
)
from .reducer import _extract_reducer, _is_binary_operator

__all__ = [
    "ChannelSpec",
    "SchemaSpec",
    "parse_state_schema",
]

#: ``TypedDict`` 里的**伪 key**（上游同做法 · 裁定 12）⇒ MUST 被跳过。
_SLOTS_KEY = "__slots__"

#: 语义标记的**封闭取值域**（FR-006 · FR-020 ①）。
SEMANTICS_OVERWRITE = "overwrite"
SEMANTICS_REDUCE = "reduce"

#: 内存地址形态（``0x…``）⇒ 投影 MUST NOT 含它（FR-011 ④ · SC-005）。
_ADDRESS_PATTERN = re.compile(r"0x[0-9a-fA-F]+")


@dataclass(frozen=True, slots=True, kw_only=True)
class ChannelSpec:
    """**单个 key** 的通道规格（不可变纯数据 · FR-010 · FR-020 ①）。

    字段（名字**逐字冻结** · 澄清 **Q8**）：

    * ``key`` —— schema 中的 key 名；
    * ``value_type`` —— **归约前的基类型 ``T``**（``Annotated[T, ...]`` 的
      ``T``；**不含** ``Annotated`` 包装 —— 澄清 **Q1** · FR-002）；
    * ``reducer`` —— 归约器**引用**（**按引用**持有 —— FR-012），
      无归约器时为**空**；
    * ``has_reducer`` —— 是否带归约器；
    * ``semantics`` —— 语义标记，取值域**恰为**
      ``{"overwrite", "reduce"}``（FR-006 · FR-020 ①）；
    * ``required`` —— 必选 / 可选标记（**只记录不执行** · FR-021 ·
      澄清 **Q2**）。

    ⚠️ **「二元性」不落字段**（FR-020 ①）⇒ 其可判定形式 =
    「非二元 ⇒ 抛 ``InvalidSchemaError``」（FR-007 ②）+ 判定表逐条比对
    （SC-004）。

    **显式不可哈希**（research D-01）：frozen dataclass 默认**仍会**生成
    ``__hash__``，而 ``reducer`` 可能是**不可哈希的可调用实例**
    ⇒ 自动生成的 ``__hash__`` 会在用户数据上抛 ``TypeError``
    ⇒ 类体 MUST **显式**写 ``__hash__ = None``。
    """

    key: str
    value_type: Any
    reducer: Callable[..., Any] | None = None
    has_reducer: bool = False
    semantics: str = SEMANTICS_OVERWRITE
    required: bool = True

    __hash__ = None

    def to_dict(self) -> dict[str, Any]:
        """**可 JSON 序列化**的投影（FR-011 · data-model §8）。

        字段构成与顺序逐字取自 data-model §8；「类型的可读文本」口径 =
        research **D-05**；「归约器标识」口径 = research **D-06** 4 级规则。

        MUST NOT 含**内存地址形态**（``0x…``）⇒ 两次投影**逐字一致**
        （SC-005 · I-9）。
        """
        return {
            "key": self.key,
            "value_type": _readable_type(self.value_type),
            "has_reducer": self.has_reducer,
            "semantics": self.semantics,
            "required": self.required,
            "reducer": (
                None if self.reducer is None else _readable_reducer(self.reducer)
            ),
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaSpec:
    """**整份 schema** 的解析产物（不可变纯数据 · FR-010 · FR-020 ②）。

    字段：

    * ``channels`` —— **保序**的「key → :class:`ChannelSpec`」映射
      （构造时包成 ``types.MappingProxyType`` ⇒ **结构性不可变**，
      写操作抛 ``TypeError`` —— research D-02）；
    * ``keys`` —— **有序**的 key 序列（顺序 = ``get_type_hints`` 的
      **插入序**：父类 key 在前 · 同名覆盖保持原位 —— research D-10）。

    「**零条规格**」是合法形态（空 TypedDict ⇒ 空映射 + 空元组，
    **不是**错误）。

    **显式不可哈希**（research D-02）：``MappingProxyType`` 本身不可哈希
    ⇒ 自动生成的 ``__hash__`` 会在 ``hash(spec)`` 时抛 ``TypeError``。
    """

    channels: Mapping[str, ChannelSpec]
    keys: tuple[str, ...]

    __hash__ = None

    def __post_init__(self) -> None:
        """把 ``channels`` 包成 ``MappingProxyType`` ⇒ **结构性不可变**。"""
        object.__setattr__(
            self, "channels", types.MappingProxyType(dict(self.channels))
        )
        object.__setattr__(self, "keys", tuple(self.keys))

    def to_dict(self) -> dict[str, Any]:
        """**可 JSON 序列化**的投影（FR-011 · data-model §8）。

        ``channels`` 按 ``keys`` 的顺序排列 ⇒ 投影**确定性**。
        """
        return {
            "keys": list(self.keys),
            "channels": [self.channels[key].to_dict() for key in self.keys],
        }


def parse_state_schema(schema: Any) -> SchemaSpec:
    """解析一份状态 schema ⇒ **保序**的通道规格集（**唯一**解析入口）。

    流程（FR-001 ~ FR-021）：

    1. **鸭子判定** schema 是不是 ``TypedDict`` ⇒ 否则抛
       ``InvalidSchemaError(key=None, reason="not_a_state_schema")``；
    2. ``get_type_hints(schema, include_extras=True)`` 解析注解
       （**保留** PEP 593 元数据 —— 裁定 5）；失败 ⇒ 逐 key 探针
       **指名**出错 key（research D-04）；
    3. 按 key 的**解析顺序**遍历 ⇒ 剥离**顶层** ``Required`` /
       ``NotRequired``（裁定 4）⇒ 取**基类型**与**末位元数据**；
    4. 末位是 callable 但**非二元** ⇒ 抛
       ``InvalidSchemaError(key=该 key, reason="reducer_not_binary")``
       （FR-007 ② —— **MUST NOT** 静默降级）；
    5. 组装 :class:`SchemaSpec`（**保序**）。

    **快速失败**（FR-007 ④ · 澄清 **Q3**）：按 key 的解析顺序逐个检查，
    命中**第一个**问题即抛出（MUST NOT 汇总多个问题）。

    **纯函数**（FR-013）：不调用归约器 · 不读环境变量 · 不出站 ·
    不写文件。
    """
    if not _is_state_schema(schema):
        raise InvalidSchemaError(key=None, reason=REASON_NOT_A_STATE_SCHEMA)

    annotations = _resolve_annotations(schema)
    required_keys = frozenset(getattr(schema, "__required_keys__", frozenset()))

    channels: dict[str, ChannelSpec] = {}
    keys: list[str] = []
    for key, annotation in annotations.items():
        if key == _SLOTS_KEY:
            continue
        stripped = _strip_requiredness(annotation)
        # ⚠️ **上游同款**（2026-11-12 上游对齐 P3 · 上游 ``graph/state.py:1862-1872``）：
        # 上游把**原始注解**（**保留 ``Annotated``**）交给通道（``LastValue(annotation)`` /
        # ``BinaryOperatorAggregate(annotation)``）⇒ 通道的 ``typ`` **带** ``Annotated`` ⇒
        # freegraph 的 ``value_type`` **同款**（**语义变更**：由「基类型 T」改为「原始注解」）
        # ⇒ **空值推导**那一侧仍由 B5F1 的宽口径剥离负责（上游 ``binop.py:22-30``）⇒ 两端口径一致。
        value_type = stripped
        candidate = _extract_reducer(stripped)
        if candidate is None:
            reducer: Callable[..., Any] | None = None
            has_reducer = False
            semantics = SEMANTICS_OVERWRITE
        else:
            if not _is_binary_operator(candidate):
                raise InvalidSchemaError(key=key, reason=REASON_REDUCER_NOT_BINARY)
            reducer = candidate
            has_reducer = True
            semantics = SEMANTICS_REDUCE
        channels[key] = ChannelSpec(
            key=key,
            value_type=value_type,
            reducer=reducer,
            has_reducer=has_reducer,
            semantics=semantics,
            required=key in required_keys,
        )
        keys.append(key)

    return SchemaSpec(channels=channels, keys=tuple(keys))


def _is_state_schema(candidate: Any) -> bool:
    """判定「是不是状态 schema」（FR-001 ① · 裁定 3）。

    ⚠️ **上游同款**（**2026-11-12 上游对齐 P3** · 上游
    ``langgraph/graph/state.py:1818``）：上游的判据**只有一条** ——
    「**有** ``__annotations__``」⇒ **pydantic 模型 / dataclass / 普通类**
    **一律接受**（上游把它们都当状态 schema）。

    ⇒ freegraph 采**同一条**判据 ⇒ **放宽**（原先要求「是 ``dict`` 的子类」+
    「有 ``__total__``」⇒ 只认 ``TypedDict``）⇒ 上游形状的 schema **直接可解析**。

    ⚠️ **``typing_extensions.TypedDict`` 仍然可用**：它有 ``__annotations__``
    ⇒ 命中本判据（**实测**：``typing.is_typeddict`` 对其返回 ``False`` ⇒
    **不能**只用它判定）⇒ 内核 MUST NOT import ``typing_extensions``
    （FR-001 ② · FR-013）。

    ⚠️ **零通道的 schema 仍被拒**（``REASON_NOT_A_STATE_SCHEMA``）—— 上游对这类 schema
    建**单根** ``__root__`` 通道（上游 ``graph/state.py:1819-1823``）⇒ **该形态的运行期语义
    归 B7F1 / B8F1**（根通道的聚合）⇒ 本层**只**放宽到「有**非空** ``__annotations__``」
    这一类（**上游同款**且**零依赖**）。

    ⚠️ **与上游的一处**刻意**收紧**（**只针对「实例」**）：上游只判 ``hasattr`` ⇒ 一个
    **实例**也会命中（类属性可见）⇒ 但上游随后 ``get_type_hints(instance)`` **会抛**
    ``TypeError`` ⇒ freegraph 要求「**是类**且有 ``__annotations__``」⇒ **实例**被显式拒绝
    （失败信号更可诊断）⇒ **成功路径与上游逐字同款**。

    ⚠️ **空 schema（零个 key）仍然合法**（B4F1 的既有冻结口径）⇒ 产出**零条**通道规格
    （Python 3.10+ 里任何类都**自动**获得一个**空** ``__annotations__`` ⇒ 空 ``TypedDict``
    命中本判据 ⇒ 零通道 ⇒ **合法**）。
    """
    return isinstance(candidate, type) and hasattr(candidate, "__annotations__")


def _resolve_annotations(schema: Any) -> dict[str, Any]:
    """以**保留 ``Annotated`` 附加信息**的方式解析注解（FR-009 · 裁定 5）。

    主路径：``get_type_hints(schema, include_extras=True)``（一次调用）。

    失败路径（research D-04）：按 ``schema.__annotations__`` 的键序逐个
    构造**单键探针** ``TypedDict("_Probe", {key: ann})`` ⇒ 命中**第一个**
    失败者 ⇒ 抛 ``InvalidSchemaError(key=该 key,
    reason="annotation_unresolvable")``。

    ⚠️ ``schema.__annotations__`` **已合并继承链**（CPython
    ``_TypedDictMeta`` 的既有行为）⇒ **父类上的坏注解同样能被指名**。

    ⚠️ 探针 MUST NOT 手工 ``eval`` 注解字符串 ⇒ 命名空间解析规则与
    ``get_type_hints`` 完全一致。
    """
    try:
        return dict(get_type_hints(schema, include_extras=True))
    except Exception as error:
        _raise_annotation_unresolvable(schema, error)


def _raise_annotation_unresolvable(schema: Any, error: Exception) -> NoReturn:
    """逐 key 探针 ⇒ **指名**出错 key（research D-04）。"""
    annotations = getattr(schema, "__annotations__", {})
    for key, annotation in annotations.items():
        if key == _SLOTS_KEY:
            continue
        try:
            probe = TypedDict("_Probe", {key: annotation})
            get_type_hints(probe, include_extras=True)
        except Exception:
            raise InvalidSchemaError(
                key=key, reason=REASON_ANNOTATION_UNRESOLVABLE
            ) from error
    raise InvalidSchemaError(key=None, reason=REASON_ANNOTATION_UNRESOLVABLE) from error


def _strip_requiredness(annotation: Any) -> Any:
    """剥离**顶层**的 ``Required[...]`` / ``NotRequired[...]``（FR-008 · 裁定 4）。

    ⚠️ **只剥离顶层**（PEP 655）⇒ ``Annotated[Required[T], reducer]`` 的
    ``value_type`` = ``Required[T]``（**不递归剥离** —— research DR-9）。
    """
    origin = getattr(annotation, "__origin__", None)
    if origin is Required or origin is NotRequired:
        arguments = getattr(annotation, "__args__", ())
        if arguments:
            return arguments[0]
    return annotation


def _base_type(annotation: Any) -> Any:
    """取**归约前的基类型 ``T``**（澄清 **Q1** · FR-002）。

    只有**带** ``Annotated`` 元数据时才取 ``__origin__`` ⇒
    ``Annotated[list[int], reducer]`` 的基类型是 ``list[int]``（**不是**
    ``list``）；无 ``Annotated`` 时基类型即该 key 的类型本身。
    """
    if getattr(annotation, "__metadata__", None) is not None:
        return annotation.__origin__
    return annotation


def _readable_type(value_type: Any) -> str:
    """「类型的可读文本」的**规范化**口径（research **D-05**）。

    ① ``isinstance(value_type, type)`` ⇒ 取 ``value_type.__name__``
    （``int`` / ``MyState``）；② 否则 ⇒ ``str(value_type)`` 去
    ``typing.`` 前缀（``list[int]`` → ``"list[int]``）。

    ⚠️ **不能**直接用 ``str()``：``str(int)`` == ``"<class 'int'>"``。
    """
    # ⚠️ **2026-11-12 上游对齐 P3**：`value_type` 现在**保留** ``Annotated`` 原样
    # （上游同款）⇒ 它的 ``str()`` **带**元数据的 repr（归约器若是 lambda ⇒ **带内存地址**）
    # ⇒ 投影里 MUST **只渲染基类型** ⇒ 仍是**确定性**且**不泄漏地址**。
    if getattr(value_type, "__metadata__", None) is not None:
        value_type = value_type.__origin__
    if isinstance(value_type, type):
        return value_type.__name__
    return str(value_type).replace("typing.", "")


def _readable_reducer(reducer: Any) -> str:
    """归约器的**可读标识**（4 级规则 · 澄清 **Q10** · research **D-06**）。

    ① 对象自身有 ``__module__`` 且有 ``__qualname__`` ⇒
    ``"{__module__}.{__qualname__}"``；
    ② 对象**无** ``__qualname__``（可调用实例）⇒ 取**其类型**的模块名 +
    限定名；
    ③ 再取不到 ⇒ ``__name__``；
    ④ 最后兜底 ``repr(obj)``，且 MUST **抹除内存地址形态**
    （``0x…`` → 固定占位）。

    ⇒ 投影 MUST NOT 含内存地址（否则快照测试假红 · SC-005）。
    """
    module = getattr(reducer, "__module__", None)
    qualname = getattr(reducer, "__qualname__", None)
    if module and qualname:
        return f"{module}.{qualname}"
    if qualname is None:
        reducer_type = type(reducer)
        type_module = getattr(reducer_type, "__module__", None)
        type_qualname = getattr(reducer_type, "__qualname__", None)
        if type_module and type_qualname:
            return f"{type_module}.{type_qualname}"
    name = getattr(reducer, "__name__", None)
    if name:
        return name
    return _ADDRESS_PATTERN.sub("<addr>", repr(reducer))
