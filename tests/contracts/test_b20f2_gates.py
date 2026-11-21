# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B20F2 · 零第三方 / 零 env / 零出站 / sqlite3 隔离 / 署名头 / 范围守卫。"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OBS = _REPO_ROOT / "src" / "freegraph" / "observability"
_NEW_MODULES = (_OBS / "_payloads.py", _OBS / "_query.py", _OBS / "_sqlite_store.py")
_FORBIDDEN_ROOTS = {"langchain", "langchain_core", "langgraph", "langsmith", "opentelemetry"}
_FORBIDDEN_EGRESS = ("socket", "http", "urllib", "requests", "httpx")


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def test_no_forbidden_third_party_imports() -> None:
    violations: list[tuple[str, str, int]] = []
    for path in _NEW_MODULES:
        for module, lineno in _imports(path):
            if module.split(".")[0] in _FORBIDDEN_ROOTS:
                violations.append((path.name, module, lineno))
    assert violations == [], violations


def _env_reads(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "os":
                if node.attr in {"environ", "environb", "getenv"}:
                    found.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in {"environ", "environb", "getenv"}:
            found.append(node.id)
    return found


def test_sqlite3_is_isolated_to_sqlite_module() -> None:
    for path in _NEW_MODULES:
        modules = {module.split(".")[0] for module, _ in _imports(path)}
        if path.name == "_sqlite_store.py":
            assert "sqlite3" in modules
            continue
        assert "sqlite3" not in modules, path.name


def test_no_env_reads_or_network_clients() -> None:
    for path in _NEW_MODULES:
        assert _env_reads(path) == [], path.name
        modules = {module.split(".")[0] for module, _ in _imports(path)}
        assert modules.isdisjoint(set(_FORBIDDEN_EGRESS)), (path.name, modules)


def test_signature_header_and_docstring() -> None:
    for path in _NEW_MODULES:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith("# Copyright (c) 2026"), path.name
        tree = ast.parse("\n".join(lines), filename=str(path))
        assert ast.get_docstring(tree), path.name


def test_dependency_closure_is_empty() -> None:
    with (_REPO_ROOT / "pyproject.toml").open("rb") as handle:
        payload = tomllib.load(handle)
    assert payload["project"]["dependencies"] == []


def test_scope_guard_has_no_out_of_scope_code() -> None:
    forbidden = (
        "opentelemetry",
        "psycopg",
        "asyncpg",
        "postgres",
        "otlp",
        "retention",
        "dataset",
    )
    for path in _NEW_MODULES:
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, (path.name, token)


def test_stdlib_only_top_level_imports() -> None:
    allowed = set(sys.stdlib_module_names) | {"freegraph"}
    for path in _NEW_MODULES:
        for module, lineno in _imports(path):
            root = module.split(".")[0]
            assert root in allowed or root == "", (path.name, module, lineno)
