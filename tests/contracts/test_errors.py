# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层异常体系的单元测试。

覆盖 data-model.md 的 **I-12 / I-13** 与 spec 的 **SC-005**：

* 统一基类 :class:`FreegraphError` 派生自 ``Exception``，是**类型锚点 + 统一捕获点**；
* 三个具名子异常同基类，``except FreegraphError`` 一次兜住全部；
* 三个子异常各暴露**结构化属性**，上层取细节**无须解析错误消息**。

本文件从 ``freegraph.contracts.errors`` **模块**导入（而非门面
``freegraph.contracts``）——门面层的「恰 8 个公开符号」断言归
``test_architecture.py`` 的 G7。
"""

from __future__ import annotations

import re

import pytest

from freegraph.contracts.errors import (
    FreegraphError,
    GraphInterrupt,
    GraphRecursionError,
    InvalidUpdateError,
)
from freegraph.contracts.types import Command


class TestBaseError:
    """基类 ``FreegraphError`` 的结构约束。"""

    def test_derives_from_exception(self) -> None:
        """基类 MUST 派生自内置异常基类。"""
        assert issubclass(FreegraphError, Exception)

    def test_is_catchable_by_itself(self) -> None:
        """``except FreegraphError`` MUST 能捕获其实例。"""
        with pytest.raises(FreegraphError):
            raise FreegraphError("boom")

    def test_message_is_preserved(self) -> None:
        """``str(exc)`` MUST 含调用方传入的消息。"""
        exc = FreegraphError("内核错误：消息原样保留")
        assert "内核错误：消息原样保留" in str(exc)

    def test_base_class_is_not_abstract(self) -> None:
        """基类可直接实例化——它是统一捕获点，不是抽象占位。"""
        exc = FreegraphError("x")
        assert isinstance(exc, Exception)
        assert exc.args == ("x",)


class TestSubErrors:
    """I-12 / I-13 / SC-005 · 三个具名子异常。"""

    @pytest.mark.parametrize(
        "cls",
        [InvalidUpdateError, GraphRecursionError, GraphInterrupt],
        ids=["InvalidUpdateError", "GraphRecursionError", "GraphInterrupt"],
    )
    def test_derives_from_freegraph_error(self, cls: type) -> None:
        """三个子异常 MUST 全部派生自 ``FreegraphError``。"""
        assert issubclass(cls, FreegraphError)
        assert issubclass(FreegraphError, Exception)

    @pytest.mark.parametrize(
        "exc",
        [
            InvalidUpdateError(["a"]),
            GraphRecursionError(25, 25),
            GraphInterrupt(object()),
        ],
        ids=["InvalidUpdateError", "GraphRecursionError", "GraphInterrupt"],
    )
    def test_base_class_catches_every_subclass(self, exc: Exception) -> None:
        """``except FreegraphError`` MUST 逐一捕获三例，无一漏网。"""
        with pytest.raises(FreegraphError):
            raise exc

    def test_command_construction_error_is_caught_by_base(self) -> None:
        """构造「三语义位全缺省」的 ``Command`` 抛出的错误 MUST 可被基类捕获。

        （SC-005 后半句 · 跨故事的一条：US1 的构造期校验错误与 US2 的异常族同源。）
        """
        with pytest.raises(FreegraphError):
            Command()

    def test_invalid_update_error_structured_attribute(self) -> None:
        """``invalid_keys`` MUST 直接可读，无须解析错误消息（I-13）。"""
        exc = InvalidUpdateError(["a"])
        assert exc.invalid_keys == ("a",)

    def test_invalid_update_error_preserves_order(self) -> None:
        """``invalid_keys`` 的顺序 MUST 保持传入顺序。"""
        exc = InvalidUpdateError(["a", "b", "c"])
        assert exc.invalid_keys == ("a", "b", "c")

    def test_graph_recursion_error_structured_attributes(self) -> None:
        """``recursion_limit`` / ``current_step`` MUST 直接可读（I-13）。"""
        exc = GraphRecursionError(25, 25)
        assert exc.recursion_limit == 25
        assert exc.current_step == 25

    def test_graph_interrupt_payload_is_the_same_object(self) -> None:
        """``payload`` MUST 保持**对象**形态（同一个对象，不是它的拷贝）。"""
        payload = object()
        exc = GraphInterrupt(payload)
        assert exc.payload is payload

    def test_graph_interrupt_payload_keeps_value_and_id(self) -> None:
        """载荷按契约 C17 带 ``.value`` 与 ``.id``——异常侧原样承载，不拆解。"""

        class Payload:
            value = "v"
            id = "i"

        payload = Payload()
        exc = GraphInterrupt(payload)
        assert exc.payload.value == "v"
        assert exc.payload.id == "i"

    def test_default_message_is_generated(self) -> None:
        """``message`` 缺省时 MUST 自动生成一句摘要。"""
        assert str(InvalidUpdateError(["a"]))
        assert str(GraphRecursionError(25, 25))
        assert str(GraphInterrupt(object()))

    def test_message_keyword_overrides_the_summary(self) -> None:
        """可选关键字 ``message="..."`` MUST 覆盖自动生成的摘要。"""
        assert str(InvalidUpdateError(["a"], message="自定义摘要")) == "自定义摘要"
        assert str(GraphRecursionError(1, 2, message="自定义摘要")) == "自定义摘要"
        assert str(GraphInterrupt(object(), message="自定义摘要")) == "自定义摘要"

    def test_default_summary_is_english_and_names_the_unknown_key(self) -> None:
        """默认摘要 MUST 为英文且**点名未知 key**（US2 验收场景 3）。"""
        msg = str(InvalidUpdateError(["typo"]))
        assert "typo" in msg
        assert re.search(r"[一-鿿]", msg) is None
