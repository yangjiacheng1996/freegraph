# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B8F3 · 人工验证记录守卫（T039）。

把 `harness/verification/B8F3/manual-verification.md` 的必备内容钉成可执行判据。
⚠️ 本文件 MUST 在 T037 完成后再启用；记录缺失 / 空壳 ⇒ 红。
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "harness" / "verification" / "B8F3" / "manual-verification.md"


def _record_text() -> str:
    assert RECORD.exists(), f"缺少人工验证记录：{RECORD}"
    text = RECORD.read_text(encoding="utf-8")
    assert text.strip(), "人工验证记录为空"
    return text


def test_record_has_five_sections() -> None:
    text = _record_text()
    for heading in ("## 1. ", "## 2. ", "## 3. ", "## 4. ", "## 5. "):
        assert heading in text, f"缺少五段式小节：{heading}"


def test_record_contains_real_outputs_for_each_area() -> None:
    text = _record_text()
    for marker in (
        "context",
        "RunConfig",
        "C25",
        "D-137",
        "D-144",
        "passed",
        "SAME 5",
    ):
        assert marker in text, f"缺少实测内容：{marker}"


def test_record_contains_constitution_and_changelog_evidence() -> None:
    text = _record_text()
    assert "1.16.0" in text
    assert "constitution-changelog" in text or "changelog" in text
    assert "C1–C24 + C26–C27" in text


def test_record_contains_t1_to_t7_acknowledgment_and_confirmation() -> None:
    text = _record_text()
    for index in range(1, 8):
        assert f"T-{index}" in text, f"缺少追认条目 T-{index}"
    assert "发起者确认" in text
    assert "2026-11-20" in text
