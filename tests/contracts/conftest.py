# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""pytest 共享夹具 —— 让**开发期免安装**即可测到源码树。

仓库当前**未安装** freegraph（发行包尚未进入本机环境），故本文件把
``<repo>/src`` 插入 ``sys.path`` 的**最前**位置——源码优先，
避免测到已安装的旧版本。

两个开关：

* ``FREEGRAPH_TEST_INSTALLED=1`` ⇒ **跳过** ``sys.path`` 注入。
  供 F3P1 的 CI「先 ``pip install .`` 再跑 pytest」用，
  否则测的是源码树而非发行产物。

路径以 **fixture** 暴露（``repo_root`` / ``src_dir`` / ``contracts_dir``），
**不**用「模块级常量 + ``from conftest import ...``」跨文件引用——
那依赖 pytest 的 rootdir 插入机制，非惯用法，且 ``tests/`` 一旦加
``__init__.py`` 即失效。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
CONTRACTS_DIR = SRC_DIR / "freegraph" / "contracts"


def _inject_src() -> None:
    """把 ``<repo>/src`` 插入 ``sys.path`` 最前（源码优先）。"""
    if os.environ.get("FREEGRAPH_TEST_INSTALLED") == "1":
        return
    src = str(SRC_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)


_inject_src()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（README.md / THIRD_PARTY_NOTICES 等活文档的定位基准）。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """``<repo>/src``（源码树根，子进程 ``PYTHONPATH`` 的注入目标）。"""
    return SRC_DIR


@pytest.fixture(scope="session")
def contracts_dir() -> Path:
    """``<repo>/src/freegraph/contracts``（架构门禁的扫描目标）。"""
    return CONTRACTS_DIR
