# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · 七种 stream mode 的门面行为（T021/T028/T033/T038/T044/T074）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, TypedDict

import pytest

from freegraph.contracts import PregelTask, RunConfig
from freegraph.graph import END, START, StateGraph


class _Append:
    @staticmethod
    def apply(left: list[str], right: list[str]) -> list[str]:
        return [*left, *right]


class _State(TypedDict):
    x: int
    llm_calls: int
    messages: Annotated[list[str], _Append.apply]


def _linear():
    def a(state: _State) -> dict:
        return {"x": 1, "llm_calls": 1, "messages": ["a"]}

    def b(state: _State) -> dict:
        return {"x": 2, "llm_calls": 2, "messages": ["b"]}

    builder = StateGraph(_State)
    builder.add_node("a", a)
    builder.add_node("b", b)
    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)
    return builder.compile()


class TestValuesStream:
    def test_initial_state_plus_one_event_per_completed_step(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({"x": 0}, stream_mode="values"))
        assert len(events) == 3
        assert events[0]["payload"]["x"] == 0
        assert events[-1]["payload"] == compiled.invoke({"x": 0})

    def test_full_key_set_and_missing_keys_are_none(self) -> None:
        compiled = _linear()
        payload = list(compiled.stream({}, stream_mode="values"))[0]["payload"]
        assert set(payload) == {"x", "llm_calls", "messages"}
        assert payload["x"] is None
        assert payload["llm_calls"] is None

    def test_envelope_and_shared_run_id(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({}, stream_mode="values"))
        assert all(
            set(event) == {"stream_mode", "payload", "run_id", "thread_id"}
            for event in events
        )
        assert len({event["run_id"] for event in events}) == 1
        assert {event["thread_id"] for event in events} == {None}

    def test_thread_id_and_run_config_run_id_are_resolved(self) -> None:
        compiled = _linear()
        config = RunConfig(
            thread_id="outer",
            configurable={"thread_id": "inner"},
            run_id="user-run",
        )
        events = list(compiled.stream({}, config=config, stream_mode="values"))
        assert {event["thread_id"] for event in events} == {"inner"}
        assert all(event["run_id"] != "user-run" for event in events)


class TestUpdatesStream:
    def test_one_event_per_task_and_payload_keys_are_node_names(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({}, stream_mode="updates"))
        assert len(events) == 2
        assert [set(event["payload"]) for event in events] == [{"a"}, {"b"}]

    def test_updates_merge_back_to_invoke_final_state(self) -> None:
        compiled = _linear()
        merged: dict = {"x": 0, "llm_calls": 0, "messages": []}
        for event in compiled.stream({"x": 0}, stream_mode="updates"):
            for update in event["payload"].values():
                for key, value in update.items():
                    if key == "messages":
                        merged[key] = _Append.apply(merged[key], value)
                    else:
                        merged[key] = value
        assert merged == compiled.invoke({"x": 0})

    def test_same_task_same_channel_multiple_writes_become_a_tuple(self) -> None:
        class _S(TypedDict):
            log: Annotated[list[int], lambda left, right: [*left, *right]]

        def a(state: _S) -> dict:
            return {"log": [1, 2]}

        builder = StateGraph(_S)
        builder.add_node("a", a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        event = list(builder.compile().stream({}, stream_mode="updates"))[0]
        assert event["payload"]["a"]["log"] == [1, 2]


class TestCustomStream:
    def test_writer_payload_is_verbatim(self) -> None:
        from freegraph.graph import get_stream_writer

        def a(state: _State) -> dict:
            get_stream_writer()({"msg": "retrieving"})
            return {"x": 1}

        builder = StateGraph(_State)
        builder.add_node("a", a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        events = list(builder.compile().stream({}, stream_mode="custom"))
        assert events[0]["payload"] == {"msg": "retrieving"}


class TestTasksDebugStream:
    def test_tasks_payload_is_pregel_task(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({}, stream_mode="tasks"))
        assert len(events) == 2
        assert all(isinstance(event["payload"], PregelTask) for event in events)
        assert [event["payload"].name for event in events] == ["a", "b"]

    def test_debug_wrapping(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({}, stream_mode="debug"))
        assert len(events) == 2
        for event in events:
            payload = event["payload"]
            assert set(payload) == {"step", "timestamp", "type", "payload"}
            assert payload["type"] == "task_result"
            assert isinstance(payload["payload"], PregelTask)
            parsed = datetime.fromisoformat(payload["timestamp"])
            assert parsed.utcoffset() == timedelta(0)
        assert [event["payload"]["step"] for event in events] == [1, 2]

    def test_interrupted_task_is_emitted(self) -> None:
        from freegraph.graph import interrupt

        class _S(TypedDict):
            x: int

        def a(state: _S) -> dict:
            interrupt("approve?")
            return {"x": 1}

        builder = StateGraph(_S)
        builder.add_node("a", a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        compiled = builder.compile()
        tasks = list(compiled.stream({}, stream_mode="tasks"))
        assert len(tasks) == 1
        assert tasks[0]["payload"].interrupts
        debug = list(compiled.stream({}, stream_mode="debug"))
        assert len(debug) == 1
        assert debug[0]["payload"]["step"] == 1


class TestModeSurface:
    @pytest.mark.parametrize(
        "mode",
        ["values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"],
    )
    def test_all_seven_modes_are_accepted(self, mode: str) -> None:
        compiled = _linear()
        list(compiled.stream({}, stream_mode=mode))

    def test_none_defaults_to_updates(self) -> None:
        compiled = _linear()
        events = list(compiled.stream({}))
        assert [event["stream_mode"] for event in events] == ["updates", "updates"]

    def test_invalid_mode_fails_at_call_time(self) -> None:
        compiled = _linear()
        with pytest.raises(ValueError):
            compiled.stream({}, stream_mode="bogus")
        with pytest.raises(ValueError):
            compiled.stream({}, stream_mode=[])

    def test_non_string_mode_fails_at_call_time(self) -> None:
        compiled = _linear()
        with pytest.raises(TypeError):
            compiled.stream({}, stream_mode=123)

    def test_duplicate_modes_are_deduped_and_order_is_fixed(self) -> None:
        compiled = _linear()
        events = list(
            compiled.stream(
                {}, stream_mode=["values", "updates", "values", "tasks"]
            )
        )
        assert [event["stream_mode"] for event in events] == [
            "values",
            "updates",
            "tasks",
            "values",
            "updates",
            "tasks",
            "values",
        ]

    def test_checkpoints_and_messages_are_empty(self) -> None:
        compiled = _linear()
        assert list(compiled.stream({}, stream_mode="checkpoints")) == []
        assert list(compiled.stream({}, stream_mode="messages")) == []


class TestRoutingStream:
    def test_conditional_edges_route_like_invoke(self) -> None:
        def route(state: dict, config) -> str:
            return "b"

        builder = StateGraph(_State)
        builder.add_node("a", lambda state: {"x": 1})
        builder.add_node("b", lambda state: {"x": 2})
        builder.add_edge(START, "a")
        builder.add_conditional_edges("a", route, ["b"])
        builder.add_edge("b", END)
        compiled = builder.compile()
        streamed = list(compiled.stream({}, stream_mode="updates"))
        assert [event["payload"] for event in streamed] == [
            {"a": {"x": 1}},
            {"b": {"x": 2}},
        ]

    def test_dual_param_route_receives_raw_config(self) -> None:
        seen = []

        def route(state: dict, config) -> str:
            seen.append(config)
            return "b"

        builder = StateGraph(_State)
        builder.add_node("a", lambda state: {"x": 1})
        builder.add_node("b", lambda state: {"x": 2})
        builder.add_edge(START, "a")
        builder.add_conditional_edges("a", route, ["b"])
        builder.add_edge("b", END)
        compiled = builder.compile()
        raw = {"configurable": {"thread_id": "t-1"}, "recursion_limit": 9}
        list(compiled.stream({}, config=raw, stream_mode="updates"))
        assert seen == [raw]
        assert seen[0] is raw
