# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **通道实现** —— 属 **B5F1**。

通道抽象 :class:`Channel` 与三类实现（覆盖型 / 归约型 / 路由型）——
「**覆盖 vs 归约 vs 清空**」这条状态语义在本模块**只有一处实现点**
（spec FR-001 · 收敛目标）。

**契约权威**：``specs/b5f1-channels/contracts/channel-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立一套口径。

**本模块不 import** B4F1 的 ``schema.py`` ⇒ 通道层与解析层**零耦合**；
schema → 通道的派生在同层的 :mod:`freegraph.runtime.mapping`。

**设计要点**（逐条附来源）：

* **抽象形态** = ``abc.ABC`` + ``@abstractmethod``（``update`` / ``get`` /
  ``is_available`` 是抽象方法；``clear()`` 给**默认无操作**实现）——
  research **D-01**；
* **属性只读** = ``__slots__``（4 个私有槽）+ 4 个只读 ``property``，
  ``value`` **无 setter** —— research **D-02**；
* **「无值」的内部表示** = 模块私有哨兵 ``_MISSING = object()``
  （**MUST NOT** 用 ``None`` —— ``None`` 是**合法用户值**）——
  research **D-03**；
* ``value`` 属性在「无值」时**抛** ``EmptyChannelError``（与 ``get()``
  **同义** ⇒ 不存在第三种语义）—— research **D-04**；
* **子类 MUST 声明 ``__slots__ = ()``** ⇒ 实例**无** ``__dict__``
  ⇒ 通道**结构上**不可能持有 4 项之外的数据（裁定 17 ①）。

**依赖纪律**（FR-015）：本模块只依赖**标准库**；MUST NOT import
``langchain*`` / ``langgraph*`` / ``langsmith`` / ``pydantic`` /
``typing_extensions``；MUST **零出站**、零文件 I/O、零环境变量读取。
"""

from __future__ import annotations

import abc
import collections.abc
from collections.abc import Callable, Sequence
from typing import Any, NotRequired, Required

from .errors import EmptyChannelError, InvalidChannelUpdateError

__all__ = [
    "BinaryOperatorAggregate",
    "Channel",
    "EphemeralValue",
    "LastValue",
]

#: 「**无值**」的哨兵（模块私有 · research D-03）。
#:
#: ⚠️ **MUST NOT** 用 ``None`` —— ``None`` 是**合法的用户值**
#: （FR-011 ③：「值为 ``None``」≠「无值」）⇒ 用**模块私有**对象 ⇒
#: 用户无法把它误当合法值写入。
_MISSING = object()

#: **公开别名**（上游同款 · ``langgraph._internal._typing.MISSING``）—— 第三方自定义通道实现
#: ``from_checkpoint`` 时需要它来区分「**无值**」⇒ **不**进 ``freegraph.runtime.__all__``
#: ⇒ 导出面**仍为 20**（B5F1 的冻结面**不动**）。
MISSING = _MISSING

#: **抽象容器** → **可实例化**容器的映射表（6 项 · FR-006 ② ·
#: research **D-06**）—— 与上游 ``langgraph/channels/binop.py:83-88``
#: **逐字同构**（契约 ``upstream-parity`` **P-06**）。
#:
#: ⚠️ 这四个抽象容器**直接构造必抛** ``TypeError``（抽象方法未实现）
#: ⇒ 不映射 ⇒ 这类 schema 的通道**永远**是「无值」⇒ 与上游**分叉**。
_ABSTRACT_CONTAINER_MAP: dict[Any, Any] = {
    collections.abc.Sequence: list,
    collections.abc.MutableSequence: list,
    collections.abc.Set: set,
    collections.abc.MutableSet: set,
    collections.abc.Mapping: dict,
    collections.abc.MutableMapping: dict,
}


class Channel(abc.ABC):
    """通道的**抽象基类** —— 状态读写的**唯一**实现单元（FR-001）。

    **构造签名**（**逐字冻结** · FR-002）::

        Channel(key: str, value_type: Any)

    ⚠️ 抽象基类本身**运行时不可实例化**（``abc.ABC`` + ``@abstractmethod``）
    ⇒ 「唯一实现点」是**运行时可判定**的（research **D-01**）。

    **四个操作**（**逐字冻结** · FR-002 · 契约 §2）：

    ============  ==========================================================
    ``update``    把「本步的写入序列」并入通道 ⇒ 返回「**本次调用是否写
                  入了值**」（非空 ⇒ 恒真 · 空 ⇒ 假）
    ``get``       取回通道当前值 ⇒ 无值时抛 ``EmptyChannelError``
    ``is_available``  判定「有值 / 无值」⇒ **恒不抛错**
    ``clear``     把通道恢复到「无值」⇒ 返回「**状态是否真的变化**」
    ============  ==========================================================

    **四个只读属性**（**逐字冻结** · FR-002 · 契约 §1）：
    ``key`` · ``value_type`` · ``value`` · ``reducer``。

    **默认实现**：``clear()`` = **无操作**（返回假）—— 本 feature 的**三类
    通道全部覆写**它（裁定 17 ① · FR-009）⇒ 未覆写它的**第三方自定义通道**
    在步末**不会**被清空。

    **构造 MUST 无副作用**（FR-002 ①）：不写日志 · 不读环境变量 ·
    不分配外部资源 · 不发起 I/O。
    """

    #: 5 个私有槽（**名字逐字冻结** · FR-013 ① · 澄清轮 Q15）。
    __slots__ = ("_key", "_value", "_reducer", "_value_type")

    # ── 上游对齐（2026-11-12 · P2-a）：以下成员对齐上游 ``BaseChannel``
    #    （``langgraph/channels/base.py:19-120``）⇒ 支撑「每轮新建实例」的多会话隔离。

    @property
    def typ(self) -> Any:
        """通道的**值类型**（上游 ``BaseChannel.typ`` · ``base.py:22,24-26``）。"""
        return self._value_type

    @property
    def ValueType(self) -> Any:  # noqa: N802 - 上游同款命名
        """通道里**存放的值**的类型（上游 ``BaseChannel.ValueType`` · ``base.py:28-33``）。"""
        return self._value_type

    @property
    def UpdateType(self) -> Any:  # noqa: N802 - 上游同款命名
        """通道收到的**更新值**的类型（上游 ``BaseChannel.UpdateType`` · ``base.py:35-38``）。"""
        return self._value_type

    def copy(self) -> "Channel":
        """返回通道的**副本**（上游 ``BaseChannel.copy`` · ``base.py:40-47``）。

        上游默认实现 = ``from_checkpoint(checkpoint())`` ⇒ **浅共享**同一个值对象
        （上游 ``checkpoint()`` 返回 ``get()`` 的同一对象 · ``base.py:49-58``）。
        """
        return self.from_checkpoint(self.checkpoint())

    def checkpoint(self) -> Any:
        """返回通道当前状态的**可序列化表示**（上游 ``base.py:49-58``）。

        无值 ⇒ 返回**缺失哨兵**（上游用 ``MISSING``）⇒ **不抛** ``EmptyChannelError``。
        """
        try:
            return self.get()
        except EmptyChannelError:
            return _MISSING

    @abc.abstractmethod
    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**一个同种通道（上游 ``base.py:60-65`` · 抽象方法）。

        ⇒ **每次运行新建实例** ⇒ 同一份图规格**可并发跑多次**且**互不干扰**
        （多会话隔离 · 上游同款 · ``pregel/_checkpoint.py:229-277``）。

        ⚠️ **子类 MUST 覆写**（上游同款：第三方自定义通道**必须**自己实现「按检查点重建」）
        ⇒ 子类的**构造签名** MUST 与其 ``from_checkpoint`` 的实现**自洽**。
        """
        raise NotImplementedError

    def consume(self) -> bool:
        """通知通道「订阅它的任务已执行」（上游 ``base.py:101-110``）—— 默认**无操作**。"""
        return False

    def finish(self) -> bool:
        """通知通道「本轮运行即将结束」（上游 ``base.py:112-120``）—— 默认**无操作**。"""
        return False

    def __init__(self, key: str, value_type: Any) -> None:
        """记录 key 与值类型（**无副作用** · FR-002 ①）。"""
        self._key: str = key
        self._value_type: Any = value_type
        self._value: Any = _MISSING
        self._reducer: Callable[..., Any] | None = None

    # ── 四个只读属性（FR-002 · 契约 §1）─────────────────────────────

    @property
    def key(self) -> str:
        """schema key（内部通道 MAY 为空串）。"""
        return self._key

    @property
    def value_type(self) -> Any:
        """**归约前的基类型** ``T``（与 B4F1 的 ``ChannelSpec.value_type``
        **同名同义** · 澄清轮 Q1）。

        ⚠️ 本属性**只**用于推导空值（FR-006）与承载类型信息，MUST **NOT**
        用于**校验**写入值的类型（FR-002 ② · FR-024 ③）。
        """
        return self._value_type

    @property
    def value(self) -> Any:
        """通道**当前值**（**只读**）。

        ⚠️ **与 ``get()`` 完全同义**（research **D-04**）—— 无值时**同样**
        抛 ``EmptyChannelError`` ⇒ **不存在**「无值 / 有值」之外的第三种
        语义（FR-011 · SC-004）。

        **无 setter** ⇒ 外部 MUST NOT 能改写（FR-002）。
        """
        return self.get()

    @property
    def reducer(self) -> Callable[..., Any] | None:
        """归约器**引用**（**按引用**持有 · FR-014）。

        ``LastValue`` / ``EphemeralValue`` 恒为**空**（不持有归约器）。
        """
        return self._reducer

    # ── 四个操作（FR-002 · 契约 §2）────────────────────────────────

    @abc.abstractmethod
    def update(self, values: Sequence[Any]) -> bool:
        """把「本步的写入序列」并入通道。

        返回「**本次调用是否写入了值**」——写入序列**非空 ⇒ 恒为真**
        （哪怕归约后的新值与旧值**逐字相等**）；**空序列 ⇒ 假**且值不变
        （澄清轮 **Q5** · 契约 §2.1）。

        一步内多值 ⇒ 抛 ``InvalidChannelUpdateError``（**值不变**）。
        """

    @abc.abstractmethod
    def get(self) -> Any:
        """取回通道当前值。

        无值 ⇒ 抛 ``EmptyChannelError``（MUST **NOT** 返回 ``None``
        冒充有值 · FR-011 ②）。
        """

    @abc.abstractmethod
    def is_available(self) -> bool:
        """判定「有值 / 无值」—— **恒不抛错**（FR-011 ①）。"""

    def clear(self) -> bool:
        """把通道恢复到「无值」（**默认实现 = 无操作** · 契约 §1）。

        返回「**状态是否真的变化**」——从「有值」清成「无值」⇒ 真；
        已是「无值」⇒ 无操作、返回**假**（契约 §2.2）。

        ⚠️ 本 feature 的**三类通道全部覆写**它（FR-009 · 裁定 17 ①）。
        """
        return False


class LastValue(Channel):
    """**覆盖型**通道 —— 「无归约器 ⇒ 覆盖」（C3 · FR-003）。

    **构造签名**（**逐字冻结** · FR-002）::

        LastValue(key: str, value_type: Any)

    * **归约器**：**无**（``reducer is None``）· **从不**调用任何归约器；
    * **初始状态**：**无值**（**不推导**空值 · FR-022 ①）；
    * **写入（1 个值）**：**覆盖**（旧值丢弃）⇒ 值 == 该值；
    * **写入（多于 1 个值）**：抛 ``InvalidChannelUpdateError``
      （**先检测后写入** ⇒ 值不变 · FR-004 · research **D-09**）；
    * **写入（空序列）**：无操作（返回假）；
    * **``clear()``**：**覆写** ⇒ **无值**（已是「无值」⇒ 无操作、返回假）
      —— ⚠️ **不是**「撤销最后一次写入」（FR-009 · 裁定 17 ①）。

    **上游对照**（``langgraph 1.2.11`` · 契约 ``upstream-parity``）：
    ``channels/last_value.py:66``（覆盖）· ``:56-64``（冲突抛错）·
    ``:57-58``（空序列 no-op）· ``:69-75``（有值 / 无值判定）。
    """

    #: **不引入新槽** ⇒ 实例**无** ``__dict__``（裁定 17 ①）。
    __slots__ = ()

    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（上游 ``LastValue.from_checkpoint`` · ``last_value.py:44-54``）。"""
        empty = type(self)(self._key, self._value_type)
        if checkpoint is not _MISSING:
            empty._value = checkpoint
        return empty

    def update(self, values: Sequence[Any]) -> bool:
        """把「本步的写入序列」并入通道 —— **覆盖**语义。

        返回「**本次调用是否写入了值**」；空序列 ⇒ **无操作**、返回**假**；
        多于一个值 ⇒ **先检测后写入** ⇒ 抛 ``InvalidChannelUpdateError``
        且**值不变**。
        """
        if len(values) == 0:
            return False
        if len(values) > 1:
            raise InvalidChannelUpdateError(
                self._key, received_count=len(values), expected_count=1
            )
        self._value = values[0]
        return True

    def get(self) -> Any:
        """取回通道当前值；无值 ⇒ 抛 ``EmptyChannelError``。"""
        if self._value is _MISSING:
            raise EmptyChannelError(self._key)
        return self._value

    def is_available(self) -> bool:
        """判定「有值 / 无值」—— **恒不抛错**。"""
        return self._value is not _MISSING

    def clear(self) -> bool:
        """把通道恢复到「**无值**」（**覆写** · FR-009 · 裁定 17 ①）。

        返回「**状态是否真的变化**」——从「有值」清成「无值」⇒ 真；
        已是「无值」⇒ 无操作、返回**假**（幂等）。

        ⚠️ 清空**不**回到初始状态 —— 覆盖型的初始状态本就是「无值」，
        但「已写入过」这一事实**不被撤销**（清空 ≠ 撤销最后一次写入）。
        """
        if self._value is _MISSING:
            return False
        self._value = _MISSING
        return True


def _strip_type_wrappers(value_type: Any) -> Any:
    """**逐层**剥离 ``Annotated`` / ``Required`` / ``NotRequired`` 包装。

    **窄口径**（research **D-05**）：只剥这三类包装，**保留**泛型别名
    （``list[int]`` **不**退化为 ``list``）⇒ 暴露的 ``value_type`` 与
    B4F1 冻结的 ``ChannelSpec.value_type`` **同名同义**。

    ⚠️ **剥离仅发生在空值推导内部**（FR-006 ① · 澄清轮 **Q15** 补）——
    通道暴露的 ``value_type`` 属性 MUST **原样**等于 B4F1 的字段。

    **上游对照**：上游用**无差别**剥 ``__origin__``（``binop.py:22-28``）⇒
    ``list[int]`` → ``list`` ⇒ **机制不同**、**空值结果完全等价**
    （契约 ``upstream-parity`` **P-05**）。
    """
    current = value_type
    while True:
        origin = getattr(current, "__origin__", None)
        if origin is None:
            return current
        if origin is Required or origin is NotRequired:
            current = current.__args__[0]
            continue
        # ⚠️ **上游同款**（``langgraph/channels/binop.py:22-30`` 的 ``_strip_extras``）：
        # **无差别**剥 ``__origin__``（含泛型别名）⇒ ``list[int]`` → ``list`` ⇒
        # 空值推导得到 ``[]``（**有值**）⇒ 与上游**逐字同款**
        # （上游对齐前的**窄口径**会让 ``typing.List[int]`` 两侧**异果**）。
        current = origin


def _derive_empty_value(value_type: Any) -> Any:
    """按**值类型**推导「空值」（FR-006 · 契约 §3.2）。

    顺序（MUST 与 spec 一致）：

    ① **剥离** ``Annotated`` / ``Required`` / ``NotRequired``（逐层）；
    ② **抽象容器映射**（``Sequence``/``MutableSequence``→``list`` ·
       ``Set``/``MutableSet``→``set`` · ``Mapping``/``MutableMapping``→``dict``）；
    ③ **尝试构造空实例**：成功 ⇒ 该**新实例**；失败（``except Exception``）
       ⇒ ``_MISSING``（⇒ 初始「无值」，**构造不失败** · FR-006 ③）。

    ⚠️ 每次调用 MUST **新建**实例（MUST NOT 跨通道共享可变对象 ·
    FR-006 ④ · I-11）—— ``typ()`` 每次调用都产生新对象。

    ⚠️ 捕获 ``Exception`` 而非 ``BaseException``（research **D-07**）⇒
    ``KeyboardInterrupt`` / ``SystemExit`` 不会被吞。

    **上游对照**：``langgraph/channels/binop.py:82-92``（同口径）。
    """
    stripped = _strip_type_wrappers(value_type)
    concrete = _ABSTRACT_CONTAINER_MAP.get(stripped, stripped)
    try:
        return concrete()
    except Exception:  # noqa: BLE001 —— research D-07（捕获 Exception 而非 BaseException）
        return _MISSING


class BinaryOperatorAggregate(Channel):
    """**归约型**通道 —— 「有归约器 ⇒ ``reducer(current, new)``」（C2 · FR-005）。

    **构造签名**（**逐字冻结** · FR-002）::

        BinaryOperatorAggregate(
            key: str,
            value_type: Any,
            reducer: Callable[[Any, Any], Any],
        )

    * **归约器**：**按引用**持有（``channel.reducer is operator.add`` ·
      FR-014 · I-9）；
    * **空值推导**：构造时按 ``value_type`` 推导（剥包装 → 抽象容器映射 →
      构造空实例）；推导失败 ⇒ **初始「无值」**（构造**不**失败 · FR-006）；
    * **写入**：

      * 通道**有值** ⇒ ``值 = reducer(写入前的值, 新值)``，多值**按序**逐个归约；
      * 通道**无值** ⇒ **直存首个值**（**单值**写入时归约器调用次数 == **0**；
        多值写入 ⇒ 首个直存、其余按序归约 · FR-007 ② · 裁定 17 ④）；
    * **归约器抛错**：异常**向上传播**；通道值**不变**（FR-008 ——
      赋值只在 reducer 返回后发生）；
    * **写入（空序列）**：无操作（返回假）；
    * **``clear()``**：**覆写** ⇒ **无值**（**不回到**初始空值 · FR-022 ③）。

    **上游对照**（``langgraph 1.2.11`` · 契约 ``upstream-parity``）：
    ``channels/binop.py:126-128``（首次写入直存）· ``:143``（归约调用形式）·
    ``:123-125``（空序列 no-op）· ``:82-92``（空值推导）。
    """

    #: **不引入新槽** ⇒ 实例**无** ``__dict__``（裁定 17 ①）。
    __slots__ = ()

    def __init__(
        self,
        key: str,
        value_type: Any,
        reducer: Callable[..., Any],
    ) -> None:
        """记录 key / 值类型 / 归约器**引用**（**无副作用** · FR-002 ①）。

        **构造期校验**（FR-025 · I-16）：

        * 归约器**不可调用** ⇒ 内置 ``TypeError``；
        * 归约器为**空**（``None``）⇒ 内置 ``ValueError``。

        ⚠️ MUST **NOT** 重做**二元性**校验（那是 **B4F1** 的职责 ·
        FR-025 ④ · SC-026 ③）⇒ 通道层**不**成为第二个判定点。
        """
        if reducer is None:
            raise ValueError(
                f"Channel {key!r} is declared with a reducer but the reducer is empty"
            )
        if not callable(reducer):
            raise TypeError(
                f"Channel {key!r} reducer must be a callable, "
                f"got {type(reducer).__name__}"
            )
        super().__init__(key, value_type)
        self._reducer = reducer
        self._value = _derive_empty_value(value_type)

    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（上游 ``binop.py:116-121`` ⇒ 归约器**一并**带上）。"""
        empty = type(self)(self._key, self._value_type, self._reducer)
        if checkpoint is not _MISSING:
            empty._value = checkpoint
        return empty

    def update(self, values: Sequence[Any]) -> bool:
        """把「本步的写入序列」并入通道 —— **归约**语义。

        返回「**本次调用是否写入了值**」；空序列 ⇒ **无操作**、返回**假**。

        ⚠️ 赋值**只在** reducer 返回后发生 ⇒ 归约失败**不污染**状态
        （FR-008）。
        """
        if len(values) == 0:
            return False
        if self._value is _MISSING:
            # 首次写入：**直存**首个值（**不调**归约器 · FR-007 ②）
            self._value = values[0]
            remaining = values[1:]
        else:
            remaining = values
        for value in remaining:
            self._value = self._reducer(self._value, value)  # type: ignore[misc]
        return True

    def get(self) -> Any:
        """取回通道当前值；无值 ⇒ 抛 ``EmptyChannelError``。"""
        if self._value is _MISSING:
            raise EmptyChannelError(self._key)
        return self._value

    def is_available(self) -> bool:
        """判定「有值 / 无值」—— **恒不抛错**。"""
        return self._value is not _MISSING

    def clear(self) -> bool:
        """把通道恢复到「**无值**」（**覆写** · FR-009 · FR-022 ③）。

        ⚠️ **不回到**初始空值 ⇒ 清空后的归约型通道**无值**（不是「有值（空值）」）
        —— 清空 ≠ 回到初始状态。
        """
        if self._value is _MISSING:
            return False
        self._value = _MISSING
        return True


class EphemeralValue(Channel):
    """**路由型**通道 —— 每 super-step 清空（C7 / C8 · FR-009 / FR-010）。

    **构造签名**（**逐字冻结** · FR-002）::

        EphemeralValue(key: str, value_type: Any)

    * **归约器**：**无**（``reducer is None``）；
    * **初始状态**：**无值**（**不推导**空值 · FR-022 ①）；
    * **写入（1 个值）**：**覆盖**为最新写入值；
    * **写入（多于 1 个值）**：抛 ``InvalidChannelUpdateError``
      （**先检测后写入** ⇒ 值不变 · FR-010）；
    * **写入（空序列）**：无操作（返回假）—— ⚠️ **清空走 ``clear()``**，
      **不靠**空序列（契约 §3.3）；
    * **``clear()``**：**覆写** ⇒ **无值**（**清空后的终态**）；已是「无值」
      ⇒ 返回**假**（幂等 · FR-009）。

    ⚠️ **路由通道不由 schema 派生**（FR-012 ③）⇒ MUST 支持**直接实例化**
    （契约 §4 `M-2`）。

    **上游对照**（``langgraph 1.2.11`` · 契约 ``upstream-parity``）：
    ``channels/ephemeral_value.py:55-61``（清空为 ``MISSING``）·
    ``:62-65``（冲突 guard）。⚠️ 上游**没有** ``clear()`` ⇒ **机制不同**、
    **可观察语义等价**（**P-10** / **P-12**）。
    """

    #: **只增**一个槽（``_guard``）⇒ 实例**仍无** ``__dict__``（裁定 17 ①）。
    __slots__ = ("_guard",)

    def __init__(self, key: str, value_type: Any, guard: bool = True) -> None:
        """记录 key / 值类型 / **guard**（上游 ``EphemeralValue(typ, guard=True)`` ·
        ``langgraph/channels/ephemeral_value.py:23-26``）。

        ⚠️ ``guard=False`` ⇒ **一步内多值不报错**、取**末值**（上游的路由用途即如此 ·
        ``ephemeral_value.py:62-67``）；``guard=True`` ⇒ 多值**显式失败**。
        """
        super().__init__(key, value_type)
        self._guard: bool = guard

    @property
    def guard(self) -> bool:
        """是否**禁止**一步内多值（上游 ``ephemeral_value.py:26``）。"""
        return self._guard

    def from_checkpoint(self, checkpoint: Any) -> "Channel":
        """按检查点**新建**同种通道（上游 ``ephemeral_value.py:48-54``）。"""
        empty = type(self)(self._key, self._value_type, self._guard)
        if checkpoint is not _MISSING:
            empty._value = checkpoint
        return empty

    def update(self, values: Sequence[Any]) -> bool:
        """把「本步的写入序列」并入通道 —— **覆盖**为最新写入值。

        返回「**本次调用是否写入了值**」。

        ⚠️ **上游同款**（``langgraph/channels/ephemeral_value.py:56-67``）：
        * **空序列** ⇒ **清空**（值 → 缺失）并返回**真**（**仅当**原先有值）⇒
          调度层用它做**步末清空**（上游 ``pregel/_algo.py:326-333``）；
        * 多于一个值 ⇒ ``guard=True`` 时**显式失败**（值不变）；``guard=False`` ⇒ 取**末值**。
        """
        if len(values) == 0:
            if self._value is _MISSING:
                return False
            self._value = _MISSING
            return True
        if len(values) > 1 and self._guard:
            raise InvalidChannelUpdateError(
                self._key, received_count=len(values), expected_count=1
            )
        self._value = values[-1]
        return True

    def get(self) -> Any:
        """取回通道当前值；无值 ⇒ 抛 ``EmptyChannelError``。"""
        if self._value is _MISSING:
            raise EmptyChannelError(self._key)
        return self._value

    def is_available(self) -> bool:
        """判定「有值 / 无值」—— **恒不抛错**。"""
        return self._value is not _MISSING

    def clear(self) -> bool:
        """把通道恢复到「**无值**」（**覆写** · FR-009 · 裁定 17 ①）。

        ⇒ 路由判定结果**不跨 super-step 残留**。

        返回「**状态是否真的变化**」——从「有值」清成「无值」⇒ 真；
        已是「无值」⇒ 无操作、返回**假**（幂等）。
        """
        if self._value is _MISSING:
            return False
        self._value = _MISSING
        return True
