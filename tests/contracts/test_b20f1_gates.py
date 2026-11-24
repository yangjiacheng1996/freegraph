# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F1 · 零环境变量 / 零第三方 / 零出站 / 署名头门禁。"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STOREFILE = REPO_ROOT / "src" / "freegraph" / "observability" / "_file_store.py"
FORBIDDEN_ROOTS = {"langchain", "langgraph", "langsmith", "opentelemetry", "sqlite3"}


def test_no_forbidden_imports_or_env_reads() -> None:
    tree = ast.parse(STOREFILE.read_text(encoding="utf-8"), filename=str(STOREFILE))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in FORBIDDEN_ROOTS, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in FORBIDDEN_ROOTS, node.module
        elif isinstance(node, ast.Name) and node.id in {"environ", "environb", "getenv"}:
            raise AssertionError("environment variable read found")


def test_no_network_client_or_stdout_side_effect() -> None:
    tree = ast.parse(STOREFILE.read_text(encoding="utf-8"), filename=str(STOREFILE))
    forbidden = {"socket", "http", "urllib", "requests", "httpx", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden, node.module


def test_signature_header_and_module_docstring() -> None:
    first_line = STOREFILE.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == (
        "# Copyright (c) 2026 杨家成 · MIT License · "
        "https://github.com/yangjiacheng1996/freegraph"
    )
    tree = ast.parse(STOREFILE.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree)
    assert isinstance(tree.body[0], ast.Expr)


def test_base_install_dependency_closure_is_still_empty() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project.get("dependencies", []) == []
    assert set(project.get("optional-dependencies", {})) == {"otlp"}
