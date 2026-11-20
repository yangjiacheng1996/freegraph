# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · US3：环境变量不启用 span + ``import freegraph`` 不加载 L5 / hook。"""

from __future__ import annotations

import json
from typing import Any, TypedDict

import pytest

from freegraph.graph import END, START, StateGraph


class _State(TypedDict, total=False):
    x: int


def _install_counters(monkeypatch: pytest.MonkeyPatch) -> tuple[list[Any], list[Any]]:
    import freegraph.observability._producer as producer_module
    import freegraph.runtime._span_hook as hook_module
    import freegraph.runtime._stream_context as stream_context
    import freegraph.runtime.superstep as superstep

    constructed: list[Any] = []
    bindings: list[Any] = []
    for module in (hook_module, producer_module):
        original = module.Span

        def wrapper(*args: Any, __original: Any = original, **kwargs: Any) -> Any:
            constructed.append(args)
            return __original(*args, **kwargs)

        monkeypatch.setattr(module, "Span", wrapper)

    original_bind = stream_context.bind_run_ids

    def bind_wrapper(run_id: str, thread_id: str | None) -> Any:
        bindings.append((run_id, thread_id))
        return original_bind(run_id, thread_id)

    monkeypatch.setattr(stream_context, "bind_run_ids", bind_wrapper)
    monkeypatch.setattr(superstep, "bind_run_ids", bind_wrapper)
    return constructed, bindings


def _graph():
    builder = StateGraph(_State)
    builder.add_node("n", lambda state: {"x": 1})
    builder.add_edge(START, "n")
    builder.add_edge("n", END)
    return builder.compile()


def test_langsmith_tracing_env_does_not_enable_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "should-not-be-read")
    constructed, bindings = _install_counters(monkeypatch)

    _graph().invoke({"x": 0})

    assert constructed == []
    assert bindings == []


def test_import_freegraph_does_not_load_l5_or_hook(
    run_in_subprocess: Any,
) -> None:
    payload = run_in_subprocess(
        "import sys\n"
        "import freegraph\n"
        "import json\n"
        "print(json.dumps({"
        "'modules': sorted(m for m in sys.modules if m.startswith('freegraph')),"
        "'__counters__': COUNTERS,"
        "}))\n"
    )
    modules = payload["modules"]
    assert modules == ["freegraph"]
    assert payload["env_reads"] == 0
    assert payload["egress"] == 0
