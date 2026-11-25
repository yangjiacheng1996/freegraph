# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · US4 文档守卫：迁移说明三类 + Y-01；README 收口。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _REPO_ROOT / "harness" / "proposals" / "更名与迁移说明.md"
_README = _REPO_ROOT / "README.md"
_ABS_COMPAT = "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md"


def _text(path: Path) -> str:
    assert path.is_file(), path
    return path.read_text(encoding="utf-8")


def test_migration_guide_has_three_classes_and_y01() -> None:
    text = _text(_MIGRATION)
    for marker in (
        "同名直接可用",
        "同名但行为有差异",
        "需要改写",
        "Y-01",
        "Command.goto",
        "COMPAT.md",
    ):
        assert marker in text, marker
    assert _ABS_COMPAT in text or "COMPAT.md" in text


def test_readme_has_quickstart_promises_and_absolute_compat_link() -> None:
    text = _text(_README)
    for marker in (
        "## 快速上手",
        "零账号",
        "零出站",
        "零第三方运行时依赖",
        "独立实现",
        "非 LangChain Inc.",
        "## 能力 → freegraph 处置",
        _ABS_COMPAT,
    ):
        assert marker in text, marker


def test_readme_does_not_embed_full_compat_matrix() -> None:
    text = _text(_README)
    assert "18 项覆盖表" not in text
    assert "| `Command` |" not in text
    assert "| `CompiledGraph` |" not in text
    assert "| `Send` |" not in text
