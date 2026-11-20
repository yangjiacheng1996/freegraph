# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · 目标提示词承接段守卫（T058）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "b18f1-span-production" / "spec.md"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_b14f1_checkpoint_wiring() -> None:
    text = _read("harness/features/B14F1_Checkpointer协议与MemorySaver.md")
    for marker in ("B18F1", "checkpoint_id", "节点 span", "D-4"):
        assert marker in text


def test_b19f1_dual_binding_and_invoke_carriers() -> None:
    text = _read("harness/features/B19F1_TraceSink与current_span.md")
    for marker in (
        "B18F1",
        "SpanProducer",
        "bind_span_tracer",
        "bind_tracer",
        "双绑定",
        "D-1",
        "D-6",
        "承接机制",
        "原样抛出的异常",
    ):
        assert marker in text


def test_b20f1_json_record_wiring() -> None:
    text = _read("harness/features/B20F1_本地Trace存储JSONL.md")
    for marker in ("B18F1", "dataclasses.asdict", "run_id", "thread_id", "checkpoint_id", "D-6", "承接机制"):
        assert marker in text


def test_b20f2_query_dimension_wiring() -> None:
    text = _read("harness/features/B20F2_Trace查询API与SQLite后端.md")
    for marker in ("B18F1", "C27", "run_id", "thread_id", "checkpoint_id", "D-6", "承接机制"):
        assert marker in text
    assert "不含 `checkpoint_id` 过滤器" in text


def test_b21f1_otlp_wiring() -> None:
    text = _read("harness/features/B21F1_OTLP导出插件与后端对接.md")
    for marker in ("B18F1", "OTLP", "gen_ai", "error.type", "1:1"):
        assert marker in text


def test_spec_downstream_clauses_match_key_phrases() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for marker in ("双绑定", "C27", "OTLP", "checkpoint_id", "承接机制"):
        assert marker in text
