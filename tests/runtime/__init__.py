# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B4F1 的**测试包**（状态 schema 解析 + 归约器提取）。

本包**自带** ``__init__.py`` ⇒ 目录名 ``tests.runtime`` 成为一个**包**
⇒ pytest 收集到的模块名带**包前缀**（``tests.runtime.test_schema_parse``）
⇒ **不会**触发 pytest 的 ``import file mismatch``（本仓库的
``tests/contracts/`` 与 ``tests/facade/`` 各有一个同族的 ``test_*.py``）。

**三个刻意分开的测试模块**（2026-11-08 分析轮）：

* ``test_future_annotations.py`` —— ``from __future__ import annotations``
  会让**整份文件**的注解变成字符串 ⇒ MUST 与其它用例**物理隔离**；
* ``test_typed_dict_variants.py`` —— pytest 的**收集期**即 import 该模块
  ⇒ 进程内 ``sys.modules`` 必含 ``typing_extensions`` ⇒ 与
  ``test_parse_contract.py`` 的「导入后无 ``typing_extensions``」断言
  **必须分文件**；
* ``test_binary_criterion.py`` —— 判定表逐条比对（判据的**唯一权威** =
  ``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``）。
"""

__all__: list[str] = []
