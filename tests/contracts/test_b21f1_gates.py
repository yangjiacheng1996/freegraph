# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B21F1 · 依赖闭包 / 许可证 / G26 / 无自研编码 / 门禁取证。"""

from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATES_DIR = _REPO_ROOT / "harness" / "scripts" / "gates"
_OBS = _REPO_ROOT / "src" / "freegraph" / "observability"
_NEW_MODULES = (
    _OBS / "_otlp_mapping.py",
    _OBS / "_otlp_transport.py",
    _OBS / "_otlp_exporter.py",
)
_EXPECTED_OTLP = [
    "opentelemetry-api>=1.20",
    "opentelemetry-sdk>=1.20",
    "opentelemetry-exporter-otlp-proto-grpc>=1.20",
]
_EXPECTED_CLOSURE = {
    "annotated-types",
    "googleapis-common-protos",
    "greenlet",
    "grpcio",
    "opentelemetry-api",
    "opentelemetry-exporter-otlp-common",
    "opentelemetry-exporter-otlp-proto-common",
    "opentelemetry-exporter-otlp-proto-grpc",
    "opentelemetry-proto",
    "opentelemetry-sdk",
    "opentelemetry-semantic-conventions",
    "ormsgpack",
    "playwright",
    "protobuf",
    "pydantic",
    "pydantic-core",
    "pyee",
    "typing-extensions",
    "typing-inspection",
}

sys.path.insert(0, str(_GATES_DIR))
import _gatekit  # noqa: E402


def _project() -> dict:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _extras() -> dict:
    manifest = _REPO_ROOT / "specs" / "b3f1-scaffold-ci-gates" / "contracts" / "extras-v2.toml"
    return tomllib.loads(manifest.read_text(encoding="utf-8"))


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
    return found


def test_base_install_is_empty_and_only_otlp_extra_is_declared() -> None:
    project = _project()["project"]
    assert project["dependencies"] == []
    extras = project["optional-dependencies"]
    assert set(extras) == {"otlp"}
    assert extras["otlp"] == _EXPECTED_OTLP


def test_extras_manifest_declares_otlp_and_full_closure() -> None:
    extras = _extras()
    declared = extras["project"]["optional-dependencies"]
    assert declared["otlp"] == _EXPECTED_OTLP
    closure = set(extras["tool"]["freegraph"]["extras_v2"]["closed_closure"])
    assert closure == _EXPECTED_CLOSURE


def test_otlp_closure_has_no_forbidden_package() -> None:
    declared = _extras()["project"]["optional-dependencies"]["otlp"]
    names = {item.split(">=")[0] for item in declared}
    assert "certifi" not in names
    assert "requests" not in names
    assert "opentelemetry-exporter-otlp" not in names
    assert "opentelemetry-exporter-otlp-proto-http" not in names
    for name in names:
        assert not name.startswith(("langchain", "langsmith", "langgraph"))


def test_g23_named_protobuf_normalization_is_exact() -> None:
    assert _gatekit.SPDX_PROSE_NORMALIZATION == {
        "protobuf": {"3-Clause BSD License": "BSD-3-Clause"}
    }
    assert _gatekit.normalize_prose_license("protobuf", "3-Clause BSD License") == "BSD-3-Clause"
    assert _gatekit.normalize_prose_license("protobuf", "MIT") == "MIT"
    assert _gatekit.normalize_prose_license("other", "3-Clause BSD License") == "3-Clause BSD License"


def test_g26_grpc_is_scanned_and_transport_is_the_only_exception() -> None:
    assert "grpc" in _gatekit.NETWORK_CLIENT_MODULES
    assert _gatekit.G26_EXCEPTED_MODULES == ("freegraph.observability._otlp_transport",)


def test_no_env_reads_in_new_modules() -> None:
    for path in _NEW_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert not (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr in {"environ", "environb", "getenv"}
                ), path.name
            if isinstance(node, ast.Name):
                assert node.id not in {"environ", "environb", "getenv"}, path.name


def test_no_self_encoding_and_only_official_encoder_stubs() -> None:
    for path in sorted((_REPO_ROOT / "src" / "freegraph").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "OTLPSpanExporter" not in text, path
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("google.protobuf"), path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("google.protobuf"), path
            elif isinstance(node, ast.Attribute):
                assert node.attr != "SerializeToString", path
    transport = (_OBS / "_otlp_transport.py").read_text(encoding="utf-8")
    assert "encode_spans" in transport
    assert "TraceServiceStub" in transport
    mapping = (_OBS / "_otlp_mapping.py").read_text(encoding="utf-8")
    assert "ReadableSpan" in mapping


def test_no_embedded_backend_packages() -> None:
    declared = _extras()["project"]["optional-dependencies"]
    names = {
        item.split(">=")[0].lower()
        for items in declared.values()
        for item in items
    }
    for forbidden in ("phoenix", "langfuse", "openlit"):
        assert forbidden not in names


def test_g21_and_g23_pass_on_the_manifest() -> None:
    manifest = (
        _REPO_ROOT
        / "specs"
        / "b3f1-scaffold-ci-gates"
        / "contracts"
        / "extras-v2.toml"
    )
    for script in ("gate_G21_dependencies.py", "gate_G23_licenses.py"):
        proc = subprocess.run(
            [sys.executable, str(_GATES_DIR / script), "--project", str(manifest)],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
