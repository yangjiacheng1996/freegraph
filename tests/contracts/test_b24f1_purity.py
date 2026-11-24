# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US2 纯度正向合成产物（FR-002 / SC-002）。"""

from __future__ import annotations

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


def _wheel(dist: Path, *, with_py_typed: bool = True) -> Path:
    path = dist / "freegraph-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("freegraph/__init__.py", "__version__ = '0.0.0'\n")
        if with_py_typed:
            zf.writestr("freegraph/py.typed", "")
        zf.writestr(
            "freegraph-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: freegraph\nVersion: 0.0.0\n",
        )
    return path


def _sdist(dist: Path) -> Path:
    path = dist / "freegraph-0.0.0.tar.gz"
    files = {
        "src/freegraph/__init__.py": "__version__ = '0.0.0'\n",
        "README.md": "# freegraph\n",
        "LICENSE": "MIT License\n",
        "pyproject.toml": "[project]\nname='freegraph'\n",
        "PKG-INFO": "Metadata-Version: 2.1\nName: freegraph\nVersion: 0.0.0\n",
    }
    with tarfile.open(path, "w:gz") as tf:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(f"freegraph-0.0.0/{name}")
            info.size = len(data)
            import io

            tf.addfile(info, io.BytesIO(data))
    return path


def test_positive_wheel_and_sdist_pass(tmp_path: Path) -> None:
    _wheel(tmp_path)
    _sdist(tmp_path)
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "全部干净" in proc.stdout


def test_wheel_missing_py_typed_fails(tmp_path: Path) -> None:
    _wheel(tmp_path, with_py_typed=False)
    proc = _run(tmp_path)
    assert proc.returncode == 1
    assert "py.typed" in proc.stdout + proc.stderr
