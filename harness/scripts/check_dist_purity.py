#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""发行产物纯度门禁：断言 ``dist/`` 里只有**包代码与必要元数据**。

为什么需要它
------------
本仓库把**全部项目内容**放在 GitHub 上供读者学习——

    harness/    调研报告、提示词、立项书、验收脚本集
    .specify/   宪法、spec 模板、speckit 脚本
    .opencode/  speckit 命令定义

但这些是**开发辅助材料**，不属于发行包：装到别人机器上、被人 ``import``
是不该发生的事。因此「GitHub 上看全部原理」与「PyPI 上的包是干净的」
必须同时成立。

打包配置里的 ``only-include`` 已经做到了这一点，但那是**配置**——有人加一行
``include`` 就会悄悄把整个仓库发上 PyPI。本脚本把它变成**门禁**：
发布流水线在 ``uv publish`` 之前先跑本脚本，不通过就不发。

用法
----
    python harness/scripts/check_dist_purity.py [dist 目录]     # 退出码 0 = 干净
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

# ── wheel 里允许出现的东西 ───────────────────────────────────────────────────
#   freegraph/                 ← 包代码（唯一允许的代码）
#   freegraph-*.dist-info/     ← 标准元数据（由构建工具生成）
WHEEL_CODE_PREFIX = "freegraph/"
WHEEL_METADATA_RE = "freegraph-*.dist-info/"

# ── sdist 里允许出现的东西 ───────────────────────────────────────────────────
#   src/freegraph/  包代码
#   README.md       包的 long_description
#   LICENSE         许可证（METADATA 的 License-File 指向它）
#   pyproject.toml  从 sdist 重建 wheel 所需
#   PKG-INFO        标准元数据
#   .gitignore      hatchling 默认附带，无害
SDIST_ALLOWED_FILES = {"README.md", "LICENSE", "pyproject.toml", "PKG-INFO", ".gitignore"}
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

# ── sdist 里必须存在的文件（防止「空包」通过门禁）────────────────────────────
SDIST_REQUIRED = ("src/freegraph/__init__.py", "README.md", "LICENSE", "PKG-INFO")
WHEEL_REQUIRED = ("freegraph/__init__.py", "freegraph/py.typed")


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
        ok = name.startswith(WHEEL_CODE_PREFIX) or name.startswith("freegraph-")
        if not ok:
            problems.append(f"wheel 含有非包内容：{name}")

    for req in WHEEL_REQUIRED:
        if req not in names:
            problems.append(f"wheel 缺少必需文件：{req}")

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
        names.append("/".join(parts[1:]))  # 去掉 sdist 顶层目录名

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
