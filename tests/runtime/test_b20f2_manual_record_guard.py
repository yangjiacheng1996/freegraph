# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · SC-015：人工验证记录与 README 的文档守卫。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B20F2" / "manual-verification.md"
_DEMO_README = _REPO_ROOT / "harness" / "demo" / "README.md"
_VERIFICATION_README = _REPO_ROOT / "harness" / "verification" / "README.md"
_B25F1 = _REPO_ROOT / "harness" / "features" / "B25F1_双跑验收与迁移说明.md"


def test_manual_record_exists_and_has_required_evidence() -> None:
    assert _RECORD.is_file(), f"missing {_RECORD}"
    text = _RECORD.read_text(encoding="utf-8")
    assert len(text.strip()) > 0
    for section in ("验证环境", "验证步骤", "实际输出", "结论", "遗留问题"):
        assert section in text, section
    for marker in (
        "run_id=run-A",
        "thread_id=t-2",
        "time[T1,T1]",
        "node=a",
        "combo:",
        "parity: True",
        "empty count",
        "order:",
        "json.dumps: True",
        "tolerance count",
        "concurrency rows",
        "Windows",
        "egress calls: 0",
        "observability.__all__",
        "B20F1 query allowed",
        "质量门禁 5",
        "发起者追认",
        "确认人",
        "2026-11-21",
        "B20F2 acceptance: PASS",
    ):
        assert marker in text, marker
    assert "```" in text


def test_b25f1_downstream_clause_covers_both_stores() -> None:
    text = _B25F1.read_text(encoding="utf-8")
    section = text.split("## 下游承接（B20F2）", 1)[1]
    assert "FileTraceStore" in section
    assert "SqliteTraceStore" in section
    assert "query()" in section


def test_demo_readme_adds_b20f2_and_keeps_b20f1() -> None:
    text = _DEMO_README.read_text(encoding="utf-8")
    assert "已锁定（B20F1）" in text
    assert "FileTraceStore(directory=" in text
    assert "已锁定（B20F2）" in text
    assert "SqliteTraceStore(database=" in text
    assert "Studio 只走 `query()`" in text


def test_verification_readme_lists_b20f2() -> None:
    text = _VERIFICATION_README.read_text(encoding="utf-8")
    assert "B20F2/manual-verification.md" in text
    assert "B20F2/acceptance.py" in text
