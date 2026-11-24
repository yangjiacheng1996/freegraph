# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · US4：三个后端示例存在 / --help / 分工表 / 延迟导入。"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLES = _REPO_ROOT / "harness" / "examples" / "B21F1"
_SCRIPTS = ("phoenix.py", "openlit.py", "langfuse.py")


def _http_exporter_available() -> bool:
    try:
        return importlib.util.find_spec(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter"
        ) is not None
    except ModuleNotFoundError:
        return False


def _python(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(_REPO_ROOT / "src"), "PYTHONUTF8": "1"}
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def test_three_examples_and_readme_exist() -> None:
    for name in _SCRIPTS:
        assert (_EXAMPLES / name).is_file(), name
    assert (_EXAMPLES / "README.md").is_file()


@pytest.mark.parametrize("name", _SCRIPTS)
def test_help_works_without_user_side_http_exporter(name: str) -> None:
    proc = _python(str(_EXAMPLES / name), "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--endpoint" in proc.stdout


@pytest.mark.skipif(
    _http_exporter_available(),
    reason="user-side HTTP exporter installed; missing-package path not observable",
)
def test_openlit_and_langfuse_missing_http_exporter_print_hint() -> None:
    openlit = _python(
        str(_EXAMPLES / "openlit.py"),
        "--endpoint",
        "http://127.0.0.1:4318/v1/traces",
    )
    assert openlit.returncode == 2
    assert "opentelemetry-exporter-otlp-proto-http" in openlit.stderr

    langfuse = _python(
        str(_EXAMPLES / "langfuse.py"),
        "--endpoint",
        "http://127.0.0.1:3000/api/public/otel/v1/traces",
        "--public-key",
        "pk",
        "--secret-key",
        "sk",
    )
    assert langfuse.returncode == 2
    assert "opentelemetry-exporter-otlp-proto-http" in langfuse.stderr


def test_readme_contains_required_markers() -> None:
    text = (_EXAMPLES / "README.md").read_text(encoding="utf-8")
    for marker in (
        "能力分工 / 重叠",
        "无默认推荐",
        "OpenLIT 旧路径 404",
        "docs.openlit.io",
        "as-of",
        "HTTP exporter 是**用户侧依赖**",
        "只连不嵌",
        "同一份标准 OTLP 数据",
    ):
        assert marker in text, marker
    assert "官方推荐 / 默认后端" in text  # 反向约束的原文说明


def test_scripts_do_not_import_forbidden_packages_or_read_env() -> None:
    for name in _SCRIPTS:
        text = (_EXAMPLES / name).read_text(encoding="utf-8")
        for forbidden in ("langchain", "langchain_core", "langsmith", "langgraph"):
            assert forbidden not in text, (name, forbidden)
        assert "os.environ" not in text, name
        assert "os.getenv" not in text, name
        assert "required=True" in text, name


def test_http_exporter_import_is_deferred_until_after_argparse() -> None:
    for name in ("openlit.py", "langfuse.py"):
        tree = ast.parse((_EXAMPLES / name).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(
                    "opentelemetry.exporter.otlp.proto.http"
                ), (name, "top-level HTTP exporter import")
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.ImportFrom) and child.module:
                        if child.module.startswith(
                            "opentelemetry.exporter.otlp.proto.http"
                        ):
                            found = True
        assert found, name
