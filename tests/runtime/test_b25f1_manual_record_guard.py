# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · SC-004 人工验收记录文档守卫。

* 常驻 CI：记录缺失 / 含占位 / 无真实轮证据 ⇒ `pytest.skip`（避免永久红 CI）；
* 发布 / 人工门禁：`B25F1_RECORD_STRICT=1` ⇒ 严格断言，无真实轮证据即失败。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECORD = _REPO_ROOT / "harness" / "verification" / "B25F1" / "manual-verification.md"
_B14_RECORD = _REPO_ROOT / "harness" / "verification" / "B14F1" / "manual-verification.md"
_B14_ACCEPTANCE = _REPO_ROOT / "harness" / "verification" / "B14F1" / "acceptance.py"

_PLACEHOLDERS = ("待填", "TODO", "⬜")
_REAL_MARKERS = ("B25F1 real round", "真实模型轮", "真实轮")
_ENV_MARKERS = ("环境偏离", "environment_deviation", "凭据未配置")


def _strict() -> bool:
    return os.environ.get("B25F1_RECORD_STRICT") == "1"


def _gate(reason: str) -> None:
    if _strict():
        pytest.fail(reason)
    pytest.skip(reason)


def _text() -> str:
    if not _RECORD.is_file():
        _gate(f"人工验收记录不存在：{_RECORD}")
    return _RECORD.read_text(encoding="utf-8")


def _ready_text() -> str:
    text = _text()
    placeholders = [item for item in _PLACEHOLDERS if item in text]
    if placeholders:
        _gate(f"记录含占位符 {placeholders}（未收口）")
    if not any(marker in text for marker in _REAL_MARKERS):
        _gate("记录缺真实模型轮证据（仅 fake / 环境偏离）")
    if all(marker in text for marker in _ENV_MARKERS) and "B25F1 real round: PASS" not in text:
        _gate("记录只有环境偏离，缺真实模型轮 PASS 证据")
    return text


def test_record_is_complete() -> None:
    text = _ready_text()
    for section in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert section in text, section
    for attachment in ("附件 1", "附件 2", "附件 3"):
        assert attachment in text, attachment
    assert len(text.strip()) > 1000


def test_record_covers_required_evidence() -> None:
    text = _ready_text()
    for marker in (
        "B15F1",
        "B16F1",
        "B20F1",
        "B20F2",
        "B21F1",
        "B23F1",
        "B24F1",
        "B14F1",
        "Y-01",
        "官方直连",
        "兼容网关",
    ):
        assert marker in text, marker
    assert "harness/verification/B14F1/manual-verification.md" in text
    assert "harness/verification/B14F1/acceptance.py" in text


def test_record_does_not_substitute_expected_for_actual() -> None:
    text = _ready_text()
    actual = text.split("## 3.", 1)[-1].split("## 4.", 1)[0]
    conclusion = text.split("## 4.", 1)[-1].split("## 5.", 1)[0]
    for section in (actual, conclusion):
        stripped = section.strip()
        assert stripped not in {"符合预期", "未验证", "符合预期。", "未验证。"}
        assert not stripped.startswith("符合预期")
        assert not stripped.startswith("未验证")


def test_record_legacy_issues_non_empty() -> None:
    text = _ready_text()
    legacy = text.split("## 5.", 1)[-1].split("## 附件", 1)[0]
    assert legacy.strip()
    assert "Y-01" in legacy
