# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · SC-008 人工记录自动守卫（宪法 v1.13.0）。"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B24F1" / "manual-verification.md"
_B25F1 = _REPO_ROOT / "harness" / "features" / "B25F1_双跑验收与迁移说明.md"


def _text(path: Path) -> str:
    assert path.is_file(), f"缺少文件：{path}"
    return path.read_text(encoding="utf-8")


def test_record_has_five_sections_and_actual_output() -> None:
    text = _text(_RECORD)
    for heading in ("## 1. 环境", "## 2. 步骤", "## 3. 实际输出", "## 4. 结论", "## 5. 遗留问题"):
        assert heading in text, heading
    for needle in (
        "B24F1 acceptance: PASS",
        "pip freeze",
        "纯度",
        "退出码",
        "COMPAT.md",
        "18 项",
        "下游",
        "G8",
        "G19",
        "G29",
        "追认",
        "选项 A",
        "质量门禁 5",
        "B25F1",
        "Y-01",
        "Y-02",
        "Y-03",
        "B15F1",
        "B16F1",
    ):
        assert needle in text, needle
    assert "待填" not in text
    assert text.strip()


def test_b25f1_prompt_has_b24f1_handoff() -> None:
    text = _text(_B25F1)
    assert "下游承接（B24F1" in text
    assert "Y-01" in text
    assert "真实模型轮" in text
