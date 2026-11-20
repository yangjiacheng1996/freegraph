# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B18F1 · 原则 IV 载体映射的文档守卫（T056）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "b18f1-span-production" / "spec.md"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_spec_contains_carrier_mapping_and_error_carrier_rule() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for marker in ("D-6", "FR-029", "SC-016", "原则 IV"):
        assert marker in text
    assert "原样抛出的异常" in text
    assert "PregelTask.error" in text
    assert "不作为失败路径载体" in text
    assert "承接机制" in text
    assert "MUST 保持空映射" in text


def test_target_prompts_are_wired_for_carriers() -> None:
    b14 = _read("harness/features/B14F1_Checkpointer协议与MemorySaver.md")
    b19 = _read("harness/features/B19F1_TraceSink与current_span.md")
    b20f1 = _read("harness/features/B20F1_本地Trace存储JSONL.md")
    b20f2 = _read("harness/features/B20F2_Trace查询API与SQLite后端.md")

    assert "B18F1" in b14 and "checkpoint_id" in b14 and "节点 span" in b14
    for text in (b19, b20f1, b20f2):
        assert "B18F1" in text
        assert "D-6" in text
        assert "承接机制" in text
    assert "原样抛出的异常" in b19
