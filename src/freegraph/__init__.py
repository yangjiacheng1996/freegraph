# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph — 图运行内核（Graph Runtime Kernel）。

**v0.0.x 是「占位版」（name-reservation placeholder）**：这几次发布只为在 PyPI 上
锁定 ``freegraph`` 这个发行名（发行名 = 导入名），内核功能尚未实现。

**v0.0.2 起**：每个源文件都携带署名头（Copyright + MIT + 项目地址）——
MIT 允许文件被单独复制，而复制不会带走 ``LICENSE``，因此署名必须随每个文件流动。

**v0.0.3 起**：基础安装**零第三方运行时依赖**（``dependencies = []``）——
原唯一的 ``typing-extensions`` 已剥离，理由见《项目宪法》修订记录 v1.2.0。

三条对外承诺（见仓库内《立项书》）：

* **零账号** —— 无需 LangSmith 账号、API key 或 license key；
* **零出站** —— freegraph 自身不主动发起任何出站连接，且不阻断用户代码出网；
* **零第三方运行时依赖** —— 基础安装**不装任何第三方包**（``pip install freegraph``
  后 site-packages 里只有 freegraph 自己）。

**最低 Python 版本：3.11** —— 3.11 一次性补齐 ``typing.Self`` / ``NotRequired`` /
``Required`` / ``TypeVarTuple`` / ``Unpack`` / ``LiteralString`` / ``dataclass_transform``
七项 typing 构件（3.12 与 3.13 各只补两项），使契约层与运行时**完全不需要**
``typing_extensions`` 兜底。

**顶层包保持惰性（FR-011）**：本模块只暴露 ``__version__`` 这一元信息，
**不导入任何子模块** —— 契约层（``freegraph.contracts``）、图定义层、运行时、
持久化层、可观测层一概不在此导入。理由：契约层必须能被外部项目（如 freechain）
**单独消费**而不拖进运行时；顶层包一旦连带导入子模块，这层分层收益即告失效，
也让「``import freegraph`` 到底加载了什么」变得不可判定。
架构门禁 G1 以子进程的 ``sys.modules`` 快照断言这条契约。

实现进度见 ``harness/proposals/立项书.md``（31 个 Phase / 93 人日 / v1.0）。
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.0.3"
