# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""门面测试包（**空占位**）。

存在意义只有一个：让 ``tests/facade/`` 成为一个**可被绝对导入的包**
⇒ 门禁辅助模块（``_gatesupport`` / ``_snapshot_tools``）与 ``conftest``
**只被导入一次**，不会因 pytest 的 rootdir 插入机制出现两份同名模块
（``tests/contracts/conftest.py`` 的模块名是 ``conftest``——若无本文件，
两个 conftest 会撞名）。

> 参见 `research.md` **D-16**：门禁测试文件**不叫** `test_architecture.py`
> ——与 `tests/contracts/test_architecture.py` 同名会在无 `__init__.py` 的
> 目录下触发 pytest 的 `import file mismatch`（收集期直接报错）。
"""

__all__: list[str] = []
