#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""Hatchling sdist 构建钩子：移除 hatchling 自动附带的 `.gitignore`。

hatchling 的 sdist builder 会把 VCS 忽略文件（如根 `.gitignore`）**强制**
加入 sdist（`get_default_build_data` 的 `force_include`），`exclude` 无法拦截。
本 feature 的 Release Gate 要求 sdist 不含 `.gitignore` ⇒ 在 sdist 构建
`finalize` 阶段从 tar.gz 中删除该条目。

本文件只对 **sdist target** 生效（配置在
`[tool.hatch.build.targets.sdist.hooks.custom]`），不影响 wheel 构建。
"""

from __future__ import annotations

import os
import tarfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class SdistPruneHook(BuildHookInterface):
    """删除 sdist 中的 `.gitignore` 条目。"""

    PLUGIN_NAME = "custom"

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        if not artifact_path.endswith(".tar.gz"):
            return
        with tarfile.open(artifact_path, "r:gz") as src:
            members = src.getmembers()
            if not any(m.name.endswith("/.gitignore") for m in members):
                return
            tmp_path = f"{artifact_path}.tmp"
            with tarfile.open(tmp_path, "w:gz") as dst:
                for member in members:
                    if member.name.endswith("/.gitignore"):
                        continue
                    payload = src.extractfile(member) if member.isfile() else None
                    dst.addfile(member, payload)
        os.replace(tmp_path, artifact_path)
