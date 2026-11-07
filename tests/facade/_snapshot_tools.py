# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""API 快照的**渲染器**（纯函数 · 无 I/O · 无副作用）。

两个入口：

* :func:`normalize_annotation` —— 注解规范化 **N-1…N-6**
  （权威：``contracts/snapshot-format.md`` §2）；
* :func:`render_api_snapshot` —— 把一个**命名空间**渲染成快照文本
  （条目语法 §1 / 文本层规则 §3）。

**为何 MUST 是纯函数**（research D-10）：门禁自检 MUST 证明「比对路径
**确实**抓得出漂移」，而自检 MUST **不碰真源码**（可在只读环境跑）⇒
渲染器 MUST 接受**人造命名空间**。

**文本层规则**（``contracts/snapshot-format.md`` §3）：

======  ==========================================================
T-1    编码 **UTF-8**（无 BOM）
T-2    换行 **LF**
T-3    **末行带换行**
T-4    顶级条目无缩进；类内条目**缩进 2 空格**
T-5    顶级条目与类内条目**均按名字排序**（字典序）
T-6    **参数顺序逐字保留**（顺序是语义，不排序）
T-7    缺省值用 ``repr`` 形态；空容器记 ``{}`` / ``()``；必填记 ``<required>``
T-8    注释头**只允许**出现在文件**顶部**
======  ==========================================================

**类内条目的排列**：**属性**（按名排序）在前、**方法**（按名排序）在后——
两种 kind **各按自己的名字排序**（spec FR-010 ②：「符号名、类内方法名与
属性名均按字典序」）。

**dataclass 属性的取数** MUST 逐条实现 ``contracts/snapshot-format.md``
§1.1 的 **D-21-1…D-21-4**（缺省值取 ``dataclasses.fields()``、``ClassVar``
取 ``cls.__annotations__``、frozen ⇒ ``(readonly)``、注解取
``fields()[i].type``）——**MUST NOT** 用 ``getattr(cls, name)`` 取缺省值
（``slots=True`` 时那会拿到 ``member_descriptor``，是**实现细节**）。
"""

from __future__ import annotations

import dataclasses
import inspect
import re
import types
import typing
from collections.abc import Mapping
from typing import Any

__all__ = ["normalize_annotation", "render_api_snapshot"]

_NONE_TYPE = type(None)

#: 快照文件的注释头（**只出现在顶部** · T-8）。
HEADER = (
    "# freegraph 公开 API 快照 —— 门面 `freegraph.graph`\n"
    "# 本文件由 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` "
    "生成，请勿手工编辑。\n"
    "# 格式契约：specs/b2f2-public-api-facade/contracts/snapshot-format.md\n"
    "# 导出面清单（哪些符号算公开）的权威是 contracts/facade-api.md §0；"
    "本文件只记录签名。\n"
    "#\n"
)

#: 必填参数 / 必填属性的缺省占位符（**逐字固定** · T-7）。
REQUIRED = "<required>"


# ── N-1…N-6 · 注解规范化 ───────────────────────────────────────────────


def _strip_qualifiers(text: str) -> str:
    """N-2 —— 去掉 ``typing.`` / ``collections.abc.`` 限定前缀。"""
    text = re.sub(r"\btyping\.", "", text)
    text = re.sub(r"\bcollections\.abc\.", "", text)
    return text


def _split_top_level(text: str) -> list[str]:
    """按**顶层**逗号切分（括号内的逗号不切）。"""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return [part.strip() for part in parts if part.strip()]


def _match_bracket(text: str, open_index: int) -> int:
    """返回与 ``text[open_index] == '['`` 配对的 ``]`` 下标（找不到 = -1）。"""
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _rewrite_union_forms(text: str) -> str:
    """N-3 —— ``Optional[X]`` → ``X | None``；``Union[X, Y]`` → ``X | Y``。

    **保持原成员顺序**（``Union[int, str]`` ⇒ ``int | str``，不排序）。
    递归处理内层 ⇒ 嵌套形态亦被收敛。
    """
    for name in ("Optional", "Union"):
        while True:
            index = text.find(name + "[")
            if index == -1:
                break
            if index > 0 and (text[index - 1].isalnum() or text[index - 1] in "_."):
                break
            open_index = index + len(name)
            end = _match_bracket(text, open_index)
            if end == -1:
                break
            inner = _rewrite_union_forms(text[open_index + 1 : end])
            parts = _split_top_level(inner)
            if name == "Optional":
                parts = parts + ["None"]
            text = text[:index] + " | ".join(parts) + text[end + 1 :]
    return text


def _normalize_text(text: str) -> str:
    """字符串形态的注解规范化（N-1 … N-5）。"""
    text = text.strip()
    # N-1 —— 去掉外层引号。
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    # N-2 —— 去掉限定前缀。
    text = _strip_qualifiers(text)
    # N-3 —— Optional / Union 收敛。
    text = _rewrite_union_forms(text)
    # N-4 —— NoneType → None。
    text = re.sub(r"\bNoneType\b", "None", text)
    # N-5 —— 空白归一为单空格。
    return " ".join(text.split())


def _origin_name(origin: Any) -> str:
    """取 ``get_origin`` 结果的**短名**（去限定前缀）。"""
    name = getattr(origin, "__name__", None)
    if isinstance(name, str) and name:
        return _strip_qualifiers(name)
    return _strip_qualifiers(str(origin))


def normalize_annotation(ann: Any) -> str:
    """把一个注解**对象**（或字符串）渲染成快照里的规范形态。

    逐条实现 ``contracts/snapshot-format.md`` §2 的 **N-1…N-6**：

    ====== ==========================================================
    N-1    去掉字符串注解的外层引号
    N-2    去掉 ``typing.`` / ``collections.abc.`` 限定前缀
    N-3    ``Optional[X]`` → ``X | None``；``Union[X, Y]`` → ``X | Y``
    N-4    ``NoneType`` → ``None``
    N-5    空白归一为单空格（缺省值另用 ``repr`` 形态）
    N-6    无注解时记 ``None``（返回注解写成 ``-> None``）
    ====== ==========================================================
    """
    if ann is None or ann is _NONE_TYPE:
        return "None"  # N-4
    if ann is inspect.Signature.empty:
        return "None"  # N-6
    if isinstance(ann, str):
        return _normalize_text(ann)  # N-1 … N-5
    if ann is Ellipsis:
        return "..."
    origin = typing.get_origin(ann)
    if origin is not None:
        args = typing.get_args(ann)
        if origin is typing.Literal:
            return "Literal[" + ", ".join(repr(arg) for arg in args) + "]"
        if origin is typing.Union or origin is types.UnionType:
            # N-3 —— 保持原成员顺序。
            return " | ".join(normalize_annotation(arg) for arg in args)
        base = _origin_name(origin)
        if not args:
            return base
        inner = ", ".join(normalize_annotation(arg) for arg in args)
        return f"{base}[{inner}]"
    name = getattr(ann, "__name__", None)
    if isinstance(name, str) and name:
        return _strip_qualifiers(name)
    return _strip_qualifiers(str(ann))


# ── 签名渲染 ───────────────────────────────────────────────────────────


def _dataclass_field_defaults(cls: type) -> dict[str, Any]:
    """D-21-1 —— 取 dataclass 字段的**缺省值**（含 ``default_factory``）。

    **MUST NOT** 用 ``getattr(cls, name)``——``slots=True`` 时那会拿到
    ``member_descriptor``（实现细节）。
    """
    defaults: dict[str, Any] = {}
    if not dataclasses.is_dataclass(cls):
        return defaults
    for field in dataclasses.fields(cls):
        if field.default is not dataclasses.MISSING:
            defaults[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            defaults[field.name] = field.default_factory()
    return defaults


def _is_class_var(annotation: Any) -> bool:
    """判定一个注解是否为 ``ClassVar``（D-21-2）。"""
    if annotation is typing.ClassVar:
        return True
    if typing.get_origin(annotation) is typing.ClassVar:
        return True
    if isinstance(annotation, str):
        return annotation.strip().startswith(("ClassVar", "typing.ClassVar"))
    return False


def _render_parameter(
    parameter: inspect.Parameter, overrides: Mapping[str, Any]
) -> str:
    """渲染单个参数（T-6：顺序逐字保留 · T-7：缺省用 ``repr``）。"""
    if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
        return f"*{parameter.name}"
    if parameter.kind is inspect.Parameter.VAR_KEYWORD:
        return f"**{parameter.name}"
    text = parameter.name
    if parameter.annotation is not inspect.Parameter.empty:
        text += f": {normalize_annotation(parameter.annotation)}"
    if parameter.name in overrides:
        text += f" = {overrides[parameter.name]!r}"
    elif parameter.default is not inspect.Parameter.empty:
        text += f" = {parameter.default!r}"
    return text


def _render_signature(func: Any, overrides: Mapping[str, Any]) -> str:
    """渲染一个可调用对象的完整调用签名（``(参数) -> 返回注解``）。"""
    signature = inspect.signature(func)
    parts: list[str] = []
    keyword_only_started = False
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY and not (
            keyword_only_started
        ):
            parts.append("*")
            keyword_only_started = True
        parts.append(_render_parameter(parameter, overrides))
    return_annotation = signature.return_annotation
    if return_annotation is inspect.Signature.empty:
        return_annotation = None  # N-6
    return "(" + ", ".join(parts) + ") -> " + normalize_annotation(return_annotation)


# ── 类成员渲染 ─────────────────────────────────────────────────────────


def _dataclass_is_frozen(cls: type) -> bool:
    """D-21-3 —— dataclass 是否 ``frozen=True``。"""
    params = getattr(cls, "__dataclass_params__", None)
    return bool(getattr(params, "frozen", False))


def _render_attributes(cls: type) -> list[str]:
    """渲染类的**公开属性**（dataclass 字段 / ``ClassVar`` / ``property``）。

    取数规则逐条实现 ``contracts/snapshot-format.md`` §1.1 的
    **D-21-1…D-21-4**。
    """
    entries: dict[str, str] = {}
    defaults = _dataclass_field_defaults(cls)
    frozen = _dataclass_is_frozen(cls)

    # D-21-1 / D-21-4 —— dataclass 字段。
    for field in dataclasses.fields(cls) if dataclasses.is_dataclass(cls) else ():
        if field.name.startswith("_"):
            continue
        annotation = normalize_annotation(field.type)
        default = defaults.get(field.name, REQUIRED)
        marker = "(readonly)" if frozen else "(writable)"
        rendered = REQUIRED if default is REQUIRED else repr(default)
        entries[field.name] = f"{field.name}: {annotation} = {rendered} {marker}"

    # D-21-2 —— ClassVar（``dataclasses.fields()`` 不含）。
    annotations = dict(getattr(cls, "__annotations__", {}) or {})
    for name, annotation in annotations.items():
        if name.startswith("_") or not _is_class_var(annotation):
            continue
        default = getattr(cls, name, REQUIRED)
        marker = "(readonly)" if frozen else "(writable)"
        entries[name] = (
            f"{name}: {normalize_annotation(annotation)} = {default!r} {marker}"
        )

    # property —— ``fset is None`` ⇒ 只读。
    for name, value in vars(cls).items():
        if name.startswith("_") or not isinstance(value, property):
            continue
        getter = value.fget
        annotation: Any = None
        if getter is not None:
            annotation = inspect.signature(getter).return_annotation
            if annotation is inspect.Signature.empty:
                annotation = None
        marker = "(readonly)" if value.fset is None else "(writable)"
        entries[name] = (
            f"{name}: {normalize_annotation(annotation)} = {REQUIRED} {marker}"
        )

    return [entries[name] for name in sorted(entries)]


def _render_methods(cls: type) -> list[str]:
    """渲染类的**公开方法**（含 ``__init__``；其余 dunder 不记）。"""
    overrides = _dataclass_field_defaults(cls)
    entries: dict[str, str] = {}
    for name, value in vars(cls).items():
        if name.startswith("_") and name != "__init__":
            continue
        if isinstance(value, classmethod):
            func: Any = value.__func__
        elif isinstance(value, staticmethod):
            func = value.__func__
        elif inspect.isfunction(value):
            func = value
        else:
            continue
        entries[name] = f"{name}{_render_signature(func, overrides)}"
    return [entries[name] for name in sorted(entries)]


def _render_class(name: str, cls: type) -> list[str]:
    """渲染一个类：``[class]`` + 属性（按名） + 方法（按名）。"""
    lines = [f"[class] {name}"]
    lines.extend(f"    [attribute] {text}" for text in _render_attributes(cls))
    lines.extend(f"    [method] {text}" for text in _render_methods(cls))
    return lines


def _render_entry(name: str, value: Any) -> list[str]:
    """渲染一个**顶级条目**（按其类别选 kind）。"""
    if isinstance(value, type):
        return _render_class(name, value)
    if inspect.isfunction(value) or inspect.ismethod(value) or inspect.isbuiltin(
        value
    ):
        return [f"[function] {name}{_render_signature(value, {})}"]
    return [f"[constant] {name} = {value!r}"]


def render_api_snapshot(namespace: Mapping[str, Any]) -> str:
    """把一个**命名空间**渲染成 API 快照文本（**纯函数**）。

    * **输入**：门面模块的**公开名集合**
      （``{k: v for k, v in vars(freegraph.graph).items() if not k.startswith("_")}``
      ——与门禁 G15 的「公开名」口径**同源**；MUST NOT 由测试侧另造一份
      符号清单，否则快照与门面**脱钩**，冻结面失效）；
    * **输出**：快照文本（UTF-8 / LF / 末行带换行）。

    **无 I/O、无副作用**（research D-10）⇒ 门禁自检可用**人造命名空间**
    喂它，零副作用地证明「比对路径确实抓得出漂移」。
    """
    lines: list[str] = []
    for name in sorted(namespace):  # T-5 —— 顶级条目按名字排序。
        lines.extend(_render_entry(name, namespace[name]))
    return HEADER + "\n".join(lines) + "\n"
