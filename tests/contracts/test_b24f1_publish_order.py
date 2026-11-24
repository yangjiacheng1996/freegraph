# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US3 发布流水线顺序（FR-003 / SC-003）。"""

from __future__ import annotations

from pathlib import Path


def test_build_purity_publish_order(repo_root: Path) -> None:
    workflow = (repo_root / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    build = workflow.index("- name: Build")
    purity = workflow.index("- name: Verify artifact purity")
    publish = workflow.index("- name: Publish to PyPI")
    assert build < purity < publish
    assert "harness/scripts/check_dist_purity.py" in workflow[purity:publish]
