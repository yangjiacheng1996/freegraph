# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""外部实现夹具包（**零内部依赖**的可插拔能力实现样本）。

本包内的模块只允许 ``from freegraph.contracts import ...`` 与标准库 import
——架构门禁 **G2** 的「内部 import 档」扫描 ``tests/contracts/**``（含本目录），
「第三方 import 档」扫描本目录 ⇒ 夹具若引入 LangChain 家族或任何第三方包即报错。

存在的意义：让「协议可被外部实现」这条判据**可被静态扫描判定**，
而不是靠人读代码（research D-20）。
"""

__all__ = []
