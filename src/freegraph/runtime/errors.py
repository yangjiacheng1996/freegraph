# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层的**错误类型** —— 属 **B4F1**（状态 schema 解析）· **B5F1**（通道）· **B10F1**（中断）。

本模块定义四个异常类型：

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
  多于一个值时抛出；
* :class:`InterruptError`（**B10F1** · **新增**）—— **中断 / 恢复**路径的
  **显式失败**信号（**仅**继承 ``FreegraphError`` · 带**封闭取值域**的
  ``reason`` 原因码 · **不**携带会话标识 / 中断 id 列表等**上下文**）。

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
（**恒为 1**）· ``InterruptError.reason``（**封闭 5 码**）。

⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（B5F1 FR-017 ⑥）——
只带 key 与计数。

**读结构化字段的路径**（裁定 14 · 调和 **Q4** 与 **Q7**）：需要读取
``key`` / ``reason`` 的上层 MAY 从 ``freegraph.runtime`` import 本类
（**L2 子包**）⇒ 契约层 **20** 符号面与门面 **7** 符号面**均不变**
（零冻结面变更）。

**落位登记**（research D-08）：本类型**不进入**契约层
``src/freegraph/contracts/__init__.py`` 的 ``__all__``（20 符号面是
**冻结面** · 门禁 G7）⇒ 契约层 ``errors.py`` 的「内核异常族唯一定义处」
措辞，其适用范围是**基类与既有子类**（该 docstring 已写明「后续可新增
子类」）⇒ **登记为措辞口径的澄清，不改判据、不改该文件**。
"""

from __future__ import annotations

from freegraph.contracts.errors import FreegraphError

__all__ = [
    "EmptyChannelError",
    "InterruptError",
    "InvalidChannelUpdateError",
    "InvalidSchemaError",
    "REASON_ANNOTATION_UNRESOLVABLE",
    "REASON_NOT_A_STATE_SCHEMA",
    "REASON_REDUCER_NOT_BINARY",
    "SCHEMA_ERROR_REASONS",
]

#: 原因码 —— schema **不是** `TypedDict`（含 Pydantic 形态 / 普通 dict / 实例）。
#: 触发时 ``key`` 为**空**（schema 级错误）。
REASON_NOT_A_STATE_SCHEMA = "not_a_state_schema"

#: 原因码 —— 元数据末位是 callable 但位置参数数 **≠ 2**（含类 / 实例 /
#: 签名不可取）。触发时 ``key`` **指名**出错的 key。
REASON_REDUCER_NOT_BINARY = "reducer_not_binary"

#: 原因码 —— 注解解析失败（如不可解析的前向引用）。触发时 ``key``
#: **指名**出错的 key。
REASON_ANNOTATION_UNRESOLVABLE = "annotation_unresolvable"

#: 原因码的**封闭取值域**（FR-007 ⑥ · data-model §7）。
SCHEMA_ERROR_REASONS = frozenset(
    {
        REASON_NOT_A_STATE_SCHEMA,
        REASON_REDUCER_NOT_BINARY,
        REASON_ANNOTATION_UNRESOLVABLE,
    }
)


def _summarize(key: str | None, reason: str) -> str:
    """产出**英文摘要**（沿用仓库既有约定：缺省摘要为英文）。

    **点名 key**（FR-007：消息 MUST 指名出错的 key）——``key`` 为空
    （schema 级错误）时不点名。
    """
    if reason == REASON_NOT_A_STATE_SCHEMA:
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
        reason: str = REASON_NOT_A_STATE_SCHEMA,
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


class InterruptError(FreegraphError):
    """**中断 / 恢复**路径的**显式失败**信号（**B10F1** · spec **裁定 3**）。

    **契约权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md``
    §7「失败信号汇总（**FS-1…FS-5**）」。

    * **继承**：**仅** ``FreegraphError`` ⇒ ⇒ **MUST NOT** 继承 ``ValueError``
      （用户既有的 ``except ValueError`` **不**误吞中断相关的失败 —— 沿用
      :class:`EmptyChannelError` 的继承纪律）⇒ ⇒ **L1 的 20 符号面零改动**
      （门禁 G7 / G8 / G16 / G19 恒绿）⇒ ⇒ **不**新增 L1 异常类；
    * **结构化字段**：``reason`` —— **原因码**（机器可读 · **取值域封闭**）
      ⇒ 上层 **MUST NOT** 需要解析消息文本即可取到全部细节（宪法原则 IV）；
    * ⚠️ **异常对象 MUST 只带 ``reason``** ⇒ ⇒ **不**携带会话标识 / 待恢复
      中断的 id 列表等**上下文**（那些是调用方自己传进去的）⇒ ⇒ 异常**只**
      回答「**为什么失败**」，**不**回答「**现场是什么**」（澄清轮 **Q2**）；
    * **消息**：**英文**摘要（沿用仓库既有约定）且 **MUST 点名**失败原因
      ⇒ **消息要点与上游逐字同款**（偏离登记 **X-2** · **类型**差异 ·
      **STRICTER** · 失败信号**更结构化**）。

    .. note::
       **上游同款**：上游抛内置 ``RuntimeError``
       （``langgraph/pregel/_loop.py:906`` / ``:917-919`` /
       ``langgraph/config.py:26-29``）⇒ ⇒ **不**照抄 —— L1 的
       ``FreegraphError`` docstring 承诺「上层只捕获基类 ``FreegraphError``
       即可兜住**全部**内核错误」⇒ ⇒ 抛内置 ``RuntimeError`` 会**破坏**该
       冻结承诺 ⇒ ⇒ **偏离登记 X-2**。
    """

    #: 原因码 —— 恢复时**未挂** checkpointer（契约 **FS-1**）。
    REASON_CHECKPOINTER_REQUIRED = "checkpointer_required"

    #: 原因码 —— ``Command(resume=...)`` 的 ``resume`` 位**未提供**（契约 **FS-2**）。
    REASON_RESUME_VALUE_REQUIRED = "resume_value_required"

    #: 原因码 —— **多个**挂起中断 + **单值**恢复（契约 **FS-3**）。
    REASON_AMBIGUOUS_RESUME = "ambiguous_resume"

    #: 原因码 —— 该会话**没有**挂起的中断（契约 **FS-4**）。
    REASON_NO_PENDING_INTERRUPT = "no_pending_interrupt"

    #: 原因码 —— 在**图运行之外**调用 ``interrupt()``（契约 **FS-5**）。
    REASON_NOT_IN_RUN = "not_in_run"

    #: 原因码的**封闭取值域**（spec 裁定 3 · data-model **V-9**）。
    REASONS = frozenset(
        {
            REASON_CHECKPOINTER_REQUIRED,
            REASON_RESUME_VALUE_REQUIRED,
            REASON_AMBIGUOUS_RESUME,
            REASON_NO_PENDING_INTERRUPT,
            REASON_NOT_IN_RUN,
        }
    )

    def __init__(self, reason: str, *, message: str | None = None) -> None:
        self.reason: str = reason
        super().__init__(
            message if message is not None else _interrupt_summary(reason)
        )


def _interrupt_summary(reason: str) -> str:
    """产出**中断失败**的**英文摘要**（契约 §7 的**消息要点**逐字）。

    ⚠️ **消息要点与上游逐字同款**（用户可读性不降 ⇒ 偏离登记 **X-2** 只改
    **类型**，**不**改消息要点）。
    """
    if reason == InterruptError.REASON_CHECKPOINTER_REQUIRED:
        return "Cannot resume without a checkpointer"
    if reason == InterruptError.REASON_RESUME_VALUE_REQUIRED:
        return "resume value is required"
    if reason == InterruptError.REASON_AMBIGUOUS_RESUME:
        return (
            "When there are multiple pending interrupts, you must specify "
            "the interrupt id when resuming."
        )
    if reason == InterruptError.REASON_NO_PENDING_INTERRUPT:
        return "No pending interrupt to resume"
    if reason == InterruptError.REASON_NOT_IN_RUN:
        return "interrupt() called outside of a graph run"
    return f"Interrupt failure: reason={reason}"
