# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**``typing_extensions.TypedDict`` 的正面路径** —— B4F1（tasks T057 · SC-018）。

⚠️ **独立文件的理由**（tasks T057 · 2026-11-08 分析轮）：pytest 的
**收集期**即 import 本模块 ⇒ 同进程内 ``sys.modules`` 必含
``typing_extensions`` ⇒ 与 ``test_parse_contract.py`` 的
「import 后无 ``typing_extensions``」断言（SC-011）**必须分文件**
（否则同进程**必假红**）。

**被测形态**与验收基准 ``harness/demo/target.py:59-61`` **同构**：

```python
class MessagesState(TypedDict):        # ← typing_extensions.TypedDict
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
```

**依赖纪律**（FR-001 ② · FR-013 · FR-016 ② · FR-019）：被测 schema 由
**测试代码**用 ``typing_extensions`` 构造；freegraph 侧 **MUST NOT**
import 它 ⇒ **MUST NOT** 把 ``typing_extensions`` 写进 ``pyproject.toml``
的任何一处。

⚠️ **环境依赖型判据**：``typing_extensions`` **不是任何声明依赖**
（v1.0 依赖面 = 零 · 宪法 v1.7.0）⇒ 其在 CI 中的可得性来自 v2.0 预验证
包的**传递带入**（**偶然**可得）⇒ 本条在部分 CI 档可能 **skip**
⇒ **skip ≠ pass**：被 skip 时 MUST 记入
``harness/verification/B4F1/manual-verification.md`` 的「遗留问题」节。

⚠️ ``pytest.importorskip`` MUST 置于**测试函数内**（MUST NOT 置于模块级：
模块级 skip 会连带跳过本文件内**其余全部**用例）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

import operator
from typing import Annotated

import pytest

from freegraph.runtime import parse_state_schema


class AnyMessage:
    """``langchain.messages.AnyMessage`` 的**零依赖替身**（仅供类型标注）。"""


def test_typing_extensions_typed_dict_is_accepted() -> None:
    """SC-018 · 裁定 3：``typing_extensions.TypedDict`` MUST 被**接受**。

    **实测事实**（CPython 3.11.16 + typing_extensions 4.16.0）：
    ``typing.is_typeddict(typing_extensions.TypedDict(...))`` 返回
    ``False`` ⇒ 只用它判定会把验收基准的 schema 判成「非 ``TypedDict````
    ⇒ 判定 MUST 用 FR-001 ① 的**鸭子口径**。
    """
    typing_extensions = pytest.importorskip("typing_extensions")

    class MessagesState(typing_extensions.TypedDict):  # type: ignore[misc]
        messages: Annotated[list[AnyMessage], operator.add]
        llm_calls: int

    spec = parse_state_schema(MessagesState)
    messages = spec.channels["messages"]
    calls = spec.channels["llm_calls"]

    assert spec.keys == ("messages", "llm_calls")
    assert messages.reducer is operator.add
    assert messages.has_reducer is True
    assert messages.semantics == "reduce"
    assert calls.reducer is None
    assert calls.has_reducer is False
    assert calls.semantics == "overwrite"


def test_typing_extensions_typed_dict_is_not_mistaken_for_a_plain_dict() -> None:
    """SC-018：「被误判为『非 ``TypedDict``』」的次数 **== 0**。"""
    typing_extensions = pytest.importorskip("typing_extensions")

    class MessagesState(typing_extensions.TypedDict):  # type: ignore[misc]
        messages: Annotated[list[AnyMessage], operator.add]

    # 若判定退化为「是不是 ``dict`` 的子类」⇒ 普通 ``dict`` 也会被接受。
    from freegraph.runtime import InvalidSchemaError

    with pytest.raises(InvalidSchemaError) as excinfo:
        parse_state_schema({"messages": []})

    assert excinfo.value.reason == "not_a_state_schema"
