# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B11F1 · ``Send`` 的 L1 契约与门面转出。"""

from __future__ import annotations

import dataclasses
import typing

import pytest

import freegraph.contracts as contracts
import freegraph.graph as facade
from freegraph.contracts import Command, Send


def test_send_is_defined_in_l1_and_reexported_by_the_facade() -> None:
    assert facade.Send is contracts.Send
    assert Send.__module__ == "freegraph.contracts.types"
    assert "Send" in contracts.__all__


def test_send_shape_and_immutability_are_unchanged() -> None:
    positional = Send("worker", {"n": 1})
    keyword = Send(node="worker", arg={"n": 1})
    assert positional == keyword
    assert dataclasses.is_dataclass(Send)
    assert Send.__dataclass_params__.frozen is True
    with pytest.raises(dataclasses.FrozenInstanceError):
        positional.node = "other"  # type: ignore[misc]
    assert Send.__dict__["__hash__"] is None
    with pytest.raises(TypeError):
        hash(positional)


def test_command_goto_annotation_widened_to_include_send() -> None:
    hint = typing.get_type_hints(Command)["goto"]
    args = typing.get_args(hint)
    assert str in args
    assert Send in args
    assert type(None) in args
