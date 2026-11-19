# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B8F2 · 人工验证记录的机械守卫（SC-020 / T060）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "harness" / "verification" / "B8F2" / "manual-verification.md"


def test_manual_verification_record_is_complete() -> None:
    assert RECORD.is_file(), f"缺人工验证记录：{RECORD}"
    text = RECORD.read_text(encoding="utf-8")
    for section in ("## §1", "## §2", "## §3", "## §4", "## §5"):
        assert section in text, f"缺五段式章节：{section}"
    for needle in (
        "values",
        "updates",
        "tasks",
        "debug",
        "checkpoints",
        "messages",
        "custom",
        "writer",
        "D-121",
        "D-136",
        "P-23 / X-6",
        "T-1",
        "T-2",
        "T-3",
        "T-4",
        "T-5",
        "R-5",
        "R-6",
        "发起者确认",
        "2026-11-20",
    ):
        assert needle in text, f"人工验证记录缺：{needle}"
