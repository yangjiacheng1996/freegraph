# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层的**错误类型** —— 属 **B4F1**（状态 schema 解析）· **B5F1**（通道）。

本模块定义三个异常类型：

* :class:`InvalidSchemaError`（**B4F1** · 既有 · **一字不动**）——
  * **双重继承** ``FreegraphError`` + ``ValueError``
    （裁定 2 · 澄清 **Q4**）—— 用户侧 ``except FreegraphError`` 与
    ``except ValueError`` **均**能捕获到它 ⇒ **捕获** MUST NOT 要求用户
    import 具体的错误子类；
  * **结构化字段** ``key``（出错的 key；schema 级错误为**空**）与
    ``reason``（原因码 · **取值域封闭**）—— 上层 MUST **无须解析消息文本**
    即可取到全部细节（澄清 **Q7** · FR-007 ⑥）；
  * **消息**只是给人看的**英文摘要**（沿用仓库既有约定
    ``src/freegraph/contracts/errors.py``：缺省摘要为**英文**），且 MUST
    **点名**出错的 key（FR-007）。
* :class:`EmptyChannelError`（**B5F1**）—— 读取「无值」通道时抛出；
* :class:`InvalidChannelUpdateError`（**B5F1**）—— 一次写入调用中收到
  多于一个值时抛出。

**通道错误的两条继承纪律**（B5F1 FR-017 ③⑦）：

* :class:`EmptyChannelError` **仅**继承 ``FreegraphError``（**不**继承
  ``ValueError``）—— 「读到无值」是稀疏状态下的**正常信号**，若它是
  ``ValueError``，用户既有的 ``except ValueError`` 会把它一并吞掉；
* :class:`InvalidChannelUpdateError` **双重继承** ``FreegraphError`` +
  ``ValueError``（与 ``InvalidSchemaError`` 同款：既是内核错误，也是
  「传进来的东西不对」）。

**结构化字段**（名字**逐字冻结** · B5F1 FR-017 ④）：
``EmptyChannelError.key`` ·
``InvalidChannelUpdateError.key`` / ``.received_count`` / ``.expected_count``
（**恒为 1**）。

⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（B5F1 FR-017 ⑥）——
只带 key 与计数。

**读结构化字段的路径**（裁定 14 · 调和 **Q4** 与 **Q7**）：需要读取
``key`` / ``reason`` 的上层 MAY 从 ``freegraph.runtime`` import 本类
（**L2 子包**）⇒ 契约层 **18** 符号面与门面 **7** 符号面**均不变**
（零冻结面变更）。

**落位登记**（research D-08）：本类型**不进入**契约层
``src/freegraph/contracts/__init__.py`` 的 ``__all__``（18 符号面是
**冻结面** · 门禁 G7）⇒ 契约层 ``errors.py`` 的「内核异常族唯一定义处」
措辞，其适用范围是**基类与既有子类**（该 docstring 已写明「后续可新增
子类」）⇒ **登记为措辞口径的澄清，不改判据、不改该文件**。
"""

from __future__ import annotations

from freegraph.contracts.errors import FreegraphError

__all__ = [
    "EmptyChannelError",
    "InvalidChannelUpdateError",
    "InvalidSchemaError",
    "REASON_ANNOTATION_UNRESOLVABLE",
    "REASON_NOT_A_TYPED_DICT",
    "REASON_REDUCER_NOT_BINARY",
    "SCHEMA_ERROR_REASONS",
]

#: 原因码 —— schema **不是** `TypedDict`（含 Pydantic 形态 / 普通 dict / 实例）。
#: 触发时 ``key`` 为**空**（schema 级错误）。
REASON_NOT_A_TYPED_DICT = "not_a_typed_dict"

#: 原因码 —— 元数据末位是 callable 但位置参数数 **≠ 2**（含类 / 实例 /
#: 签名不可取）。触发时 ``key`` **指名**出错的 key。
REASON_REDUCER_NOT_BINARY = "reducer_not_binary"

#: 原因码 —— 注解解析失败（如不可解析的前向引用）。触发时 ``key``
#: **指名**出错的 key。
REASON_ANNOTATION_UNRESOLVABLE = "annotation_unresolvable"

#: 原因码的**封闭取值域**（FR-007 ⑥ · data-model §7）。
SCHEMA_ERROR_REASONS = frozenset(
    {
        REASON_NOT_A_TYPED_DICT,
        REASON_REDUCER_NOT_BINARY,
        REASON_ANNOTATION_UNRESOLVABLE,
    }
)


def _summarize(key: str | None, reason: str) -> str:
    """产出**英文摘要**（沿用仓库既有约定：缺省摘要为英文）。

    **点名 key**（FR-007：消息 MUST 指名出错的 key）——``key`` 为空
    （schema 级错误）时不点名。
    """
    if reason == REASON_NOT_A_TYPED_DICT:
        return "Invalid state schema: expected a TypedDict, got a non-TypedDict object"
    if reason == REASON_REDUCER_NOT_BINARY:
        return (
            "Invalid state schema: reducer for key "
            f"{key!r} must accept exactly 2 positional arguments"
        )
    if reason == REASON_ANNOTATION_UNRESOLVABLE:
        return f"Invalid state schema: cannot resolve annotation for key {key!r}"
    return f"Invalid state schema: key={key!r}, reason={reason}"


class InvalidSchemaError(FreegraphError, ValueError):
    """非法状态 schema 的**显式失败**信号（FR-007）。

    结构化属性：

    * ``key`` —— **出错的 key**（``str | None``；schema 级错误 ——
      即「不是 `TypedDict`」—— 时为**空**）；
    * ``reason`` —— **原因码**（机器可读 · **取值域封闭**）：
      ``not_a_typed_dict`` / ``reducer_not_binary`` /
      ``annotation_unresolvable``。

    错误消息**只是给人看的摘要**——上层取细节时 MUST NOT 需要解析消息，
    直接读 ``key`` / ``reason`` 即可。

    缺省摘要为**英文**，且 MUST **点名**出错的 key。
    """

    def __init__(
        self,
        key: str | None = None,
        reason: str = REASON_NOT_A_TYPED_DICT,
        *,
        message: str | None = None,
    ) -> None:
        self.key: str | None = key
        self.reason: str = reason
        super().__init__(
            message if message is not None else _summarize(key, reason)
        )


class EmptyChannelError(FreegraphError):
    """读取「**无值**」通道时的**显式失败**信号（B5F1 FR-017 ①）。

    * **继承**：**仅** ``FreegraphError``（**MUST NOT** 继承
      ``ValueError`` —— FR-017 ⑦：「读到无值」是稀疏状态下的**正常信号**，
      若它是 ``ValueError``，用户既有的 ``except ValueError`` 会把它一并吞掉）；
    * **结构化字段** ``key`` —— **出错的通道 key**（名字**逐字冻结** ·
      FR-017 ④）；
    * **消息**：**英文摘要**且**点名** key（FR-017 ⑤）。

    ⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（FR-017 ⑥）——
    只带 key。
    """

    def __init__(self, key: str, *, message: str | None = None) -> None:
        self.key: str = key
        super().__init__(
            message
            if message is not None
            else f"Channel {key!r} has no value: the channel is empty"
        )


class InvalidChannelUpdateError(FreegraphError, ValueError):
    """一次写入调用中收到**多于一个值**时的**显式失败**信号（B5F1 FR-017 ②）。

    * **继承**：``FreegraphError`` **且** ``ValueError``（与 B4F1 的
      ``InvalidSchemaError`` 同款：既是内核错误，也是「传进来的东西不对」）；
    * **结构化字段**（名字**逐字冻结** · FR-017 ④）：

      * ``key`` —— **出错的通道 key**；
      * ``received_count`` —— 本次写入调用收到的**值个数**；
      * ``expected_count`` —— 期望的值个数（**恒为 1**）；
    * **消息**：**英文摘要**且**点名** key + 计数（FR-017 ⑤）。

    ⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（FR-017 ⑥）——
    只带 key 与计数。
    """

    def __init__(
        self,
        key: str,
        received_count: int,
        expected_count: int = 1,
        *,
        message: str | None = None,
    ) -> None:
        self.key: str = key
        self.received_count: int = received_count
        self.expected_count: int = expected_count
        super().__init__(
            message
            if message is not None
            else (
                f"Channel {key!r} received {received_count} values in a single "
                f"update, expected {expected_count}"
            )
        )
