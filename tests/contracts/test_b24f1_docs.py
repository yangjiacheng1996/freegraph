# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US5 README 发布基线（FR-006 / FR-007 / FR-008 / FR-018 / SC-007）。"""

from __future__ import annotations

import re
from pathlib import Path

_ABS_COMPAT = "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md"
_CAPABILITY_HEADER = "| 能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1 |"
_OLD_COUNTS = ("31 个 feature", "93 人日", "契约层 18", "契约层 20", "契约层 21", "门面 7")


def _readme(repo_root: Path) -> str:
    return (repo_root / "README.md").read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"缺少章节 {heading}"
    return match.group(1)


def test_independence_and_promises(repo_root: Path) -> None:
    text = _readme(repo_root)
    assert "独立实现、非 LangChain Inc. 产品" in text
    assert "兼容意图为互操作，不构成 affiliation" in text
    for promise in ("零账号", "零出站", "零第三方运行时依赖", "license key"):
        assert promise in text, promise


def test_status_has_no_outdated_claims(repo_root: Path) -> None:
    text = _readme(repo_root)
    for outdated in (
        "内核尚未实现",
        "没有任何图运行时能力",
        "请勿用于生产",
        "请勿当作可用替代品",
        "不要把它当作",
    ):
        assert outdated not in text, outdated
    assert "占位版" in text


def test_capability_table_is_5_columns_and_8_rows(repo_root: Path) -> None:
    section = _section(_readme(repo_root), "## 能力 → freegraph 处置")
    assert _CAPABILITY_HEADER in section
    assert "2026-11-01" in section and "as-of" in section.lower()
    rows = [
        line.strip()
        for line in section.splitlines()
        if line.strip().startswith("|") and not line.strip().startswith("| 能力 ")
    ]
    data_rows = [row for row in rows if not re.fullmatch(r"\|[\s\-|:]+\|", row)]
    assert len(data_rows) == 8, data_rows


def test_compat_pointer_is_absolute_and_readme_has_no_matrix(repo_root: Path) -> None:
    text = _readme(repo_root)
    section = _section(text, "## API 兼容矩阵")
    assert _ABS_COMPAT in section
    assert not re.search(r"^\|\s*`[A-Za-z_][A-Za-z0-9_]*`\s*\|", section, re.M)


def test_otlp_section_keeps_three_backends_without_default(repo_root: Path) -> None:
    section = _section(_readme(repo_root), "## OTLP 导出（B21F1 · 可选 `[otlp]`）")
    for backend in ("OpenLIT", "Langfuse", "Phoenix"):
        assert backend in section
    assert "无默认推荐" in section
    assert "官方推荐" not in section
    assert "freegraph[otlp]" in section


def test_english_section_covers_key_parts(repo_root: Path) -> None:
    section = _section(_readme(repo_root), "## English")
    lowered = section.lower()
    for needle in (
        "independent implementation",
        "not a langchain inc. product",
        "zero account",
        "zero egress",
        "zero third-party runtime dependencies",
        "pip install",
        "compat.md",
    ):
        assert needle in lowered, needle


def test_chinese_first_structure_and_no_old_counts(repo_root: Path) -> None:
    text = _readme(repo_root)
    headings = re.findall(r"^## (.+)$", text, re.M)
    for heading in headings:
        if heading in {"English", "English Summary"}:
            continue
        assert re.search(r"[\u4e00-\u9fff]", heading), heading
    for old in _OLD_COUNTS:
        assert old not in text, old


def test_no_brand_assets(repo_root: Path) -> None:
    text = _readme(repo_root)
    assert not re.search(r"!\[[^\]]*\]\(", text)
    assert "官方推荐" not in text
    assert "默认后端" not in text
