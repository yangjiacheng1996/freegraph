# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B13F1 · 静态中断点 before / after / 恢复 / 最终节点 / 优先级。"""

from __future__ import annotations

import pytest

from freegraph.contracts import Command, GraphRecursionError, RunConfig
from freegraph.graph import interrupt
from freegraph.runtime import GraphSpec, InterruptResult, NodeSpec, run_graph
from freegraph.runtime.channel import LastValue

from .test_interrupt_checkpoint import StubCheckpointer


def _spec(*, before=(), after=(), final: bool = True) -> tuple[GraphSpec, dict[str, int]]:
    calls = {"prepare": 0, "review": 0, "final": 0}

    def prepare(state: dict) -> dict:
        calls["prepare"] += 1
        return {"count": 1}

    def review(state: dict) -> dict:
        calls["review"] += 1
        return {"count": state.get("count", 0) + 1}

    def final_node(state: dict) -> dict:
        calls["final"] += 1
        return {"count": state.get("count", 0) + 1}

    nodes = {
        "prepare": NodeSpec((), prepare),
        "review": NodeSpec(("count",), review),
        "final": NodeSpec(("count",), final_node),
    }
    edges = {
        "__start__": ("prepare",),
        "prepare": ("review",),
        "review": (("final",) if final else ()),
    }
    return (
        GraphSpec(
            channels={"count": LastValue("count", int)},
            nodes=nodes,
            edges=edges,
            interrupt_before=before,
            interrupt_after=after,
        ),
        calls,
    )


def _run(spec, checkpointer, config, input=None):
    return run_graph(spec, input, checkpointer=checkpointer, config=config)


def test_before_suspends_without_executing_the_target() -> None:
    spec, calls = _spec(before=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-before")
    paused = _run(spec, stub, config)
    assert isinstance(paused, InterruptResult)
    assert paused.interrupts == ()
    assert paused.executed == ("prepare",)
    assert paused.state == {"count": 1}
    assert paused.steps == 1
    assert calls["review"] == 0
    assert paused.as_result_dict()["__interrupt__"] == ()


def test_before_preserves_writes_from_previous_rounds_only() -> None:
    spec, calls = _spec(before=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-before-writes")
    paused = _run(spec, stub, config)
    assert paused.state["count"] == 1
    assert "review" not in paused.executed
    assert calls["review"] == 0


def test_before_resume_with_none_executes_target_once() -> None:
    spec, calls = _spec(before=("review",), final=False)
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-before-none")
    first = _run(spec, stub, config)
    assert isinstance(first, InterruptResult)
    second = _run(spec, stub, config, None)
    assert not isinstance(second, InterruptResult)
    assert calls["review"] == 1
    assert second.state["count"] == 2


def test_before_resume_with_empty_dict_does_not_rehang() -> None:
    spec, calls = _spec(before=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-before-empty")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    second = _run(spec, stub, config, {})
    assert not isinstance(second, InterruptResult)
    assert calls["review"] == 1


def test_before_resume_with_command_does_not_deliver_value() -> None:
    spec, calls = _spec(before=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-before-command")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    second = _run(spec, stub, config, Command(resume="ignored"))
    assert not isinstance(second, InterruptResult)
    assert calls["review"] == 1


def test_before_target_entry_suspends_before_any_node() -> None:
    calls: list[str] = []

    def review(state: dict) -> dict:
        calls.append("review")
        return {"count": 1}

    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"review": NodeSpec((), review)},
        edges={"__start__": ("review",)},
        interrupt_before=("review",),
    )
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-entry")
    paused = run_graph(spec, {}, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)
    assert paused.executed == ()
    assert paused.state == {}
    assert calls == []
    completed = run_graph(spec, None, checkpointer=stub, config=config)
    assert not isinstance(completed, InterruptResult)
    assert calls == ["review"]


def test_after_executes_target_and_merges_writes_before_suspending() -> None:
    spec, calls = _spec(after=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-after")
    paused = _run(spec, stub, config)
    assert isinstance(paused, InterruptResult)
    assert paused.executed == ("prepare", "review")
    assert paused.interrupts == ()
    assert paused.state["count"] == 2
    assert paused.steps == 2
    assert calls["review"] == 1


def test_after_resume_does_not_rerun_target() -> None:
    spec, calls = _spec(after=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-after-resume")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    resumed = _run(spec, stub, config, None)
    assert not isinstance(resumed, InterruptResult)
    assert calls["review"] == 1
    assert calls["final"] == 1


def test_after_on_last_node_with_empty_next_still_resumes() -> None:
    spec, calls = _spec(after=("review",), final=False)
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-after-last")
    paused = _run(spec, stub, config)
    assert isinstance(paused, InterruptResult)
    assert paused.state["count"] == 2
    completed = _run(spec, stub, config, None)
    assert not isinstance(completed, InterruptResult)
    assert calls["review"] == 1


def test_after_command_resume_continues() -> None:
    spec, calls = _spec(after=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-after-command")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    resumed = _run(spec, stub, config, Command(resume="ignored"))
    assert not isinstance(resumed, InterruptResult)
    assert calls["review"] == 1
    assert calls["final"] == 1


def test_same_node_before_and_after_runs_before_then_after() -> None:
    spec, calls = _spec(before=("review",), after=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-both")
    before = _run(spec, stub, config)
    assert isinstance(before, InterruptResult)
    assert calls["review"] == 0
    after = _run(spec, stub, config, None)
    assert isinstance(after, InterruptResult)
    assert calls["review"] == 1
    completed = _run(spec, stub, config, None)
    assert not isinstance(completed, InterruptResult)
    assert calls["review"] == 1


def test_true_exception_beats_static_after() -> None:
    def boom(state: dict) -> dict:
        raise RuntimeError("boom")

    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"boom": NodeSpec((), boom)},
        edges={"__start__": ("boom",)},
        interrupt_after=("boom",),
    )
    with pytest.raises(RuntimeError, match="boom"):
        run_graph(spec, config=RunConfig(thread_id="t-boom"))


def test_dynamic_interrupt_beats_static_after() -> None:
    def ask(state: dict) -> dict:
        return {"count": interrupt("approve?")}

    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"ask": NodeSpec((), ask)},
        edges={"__start__": ("ask",)},
        interrupt_after=("ask",),
    )
    stub = StubCheckpointer()
    paused = run_graph(spec, checkpointer=stub, config=RunConfig(thread_id="t-dyn"))
    assert isinstance(paused, InterruptResult)
    assert len(paused.interrupts) == 1
    assert paused.interrupts[0].value == "approve?"


def test_recursion_limit_beats_static_before() -> None:
    def prepare(state: dict) -> dict:
        return {"count": 1}

    def loop(state: dict) -> dict:
        return {"count": state.get("count", 0) + 1}

    spec = GraphSpec(
        channels={"count": LastValue("count", int)},
        nodes={"prepare": NodeSpec((), prepare), "loop": NodeSpec(("count",), loop)},
        edges={"__start__": ("prepare",), "prepare": ("loop",), "loop": ("loop",)},
        interrupt_before=("loop",),
    )
    with pytest.raises(GraphRecursionError):
        run_graph(spec, {"count": 0}, config={"recursion_limit": 1})


def test_no_static_configuration_behaves_normally() -> None:
    spec, calls = _spec()
    result = run_graph(spec, {"count": 0}, config=RunConfig(thread_id="t-normal"))
    assert result.state["count"] == 3
    assert calls == {"prepare": 1, "review": 1, "final": 1}


def test_static_completion_clears_suspension_markers() -> None:
    spec, _ = _spec(before=("review",))
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-clear")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    _run(spec, stub, config, None)
    metadata = stub.snapshots["t-clear"]["metadata"]
    assert metadata["suspension_kind"] is None
    assert metadata["static_ack"] is None
    assert metadata["next"] == ()
    assert metadata["scheduler"]["suspension_kind"] is None
    assert metadata["scheduler"]["static_ack"] is None
    assert metadata["scheduler"]["fanout"] == {}


def test_ordinary_completion_writes_initial_and_step_snapshots_only() -> None:
    spec, _ = _spec()
    stub = StubCheckpointer()
    run_graph(spec, {"count": 0}, checkpointer=stub, config=RunConfig(thread_id="t-plain"))
    # prepare -> review -> final = 3 实际执行轮；B14F1 写「初始 + 每轮」= 4 次 put。
    # 普通完成没有 F-10 完成快照（否则会是第 5 次）。
    assert stub.calls.count("put") == 4


def test_static_before_without_checkpointer_still_returns_a_suspension() -> None:
    spec, calls = _spec(before=("review",), final=False)
    paused = run_graph(spec, {}, config=RunConfig(thread_id="t-no-saver-before"))
    assert isinstance(paused, InterruptResult)
    assert calls["review"] == 0


def test_static_after_without_checkpointer_still_returns_a_suspension() -> None:
    spec, calls = _spec(after=("review",), final=False)
    paused = run_graph(spec, {}, config=RunConfig(thread_id="t-no-saver-after"))
    assert isinstance(paused, InterruptResult)
    assert calls["review"] == 1


def test_static_command_resume_applies_update() -> None:
    spec, calls = _spec(after=("review",), final=False)
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-static-update")
    assert isinstance(_run(spec, stub, config), InterruptResult)
    resumed = _run(
        spec,
        stub,
        config,
        Command(update={"count": 10}, resume="ignored"),
    )
    assert not isinstance(resumed, InterruptResult)
    assert calls["review"] == 1
    assert resumed.state["count"] == 10


def test_non_static_history_without_interrupts_still_raises_no_pending() -> None:
    from freegraph.runtime import InterruptError

    spec, _ = _spec(final=False)
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-no-pending")
    stub.put(
        config,
        values={},
        metadata={"next": (), "interrupts": (), "scheduler": {}},
    )
    with pytest.raises(InterruptError) as exc:
        run_graph(spec, Command(resume="x"), checkpointer=stub, config=config)
    assert exc.value.reason == "no_pending_interrupt"


def test_static_interrupts_are_deterministic_across_repeated_specs() -> None:
    snapshots = []
    for _ in range(3):
        spec, _ = _spec(before=("review",), after=("review",))
        stub = StubCheckpointer()
        config = RunConfig(thread_id="t-deterministic")
        first = _run(spec, stub, config)
        assert isinstance(first, InterruptResult)
        second = _run(spec, stub, config, None)
        assert isinstance(second, InterruptResult)
        snapshots.append(
            (first.state, first.executed, first.steps, second.state, second.executed, second.steps)
        )
    assert snapshots[0] == snapshots[1] == snapshots[2]
