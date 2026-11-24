# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US3 纯度负向合成产物（FR-002 / FR-010 / FR-017 / SC-002 / SC-003）。"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "harness" / "scripts" / "check_dist_purity.py"


def _run(dist: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(dist)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _wheel(
    dist: Path,
    *,
    extra: dict[str, str] | None = None,
    metadata_extra: str = "",
) -> Path:
    path = dist / "freegraph-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("freegraph/__init__.py", "__version__ = '0.0.0'\n")
        zf.writestr("freegraph/py.typed", "")
        zf.writestr(
            "freegraph-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: freegraph\nVersion: 0.0.0\n" + metadata_extra,
        )
        for name, text in (extra or {}).items():
            zf.writestr(name, text)
    return path


def _sdist(dist: Path, *, omit: set[str] | None = None, extra: dict[str, str] | None = None) -> Path:
    path = dist / "freegraph-0.0.0.tar.gz"
    omit = omit or set()
    files = {
        "src/freegraph/__init__.py": "__version__ = '0.0.0'\n",
        "README.md": "# freegraph\n",
        "LICENSE": "MIT License\n",
        "pyproject.toml": "[project]\nname='freegraph'\n",
        "PKG-INFO": "Metadata-Version: 2.1\nName: freegraph\nVersion: 0.0.0\n",
    }
    files.update(extra or {})
    with tarfile.open(path, "w:gz") as tf:
        for name, text in files.items():
            if name in omit:
                continue
            data = text.encode()
            info = tarfile.TarInfo(f"freegraph-0.0.0/{name}")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return path


def test_injected_repo_file_fails(tmp_path: Path) -> None:
    _wheel(tmp_path)
    _sdist(tmp_path, extra={"harness/report.md": "leak\n"})
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "harness/report.md" in proc.stdout + proc.stderr
    assert "拒绝发布" in proc.stdout + proc.stderr


def test_sdist_missing_required_files_fails(tmp_path: Path) -> None:
    for filename in ("pyproject.toml", "LICENSE", "PKG-INFO"):
        dist = tmp_path / filename.replace(".", "_")
        dist.mkdir()
        _sdist(dist, omit={filename})
        proc = _run(dist)
        assert proc.returncode == 1, filename
        assert filename in proc.stdout + proc.stderr


def test_sdist_gitignore_fails(tmp_path: Path) -> None:
    _sdist(tmp_path, extra={".gitignore": "*\n"})
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert ".gitignore" in proc.stdout + proc.stderr


def test_stray_zip_fails(tmp_path: Path) -> None:
    _wheel(tmp_path)
    (tmp_path / "evil.zip").write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "evil.zip" in proc.stdout + proc.stderr


def test_dist_gitignore_marker_is_exempt(tmp_path: Path) -> None:
    _wheel(tmp_path)
    _sdist(tmp_path)
    (tmp_path / ".gitignore").write_text("*\n", encoding="utf-8")
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_empty_or_missing_dist_exits_2(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _run(empty).returncode == 2
    assert _run(tmp_path / "missing").returncode == 2


def test_windows_style_repo_path_fails(tmp_path: Path) -> None:
    _sdist(tmp_path, extra={"harness\\report.md": "leak\n"})
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "report.md" in proc.stdout + proc.stderr


def test_wheel_root_prefix_is_not_a_blanket_exemption(tmp_path: Path) -> None:
    _wheel(tmp_path, extra={"freegraph-evil.txt": "evil\n"})
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "freegraph-evil.txt" in proc.stdout + proc.stderr


def test_metadata_illegal_extra_fails(tmp_path: Path) -> None:
    _wheel(tmp_path, metadata_extra="Provides-Extra: png\n")
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "Provides-Extra" in proc.stdout + proc.stderr


def test_metadata_polluted_otlp_fails(tmp_path: Path) -> None:
    _wheel(
        tmp_path,
        metadata_extra='Provides-Extra: otlp\nRequires-Dist: requests; extra == "otlp"\n',
    )
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "requests" in proc.stdout + proc.stderr
