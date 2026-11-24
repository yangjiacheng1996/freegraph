# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US1 `[otlp]` 元数据 / 禁用包（FR-001 / FR-013 / FR-017 / SC-005 / SC-006）。"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

_FORBIDDEN = {
    "certifi",
    "requests",
    "opentelemetry-exporter-otlp",
    "opentelemetry-exporter-otlp-proto-http",
}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _package_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    assert match, requirement
    return _normalize(match.group(1))


def test_otlp_extra_is_gRPC_only(repo_root: Path) -> None:
    project = tomllib.loads(
        (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    otlp = project["optional-dependencies"]["otlp"]
    assert {_package_name(item) for item in otlp} == {
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp-proto-grpc",
    }
    assert all(_package_name(item) not in _FORBIDDEN for item in otlp)
    assert not any("certifi" in item or "proto-http" in item for item in otlp)
