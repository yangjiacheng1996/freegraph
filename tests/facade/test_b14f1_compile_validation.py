# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · ``compile(checkpointer=...)`` 编译期校验。"""

from __future__ import annotations

from typing import TypedDict

import pytest

from freegraph.graph import END, START, StateGraph
from freegraph.persistence import MemorySaver


class _State(TypedDict, total=False):
    x: int


def _graph() -> StateGraph:
    builder = StateGraph(_State)
    builder.add_node("a", lambda state: {"x": 1})
    builder.add_edge(START, "a")
    builder.add_edge("a", END)
    return builder


def test_none_true_false_and_memory_saver_are_accepted_and_recorded() -> None:
    for value in (None, True, False):
        compiled = _graph().compile(checkpointer=value)
        assert compiled.checkpointer is value
    saver = MemorySaver()
    compiled = _graph().compile(checkpointer=saver)
    assert compiled.checkpointer is saver


@pytest.mark.parametrize("value", [object(), "saver", [], 0, 1, 0.0])
def test_non_conforming_checkpointers_raise_type_error(value) -> None:
    with pytest.raises(TypeError):
        _graph().compile(checkpointer=value)
