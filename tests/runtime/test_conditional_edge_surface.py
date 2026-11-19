# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**零新增公开面**的清点断言 —— 属 **B8F1**（tasks T023）。

本 feature 新增了 ``src/freegraph/runtime/_routing.py``（**L2 私有**）⇒ ⇒ ⇒
**公开面 MUST 零变更**（spec **FR-037** / **SC-016** / 契约 **I-13**）⇒ ⇒ ⇒
下列六项**逐一**断言（**单一事实源** = ``tests/runtime/_runtime_export_manifest.py``
+ 既有门禁的硬编码数字）：

① ``freegraph.graph.__all__`` == **7** 个符号；
② ``freegraph.runtime.__all__`` == **23** 个符号（**清单**口径 · 非硬编码）；
③ ``freegraph.contracts.__all__`` == **21** 个符号；
④ ``vars(compiled)`` 的键数 == **11**（3 私有 + 8 公开 · B7F2 的冻结面）；
⑤ ``freegraph.runtime.errors`` 的符号集合**不变**（**零新增错误类型** · **I-14**）；
⑥ **未实现**的 L1 协议方法（**恰 5** 个）仍抛内置 ``NotImplementedError``
且消息**点名归属 feature**（**FR-036**）。

⚠️ **``draw_mermaid_png()`` 尚未存在**（属 **B23F1** 的 ``Graph`` 侧能力）
⇒ ⇒ ⇒ **MUST NOT** 计入本项（spec SC-016 的实测口径）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph import contracts, graph, runtime
from freegraph.runtime import errors

from ._runtime_export_manifest import ERROR_EXPORT_SYMBOLS, RUNTIME_EXPORT_SYMBOLS


class _State(TypedDict):
    llm_calls: int


def _compiled():
    """编译一张**最小图**（⇒ 拿到 ``CompiledGraph`` 产物）。"""
    builder = graph.StateGraph(_State)
    builder.add_node("a", lambda state: {"llm_calls": 1})
    builder.add_edge(graph.START, "a")
    return builder.compile()


def test_the_facade_exports_exactly_eight_symbols() -> None:
    """① 门面 ``freegraph.graph`` 的导出面 == **8** 个符号（B8F2 +1）。"""
    assert len(graph.__all__) == 8
    assert set(graph.__all__) == {
        "StateGraph",
        "START",
        "END",
        "Send",
        "interrupt",
        "Command",
        "RunConfig",
        "get_stream_writer",
    }


def test_the_runtime_export_face_is_unchanged() -> None:
    """② ``freegraph.runtime.__all__`` == **清单**（23 个 · **零变更**）。"""
    assert set(runtime.__all__) == set(RUNTIME_EXPORT_SYMBOLS)
    assert len(runtime.__all__) == 23


def test_the_contract_layer_exports_exactly_twenty_two_symbols() -> None:
    """③ 契约层 ``freegraph.contracts.__all__`` == **22** 个符号（B8F2 +1）。"""
    assert len(contracts.__all__) == 22


def test_the_compiled_product_still_holds_eleven_keys() -> None:
    """④ ``vars(compiled)`` 的键数 == **11**（**零新增**私有字段 · **T-3 不破**）。"""
    compiled = _compiled()
    assert len(vars(compiled)) == 11
    assert set(vars(compiled)) == {
        "_spec",
        "_builder_spec",
        "_conditional_edges",
        "checkpointer",
        "store",
        "cache",
        "debug",
        "name",
        "transformers",
        "interrupt_before_nodes",
        "interrupt_after_nodes",
    }


def test_the_error_symbol_set_is_unchanged() -> None:
    """⑤ ``freegraph.runtime.errors`` 的符号集合**不变**（**零新增错误类型**）。"""
    assert set(errors.__all__) == set(ERROR_EXPORT_SYMBOLS)


@pytest.mark.parametrize(
    ("method_name", "args", "owner"),
    [
        ("get_graph", (), "B22F1"),
        ("get_state", (None,), "B15F1"),
        ("get_state_history", (None,), "B15F1"),
        ("update_state", (None, {}), "B16F1"),
    ],
)
def test_the_unimplemented_protocol_methods_still_name_their_owner(
    method_name: str, args: tuple, owner: str
) -> None:
    """⑥ **未实现**的 L1 协议方法仍抛 ``NotImplementedError`` 且**点名归属 feature**。"""
    compiled = _compiled()
    method = getattr(compiled, method_name)
    with pytest.raises(NotImplementedError) as excinfo:
        method(*args)
    assert owner in str(excinfo.value)
