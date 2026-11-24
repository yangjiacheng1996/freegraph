# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · SC-010 文档守卫：人工记录 / B25F1 承接 / README / 示例 README。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B21F1" / "manual-verification.md"
_ACCEPTANCE = _REPO_ROOT / "harness" / "verification" / "B21F1" / "acceptance.py"
_B25F1 = _REPO_ROOT / "harness" / "features" / "B25F1_双跑验收与迁移说明.md"
_README = _REPO_ROOT / "README.md"
_EXAMPLES_README = _REPO_ROOT / "harness" / "examples" / "B21F1" / "README.md"


def _text(path: Path) -> str:
    assert path.is_file(), path
    return path.read_text(encoding="utf-8")


def test_record_has_five_sections_and_is_non_empty() -> None:
    text = _text(_RECORD)
    for section in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert section in text, section
    assert len(text.strip()) > 1000
    assert "待填" not in text


def test_record_covers_required_evidence() -> None:
    text = _text(_RECORD)
    for marker in (
        "B21F1 acceptance: PASS",
        "显式端点",
        "最小 gRPC",
        "默认关闭",
        "失败隔离",
        "三示例",
        "protobuf",
        "质量门禁 5",
        "发起者书面追认",
        "B25F1",
    ):
        assert marker in text, marker


def test_acceptance_script_exists() -> None:
    assert _ACCEPTANCE.is_file()
    assert "B21F1 acceptance: PASS" in _text(_ACCEPTANCE)


def test_b25f1_downstream_clause_is_wired() -> None:
    text = _text(_B25F1)
    assert "下游承接（B21F1" in text
    assert "OTLP" in text
    assert "OtlpExporter" in text


def test_readme_and_examples_readme_markers() -> None:
    readme = _text(_README)
    for marker in ("OTLP 导出（B21F1", "freegraph[otlp]", "无默认推荐"):
        assert marker in readme, marker
    examples = _text(_EXAMPLES_README)
    for marker in (
        "能力分工 / 重叠",
        "无默认推荐",
        "OpenLIT 旧路径 404",
        "docs.openlit.io",
        "as-of",
        "HTTP exporter 是**用户侧依赖**",
        "只连不嵌",
    ):
        assert marker in examples, marker
