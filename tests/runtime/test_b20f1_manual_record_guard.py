# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · SC-012 / SC-013：人工验证记录与 README 锁定的文档守卫。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B20F1" / "manual-verification.md"
_DEMO_README = _REPO_ROOT / "harness" / "demo" / "README.md"
_VERIFICATION_README = _REPO_ROOT / "harness" / "verification" / "README.md"


def test_manual_record_exists_and_has_required_evidence() -> None:
    assert _RECORD.is_file(), f"missing {_RECORD}"
    text = _RECORD.read_text(encoding="utf-8")
    assert len(text.strip()) > 0
    for section in ("验证环境", "验证步骤", "实际输出", "结论", "遗留问题"):
        assert section in text, section
    for marker in (
        "```json",
        "json.loads",
        "write_errors",
        "on_error",
        "零出站",
        "FileTraceStore",
        "质量门禁 5",
        "发起者追认",
        "2026-11-21",
    ):
        assert marker in text, marker
    assert "B20F1 acceptance: PASS" in text


def test_demo_readme_locks_the_trace_directory_shape() -> None:
    text = _DEMO_README.read_text(encoding="utf-8")
    assert "B20F1 未说参数名" not in text
    assert "已锁定（B20F1）" in text
    assert "FileTraceStore(directory=" in text


def test_verification_readme_lists_b20f1() -> None:
    text = _VERIFICATION_README.read_text(encoding="utf-8")
    assert "B20F1/manual-verification.md" in text
    assert "B20F1/acceptance.py" in text
