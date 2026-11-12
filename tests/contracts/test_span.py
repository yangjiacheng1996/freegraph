# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**可观测数据面**的契约面断言 —— ``Span`` / ``TraceQuery``。

覆盖 US2（``Span`` 11 字段 / 生命周期 / 不可变 / JSON 可序列化）与
US4（``TraceQuery`` 5 字段 / 全可空可组合 / 可哈希）。
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, fields, replace
from typing import Any, get_type_hints

import pytest

from freegraph.contracts import RunConfig, Span, TraceQuery, TraceSink

#: ``Span`` 的字段清单（**11 个**，逐字）——与 ``data-model.md`` §3.4 一致。
SPAN_FIELDS = [
    "id",
    "name",
    "attributes",
    "parent",
    "start_time",
    "end_time",
    "context",
    "thread_id",
    "run_id",
    "node",
    "checkpoint_id",
]

#: ``Span`` 的**必带四项**（C23 · D11）。
SPAN_REQUIRED_FIELDS = ["thread_id", "run_id", "node", "checkpoint_id"]


def _make_span(**overrides: Any) -> Span:
    """造一个字段齐备的 span（``overrides`` 覆盖个别字段）。"""
    base: dict[str, Any] = {
        "id": "span-1",
        "name": "node:a",
        "start_time": "2026-11-06T10:00:00+00:00",
        "run_id": "run-1",
        "node": "a",
    }
    base.update(overrides)
    return Span(**base)


# ── US2 · Span ─────────────────────────────────────────────────────────


class TestSpanFields:
    """US2 · ``Span`` 的字段清单与缺省。"""

    def test_field_list_is_exactly_eleven(self) -> None:
        """字段清单 MUST **恰为**那 11 个（逐字）。"""
        assert [f.name for f in fields(Span)] == SPAN_FIELDS

    def test_field_types_are_resolvable(self) -> None:
        """全部字段注解 MUST 能被 ``typing.get_type_hints`` 完整解析。"""
        hints = get_type_hints(Span)
        assert set(hints) == set(SPAN_FIELDS)

    def test_end_time_defaults_to_none(self) -> None:
        """``end_time`` 缺省 MUST 为 ``None``（未结束时为空）。"""
        assert _make_span().end_time is None

    def test_required_four_are_readable(self) -> None:
        """**必带四项**（``thread_id`` / ``run_id`` / ``node`` / ``checkpoint_id``）均可读。"""
        span = _make_span(
            thread_id="thread-1",
            checkpoint_id="ckpt-1",
        )
        for name in SPAN_REQUIRED_FIELDS:
            assert getattr(span, name) is not None, name

    def test_run_config_field_list_is_unchanged(self) -> None:
        """``RunConfig`` 的字段清单 MUST 恰为**九**字段（**上游同款**）。

        ⚠️ **2026-11-12 上游对齐 P3**：由**四**字段增为**九**字段 —— 新增
        ``configurable`` / ``max_concurrency`` / ``recursion_limit`` / ``run_name`` / ``run_id``
        （**上游同款** · 上游 ``langchain_core/runnables/config.py:98,103,109,115,124``）
        ⇒ 下游 langchain 的 ``RunnableConfig`` 可**原样**落进来。
        （C22 · D11 的「``run_id`` 不进运行配置」**已被上游对齐取代** —— 上游的
        ``RunnableConfig`` **确实**带 ``run_id``。）
        """
        names = [f.name for f in fields(RunConfig)]
        assert names == [
            "thread_id",
            "context",
            "metadata",
            "tags",
            "configurable",
            "max_concurrency",
            "recursion_limit",
            "run_name",
            "run_id",
        ]


class TestSpanImmutability:
    """US2 · ``Span`` 不可变、不可哈希、字段级相等。"""

    def test_fields_are_frozen(self) -> None:
        """构造后改字段 MUST 抛 ``FrozenInstanceError``。"""
        span = _make_span()
        with pytest.raises(FrozenInstanceError):
            span.run_id = "run-2"  # type: ignore[misc]

    def test_is_unhashable(self) -> None:
        """``hash()`` MUST 抛 ``TypeError``（含映射字段 ⇒ 不可哈希）。"""
        with pytest.raises(TypeError):
            hash(_make_span())

    def test_equality_is_field_level(self) -> None:
        """同字段值 ⇒ 相等；异值 ⇒ 不等。"""
        assert _make_span() == _make_span()
        assert _make_span() != _make_span(run_id="run-2")


class TestSpanCopySemantics:
    """US2 · 映射型字段的**防御性浅拷贝**。"""

    def test_attributes_are_shallow_copied(self) -> None:
        """构造后改原 dict MUST NOT 影响实例。"""
        attributes: dict[str, Any] = {"gen_ai.system": "freegraph"}
        span = _make_span(attributes=attributes)
        attributes["gen_ai.system"] = "tampered"
        assert span.attributes == {"gen_ai.system": "freegraph"}

    def test_context_is_shallow_copied(self) -> None:
        """构造后改原 dict MUST NOT 影响实例。"""
        context: dict[str, Any] = {"phase": "plan"}
        span = _make_span(context=context)
        context["phase"] = "tampered"
        assert span.context == {"phase": "plan"}


class TestSpanJsonSerializability:
    """US2 · ``Span`` 100% 可 JSON 序列化（C27 的前提）。"""

    def test_span_is_json_serializable(self) -> None:
        """``json.dumps(asdict(span))`` MUST 不抛错。"""
        span = _make_span(
            attributes={"gen_ai.system": "freegraph"},
            context={"phase": "plan"},
            thread_id="thread-1",
            checkpoint_id="ckpt-1",
        )
        payload = json.dumps(asdict(span))
        assert json.loads(payload)["id"] == "span-1"

    def test_span_list_is_json_serializable(self) -> None:
        """**返回结构 = span 列表** ⇒ 整批 span 整体亦可序列化。"""
        spans = [_make_span(), _make_span(id="span-2")]
        payload = json.dumps([asdict(s) for s in spans])
        assert len(json.loads(payload)) == 2


class TestSpanLifecycle:
    """US2 · span 生命周期：按 ``id`` 配对、开始快照**不被事后改写**。"""

    def test_end_instance_shares_the_id_and_fills_end_time(self) -> None:
        """结束版 MUST 与开始版**同 ``id``**，且 ``end_time`` 已填。"""
        start = _make_span()
        end = replace(start, end_time="2026-11-06T10:00:01+00:00")
        assert end.id == start.id
        assert end.end_time == "2026-11-06T10:00:01+00:00"

    def test_start_snapshot_is_not_rewritten(self) -> None:
        """开始时的实例 MUST **不被事后改写**（其 ``end_time`` 始终为空）。"""
        start = _make_span()
        replace(start, end_time="2026-11-06T10:00:01+00:00")
        assert start.end_time is None

    def test_two_callbacks_pair_by_id(self) -> None:
        """两次回调 MUST 能**按 ``id`` 配对**，且开始快照不被事后改写。"""
        from fixtures.external_impl import RecordingTraceSink  # noqa: PLC0415

        sink = RecordingTraceSink()
        start = _make_span()
        end = replace(start, end_time="2026-11-06T10:00:01+00:00")

        sink.on_span_start(start)
        sink.on_span_end(end)

        assert sink.started == ["span-1"]
        assert sink.ended == ["span-1"]
        assert sink.started[0] == sink.ended[0]
        assert sink.end_times == ["2026-11-06T10:00:01+00:00"]
        assert start.end_time is None


class TestTraceSinkProtocol:
    """US2 · ``TraceSink`` 三方法。"""

    def test_method_set_is_exactly_three(self) -> None:
        """方法集 MUST **恰为**那 3 个。"""
        from test_protocols import _protocol_methods  # noqa: PLC0415

        assert _protocol_methods(TraceSink) == {
            "on_span_start",
            "on_span_end",
            "current_span",
        }

    def test_complete_implementation_is_accepted(self) -> None:
        """完整实现 MUST 判**真**。"""
        from fixtures.external_impl import RecordingTraceSink  # noqa: PLC0415

        assert isinstance(RecordingTraceSink(), TraceSink)

    @pytest.mark.parametrize(
        "missing", ["on_span_start", "on_span_end", "current_span"]
    )
    def test_missing_any_method_is_not_an_instance(self, missing: str) -> None:
        """缺**任一**方法的实现 MUST 判**假**。"""
        from test_protocols import _partial_protocol  # noqa: PLC0415

        partial = _partial_protocol(TraceSink, missing)()
        assert not isinstance(partial, TraceSink)


# ── US4 · TraceQuery ───────────────────────────────────────────────────

#: ``TraceQuery`` 的字段清单（**5 个**，逐字）——``data-model.md`` §3.5。
TRACE_QUERY_FIELDS = ["run_id", "thread_id", "node", "start_time", "end_time"]


class TestTraceQuery:
    """US4 · trace 查询请求（C27 的请求结构）。"""

    def test_field_list_is_exactly_five(self) -> None:
        """字段清单 MUST **恰为**那 5 个（逐字）。"""
        assert [f.name for f in fields(TraceQuery)] == TRACE_QUERY_FIELDS

    def test_all_fields_default_to_none(self) -> None:
        """五字段**全部可空**（缺省 ``None``）。"""
        query = TraceQuery()
        for name in TRACE_QUERY_FIELDS:
            assert getattr(query, name) is None, name

    def test_any_combination_is_constructible(self) -> None:
        """五字段 MUST 可**任意组合**（穷举 32 种组合构造不抛错）。"""
        import itertools

        for combination in itertools.product([None, "v"], repeat=len(TRACE_QUERY_FIELDS)):
            payload = dict(zip(TRACE_QUERY_FIELDS, combination, strict=True))
            assert TraceQuery(**payload) is not None

    def test_empty_query_means_everything(self) -> None:
        """**全空 = 取全部**——本层只断言「全空可构造」。"""
        query = TraceQuery()
        assert all(getattr(query, name) is None for name in TRACE_QUERY_FIELDS)

    def test_is_json_serializable(self) -> None:
        """``TraceQuery`` MUST 可 JSON 序列化。"""
        payload = json.dumps(asdict(TraceQuery(run_id="run-1")))
        assert json.loads(payload)["run_id"] == "run-1"

    def test_is_hashable(self) -> None:
        """``TraceQuery`` MUST **可哈希**（五字段全为标量 ⇒ dataclass 默认可哈希）。

        **有意如此**——与另四类的「不可哈希」不同（它本就没有映射字段）。
        """
        query = TraceQuery(run_id="run-1")
        assert hash(query) == hash(TraceQuery(run_id="run-1"))
        assert len({query, TraceQuery(run_id="run-1")}) == 1
