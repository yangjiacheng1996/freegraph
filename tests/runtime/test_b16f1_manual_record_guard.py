# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B16F1 · 人工验证记录守卫（SC-013）。"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "harness" / "verification" / "B16F1" / "manual-verification.md"


def test_manual_record_exists_with_five_sections() -> None:
    assert RECORD.exists(), f"missing manual verification record: {RECORD}"
    text = RECORD.read_text(encoding="utf-8")
    for heading in (
        "## 1. 环境",
        "## 2. 步骤",
        "## 3. 实际输出",
        "## 4. 结论",
        "## 5. 遗留问题",
    ):
        assert heading in text, heading


def test_manual_record_has_non_empty_fake_round_evidence() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert "fake 轮" in text
    assert "replay result: ['a', 'b', 'c']" in text
    assert "fork invoke: ['a', 'fork', 'b', 'c']" in text
    assert "original unchanged: True" in text
    assert "2345 passed" in text


def test_manual_record_has_real_model_round_and_ratification() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert "真实模型轮" in text
    assert "人工验收通过" in text
    assert "2026-11-24" in text
    assert "R-1" in text
    assert "StateSnapshot" in text
    assert "RunConfig" in text
    assert "唯一一次" in text


def test_acceptance_script_exists() -> None:
    acceptance = RECORD.parent / "acceptance.py"
    assert acceptance.exists(), f"missing acceptance script: {acceptance}"
    text = acceptance.read_text(encoding="utf-8")
    assert "B16F1 acceptance: PASS" in text


def test_manual_record_discloses_parity_differences() -> None:
    text = RECORD.read_text(encoding="utf-8")
    assert "D-07" in text
    assert "D-17" in text
    assert "STRICTER" in text
