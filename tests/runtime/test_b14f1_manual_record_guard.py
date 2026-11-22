# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B14F1 · 人工验证记录文档守卫（SC-022）。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B14F1" / "manual-verification.md"


def test_manual_verification_record_has_required_sections_and_real_output() -> None:
    assert _RECORD.exists(), _RECORD
    text = _RECORD.read_text(encoding="utf-8")
    for heading in ("## 环境", "## 步骤", "## 实际输出", "## 结论", "## 遗留问题"):
        assert heading in text, heading
    assert "Command(resume=" in text
    assert "[second] state=" in text
    assert "answer=" in text
    assert "snapshot_count" in text
