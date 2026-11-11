# B2F2 · 公开 API 门面 `freegraph/graph.py` + API 签名快照 —— 人工验证记录

**feature**: B2F2（公开 API 门面 · 7 符号导出面 + API 签名快照 + 顶层包惰性断言）
**验收依据**: `specs/b2f2-public-api-facade/spec.md` · `plan.md` · `tasks.md`
**验收指南**: [`specs/b2f2-public-api-facade/quickstart.md`](../../../specs/b2f2-public-api-facade/quickstart.md)
**记录日期**: 2026-11-07
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：环境 / 步骤 / 实际输出 / 结论 / 遗留问题）。
> 第 3 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的平台 / 版本
> 逐条登记在第 5 节。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python | **3.12.3**（`/usr/bin/python3`） |
| 隔离 venv Python | **3.11.16**（`/tmp/fg-b2f2/bin/python`）—— 与 §2 的 **CPython 3.11.x** 基准一致 |
| 平台 | Linux 6.8.0-139-generic x86_64 |
| CPU | Intel Xeon Processor (Skylake, IBRS) |
| 性能预算基准解释器 | **CPython 3.11.16**（`/tmp/fg-b2f2/bin/python`）—— FR-019 ③ 要求 3.11.x，**本机有**，已按 3.11 实测 |
| freegraph 版本 | **0.0.3**（`pyproject.toml` 的 `version`） |
| pytest 版本 | 开发期 **7.4.4**（`/usr/bin/python3 -m pytest`）· 隔离 venv **9.2.0**（`/tmp/fg-b2f2/bin/python -m pytest`） |
| `requires-python` | `>=3.11` |
| 基础安装的包清单 | `pip list` ⇒ **仅** `freegraph 0.0.3`（+ venv 自带的 `pip` / `setuptools`）⇒ **依赖闭包为空集** |
| 依赖闭包实测 | `importlib.metadata.requires('freegraph')` ⇒ **`None`**（无任何 `Requires-Dist`） |
| 上游核实环境 | `langgraph 1.2.11` / `langchain-core 1.6.3`（**本 feature 未重新核实上游源码**——上游行号沿用 `research.md` §6 的逐条实测记录，见第 5 节遗留 #2） |

---

## 2. 步骤

> 逐条对应 `quickstart.md` 的场景 A–K。**venv 复用**：场景 A 建的 venv
> （`/tmp/fg-b2f2`）被 `tasks.md` T039 / T040 **复用**（未各建一套）。

| # | 场景 | 命令 | 关联判据 |
|---|---|---|---|
| A | 隔离环境 import | `/tmp/fg-b2f2/bin/python -c "from freegraph.graph import StateGraph, START, END"` | A1 / SC-001 |
| B | 导出面与常量 | `python3 -m pytest tests/facade/test_facade.py -v` | SC-002 / SC-003 |
| C | 快照 | `python3 -m pytest tests/facade/test_api_snapshot.py -v` | A2 / SC-005 / SC-006 |
| D | 未接线语义与构造 | `python3 -m pytest tests/facade/test_facade.py -v -k "not_wired or constructor or send or interrupt"` | SC-010 / SC-011 / SC-017 |
| E | 顶层包惰性 / 模块加载面 | `python3 -m pytest tests/facade/test_facade_gates.py -v -k "load or lazy"` | A3 / SC-007 / SC-008 |
| F | 依赖卫生 | `python3 -m pytest tests/facade/test_facade_gates.py -v -k hygiene` | SC-009 |
| G | 兼容矩阵 | `python3 -m pytest tests/facade/test_facade_gates.py -v -k matrix` | SC-012 |
| H | 契约层未受影响 | `python3 -m pytest tests/contracts/test_architecture.py -q -k "g7 or g12"` | SC-015 |
| I | 只读基准 / 署名头 | `git diff --exit-code -- harness/demo/target.py` | SC-014 |
| J | 验收脚本的预期退出码 | `PYTHONPATH=src python3 harness/demo/graph_core.py; echo $?` | SC-011 |
| K | 导入开销预算 | `/tmp/fg-b2f2/bin/python -c "import time; t=time.perf_counter(); import freegraph.graph; print(time.perf_counter()-t)"`（**先预热一次**，再取**三次**的最小值） | SC-018 |
| 全量 | 全量测试（开发机） | `python3 -m pytest -q` | 全部 |
| 全量 | 全量测试（**隔离 venv · 发行产物**） | `FREEGRAPH_TEST_INSTALLED=1 /tmp/fg-b2f2/bin/python -m pytest -q` | 全部 |
| 脚本 | 逐 feature 验收脚本（T046） | `python3 harness/verification/B2F2/acceptance.py --record out.md` | A1 / A2 / A3（退出码 0 = PASS） |

---

## 3. 实际输出

### 3.1 场景 A · 隔离环境 import（T018）

```console
$ rm -rf /tmp/fg-b2f2 && python3.11 -m venv /tmp/fg-b2f2
$ /tmp/fg-b2f2/bin/python -V
Python 3.11.16
$ /tmp/fg-b2f2/bin/pip install -q .
$ /tmp/fg-b2f2/bin/python -c "from freegraph.graph import StateGraph, START, END; print(START, END, StateGraph)"
__start__ __end__ <class 'freegraph._stategraph.StateGraph'>
$ echo $?
0
$ /tmp/fg-b2f2/bin/pip list
Package    Version
---------- -------
freegraph  0.0.3
pip        24.0
setuptools 79.0.1
$ /tmp/fg-b2f2/bin/python -c "from importlib.metadata import requires; print('requires =', requires('freegraph'))"
requires = None
```

⇒ **退出码 0**；`pip list` 中**只有** `freegraph`（`pip` / `setuptools` 是 venv 自带工具，
非依赖）⇒ **依赖闭包为空集**（A1 成立）。

### 3.2 场景 B · 导出面与常量

```console
$ python3 -m pytest tests/facade/test_facade.py -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-7.4.4, pluggy-1.4.0 -- /usr/bin/python3
collected 29 items

tests/facade/test_facade.py::TestImportSmoke::test_import_succeeds_in_a_fresh_interpreter PASSED [  3%]
tests/facade/test_facade.py::TestImportSmoke::test_start_and_end_values PASSED         [  6%]
tests/facade/test_facade.py::TestImportSmoke::test_start_and_end_are_plain_strings PASSED [ 10%]
tests/facade/test_facade.py::TestExportSurfaceSubset::test_all_contains_the_us1_subset PASSED [ 13%]
tests/facade/test_facade.py::TestExportSurfaceSubset::test_public_names_contain_the_us1_subset PASSED [ 17%]
tests/facade/test_facade.py::TestExportSurfaceSubset::test_constructor_accepts_exactly_one_positional_argument PASSED [ 20%]
tests/facade/test_facade.py::TestExportSurfaceSubset::test_constructor_has_no_side_effect PASSED [ 24%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_method_raises_not_implemented[add_node] PASSED [ 27%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_method_raises_not_implemented[add_edge] PASSED [ 31%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_method_raises_not_implemented[add_conditional_edges] PASSED [ 34%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_method_raises_not_implemented[compile] PASSED [ 37%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_compile_reports_b7f2 PASSED [ 41%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_methods_produce_no_real_semantics PASSED [ 44%]
tests/facade/test_facade.py::TestNotWired::test_not_wired_compile_does_not_return_an_executable PASSED [ 48%]
tests/facade/test_facade.py::TestExportSurfaceEquality::test_all_matches_the_manifest PASSED [ 51%]
tests/facade/test_facade.py::TestExportSurfaceEquality::test_public_names_match_the_manifest PASSED [ 55%]
tests/facade/test_facade.py::TestExportSurfaceEquality::test_selfcheck_detects_a_missing_export PASSED [ 58%]
tests/facade/test_facade.py::TestReExportedObjects::test_command_is_the_contract_object PASSED [ 62%]
tests/facade/test_facade.py::TestReExportedObjects::test_run_config_is_the_contract_object PASSED [ 65%]
tests/facade/test_facade.py::TestReExportedObjects::test_re_exported_types_are_not_subclasses PASSED [ 68%]
tests/facade/test_facade.py::TestSend::test_both_call_forms_are_legal PASSED [ 72%]
tests/facade/test_facade.py::TestSend::test_is_a_frozen_dataclass PASSED [ 75%]
tests/facade/test_facade.py::TestSend::test_mutating_an_attribute_fails PASSED [ 79%]
tests/facade/test_facade.py::TestSend::test_is_explicitly_unhashable PASSED [ 82%]
tests/facade/test_facade.py::TestSend::test_does_not_use_kw_only PASSED  [ 86%]
tests/facade/test_facade.py::TestInterrupt::test_raises_not_implemented[positional] PASSED [ 89%]
tests/facade/test_facade.py::TestInterrupt::test_raises_not_implemented[keyword] PASSED [ 93%]
tests/facade/test_facade.py::TestAcceptanceScriptsCanImportTheFacade::test_script_does_not_exit_with_environment_not_ready[graph_core] PASSED [ 96%]
tests/facade/test_facade.py::TestAcceptanceScriptsCanImportTheFacade::test_script_does_not_exit_with_environment_not_ready[acceptance] PASSED [100%]

============================== 29 passed in 0.83s ==============================
```

### 3.3 场景 C · 快照（T021–T024）

```console
$ python3 -m pytest tests/facade/test_api_snapshot.py -v
platform linux -- Python 3.12.3, pytest-7.4.4, pluggy-1.4.0 -- /usr/bin/python3
collected 16 items

tests/facade/test_api_snapshot.py::TestSnapshotComparison::test_snapshot_matches_the_committed_file PASSED [  6%]
tests/facade/test_api_snapshot.py::TestSnapshotComparison::test_difference_would_be_reported PASSED [ 12%]
tests/facade/test_api_snapshot.py::TestSnapshotComparison::test_snapshot_is_reproducible PASSED [ 18%]
tests/facade/test_api_snapshot.py::TestUpdateEntryPoint::test_update_option_defaults_to_off PASSED [ 25%]
tests/facade/test_api_snapshot.py::TestUpdateEntryPoint::test_update_entry_point_is_off_by_default PASSED [ 31%]
tests/facade/test_api_snapshot.py::TestUpdateEntryPoint::test_explicit_update_is_idempotent PASSED [ 37%]
tests/facade/test_api_snapshot.py::TestUpdateEntryPoint::test_snapshot_file_is_updated_only_when_requested SKIPPED [ 43%]
tests/facade/test_api_snapshot.py::TestSnapshotSelfCheck::test_selfcheck_detects_a_renamed_parameter PASSED [ 50%]
tests/facade/test_api_snapshot.py::TestSnapshotSelfCheck::test_selfcheck_detects_a_changed_annotation PASSED [ 56%]
tests/facade/test_api_snapshot.py::TestSnapshotSelfCheck::test_selfcheck_detects_a_new_public_attribute PASSED [ 62%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_file_is_utf8_without_bom PASSED [ 68%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_line_endings_are_lf PASSED [ 75%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_last_line_has_a_trailing_newline PASSED [ 81%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_text_contains_no_non_deterministic_content PASSED [ 87%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_top_level_entries_match_the_current_export_surface PASSED [ 93%]
tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_no_comment_lines_between_entries PASSED [100%]

======================== 15 passed, 1 skipped in 1.97s =========================
```

> `SKIPPED` 的那一条是「**入库**」用例——它**只在**显式带上 `--update-api-snapshot`
> 时才写盘（**默认关闭** · FR-011 ①）。

**入库快照**（`specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`，
由 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` 生成后
**人工 review diff**）：

```text
# freegraph 公开 API 快照 —— 门面 `freegraph.graph`
# 本文件由 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` 生成，请勿手工编辑。
# 格式契约：specs/b2f2-public-api-facade/contracts/snapshot-format.md
# 导出面清单（哪些符号算公开）的权威是 contracts/facade-api.md §0；本文件只记录签名。
#
[class] Command
    [attribute] PARENT: ClassVar[Literal['__parent__']] = '__parent__' (readonly)
    [attribute] goto: str | Sequence[str] | None = None (readonly)
    [attribute] resume: Any | None = None (readonly)
    [attribute] update: dict[str, Any] | None = None (readonly)
    [method] __init__(self, *, goto: str | Sequence[str] | None = None, update: dict[str, Any] | None = None, resume: Any | None = None) -> None
[constant] END = '__end__'
[class] RunConfig
    [attribute] context: Any = None (readonly)
    [attribute] metadata: Mapping[str, Any] = {} (readonly)
    [attribute] tags: Sequence[str] = () (readonly)
    [attribute] thread_id: str | None = None (readonly)
    [method] __init__(self, *, thread_id: str | None = None, context: Any = None, metadata: Mapping[str, Any] = {}, tags: Sequence[str] = ()) -> None
    [method] from_dict(cls, d: Mapping[str, Any], *, ignore_unknown: bool = False) -> RunConfig
[constant] START = '__start__'
[class] Send
    [attribute] arg: Any = <required> (readonly)
    [attribute] node: str = <required> (readonly)
    [method] __init__(self, node: str, arg: Any) -> None
[class] StateGraph
    [method] __init__(self, schema: Any) -> None
    [method] add_conditional_edges(self, src: str, path_fn: Callable[..., str | list[str]], path_map: list[str] | dict[str, str]) -> Self
    [method] add_edge(self, src: str | list[str], dst: str) -> Self
    [method] add_node(self, name: str, fn: NodeFunc, *, alias: str | None = None) -> Self
    [method] compile(self, *, checkpointer: Checkpointer | None = None, store: Store | None = None) -> CompiledGraph
[function] interrupt(value: Any) -> Any
```

> **口径说明（两处与 `data-model.md` §3.2 的示意不同，均以**规范性文本**为准）**：
> ① **顶级条目按名字排序**（spec FR-010 ② · `snapshot-format.md` T-5 ·
> `research.md` D-05「顶级条目 = 导出面成员，按**名字排序**」）⇒
> `Command` / `END` / `RunConfig` / `START` / `Send` / `StateGraph` / `interrupt`；
> §3.2 的示意是**手写**的（且它与 `research.md` D-05 的示意**互不一致**）
> ⇒ 以**排序规则**为准。② `update` 的注解渲染为 **`dict[str, Any] | None`**
> ——`snapshot-format.md` §1.1 的 **D-21-4** 规定「注解取自
> `dataclasses.fields(cls)[i].type`」⇒ 取到的是**求值对象**
> （`StateDict` 是 `dict[str, Any]` 的**别名**，运行时已展开），
> 故**不可能**渲染出别名名 `StateDict`。

### 3.4 场景 D · 未接线语义与构造

```console
$ python3 -m pytest tests/facade/test_facade.py -v -k "not_wired or constructor or send or interrupt"
collected 29 items / 13 deselected / 16 selected
============================= 16 passed in 0.14s ==============================
```

**未接线消息**（实测抛出）：

```text
add_node 尚未接线（由 B6F1 交付）
add_edge 尚未接线（由 B6F1 交付）
add_conditional_edges 尚未接线（由 B6F1 交付）
compile 尚未接线（由 B7F2 交付）
interrupt 尚未接线（由 B10F1 交付）
```

### 3.5 场景 E · 顶层包惰性 / 模块加载面

```console
$ python3 -m pytest tests/facade/test_facade_gates.py -v -k "load or lazy"
collected 37 items / 32 deselected / 5 selected
tests/facade/test_facade_gates.py::TestFacadeModuleLoadingSurface::test_importing_the_facade_loads_no_l4_or_l5 PASSED [ 20%]
tests/facade/test_facade_gates.py::TestFacadeModuleLoadingSurface::test_importing_the_facade_loads_the_contract_layer PASSED [ 40%]
tests/facade/test_facade_gates.py::TestFacadeModuleLoadingSurface::test_top_level_package_stays_lazy PASSED [ 60%]
tests/facade/test_facade_gates.py::TestFacadeModuleLoadingSurface::test_selfcheck_detects_a_forbidden_loaded_module PASSED [ 80%]
tests/facade/test_facade_gates.py::TestFacadeModuleLoadingSurface::test_selfcheck_detects_a_facade_pulling_l4 PASSED [100%]
======================= 5 passed, 32 deselected in 0.39s =======================
```

**手工复核**（`quickstart.md` §6 的等价口径）：

```console
$ PYTHONPATH=src python3 -c "import sys, freegraph; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
['freegraph']
$ PYTHONPATH=src python3 -c "import sys, freegraph.graph; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
['freegraph', 'freegraph._primitives', 'freegraph._stategraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.graph', 'freegraph.contracts.protocols', 'freegraph.contracts.trace', 'freegraph.contracts.types', 'freegraph.graph']
```

⇒ `import freegraph` 后 `freegraph.*` 的**子模块数 == 0**（A3）；
`import freegraph.graph` 后**不含任何** `persistence` / `observability` 形态的模块。

### 3.6 场景 F · 依赖卫生（G17 · 两档制）

```console
$ python3 -m pytest tests/facade/test_facade_gates.py -v -k hygiene
collected 37 items / 32 deselected / 5 selected
tests/facade/test_facade_gates.py::TestFacadeDependencyHygiene::test_no_internal_l4_l5_import PASSED [ 20%]
tests/facade/test_facade_gates.py::TestFacadeDependencyHygiene::test_no_third_party_import PASSED [ 40%]
tests/facade/test_facade_gates.py::TestFacadeDependencyHygiene::test_no_env_var_read_and_no_egress PASSED [ 60%]
tests/facade/test_facade_gates.py::TestFacadeDependencyHygiene::test_selfcheck_detects_an_env_var_read PASSED [ 80%]
tests/facade/test_facade_gates.py::TestFacadeDependencyHygiene::test_selfcheck_detects_an_l4_import_only PASSED [100%]
======================= 5 passed, 32 deselected in 0.05s =======================
```

### 3.7 场景 G · 兼容矩阵（G19）

```console
$ python3 -m pytest tests/facade/test_facade_gates.py -v -k matrix
collected 37 items / 32 deselected / 5 selected
tests/facade/test_facade_gates.py::TestCompatMatrixCoversTheFacade::test_matrix_covers_every_facade_symbol PASSED [ 20%]
tests/facade/test_facade_gates.py::TestCompatMatrixCoversTheFacade::test_matrix_covers_exactly_the_two_layers PASSED [ 40%]
tests/facade/test_facade_gates.py::TestCompatMatrixCoversTheFacade::test_new_rows_declare_equivalence_and_source PASSED [ 60%]
tests/facade/test_facade_gates.py::TestCompatMatrixCoversTheFacade::test_existing_contract_rows_are_unchanged PASSED [ 80%]
tests/facade/test_facade_gates.py::TestCompatMatrixCoversTheFacade::test_selfcheck_detects_a_missing_row PASSED [100%]
======================= 5 passed, 32 deselected in 0.06s =======================

$ sed -n '/^## API 兼容矩阵/,/^## /p' README.md | grep -E '^\| `(StateGraph|START|END|Send|interrupt)`'
| `StateGraph` | `langgraph.graph.StateGraph` | 部分等价 | 构造**只接受** `schema` 一个位置参数（上游另有 `context_schema` / `input_schema` / `output_schema`）；`add_node` 的参数名为 `name` / `fn`（上游 `node` / `action`）且新增 `alias` 关键字；`compile` 只保留 `checkpointer` / `store` 两个关键字（上游另含 `cache` / `interrupt_before` / `interrupt_after` / `debug` / `name` / `transformers`）；**构建器行为待 B6F1 / B7F2 交付**；上游来源 `langgraph/graph/state.py:131`（核实环境 `langgraph 1.2.11`） |
| `START` | `langgraph.constants.START` | 行为等价 | 值与语义均一致（`'__start__'`）；上游来源 `langgraph/constants.py:30`（核实环境 `langgraph 1.2.11`） |
| `END` | `langgraph.constants.END` | 行为等价 | 值与语义均一致（`'__end__'`）；上游来源 `langgraph/constants.py:28`（核实环境 `langgraph 1.2.11`） |
| `Send` | `langgraph.types.Send` | 部分等价 | 形状等价（`node` / `arg`）；**freegraph 侧不可变**（上游可变）；**fan-out 行为待 B11F1 交付**；上游来源 `langgraph/types.py:704`（核实环境 `langgraph 1.2.11`） |
| `interrupt` | `langgraph.types.interrupt` | 部分等价 | 形状等价（`value`）；**中断 / 恢复行为待 B10F1 交付**；上游来源 `langgraph/types.py:851`（核实环境 `langgraph 1.2.11`） |
```

### 3.8 场景 H · 契约层未受影响（SC-015）

```console
$ python3 -m pytest tests/contracts/test_architecture.py -q -k "g7 or g12"
....                                                                     [100%]
4 passed, 109 deselected in 0.06s

$ PYTHONPATH=src python3 -c "import freegraph.contracts as c; print(len(c.__all__)); print('Send' in c.__all__, 'interrupt' in c.__all__)"
18
False False
```

### 3.9 场景 I · 只读基准与红线（T041）

```console
$ git diff --exit-code -- harness/demo/target.py ; echo "exit=$?"
exit=0
$ git diff --exit-code -- THIRD_PARTY_NOTICES ; echo "exit=$?"
exit=0
$ git diff --exit-code -- pyproject.toml ; echo "exit=$?"
exit=0
$ git diff --stat -- src/freegraph/contracts/
（空 —— 契约层源码**逐字未动** ✓）
```

### 3.10 场景 J · 验收脚本的**预期退出码**（SC-011）

```console
$ PYTHONPATH=src python3 harness/demo/graph_core.py > /tmp/gc.out 2>&1 ; echo "exit=$?"
exit=1
$ tail -3 /tmp/gc.out
  ✘ A8 递归上限 · B13F1 · 用例组 case_recursion_limit 未抛异常即完成 — NotImplementedError: add_node 尚未接线（由 B6F1 交付）
  ✘ A9 运行时配置与 context 独立通道 · C21 / C22 · 用例组 case_run_config_and_context 未抛异常即完成 — NotImplementedError: add_node 尚未接线（由 B6F1 交付）
  ✘ A10 节点别名 · C25 · 用例组 case_node_alias 未抛异常即完成 — NotImplementedError: add_node 尚未接线（由 B6F1 交付）
结论：FAIL

$ PYTHONPATH=src python3 harness/demo/acceptance.py > /tmp/acc.out 2>&1 ; echo "exit=$?"
exit=1
$ tail -2 /tmp/acc.out
── 编排结论 ──
自身检查 1 · 子脚本 FAIL → 总体 1
```

⇒ 两个脚本都**能导入**门面的 7 个名字 ⇒ **不再**以退出码 **2**（环境未就绪）结束；
用例**必然全红**（`StateGraph` 未接线）⇒ 退出码 **1**。
**退出码 1 是本 feature 的预期状态**。

### 3.11 场景 K · 导入开销预算（T040 · FR-019 / SC-018）

**唯一计时口径**：以 `time.perf_counter()` 在 import 语句**前后**取差、
**不含解释器自身启动**、**暖机 best-of-3**（先预热一次再取三次的**最小值**）、
**基准 CPython 3.11.x**。

```console
$ /tmp/fg-b2f2/bin/python -c "import freegraph.graph"          # 预热
$ for i in 1 2 3; do /tmp/fg-b2f2/bin/python -c "import time; t=time.perf_counter(); import freegraph.graph; print(time.perf_counter()-t)"; done
0.06559715600451455
0.05220159998862073
0.052627631986979395
$ for i in 1 2 3; do /tmp/fg-b2f2/bin/python -c "import time; t=time.perf_counter(); import freegraph.contracts; print(time.perf_counter()-t)"; done
0.053192507999483496
0.06865424901479855
0.0622953400015831
```

| 项 | 实测（best-of-3） | 预算 | 判定 |
|---|---|---|---|
| `import freegraph.graph`（门面） | **52.2 ms** | **< 120 ms** | ✅ 通过（≈ 基线的 0.98 倍） |
| `import freegraph.contracts`（基线） | **53.2 ms** | — | — |

> 三个新增模块（门面 + 两个外壳）**零 I/O** ⇒ 门面的导入开销与契约层**基线持平**
> （52.2 ms vs 53.2 ms）。`research.md` D-19 记录的基线是 **50–63 ms**
> （CPython 3.12.3 · 2026-11-07）⇒ 本次 3.11.16 的实测落在同一区间内。

### 3.12 全量验收（T039）

```console
$ python3 -m pytest -q                       # 开发机 3.12.3 · 源码树
360 passed, 7 skipped in 5.17s

$ FREEGRAPH_TEST_INSTALLED=1 /tmp/fg-b2f2/bin/python -m pytest -q   # 隔离 venv 3.11.16 · 发行产物
365 passed, 2 skipped in 3.61s
```

> 差异来自 **G3（依赖闭包）**：未安装 freegraph 时该门禁 `skip`（5 条），
> 隔离 venv 里 freegraph **已安装** ⇒ 5 条**转为通过**（365 − 360 = 5）。
> 另有 1 条 `SKIPPED` 是「快照入库」用例（**默认关闭** · FR-011 ①）。

### 3.13 逐 feature 验收脚本（T046）

```console
$ python3 harness/verification/B2F2/acceptance.py ; echo "exit=$?"
...
── B2F2 人工验收 汇总 ──
硬断言 76 条 · 通过 76 · 失败 0
结论：PASS
  · 耗时 0.9s
exit=0

$ /tmp/fg-b2f2/bin/python harness/verification/B2F2/acceptance.py ; echo "exit=$?"
硬断言 76 条 · 通过 76 · 失败 0
结论：PASS
exit=0
```

---

## 3.x 补充验收（2026-11-11 · **B9F1 破 L1 冻结面的返工后** · **发起者验收**）

> **背景**：**B9F1** 为支持**命令列表**形态（上游 `ToolNode` **自身即用** · `langgraph/prebuilt/tool_node.py:890-920`），
> **经发起者特批**放宽了 L1 的 `NodeFunc.__call__` 返回联合
> （`StateDict | Command | None` ⇒ **`StateDict | Command | list[Command | StateDict] | None`）
> ⇒ **本 feature 的契约面**（`spec.md` FR-001 · `contracts/public-api.md`）随之改写 ⇒
> **本记录中记载旧签名的部分已失效** ⇒ 故在返工后**重新验收**。

### 步骤与实际输出（**发起者于 2026-11-11 亲自执行**）

```text
$ .venv/bin/python harness/verification/B2F2/acceptance.py
── B2F2 人工验收 汇总 ──
硬断言 76 条 · 通过 76 · 失败 0
结论：PASS
  · 耗时 0.6s
```

### 结论

- **三个已落地 feature 的验收脚本全绿**（B2F1 **124/124** · B2F2 **76/76** · B7F1 **104/104**）
  ⇒ **L1 公开签名变更未破坏任何既有验收判据**；
- ⚠️ **B2F1 的 SC021**（「兼容矩阵逐符号覆盖公开符号面（**18** 个）」）**自 B2F2 落地起即已过期**
  （矩阵**合法地**增补了门面的 **5** 个符号 ⇒ 矩阵共 **23** 行）⇒ 已按「**补齐过期**」修复
  （期望值补为 `18 ∪ 门面新增 5 = 23` ⇒ 断言**恢复为真**、**非放宽**）⇒ **与本次返工无关**
  （矩阵的**符号集合**返工前后**完全相同**）；
- **本记录由发起者验收并确认**（**实施者未代签**）⇒ 依据：B9F1 的 `plan.md` 登记项 **R-8 ③**。


## 4. 结论

| 判据 | 结论 | 说明 |
|---|---|---|
| **A1** `from freegraph.graph import StateGraph, START, END` 可用 | ✅ **通过** | 隔离 venv（CPython 3.11.16 · `pip install .`）退出码 **0**；`pip list` 仅 `freegraph`；依赖闭包为空集 |
| **A2** 签名快照入库 | ✅ **通过** | 快照文件已入库；逐字节比对 + 可复现 + 更新入口默认不生效 + **自检三例**全绿 |
| **A3** 顶层包惰性 | ✅ **通过** | `import freegraph` 后 `freegraph.*` 子模块数 **== 0**（只有 `freegraph`） |

**成功标准逐条核对**（SC-001…SC-018）：

| SC | 结论 | 落点 |
|---|---|---|
| SC-001 | ✅ | 场景 A（隔离环境退出码 0） |
| SC-002 | ✅ | `test_start_and_end_values` / `..._are_plain_strings` |
| SC-003 | ✅ | `TestExportSurfaceEquality` + 门禁 G15 两段 |
| SC-004 | ✅ | 门禁 G14（AST 零实现体）+ 自检 2 例 |
| SC-005 | ✅ | `TestSnapshotComparison` / `TestUpdateEntryPoint` / `TestSnapshotSelfCheck` + 门禁 G16 |
| SC-006 | ✅ | `test_snapshot_is_reproducible` + `TestSnapshotTextCompliance`（7 条） |
| SC-007 | ✅ | 门禁 G18（子进程模块加载面） |
| SC-008 | ✅ | `test_importing_the_facade_loads_no_l4_or_l5` |
| SC-009 | ✅ | 门禁 G17（两档制）+ 自检 2 例 |
| SC-010 | ✅ | `test_constructor_*`（构造成功 / `TypeError` / 零副作用） |
| SC-011 | ✅ | `test_not_wired_*` + 场景 J（退出码 **1** 而非 2） |
| SC-012 | ✅ | 门禁 G19（5 行齐备 + 等价程度 + 上游来源 + 既有 18 行未改） |
| SC-013 | ✅ | 本文件（五段式 + **来源覆盖表**）+ 验收脚本 76 条断言 |
| SC-014 | ✅ | 场景 I（`target.py` diff 为空）+ 门禁 G20（10 个文件署名头） |
| SC-015 | ✅ | 场景 H（契约层仍 18 个 · 不含 `Send` / `interrupt`） |
| SC-016 | ✅ | `test_not_wired_methods_produce_no_real_semantics` |
| SC-017 | ✅ | `TestSend`（不可变 / 不可哈希 / 两种调用形态） |
| SC-018 | ✅ | 场景 K（52.2 ms < 120 ms） |

**「用例未转绿是预期状态」的登记**（必填）：`harness/demo/graph_core.py` 与
`harness/demo/acceptance.py` 的用例在本 feature **必然全红**
（`StateGraph` 未接线）⇒ 预期**退出码 1**；**MUST NOT** 因此宣称验收脚本已跑通
（spec FR-009 / FR-018）。

**导出面 7 符号 × 来源 覆盖表**（必填 · SC-013「无来源项数 == 0」的载体）：

| 符号 | 来源（逐条填实） |
|---|---|
| `StateGraph` | 宪法原则 III 第 2–6 项（构造签名 / `add_node` / `add_edge` / `add_conditional_edges` / `compile`）· 立项书 §4.3 **第 1–6 项**（脚本行号 103 / 123 / 126–127 / 130,136 / 131–135 / 139）· `harness/demo/graph_core.py:48`（import 段）· 契约 C1 / C9 / C10 / C25 · 上游 `langgraph/graph/state.py:131`（核实环境 `langgraph 1.2.11`） |
| `START` | 契约 **C9** · 立项书 §4.3 **第 1 项**（脚本行号 103）· `harness/demo/graph_core.py:48` · 上游 `langgraph/constants.py:30`（核实环境 `langgraph 1.2.11`） |
| `END` | 契约 **C9** · 立项书 §4.3 **第 1 项**（脚本行号 103）· `harness/demo/graph_core.py:48` · 上游 `langgraph/constants.py:28`（核实环境 `langgraph 1.2.11`） |
| `Command` | 契约 **C16**（B1F1 冻结）· `harness/demo/graph_core.py:322`（`Command(goto=END, update=...)`）· `harness/demo/acceptance.py:51`（import 段）· 上游 `langgraph/types.py:833`（核实环境 **LangGraph 1.2.19** · 既有 18 行的版本口径） |
| `Send` | 契约 **C18**（不可变记录 · 不可哈希 · FR-005 ① 裁定 11）· `harness/demo/graph_core.py:339`（`Send("worker", {"n": 1})` —— **位置参数** ⇒ D-13「不用 `kw_only=True`」）· 上游 `langgraph/types.py:704`（核实环境 `langgraph 1.2.11`） |
| `interrupt` | 契约 **C17** · `harness/demo/graph_core.py:362`（`interrupt("approve?")`）· `harness/demo/acceptance.py:51` · 上游 `langgraph/types.py:851`（核实环境 `langgraph 1.2.11`） |
| `RunConfig` | 契约 **C22 / C21**（B1F1 冻结 · `thread_id` 在配置内 · `run_id` **NOT in** 字段清单）· `harness/demo/graph_core.py:484`（`RunConfig(thread_id=..., context=..., metadata=..., tags=...)`）· 上游 `langchain_core.runnables.RunnableConfig`（**行为不等价** · 刻意替代 · 既有 18 行的版本口径） |

**未列入本表的符号数 == 0** ✅

---

## 5. 遗留问题

| # | 事项 | 影响 | 归属 |
|---|---|---|---|
| 1 | **既有门禁 G8 的口径随兼容矩阵扩容而收敛**（`tests/contracts/test_architecture.py` 的**唯一**改动）：兼容矩阵自 B2F2 起**同时**承载契约层 18 个与门面层 7 个符号，原「矩阵首列符号集合 **==** 契约层 18 个」的**整表**判据不再成立 ⇒ G8 改为**按层**判定（「契约层 18 个**齐备**」+「无重复行」），**整表**的「无清单外符号」判据移交门禁 **G19**（门面侧）。**契约层的任何一条判据都未被削弱**；`src/freegraph/contracts/**` **逐字未动**。 | `tests/contracts/**` 不再是「零改动」——`plan.md`「与既有 feature 的关系」与 `tasks.md` T043 的 `git diff --stat -- tests/contracts/` 为空**这一条**未成立（原因见本表）。**该冲突源于 spec 自身**：FR-012 ③ 要求补入 5 行，而既有 G8 的整表集合相等判据与之互斥；B2F2 的门禁契约（`architecture-gates.md` §3）已声明 G8 的范围**只是**契约层 18 个符号 ⇒ 按声明范围收敛是唯一自洽解。 | **已在本 feature 内解决**（登记，不改 spec 的 FR-012 ③） |
| 2 | **上游行号未重新核实**：兼容矩阵 5 行的上游来源行号沿用 `research.md` §6 的实测记录（核实环境 `langgraph 1.2.11` / `langchain-core 1.6.3`，2026-11-07）——本 feature **未**在本机重新安装并逐条复核上游源码（上游包未在隔离 venv 中安装，避免污染「零依赖」证据）。 | 若上游换版本，5 行的来源行号可能失效（宪法原则 VIII：换版本 MUST 重新核实）。 | **B24F1**（全库矩阵补全与定稿） |
| 3 | **B2F1 的历史验收脚本口径已过时**：`harness/verification/B2F1/acceptance.py` 里的「兼容矩阵逐符号覆盖公开符号面（18 个）」那条判据在 B2F2 起**口径已变**（矩阵同时承载门面层 7 个符号）⇒ 该脚本**重跑**会报 1 条**假失败**。本 feature **不修改**历史验收脚本（它是 B2F1 的验收记录），改由 `harness/verification/B2F2/acceptance.py` 承担整表口径的判定。 | 重跑 B2F1 的验收脚本会看到 1 条假失败。 | **B24F1**（验收脚本随全库口径统一复核） |
| 4 | **Python 3.11 最低档的既有断言缺陷（顺带修复）**：`tests/contracts/test_architecture.py` 的 `_symbol_annotations` 原依赖 `Protocol.__protocol_attrs__`——该属性**只在 Python 3.12+ 存在**（3.11 没有）⇒ 该断言在 **3.11 最低档**恒失败（`Checkpointer` 取不到注解）。**该缺陷在本 feature 之前即存在**（已在 pristine 工作树上复现）。本 feature 改为从类的 `__dict__` 枚举协议方法（跨版本稳定，3.11 / 3.12 实测一致）。 | 不修则隔离 venv（3.11）的「全量 pytest 全绿」（T039）不可能成立。 | **已在本 feature 内解决**（登记） |
| 5 | **3.13 / 3.14 档未实测**：隔离 venv 只建了 **3.11.16**（FR-019 的基准档）一个；`pyproject.toml` 声明 `>=3.11`，**3.13 / 3.14 未实测**。 | 门禁 G9（typing 构件上限 3.11）在这两档上**未实跑**。 | **B3F1**（CI 多版本矩阵） |
| 6 | **CI 流水线未挂载快照检查**：本 feature 只交付 pytest 断言，**不新建** `harness/` 下的门禁脚本、**不改** `.github/workflows/`（门禁归 **B3F1**）。 | 快照漂移目前只在本地 `pytest` 时可见。 | **B3F1** |

---

## 6. 移交后续 feature（与 `contracts/facade-api.md` §6 同口径）

| # | 事项 | 归属 |
|---|---|---|
| 1 | `StateGraph` 的构建 / 编译行为 | B6F1 / B7F2 |
| 2 | `interrupt` / `Send` / `Command` 的运行时语义 | B10F1 / B11F1 / B9F1 |
| 3 | API 快照检查挂进 CI 流水线 | B3F1 |
| 4 | 兼容矩阵的全库补全与定稿（`COMPAT.md`） | B24F1 |
| 5 | 外壳模块搬到目标层（L2 / L3）时**只改门面的 import 行** —— 门面导出面 MUST NOT 变 | B6F1 / B10F1 / B11F1 |
