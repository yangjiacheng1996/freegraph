# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US4 `THIRD_PARTY_NOTICES` 定稿（FR-005 / SC-004）。"""

from __future__ import annotations

import re
from pathlib import Path


def _notices(repo_root: Path) -> str:
    return (repo_root / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")


def _section(text: str, number: int) -> str:
    match = re.search(rf"^##\s*{number}\..*?(?=^##\s|\Z)", text, re.S | re.M)
    assert match, f"缺少章节 {number}"
    return match.group(0)


def _data_rows(section: str) -> list[str]:
    rows: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.fullmatch(r"\|[\s\-|:]+\|", stripped):
            continue
        if stripped.startswith("| 包 ") or stripped.startswith("| 项目 "):
            continue
        if "（暂无条目）" in stripped:
            continue
        rows.append(stripped)
    return rows


def test_introduced_code_registration(repo_root: Path) -> None:
    section = _section(_notices(repo_root), 1)
    assert "langgraph-checkpoint-sqlite" in section
    assert "LangChain, Inc." in section
    assert "MIT" in section


def test_otlp_closure_and_protobuf_normalization(repo_root: Path) -> None:
    section = _section(_notices(repo_root), 2)
    for needle in (
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp-proto-grpc",
        "protobuf",
        "BSD-3-Clause",
        "3-Clause BSD License",
    ):
        assert needle in section, needle


def test_base_install_has_no_dependency_rows(repo_root: Path) -> None:
    assert _data_rows(_section(_notices(repo_root), 2)) == []


def test_test_only_dependency_is_not_registered(repo_root: Path) -> None:
    assert "langgraph==1.2.11" not in _notices(repo_root)


def test_affiliation_and_maintenance_point_to_compat(repo_root: Path) -> None:
    text = _notices(repo_root)
    section3 = _section(text, 3)
    assert "不构成 affiliation" in section3
    assert "COMPAT.md" in section3
    section4 = _section(text, 4)
    assert "COMPAT.md" in section4
    assert "README.md` 的 API 兼容矩阵" not in section4
    assert "F1P1" not in text and "F24P1" not in text
