# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**二元性判定** + **归约器提取** —— B4F1 的判据实现处（判据的**唯一实现**）。

判据的**唯一权威**是
``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``
（``<!-- authority: yes -->``）—— 本模块 MUST 与它**逐条一致**
（测试 ``tests/runtime/test_binary_criterion.py`` 逐条比对）。

**口径**（binary-criterion §1 · FR-004）：

* **候选**：元数据**末位**元素是 **callable**（**类**与**可调用对象实例**
  都**不**特殊排除 · 澄清 **Q6** · 裁定 9）；
* **计数**：位置专用（``POSITIONAL_ONLY``）**+** 位置或关键字
  （``POSITIONAL_OR_KEYWORD``）**== 2**；
  **可变位置（``*args``）· 可变关键字（``**kwargs``）· 仅关键字
  （keyword-only）一律不计入**；
* **签名取不到**（``inspect.signature`` 抛 ``ValueError`` / ``TypeError``）
  ⇒ 判为**非二元** ⇒ **拒绝**。

与上游 ``langgraph/graph/state.py:1904-1922`` 的**差异只有一处**：
上游抛 ``ValueError``，freegraph 抛 ``InvalidSchemaError``
（**继承 ``FreegraphError`` + ``ValueError``** · 裁定 2）
⇒ **判定结果（接受 / 拒绝）逐条一致**。

本模块**只读签名**、**从不调用**候选 ⇒ 解析是**纯函数**
（FR-013 · SC-009）。
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

__all__: list[str] = []


def _is_binary_operator(candidate: Any) -> bool:
    """判定 ``candidate`` 是否是「**恰好 2 个位置参数**」的 callable。

    计数口径 = 位置专用 + 位置或关键字（FR-004 · binary-criterion §1）：
    ``*args`` / ``**kwargs`` / keyword-only **一律不计入**。

    签名**取不到**（内置类型 / 内置函数 ⇒ ``inspect.signature`` 抛
    ``ValueError``）⇒ 判为**非二元**（**False**）⇒ 由调用方按
    FR-007 ② 报错。

    **类**与**可调用对象实例**都**不**特殊排除（澄清 **Q6** · 裁定 9）
    —— 完全按签名**机械判定**。
    """
    try:
        signature = inspect.signature(candidate)
    except (ValueError, TypeError):
        return False
    positional = sum(
        1
        for parameter in signature.parameters.values()
        if parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    )
    return positional == 2


def _extract_reducer(annotation: Any) -> Callable[..., Any] | None:
    """从 ``Annotated[T, ...]`` 的元数据**末位**提取归约器候选。

    * 无 ``__metadata__``（无 ``Annotated``）⇒ 返回**空**；
    * 末位**非** callable ⇒ 返回**空**（FR-003 ① —— **不报错**，
      该 key 走默认覆盖语义）；
    * 末位是 callable ⇒ **返回该对象本身**（**按引用** · FR-012）。

    ⚠️ 本函数**不判定二元性**——末位是 callable 但**非二元**时，
    由**调用方**按 FR-007 ② 抛 ``InvalidSchemaError``
    （MUST NOT 在此静默降级为「无归约器」）。
    """
    metadata = getattr(annotation, "__metadata__", None)
    if not metadata:
        return None
    candidate = metadata[-1]
    if not callable(candidate):
        return None
    return candidate
