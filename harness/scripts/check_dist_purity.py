#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""发行产物纯度门禁：断言 ``dist/`` 里只有**包代码与必要元数据**。

用法
----
    python harness/scripts/check_dist_purity.py [dist 目录]     # 退出码 0 = 干净

退出码：0 = 干净 · 1 = 有违规 · 2 = 目录 / 产物不存在。

本脚本 **只使用标准库**（发布流水线用系统 ``python3`` 直接执行）；
MUST NOT import ``packaging``。
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

# ── wheel 里允许出现的东西 ───────────────────────────────────────────────────
WHEEL_CODE_PREFIX = "freegraph/"
WHEEL_METADATA_RE = re.compile(r"^freegraph-[^/]+\.dist-info/")

# ── sdist 里允许出现的东西 ───────────────────────────────────────────────────
SDIST_ALLOWED_FILES = {"README.md", "LICENSE", "pyproject.toml", "PKG-INFO"}
SDIST_CODE_PREFIX = "src/freegraph/"

# ── 绝对不允许出现在任何产物里的目录 ─────────────────────────────────────────
FORBIDDEN_DIRS = (
    "harness/",
    ".specify/",
    ".opencode/",
    ".github/",
    "node_modules/",
    "specs/",
    "dist/",
    "tests/",
    "test/",
    ".venv/",
    "__pycache__/",
)

# ── 必需文件（防止「空包」通过门禁）─────────────────────────────────────────
SDIST_REQUIRED = (
    "src/freegraph/__init__.py",
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "PKG-INFO",
)
WHEEL_REQUIRED = ("freegraph/__init__.py", "freegraph/py.typed")

# ── 额外归档产物（不得静默忽略）─────────────────────────────────────────────
EXTRA_ARCHIVE_SUFFIXES = (".zip", ".tar", ".tgz", ".tbz2", ".tar.bz2", ".tar.xz")

# ── [otlp] 精确禁用包名（PEP 503 规范化后比较）──────────────────────────────
FORBIDDEN_OTLP = {
    "certifi",
    "requests",
    "opentelemetry-exporter-otlp",
    "opentelemetry-exporter-otlp-proto-http",
}


def _normalize_name(name: str) -> str:
    """PEP 503 包名规范化。"""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(spec: str) -> str:
    """从 ``Requires-Dist`` 行取包名（不做完整 requirement 解析）。"""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    if not match:
        raise ValueError(f"无法解析 Requires-Dist：{spec!r}")
    return _normalize_name(match.group(1))


def _extra_marker(spec: str) -> str | None:
    """返回 marker 中的 ``extra == "..."`` 值；没有则 ``None``。"""
    _, sep, marker = spec.partition(";")
    if not sep:
        return None
    match = re.search(r'\bextra\s*==\s*["\']([^"\']+)["\']', marker, re.I)
    return _normalize_name(match.group(1)) if match else None


def _check_metadata(text: str) -> list[str]:
    """检查 wheel ``METADATA`` 的 extras / 基础依赖 / [otlp] 闭包。"""
    problems: list[str] = []
    meta = Parser().parsestr(text)

    extras = {_normalize_name(item) for item in (meta.get_all("Provides-Extra") or [])}
    illegal_extras = sorted(extras - {"otlp"})
    if illegal_extras:
        problems.append(f"METADATA 含非法 Provides-Extra：{illegal_extras}")

    base_requires: list[str] = []
    otlp_requires: list[str] = []
    for spec in meta.get_all("Requires-Dist") or []:
        marker_extra = _extra_marker(spec)
        if marker_extra is None:
            if "extra" in spec.partition(";")[2].lower():
                problems.append(f"无法识别的 extra marker：{spec}")
            else:
                base_requires.append(spec)
        elif marker_extra == "otlp":
            otlp_requires.append(spec)
        else:
            problems.append(f"METADATA 含非法 extra marker：{spec}")

    if base_requires:
        problems.append(f"基础 Requires-Dist 非空：{base_requires}")
    for spec in otlp_requires:
        try:
            name = _requirement_name(spec)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        if name in FORBIDDEN_OTLP:
            problems.append(f"[otlp] 含禁用包：{name}")
    return problems


def _forbidden_hits(paths: list[str]) -> list[str]:
    hits = []
    for p in paths:
        norm = p.replace("\\", "/")
        if any(f"/{d}" in f"/{norm}" for d in FORBIDDEN_DIRS):
            hits.append(p)
        elif any(norm == d.rstrip("/") or norm.startswith(d) for d in FORBIDDEN_DIRS):
            hits.append(p)
    return sorted(set(hits))


def check_wheel(path: Path) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]

    for name in names:
        ok = name.startswith(WHEEL_CODE_PREFIX) or bool(WHEEL_METADATA_RE.match(name))
        if not ok:
            problems.append(f"wheel 含有非包内容：{name}")

    for req in WHEEL_REQUIRED:
        if req not in names:
            problems.append(f"wheel 缺少必需文件：{req}")

    metadata_names = [
        name for name in names if WHEEL_METADATA_RE.match(name) and name.endswith("/METADATA")
    ]
    if not metadata_names:
        problems.append("wheel 缺少 freegraph-*.dist-info/METADATA")
    else:
        with zipfile.ZipFile(path) as zf:
            text = zf.read(metadata_names[0]).decode("utf-8")
        problems.extend(_check_metadata(text))

    for hit in _forbidden_hits(names):
        problems.append(f"wheel 含有禁止目录内容：{hit}")

    return problems


def check_sdist(path: Path) -> list[str]:
    problems: list[str] = []
    with tarfile.open(path, "r:gz") as tf:
        members = [m for m in tf.getmembers() if m.isfile()]

    names: list[str] = []
    for m in members:
        parts = Path(m.name).parts
        if len(parts) < 2:
            continue
        names.append("/".join(parts[1:]))

    for name in names:
        if name.startswith(SDIST_CODE_PREFIX):
            continue
        if name in SDIST_ALLOWED_FILES:
            continue
        problems.append(f"sdist 含有非允许内容：{name}")

    for req in SDIST_REQUIRED:
        if req not in names:
            problems.append(f"sdist 缺少必需文件：{req}")

    for hit in _forbidden_hits(names):
        problems.append(f"sdist 含有禁止目录内容：{hit}")

    return problems


def _extra_archive_problems(dist: Path) -> list[str]:
    """``dist/`` 内任何归档类非 ``.whl`` / ``.tar.gz`` 文件 ⇒ 违规。

    ``uv build`` 自动生成的 ``dist/.gitignore`` 是构建目录标记 ⇒ 显式豁免。
    """
    problems: list[str] = []
    for path in sorted(dist.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        if name in {".gitignore"} or name.endswith((".whl", ".tar.gz")):
            continue
        if name.endswith(EXTRA_ARCHIVE_SUFFIXES):
            problems.append(f"dist 含额外归档产物：{name}")
    return problems


def main(argv: list[str]) -> int:
    dist = Path(argv[1]) if len(argv) > 1 else Path("dist")
    if not dist.is_dir():
        print(f"[纯度门禁] 目录不存在：{dist}", file=sys.stderr)
        return 2

    artifacts = sorted(
        [p for p in dist.glob("*.whl")] + [p for p in dist.glob("*.tar.gz")]
    )
    if not artifacts:
        print(f"[纯度门禁] {dist}/ 里没有任何产物", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    for art in artifacts:
        problems = check_wheel(art) if art.suffix == ".whl" else check_sdist(art)
        kind = "wheel" if art.suffix == ".whl" else "sdist"
        if problems:
            print(f"[纯度门禁] ❌ {art.name}（{kind}）")
            for p in problems:
                print(f"    · {p}")
            all_problems.extend(f"{art.name}: {p}" for p in problems)
        else:
            print(f"[纯度门禁] ✅ {art.name}（{kind}）——仅含包代码与必要元数据")

    extra_problems = _extra_archive_problems(dist)
    for p in extra_problems:
        print(f"[纯度门禁] ❌ {p}")
    all_problems.extend(extra_problems)

    if all_problems:
        print(
            f"\n[纯度门禁] 发行产物不干净，共 {len(all_problems)} 处问题；**拒绝发布**。\n"
            f"           仓库内容（harness/ .specify/ .opencode/）不得进入 PyPI 发行包。",
            file=sys.stderr,
        )
        return 1

    print(f"\n[纯度门禁] {len(artifacts)} 个产物全部干净，可以发布。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
