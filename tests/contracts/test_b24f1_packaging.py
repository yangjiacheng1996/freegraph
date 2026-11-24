# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US1 打包元数据 / py.typed / 许可证（FR-001 / FR-008 / FR-009 / FR-013 / SC-005）。"""

from __future__ import annotations

import tomllib
from pathlib import Path


def _project(repo_root: Path) -> dict:
    return tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_base_metadata(repo_root: Path) -> None:
    project = _project(repo_root)
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == []
    assert set(project.get("optional-dependencies", {})) == {"otlp"}


def test_no_v2_extras_in_v1_metadata(repo_root: Path) -> None:
    extras = set(_project(repo_root).get("optional-dependencies", {}))
    assert extras.isdisjoint({"pydantic", "checkpoint", "otel", "png"})


def test_py_typed_exists(repo_root: Path) -> None:
    assert (repo_root / "src" / "freegraph" / "py.typed").is_file()


def test_license_is_mit(repo_root: Path) -> None:
    project = _project(repo_root)
    assert project["license"] == "MIT"
    text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Permission is hereby granted" in text
