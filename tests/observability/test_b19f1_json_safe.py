# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · JSON 安全降级：确定、不抛、不泄漏。"""

from __future__ import annotations

import json

from freegraph.observability._record import json_safe


def test_plain_values_are_preserved() -> None:
    value = {"a": 1, "b": [1, 2], "c": (True, None), "d": "x"}
    assert json_safe(value) == {"a": 1, "b": [1, 2], "c": [True, None], "d": "x"}


def test_non_string_dict_keys_are_stringified() -> None:
    assert json_safe({1: "a", (1, 2): "b"}) == {
        "1": "a",
        "<builtins.tuple>": "b",
    }


def test_set_is_sorted_and_objects_use_type_placeholders() -> None:
    class Opaque:
        pass

    first = json_safe({"s": {3, 1, 2}, "o": Opaque(), "b": b"bytes"})
    second = json_safe({"s": {2, 3, 1}, "o": Opaque(), "b": b"bytes"})
    assert first == second
    assert first["s"] == [1, 2, 3]
    assert first["o"].startswith("<")
    assert first["b"] == "<builtins.bytes>"


def test_cycles_become_cycle_marker_and_never_raise() -> None:
    value: dict[str, object] = {}
    value["self"] = value
    safe = json_safe(value)
    assert safe == {"self": "<cycle>"}
    assert json.dumps(safe)


def test_no_object_content_leaks() -> None:
    class Secret:
        def __repr__(self) -> str:
            return "super-secret"

    safe = json_safe(Secret())
    assert "super-secret" not in safe
    assert "Secret" in safe
