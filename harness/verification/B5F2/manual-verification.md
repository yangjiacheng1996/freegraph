# B5F2 · 稀疏状态读取（C4 独立回归测试）+ 差分测试夹具 —— 人工验证记录

**feature**: B5F2（M1 运行时内核 · L2 执行内核层 · 状态读取层）
**验收依据**: `specs/b5f2-sparse-state-read/spec.md` · `plan.md` · `tasks.md` ·
`contracts/read-contract.md` · `contracts/differential-fixture.md` · `contracts/upstream-parity.md`
**验收指南**: [`specs/b5f2-sparse-state-read/quickstart.md`](../../../specs/b5f2-sparse-state-read/quickstart.md)
**记录日期**: 2026-11-10
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：① 验证环境 · ② 逐条判据的实测输出 ·
> ③ 与上游的逐条对照 · ④ 未实跑项 · ⑤ 来源覆盖表）。
> 第 2 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的项逐条登记在第 4 节。
>
> ⚠️ **追认栏已闭合** —— **R-1 / R-2 / R-3 / R-4** 四条**阻断合入**的登记项，
> 由**发起者本人**于 **2026-11-10** 在本会话中明示「**追认全部四条**」⇒ 依宪法 v1.6.0
> 「质量门禁的分阶段落地与发起者追认」，该追认由**发起者**作出，
> 实现者**未代签**、**未**改宪法正文、**未**写一条永久红的 CI、**未**把
> `GATE-MOUNT: C8` 改成 `landed` ⇒ **执行闸口 A7 通过** ⇒ **可合入**。

---

## 1. 验证环境

| 项 | 实际值 |
|---|---|
| 本机 Python（**主判定档** · `.venv`） | **3.11.16**（CI 矩阵的**最低档**） |
| 平台 | Linux-6.8.0-139-generic-x86_64-with-glibc2.39 |
| uv / pytest / coverage | **0.12.7** / **9.2.0** / **7.17.2**（coverage 是**开发期工具** · **未进** `pyproject.toml`） |
| freegraph 版本 | **0.0.3**（**可编辑安装** · `uv pip install -e .`） |
| `requires-python` | `>=3.11` |
| **v1.0 的发行元数据** | **零依赖包名** —— `dependencies = []` · `Requires-Dist` == `[]` |
| 核实环境（上游行号） | **`langgraph 1.2.11`**（`contracts/upstream-parity.md` 的 `路径:行号` 全部指向该版本） |
| **跑测试的命令口径** | `uv run --no-project --python .venv python -m pytest …`（**与 CI 逐字同款** · `--no-project` 不可省 ⇒ 否则 uv 同步环境会卸载 `differential` 组 ⇒ 差分用例全 skip ⇒ **假绿**） |
| 差分依赖组的安装 | `uv pip install --python .venv --group differential` ⇒ `langgraph==1.2.11` + 传递依赖（`langchain-core` / `langsmith` / …）**仅在测试侧** |
| **★ 一键验收入口** | `harness/verification/B5F2/acceptance.py`（**单文件 · 只依赖标准库** · **一条命令跑完全部验收闸口 V1–V12** + 覆盖率取证 + 10 条门禁 · **两态运行** · `--record` 产五段式片段 · 退出码 **0/1/2** · **裁定 34** · FR-039 / SC-034） |

### 1.0 · ★ **一键验收**（`harness/verification/B5F2/acceptance.py` · 裁定 34）

```bash
.venv/bin/python harness/verification/B5F2/acceptance.py
```

**实测输出（汇总段 · 原样粘贴）**：

```text
[V10 · 门禁实跑（10 条 · 零新增门禁编号）]
  ✔ 门禁 G21 通过（退出码 0）
  ✔ 门禁 G23 通过（退出码 0）
  ✔ 门禁 G24 通过（退出码 0）
  ✔ 门禁 G25 通过（退出码 0）
  ✔ 门禁 G26 通过（退出码 0）
  ✔ 门禁 G29 通过（退出码 0）
  ✔ 门禁 G30 通过（退出码 0）
  ✔ 门禁 G22 通过（**Linux only** · 只观测不阻断）
  ✔ 门禁 G27 通过（**Linux only** · 只观测不阻断）
  ✔ 门禁 G28 通过（**Linux only** · 只观测不阻断）

── B5F2 人工验收 汇总 ──
硬断言 88 条 · 通过 88 · 失败 0
结论：PASS
  · 耗时 64.5s
```

⇒ **退出码 0**（PASS）· **硬断言 88 条**（上游在场）⇒ **零新增门禁编号**（仍 **30**）。

**「缺席即 skip」的同款取证**（**未装 `differential` 组**的隔离 venv）：

```text
── B5F2 人工验收 汇总 ──
硬断言 66 条 · 通过 66 · 失败 0
待环境就绪 1 条（不判失败）：
  ◌ V7 / V8 · 差分夹具（三项投影逐字段相等 · 缺席即 skip） · 差分夹具的真实执行（上游**在场**） — 本解释器**未装** `langgraph`（PEP 735 的 `differential` 组）⇒ 差分组 **skip**（**非失败** · FR-019）
  ⇒ **skip ≠ pass** —— 补齐环境后请重跑：…
结论：PASS
  · 耗时 0.1s
```

⇒ **退出码 0** · **失败 0** ⇒ **skip ≠ fail**（FR-019 / SC-009）。


### 1.1 · ★ **实现前的绿基线**（tasks **T006** · 取自 B5F2 落地**之前**）

```bash
uv run --no-project --python .venv python -m pytest tests/ -ra
uv run --no-project --python .venv python -c "import importlib.metadata as m; print(m.requires('freegraph') or [])"
```

**实测输出（原样粘贴）**：

```text
=========================== short test summary info ============================
SKIPPED [1] tests/contracts/test_contract_regressions.py:35: 未落地 —— C4（稀疏状态读）由 B5F2（M1）建立
SKIPPED [1] tests/contracts/test_contract_regressions.py:45: 未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
SKIPPED [1] tests/facade/test_api_snapshot.py:189: 未开启 --update-api-snapshot（默认关闭 · FR-011 ①）
======================= 720 passed, 4 skipped in 18.15s ========================
```

```text
[]
```

⇒ **基线 = 720 passed / 4 skipped** · **`Requires-Dist` == `[]`**（**整体为空**）。

> ⚠️ **取样纪律**：本基线 MUST 在 **`T001`（`[dependency-groups] differential` 落地）之前**采集
> ⇒ 否则既有判据 `test_dependency_declarations_contain_no_upstream_package`（取样范围含
> `[dependency-groups]`）**立刻变红** ⇒ 基线将**不是绿**。**实测确认**：T001 落地后该判据
> **如期变红**（见 §2.7 的登记项 **R-3**）。

### 1.2 · 落地后的全量套件（**对照基线**）

```text
=========================== short test summary info ============================
SKIPPED [1] tests/contracts/test_contract_regressions.py:85: 未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
SKIPPED [1] tests/facade/test_api_snapshot.py:189: 未开启 --update-api-snapshot（默认关闭 · FR-011 ①）
======================= 802 passed, 3 skipped in 20.31s ========================
```

⇒ **720 → 802 passed**（**+82 条**）· **4 → 3 skipped**（C4 的那条 skip **翻成通过**）
⇒ **既有门禁零破坏**。

---

## 2. 逐条判据的实测输出

### 2.1 · §1 · C4 稀疏状态读（**验收判据 A1 / A2** · SC-001 / SC-002）

```bash
uv run --no-project --python .venv python -m pytest -q tests/runtime/test_read_c4_sparse_state.py
```

```text
.                                                                        [100%]
1 passed in 0.05s
```

**手工复核**（quickstart §1 的脚本 · **不经由图执行**）：

```text
True ['messages'] 0
```

⇒ 「`llm_calls` **缺席**」+「`.get(..., 0)` 返回 **`0`** 而非 `None`」+「结果是**普通 `dict`**」三条同时成立。
（断言**逐字**：`assert "llm_calls" not in node_input` / `assert node_input.get("llm_calls", 0) == 0`。）

### 2.2 · §2 · 挂载点接线（SC-015 / SC-025）

```bash
grep -n "GATE-MOUNT" tests/contracts/test_contract_regressions.py
```

```text
22:    # GATE-MOUNT: <编号> · status=<not-landed|landed> · owner=<承接方> · milestone=<里程碑> · desc=<说明>
35:# GATE-MOUNT: C4 · status=landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
36:# GATE-MOUNT: C8 · status=not-landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读
```

```bash
uv run --no-project --python .venv python -m pytest -q tests/contracts/test_architecture.py -k "internal_import"
```

```text
..                                                                       [100%]
2 passed, 111 deselected in 0.14s
```

⇒ **C4 = `landed`**（本 feature）· **C8 = `not-landed`**（**一字未动** · 仍属 **B8F1**）· **G2 仍绿**
（挂载点文件的**元测试只做路径扫描** · **零** `freegraph.*` import）。

### 2.3 · §3 · 稀疏读的语义（SC-003 / SC-004 / SC-027）

```bash
uv run --no-project --python .venv python -m pytest -q tests/runtime/test_read_semantics.py
```

```text
..............                                                           [100%]
14 passed in 0.07s
```

逐条判定（**断言落点** = `tests/runtime/test_read_semantics.py`）：

| 判定 | 断言落点 | 实测 |
|---|---|---|
| `type(result) is dict`（**逐字**） | `test_result_is_exactly_a_plain_dict` | ✅ |
| key 集合 == 「`is_available()` 为真」的集合（**I-1**） | `test_result_key_set_equals_the_available_channel_set` | ✅ |
| key **顺序** == 入参映射顺序（**I-2** · 含**反证**用例） | `test_result_key_order_follows_the_input_mapping_order` · `..._is_the_mapping_order_not_the_sorted_order` | ✅ |
| 值与通道当前值**同一对象**（**I-4**） | `test_result_values_are_the_very_same_objects_as_the_channel_values` | ✅ |
| 改结果 `dict` 的**键集合**不影响通道 | `test_mutating_the_result_key_set_does_not_affect_channel_state` | ✅ |
| 「值为 `None`」的通道**出现**（**I-10**） | `test_channel_holding_none_is_present_in_the_result` | ✅ |
| `skip_empty=False` ⇒ 抛 `EmptyChannelError`（`key` 指向该 key） | `test_skip_empty_false_raises_empty_channel_error_for_the_empty_key` | ✅ |
| 省略 `skip_empty` == 显式 `skip_empty=True` | `test_omitting_skip_empty_equals_explicit_true` | ✅ |
| **Edge Case ①** 空串 key 照常出现 | `test_empty_string_channel_key_is_kept_as_a_plain_dict_key` | ✅ |
| **Edge Case ②** schema 外的 key 照常读取 | `test_key_outside_the_schema_is_still_read` | ✅ |
| **Edge Case ③** 空映射 ⇒ 空 `dict` | `test_empty_mapping_returns_an_empty_dict` | ✅ |
| 入参非映射 ⇒ `TypeError` | `test_non_mapping_argument_raises_type_error` | ✅ |
| **已知面**：就地改值对象**会**影响通道（**与上游同构**） | `test_in_place_mutation_of_the_value_object_is_visible_on_the_channel` | ✅ |

### 2.4 · §4 · fresh 读（SC-005 · C8 的读取原语 · **SC-033**）

```bash
uv run --no-project --python .venv python -m pytest -q tests/runtime/test_read_fresh.py
```

```text
..............                                                           [100%]
14 passed in 0.06s
```

| 判定 | 断言落点 | 实测 |
|---|---|---|
| `fresh=True` 的视图**含**本次写入 | `test_fresh_view_contains_this_writes_values` | ✅ |
| 归约型通道的 fresh 视图 == **归约后**的结果 | `test_reducing_channel_fresh_view_equals_the_reduced_result` | ✅ |
| `fresh=False` 的视图**不含**本次写入 | `test_non_fresh_view_does_not_contain_this_writes_values` | ✅ |
| 覆盖型**无值** + 1 写 ⇒ 视图里出现该值 | `test_fresh_view_of_a_channel_without_a_value_shows_the_written_value` | ✅ |
| **零污染**（**绑定与可用性判定**前后**不变**） | `test_binding_and_availability_are_unchanged_by_a_fresh_read` · `..._by_a_non_fresh_read` | ✅ |
| 未知 key ⇒ `InvalidChannelUpdateError`（`key` 指向该 key） | `test_unknown_write_key_raises_invalid_channel_update_error` · `..._with_a_non_sequence_value_still_fails_explicitly` | ✅ |
| 归约器抛错 ⇒ **向上传播**且通道正式值**不变** | `test_reducer_failure_propagates_and_leaves_the_channel_unchanged` | ✅ |
| **已知面**：**就地修改型**归约器改写原通道的值对象 | `test_in_place_mutating_reducer_rewrites_the_original_value_object` | ✅ |
| **两个稀疏入口的结果逐字相等**（**I-11** · **SC-033**） | `test_the_two_sparse_entries_are_byte_identical` | ✅ |
| **Edge Case ④** 待写入映射为空 ⇒ 与非 fresh 读**逐字相等** | `test_empty_writes_mapping_returns_the_same_view_as_a_non_fresh_read` | ✅ |
| **Edge Case ⑤** 同一通道既读又写 ⇒ 视图 == 写入生效后的状态 | `test_same_channel_read_and_written_in_one_fresh_read` | ✅ |
| **Edge Case ⑥** 第三方 `Channel` 子类可被读取（且**可复制**） | `test_third_party_channel_subclass_is_readable` | ✅ |

### 2.5 · §5 · 差分夹具（**验收判据 A3 / A4** · SC-006 / SC-007 / **SC-032** / SC-013）

```bash
uv run --no-project --python .venv python -m pytest -q tests/differential/ -v
```

```text
collected 12 items

tests/differential/test_differential.py ............                     [100%]

============================== 12 passed in 0.61s ==============================
```

**判定记录 · 比对的具体字段**（FR-017 / SC-019 · **MUST NOT** 只写「一致」）——
混合规格（**有归约器** `messages` + **无归约器** `llm_calls` + **空 key** `""`）：

| 字段 | 期望（上游） | 实际（freegraph） | 结果 |
|---|---|---|---|
| `节点入参.count` | `3` | `3` | ✅ |
| `节点入参[0].keys` | `['messages']` | `['messages']` | ✅ |
| `节点入参[0]['messages']` | `['old']` | `['old']` | ✅ |
| `节点入参[1].keys` | `['messages']` | `['messages']` | ✅ |
| `节点入参[1]['messages']` | `['old', 'a']` | `['old', 'a']` | ✅ |
| `节点入参[2].keys` | `['', 'llm_calls', 'messages']` | `['', 'llm_calls', 'messages']` | ✅ |
| `节点入参[2]['']` | `'空键的值'` | `'空键的值'` | ✅ |
| `节点入参[2]['llm_calls']` | `1` | `1` | ✅ |
| `节点入参[2]['messages']` | `['old', 'a']` | `['old', 'a']` | ✅ |
| `输出状态.keys` | `['', 'llm_calls', 'messages']` | `['', 'llm_calls', 'messages']` | ✅ |
| `输出状态['']` | `'空键的值'` | `'空键的值'` | ✅ |
| `输出状态['llm_calls']` | `1` | `1` | ✅ |
| `输出状态['messages']` | `['old', 'a']` | `['old', 'a']` | ✅ |
| `事件序列.count` | `3` | `3` | ✅ |
| `事件序列[0]` | `(0, 'a', {'messages': ['a']})` | `(0, 'a', {'messages': ['a']})` | ✅ |
| `事件序列[1]` | `(1, 'b', {'llm_calls': 1, '': '空键的值'})` | `(1, 'b', {'llm_calls': 1, '': '空键的值'})` | ✅ |
| `事件序列[2]` | `(2, 'empty', None)` | `(2, 'empty', None)` | ✅ |

⇒ **三项投影逐项差异 == 0**（**SC-032** / SC-006 / SC-007）· **上游版本已记入判定记录**（`1.2.11`）。
⚠️ **key 的顺序不比对**（契约 §5）⇒ 归一化只取「**key 集合** + 逐 key 值」。

**判定器**的**灵敏度**（防「判据与实现同源 ⇒ 自证」）——
`test_the_comparison_reports_the_offending_field` **故意**制造一处差异 ⇒
报告 `节点入参[0]['messages']` · `expected == ['old']` · `actual == ['WRONG']` ⇒ ✅。

**图规格的前置校验**（**不依赖上游** ⇒ 缺席也照常跑）：

| 场景 | 断言落点 | 实测 |
|---|---|---|
| 覆盖「有归约器 + 无归约器 + 空 key」三者（**SC-013**） | `test_the_mixed_spec_exercises_reducer_cover_and_empty_key` | ✅ |
| 「模型工厂」钩子**非空** ⇒ **显式失败**（**SC-030**） | `test_a_non_empty_model_factory_is_an_explicit_failure` | ✅ |
| `conditional_edges` **非空** ⇒ **显式失败**（裁定 15） | `test_non_empty_conditional_edges_are_an_explicit_failure` | ✅ |
| 节点名**重复** ⇒ **显式失败** | `test_duplicate_node_names_are_an_explicit_failure` | ✅ |
| 初始输入含 schema 外的 key ⇒ **显式失败** | `test_an_initial_input_key_outside_the_schema_is_an_explicit_failure` | ✅ |
| 字段描述**缺值类型** ⇒ **显式失败** | `test_a_field_without_a_value_type_is_an_explicit_failure` | ✅ |
| 节点返回 schema 外的 key ⇒ **显式失败** | `test_a_node_returning_a_key_outside_the_schema_is_an_explicit_failure` | ✅ |
| 初始值与归约器不兼容 ⇒ **向上传播**且通道**不被污染** | `test_an_initial_value_incompatible_with_the_reducer_propagates_and_keeps_the_channel` | ✅ |

### 2.6 · §6 · 依赖红线（**验收判据 A5** · SC-008 / SC-010）

```bash
uv run --no-project --python .venv python -c "import importlib.metadata as m; print(m.requires('freegraph') or [])"
grep -rn "import langgraph\|import langchain\|from langgraph\|from langchain" src/freegraph/ || echo "OK：无上游导入"
```

```text
[]
OK：无上游导入
```

```bash
uv run --no-project --python .venv python -m pytest -q tests/runtime/test_parse_contract.py -k "dependency or workflow"
```

```text
..                                                                       [100%]
2 passed, 23 deselected in 0.05s
```

⇒ 发行元数据**整体为空** · 内核路径**零**上游导入 · **既有依赖判据按 R-3 拆分取样范围**（见 §2.7）。

### 2.7 · 登记项 **R-3** 的落地实测（**取样范围拆分** · SC-031）

| # | 判据 | 实测 | 结论 |
|---|---|---|---|
| ① | `[project].dependencies` 零上游（**原断言一字未动**） | `test_dependency_declarations_contain_no_upstream_package` ✅ | ✅ |
| ② | `[project].optional-dependencies]` 零上游（v1.0 **不存在** ⇒ 天然为零） | 同上 ✅ | ✅ |
| ③ | `[dependency-groups]` 含上游的组 == **恰好 1 个**且为 `differential` | `test_only_the_differential_group_may_declare_an_upstream_package` ✅ | ✅ |
| ④ | `ci.yml` 的上游安装路径 == **仅** `--group differential` | `test_the_ci_installs_the_upstream_only_through_the_differential_group` ✅ | ✅ |
| ⑤ | **拆分前的其余断言一条未放宽**（`ci.yml` 文本中 `langgraph` 字样 == **0**） | `test_ci_workflow_never_installs_langgraph` ✅（实测计数 == **0**） | ✅ |

⚠️ **实测记录（T001 落地后的必然变红）**：`T001` 落地**之前**，
`test_dependency_declarations_contain_no_upstream_package` **如期变红**（其取样范围含
`[dependency-groups]`）⇒ 这正是 **R-3** 登记的成因 ⇒ 按 **R-3** **拆分取样范围**
（**发行面部分逐字保留** + `[dependency-groups]` 改**正向枚举**）⇒
**MUST NOT** 以「删断言 / 放宽断言」的方式消除红灯 ⇒ **原断言一条未放宽**。

### 2.8 · §7 · 全量测试 + 门禁（CI 的等价物）

```bash
uv run --no-project --python .venv python -m pytest tests/ -ra
```

```text
======================= 802 passed, 3 skipped in 20.31s ========================
```

**门禁逐条实跑（10 条 · 退出码即判定）**：

| 门禁 | 退出码 | 输出摘要 |
|---|---|---|
| **G21** 依赖黑名单 | **0** | `[G21] PASS —— 依赖闭包黑名单（声明级 · 含全部 extras 变体）` |
| **G23** 许可证 | **0** | `[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）` |
| **G24** 配置层 | **0** | `[G24] PASS —— 配置层（LANGSMITH_* / LANGCHAIN_* / LANGGRAPH_* 零读取 + 内核零环境变量）` |
| **G25** 导入图单向 | **0** | `[G25] PASS —— 导入图单向（ARCH-1 · 层注册表驱动）`（新增的 `runtime/read.py` = **L2** ⇒ 自动纳入扫描） |
| **G26** 网络静态 | **0** | `[G26] PASS —— 网络静态扫描（src/freegraph/** 无网络客户端调用）` |
| **G27** 零出站动态（Linux） | **0** | `[G27] 框架出站 = 0 · 用户出站 = 2（记录在案，不判失败）` ⇒ `[G27] PASS` |
| **G29** 契约载体 | **0** | `[G29] 挂载点 C4：已落地` · `[G29] 挂载点 C8：未落地` ⇒ `[G29] PASS` |
| **G30** 署名头 + 品牌资产 | **0** | `[G30] PASS —— 全仓署名头（覆盖率 == 100%）+ 第三方品牌资产（FR-021）` |
| **G22** 隔离环境（Linux） | **0** | `[G22] PASS —— 隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）` |
| **G28** 断网等价性（Linux） | **0** | `[G28] 排除项 = 3 条（逐条有理由）· 实际执行 = 802 / 收集到 805` ⇒ `[G28] PASS` |

⇒ **门禁编号仍为 30**（`test_gate_numbering_is_unchanged` ✅）· **G29 输出含「挂载点 C4：**已落地**」**。

**⚠️ G27 的归因实测**（plan **R-2 风险 ④** · MUST NOT 把上游自身的出站记到 freegraph 头上）：

```text
[G27] 框架出站 = 0 · 用户出站 = 2（记录在案，不判失败）
- target=127.0.0.1:9 attribution=user 首个非标准库帧=_gatekit (harness/scripts/gates/_gatekit.py)
- target=127.0.0.1:9 attribution=user 首个非标准库帧=_gatekit (harness/scripts/gates/_gatekit.py)
```

⇒ **两条「用户出站」是门禁自身的反向验证用例自注入的**
（`tests/gates/test_gates.py:590` 的 `socket.create_connection(("127.0.0.1", 9), timeout=0.5)`
—— **RFC 863 的 discard 端口**）⇒ **与上游无关**。
**对照实测**：在**未装 `differential` 组**的隔离 venv 里跑同一监测 ⇒ **同样**是 2 条
`127.0.0.1:9` / `framework = 0` ⇒ **上游在 socket 监测下被 import 时**出站次数 == **0**
⇒ **框架出站 = 0**（结论按「**框架出站 = 0**」的归因口径判定）。

**步骤 5.6 的位置校验**（quickstart §7 的脚本）：

```text
OK：5.6 位置 4651 < 步骤 6 位置 5055
langgraph 字样计数 = 0
```

⇒ 步骤 5.6 **位于步骤 6（全量测试套件）之前** ⇒ 差分用例在 CI 里**真实执行**（**非永远 skip**）。

### 2.9 · §8 · 覆盖率取证（SC-018）

```bash
uv run --no-project --python .venv python -m coverage run --branch -m pytest -q tests/runtime tests/differential
uv run --no-project --python .venv python -m coverage report --include="src/freegraph/runtime/read.py,src/freegraph/runtime/__init__.py" --show-missing
```

```text
396 passed in 3.81s
Name                                Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------
src/freegraph/runtime/__init__.py       7      0      0      0   100%
src/freegraph/runtime/read.py          46      0     20      0   100%
-------------------------------------------------------------------------------
TOTAL                                  53      0     20      0   100%
```

**整包**（**记录 · 不阻断**）：

```text
src/freegraph/runtime/__init__.py       7      0      0      0   100%
src/freegraph/runtime/channel.py      125      0     34      0   100%
src/freegraph/runtime/errors.py        30      1      6      1    94%
src/freegraph/runtime/mapping.py       12      0      4      0   100%
src/freegraph/runtime/read.py          46      0     20      0   100%
src/freegraph/runtime/reducer.py       20      0      4      0   100%
src/freegraph/runtime/schema.py       109      7     32      6    89%
TOTAL                                 349      8    100      7    96%
```

⇒ **`read.py` 行 / 分支覆盖 == 100%**（**阻断判据**已达成）· `__init__.py` **新增部分** == **100%** ·
**整包 96%**（**记录但不阻断** · B5F1 无基线）。

### 2.10 · §9 · 冻结面审计（SC-011 / SC-012 / SC-029）

```text
契约层符号数 = 18 （MUST == 18）
门面符号数   = 7 （MUST == 7）
runtime 符号数 = 14 （MUST == 14 · 含 read_channels / local_read）
读取入口在 runtime 上 = True
```

⇒ 既有冻结面**零变更** · L2 导出面 **12 → 14**。

### 2.11 · §10 · 跨 feature 接线复核（宪法 **v1.8.0**）

```text
B7F1「承接条款（B5F2 → B7F1」命中数 = 2
B8F1「夹具接口口径（B5F2 → B8F1」命中数 = 2
B8F1「MUST 在使用 local_read 时显式传 fresh=True」命中数 = 1
B25F1「承接条款（B5F2 → B25F1」命中数 = 1
B4F1「承接条款（B5F2 → B4F1」命中数 = 1
B4F1「取样范围拆分」命中数 = 1
B4F1「判据收窄」命中数 = 0
```

⇒ **五处接线全部在位**（**含**本 feature 补入的**第五处**：**B8F1 MUST 显式传
`fresh=True`** · MUST **NOT** 依赖缺省 · MUST **NOT** 假设上游的 `managed` 语义）⇒
**B4F1 的措辞**与**裁定 27**一致（**取样范围拆分** ≥ 1 · **判据收窄** == 0）。

### 2.12 · **SC-009** 的取证（**缺席即跳过** · 未装 `differential` 组的环境）

```bash
uv venv --python 3.11 /tmp/opencode/venv-nolanggraph
uv pip install --python /tmp/opencode/venv-nolanggraph pytest packaging
uv pip install --python /tmp/opencode/venv-nolanggraph -e .
/tmp/opencode/venv-nolanggraph/bin/python -m pytest tests/differential/ -ra
```

```text
collected 12 items

tests/differential/test_differential.py .ss........s                     [100%]

=========================== short test summary info ============================
SKIPPED [1] tests/differential/test_differential.py:72: could not import 'langgraph': No module named 'langgraph'
SKIPPED [1] tests/differential/test_differential.py:93: could not import 'langgraph': No module named 'langgraph'
SKIPPED [1] tests/differential/test_differential.py:278: could not import 'langgraph': No module named 'langgraph'
========================= 9 passed, 3 skipped in 0.09s ==========================
```

⇒ **跳过标记数 == 3（≥ 1）** 且 **失败数 == 0** ⇒ **SC-009 成立**（**skip 而非 fail**）。
⚠️ **与 CI 主测试档互不替代**：CI 的 Linux 3.11 / 3.14 两档**装了**该组 ⇒ 差分用例
**真实执行**（**SC-014**）⇒ 见 §2.13。

### 2.13 · 档位实测（`langgraph==1.2.11` 的**安装与可导入性** · T035）

| 档位 | 实测 | 结论 | CI 处置 |
|---|---|---|---|
| **Linux x86_64 · CPython 3.11.16** | 安装 ✅ · 导入 ✅ · 差分用例 **12 条全绿** | ✅ **通过** | **步骤 5.6 装该组** |
| **Linux x86_64 · CPython 3.14.7** | 安装 ✅ · 导入 ✅ · 差分用例 **12 条全绿** | ✅ **通过** | **步骤 5.6 装该组** |
| **macOS 3.11 / 3.14** | **未实测**（本机无该平台） | ⚠️ **未实测** | **不装** ⇒ 该档差分用例 **skip**（**非失败**）· 已登记（§4） |
| **Windows 3.11 / 3.14** | **未实测**（本机无该平台） | ⚠️ **未实测** | **不装** ⇒ 该档差分用例 **skip**（**非失败**）· 已登记（§4） |
| **Linux arm64 · 3.11** | **未实测**（本机为 x86_64） | ⚠️ **未实测** | **不装** ⇒ 该档差分用例 **skip**（**非失败**）· 已登记（§4） |

**3.14 档的实测输出**：

```text
python 3.14.7
langgraph 1.2.11
import OK
12 passed, 13 warnings in 0.64s
```

⚠️ **MUST NOT 静默不跑** ⇒ 上表三档「未实测」已逐条登记在 **§4** ⇒ 交由 CI 实测确认
（**实测通过**的档 MUST 装该组）。

### 2.14 · 验收闸口 **V1–V12** 的逐条结论

| 闸口 | 内容 | 实测 | 结论 |
|---|---|---|---|
| **V1** | C4 独立回归测试**通过**（A1 / A2 两条断言） | §2.1（`1 passed` + `True ['messages'] 0`） | ✅ |
| **V2** | 挂载点 C4 = `landed` · C8 = `not-landed` | §2.2 | ✅ |
| **V3** | **G2 门禁绿**（`tests/contracts/**` 无 `freegraph.*` 导入） | §2.2（`2 passed`） | ✅ |
| **V4** | 稀疏读的三条判定（普通 `dict` / key 集合 / `None` 值） | §2.3（`14 passed`） | ✅ |
| **V5** | `skip_empty` 两分支（缺省稀疏 / 抛错） | §2.3 | ✅ |
| **V6** | fresh 读的五条判定（含**零污染**）**＋ 两个稀疏入口逐字相等**（**SC-033**） | §2.4（`14 passed`） | ✅ |
| **V7** | 差分夹具的**三项投影**一致（含**节点入参投影** · **SC-032**） | §2.5（**17 个字段逐项相等**） | ✅ |
| **V8** | `langgraph` 缺席 ⇒ **skip 而非 fail** | §2.12（**3 skipped / 0 failed**） | ✅ |
| **V9** | 发行元数据**零依赖包**（A5） | §2.6（`[]`） | ✅ |
| **V10** | 全量测试 + 既有门禁**全绿** · 门禁编号仍为 **30** · 步骤 5.6 位于步骤 6 之前 | §2.8（`802 passed` + 10 条门禁退出码 0 + 位置校验 OK） | ✅ |
| **V11** | 读取层覆盖率 == **100%** | §2.9（`read.py` 行/分支 **100%**） | ✅ |
| **V12** | 冻结面**零变更** + 跨 feature 接线**在位**（五处） | §2.10 + §2.11 | ✅ |

| **V13** | **一键验收入口**（`acceptance.py` · 裁定 34 · FR-039 / SC-034） | §1.0（**88 条硬断言全绿 · 退出码 0**；无上游时 **66 条 + 1 条 soft skip · 仍退出码 0**） | ✅ |

⇒ **V1–V12 全绿** + **V13（一键验收入口）全绿**。

---

## 3. 与上游的逐条对照

**核实环境**：`langgraph` **1.2.11** · CPython **3.11.16** —— 核实于 **2026-11-09 / 2026-11-10**
（`contracts/upstream-parity.md` 的 `路径:行号` 全部指向该版本 · **换版本 MUST 重新核实**）。

| # | 语义点 | freegraph 口径 | 上游实现（`langgraph 1.2.11`） | 上游行号 | 差异 | 实测落点 |
|---|---|---|---|---|---|---|
| **P-01** | 稀疏的实现机制 | `is_available()` 判定（**恒不抛错**） | `read_channel(channels, k, catch=not skip_empty)` + 外层 `except EmptyChannelError: pass` | `pregel/_io.py:48-52` | **机制不同** ⇒ **可观察语义等价** | `test_result_key_set_equals_the_available_channel_set` |
| **P-02** | 入参形态 | `Mapping[str, Channel]`（**恒读全部**） | `channels: Mapping[str, BaseChannel]`（+ `select`） | `pregel/_io.py:39-41` | **形状不同** | `test_the_two_entry_names_and_signatures_match_the_contract_verbatim` |
| **P-03** | `skip_empty` 缺省 | `True` | `skip_empty: bool = True` | `pregel/_io.py:42` | **无** | `test_omitting_skip_empty_equals_explicit_true` |
| **P-04** | `skip_empty=False` | 读到无值 ⇒ **抛 `EmptyChannelError`** | `catch=True` ⇒ **以 `None` 填充** | `pregel/_io.py:26-33` · `:50` | **语义不同** ⇒ 该分支**上游全包从未使用** ⇒ **不可观察**（DR-1） | `test_skip_empty_false_raises_empty_channel_error_for_the_empty_key` |
| **P-05** | 返回类型 | **恒为 `dict`** | `dict[str, Any] \| Any` | `pregel/_io.py:44-53` | **形状不同** | `test_result_is_exactly_a_plain_dict` |
| **P-06** | fresh 读的构造 | **副本法**：复制通道 → 副本上 `update` → 从副本读 | **同款**：`cc = channels[k].copy(); cc.update(updated[k]); read_channels(local_channels, select)` | `pregel/_algo.py:213-219` | **无**（**逐字同构**） | `test_fresh_view_equals_the_manually_computed_copy_based_view` |
| **P-07** | 通道的复制机制 | 标准库 `copy.copy` | `BaseChannel.copy()` = `from_checkpoint(checkpoint())` ⇒ **浅共享** | `channels/base.py:38-46` · `:63-70` | **机制不同** ⇒ **浅共享语义等价** | `test_channel_copy_keeps_the_very_same_reducer_reference` |
| **P-08** | 初始输入 | 视为**一次写入** | `invoke(input)` 把入参当**一次写入** | 实测 E2 | **无** | `test_an_initial_input_key_outside_the_schema_is_an_explicit_failure`（负例）· §2.5 的输出状态 |
| **P-09** | 「值为 `None`」的通道 | **有值** ⇒ 出现（值为 `None`） | **出现** | 实测 E1'' | **无** | `test_channel_holding_none_is_present_in_the_result` |
| **P-10** | 通道构造签名 | `Channel(key, value_type)` | `BaseChannel(typ, key="")` · `BinaryOperatorAggregate(typ, operator)` | `channels/base.py:52-54` | **形状不同**（freegraph 侧**不改动**） | B5F1 的冻结面（**零改动**） |
| **P-11** | `local_read` 的签名 | `(channels, writes, *, fresh=False)` | `(scratchpad, channels, managed, task, select, fresh=False)` | `pregel/_algo.py:188-201` | **形状不同**（**不实现** `managed` · DR-3） | `test_the_two_entry_names_and_signatures_match_the_contract_verbatim` |
| **P-12** | `local_read` 遇「待写入里有、通道里没有」的 key | **抛 `InvalidChannelUpdateError`** | **静默丢弃**（**实测 E3**） | `pregel/_algo.py:208-210` | **上游偏离** ⇒ 该场景**不进入**差分比对 | `test_unknown_write_key_raises_invalid_channel_update_error` |

**实测 E3（P-12 的上游侧 · 2026-11-10 · 任务 T044）**：

```python
from langgraph.pregel._algo import local_read
from langgraph.channels import LastValue

class Task:
    writes = [("unknown_key", 42)]

ch = {"a": LastValue("a")}
ch["a"].update([1])
local_read({}, ch, {}, Task(), ["a"], fresh=True)
# ⇒ {'a': 1}   ← 未抛错（未知 key 被静默丢弃）
```

⇒ **P-12 的上游侧已实测** ⇒ `contracts/upstream-parity.md` 的 **12 条全部有实测依据**。

### 3.1 · 上游实测基线（`contracts/upstream-parity.md` §2）的**逐项对齐**（T022 · SC-020）

| 基线项 | 基线值 | 实测 | 结论 |
|---|---|---|---|
| **C4 · 稀疏入参**（初始输入只给 `messages`） | 节点入参 `keys == ['messages']` | ✅ | ✅ |
| **归约语义**（两节点各写一次 `messages`） | `['a', 'b']` | ✅ | ✅ |
| **空更新**（节点返回 `{}`） | 事件序列的「写入」== `None` | ✅ | ✅ |
| **fresh 读**（`local_read(fresh=True)`） | `['old', 'new']`（`fresh=False` ⇒ `['old']`） | ✅ | ✅ |

⇒ 断言落点 = `tests/differential/test_differential.py::test_the_upstream_measured_baseline_still_holds`
（基线常量 = `tests/differential/runner.py` 的 `UPSTREAM_BASELINE` · 版本钉 `1.2.11`）
⇒ **MUST NOT** 凭记忆写期望值 ⇒ **换上游版本时 MUST 重新实测**。

### 3.2 · 「写入」投影的**语义一致性**复核（T045 · 5 处引用点）

| # | 引用点 | 措辞 | 一致？ |
|---|---|---|---|
| ① | `contracts/differential-fixture.md` §3.3 | 「节点函数返回的部分状态（原样 · 未归约）· **无更新 ⇒ `None`**」 | ✅ |
| ② | `contracts/upstream-parity.md` §2 | 「节点函数返回的部分状态（原样 · 未归约）」 | ✅ |
| ③ | `data-model.md` §4 | 「节点函数返回的部分状态（原样 · 未归约）· **无更新 ⇒ 写入为 `None`**」 | ✅ |
| ④ | spec `FR-034` + **裁定 23** | 「节点执行了但没有产生任何写入 ⇒ 计入事件序列，其「写入」投影 MUST 取 `None`（**不是** `{}`、**不是**缺席）」 | ✅ |
| ⑤ | 实现（`tests/differential/driver.py` + `runner.py`） | `dict(output) if output else None`（**原样 · 未归约**）· 上游侧取 `stream` 的**原值** | ✅ |

⇒ **5 处语义一致**（**取法相同** ⇒ 无「稳定假差异」风险）⇒ **无须补齐任何同步点**。

---

## 4. 未实跑项（**MUST NOT** 伪造输出）

| # | 未实跑项 | 原因 | 承接方 | 处置 |
|---|---|---|---|---|
| **1** | **macOS 3.11 / 3.14 两档**的 `langgraph==1.2.11` 安装与可导入性 | 本机为 **Linux x86_64** ⇒ **无法实跑** | **CI**（macOS 作业） | 该档**不装** `differential` 组 ⇒ 差分用例 **skip**（**非失败**）⇒ **MUST NOT** 静默不跑；CI 实测通过后 MUST 补装 |
| **2** | **Windows 3.11 / 3.14 两档**同上 | 同上 | **CI**（Windows 作业） | 同上 |
| **3** | **Linux arm64 3.11 档**同上 | 本机为 **x86_64** ⇒ **无法实跑** | **CI**（arm64 作业） | 同上 |
| **4** | **CI 的步骤 5.6 的实际执行日志**（`tests/differential` 段 `passed ≥ 1` 且 `skipped == 0`） | **CI 未在本会话运行** ⇒ 该证据**不存在** ⇒ **回填即伪造** | **CI**（下一次推送后） | **待 CI 跑过后**回填 §2.13 与本表 ⇒ 在此之前 **SC-014 的 CI 侧证据缺失**（本地已用 §2.5 / §2.13 的等价实测顶替） |
| **5** | **G28 的网络命名空间隔离层**（本机 `unshare --net --map-root-user` 不可用 ⇒ 命名空间由外层施加） | **平台性限制**（容器 **AppArmor**）⇒ **非本 feature 的缺陷** | **CI**（Linux 作业） | 已实测**脚本本体**（`[G28] PASS` · `799 passed, 3 skipped, 3 deselected`）⇒ 隔离层归 CI |
| **6** | **「真实模型一轮」**（宪法质量门禁 5） | 本 feature **无图可跑** ⇒ **物理不可达成** | **B7F3 / B25F1** | **登记项 R-1** ⇒ 见 §6 |
| **7** | **「fake 模型跑通验收基线的一轮」**（宪法质量门禁 4） | 同上 | **B7F2 / B7F3** | **登记项 R-1** ⇒ 见 §6 |
| **8** | **C8 的独立回归测试** | 路由语义 + 调度循环属 **B8F1** | **B8F1** | 挂载点 **C8 仍为 `not-landed`**（**一字未动**） |
| **9** | **C4 的「节点边界」断言**（真实节点收到的那个 dict） | 调度循环属 **B7F1** | **B7F1** | 本 feature 交付**读取层口径**（C4 的**载荷**）⇒ **登记项 R-1** ① |

### 4.1 · **已知的上游怪癖**（实测 · 登记在案 · 不计入本 feature 的缺陷）

| # | 怪癖 | 实测 | 影响 | 处置 |
|---|---|---|---|---|
| **1** | 上游在**整个状态为空**时**不产出**状态（`invoke({})` ⇒ `None`；`stream` 无 `values` 条目） | 2026-11-10 实测 | 「输出状态」这一项投影在**空初始输入**下会出现**稳定假差异** | 夹具的图规格 MUST 带**至少一个**初始 key ⇒ 已写入 `runner.py` 的 docstring 与 `_reduce_spec` 的 docstring |
| **2** | 上游 `local_read` 对**未知 key** 的写入**静默丢弃** | 实测 E3（§3） | 该场景两侧**不等价地失败** ⇒ **不进入**差分比对 | 已登记为「**上游偏离**」（**P-12**）⇒ 由 freegraph 的单元测试**独占断言** |

### 4.2 · **已知面**（**MUST NOT** 计入零污染判据 · **MUST NOT** 修）

| # | 已知面 | 依据 | 处置 |
|---|---|---|---|
| **1** | **就地修改型**归约器（如 `a.extend(b)` 一类）会**改写原通道的值对象**（副本与原通道**浅共享值对象**） | 契约 §3.3 · research **D-10** / **DR-4** · **与上游同构**（上游 `checkpoint()` 亦返回同一对象） | **不修**（深拷贝会破坏 FR-005 的**对象身份语义**、对不可拷贝对象**会失败**、且**与上游分叉**）⇒ **不计入**「零污染」判据（作用域 = **绑定与可用性判定**）⇒ 已由 `test_in_place_mutating_reducer_rewrites_the_original_value_object` **显式断言写明** |
| **2** | 结果里的值与通道的值**同一对象** ⇒ 就地修改结果里的**值对象**会**影响**通道 | 契约 §2.1 · research **D-08** | **与上游同构** ⇒ 已由 `test_in_place_mutation_of_the_value_object_is_visible_on_the_channel` **显式断言写明** |

### 4.3 · **research 的遗留登记**（DR-1 … DR-5）的处置

| # | 遗留 | 本 feature 的处置 | 触发重新评估的信号 |
|---|---|---|---|
| **DR-1** | `skip_empty=False` 的口径与上游分叉（抛错 vs 以 `None` 填充） | 保留**抛错**口径（契约 §2.3）⇒ 登记为「**不可观察**的语义差异」（**P-04**） | 上游开始**显式**使用该分支 ⇒ 重新评估 |
| **DR-2** | 节点返回**未知 key** ⇒ 上游静默丢弃 / freegraph 显式失败 | 该场景**不进入**差分比对（契约 §5）⇒ 由 freegraph 的单元测试**独占断言** | 两侧行为**收敛** ⇒ 可纳入比对 |
| **DR-3** | 上游 `local_read` 的第四类入参 `managed` | freegraph **不实现** ⇒ MUST **NOT** 假设其语义（已写入 **B8F1** 的第五处接线） | B8F1 需要 `managed` 语义 ⇒ 重新评估契约面 |
| **DR-4** | 「就地修改型」归约器改写值对象 | **不修** · **不计入**零污染判据 ⇒ **显式登记**（§4.2） | 用户要求「值对象级零污染」⇒ 重新评估（代价 = 破坏对象身份语义） |
| **DR-5** | 「模型工厂」钩子的**注入实现** | 本 feature **恒空** ⇒ 非空即**显式失败** ⇒ **注入实现归 B25F1** | **B25F1** 落地（承接条款**已在位**） |

---

## 5. 来源覆盖表

> **核实环境**：上游 `langgraph` **1.2.11** · CPython **3.11.16** —— 核实于 **2026-11-09 / 2026-11-10**
> ⇒ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII）。

### 5.1 · 验收判据 **A1–A5**（引文 §6 / 立项书 §5.2）

| 判据 | 内容 | 来源（上游 `路径:行号` + 核实版本） | 断言落点 | 结论 |
|---|---|---|---|---|
| **A1** | `"llm_calls" not in node_input` | `langgraph/pregel/_io.py:38-53`（`read_channels` 的 `except EmptyChannelError: pass` ⇒ key 缺席）—— **1.2.11** | `tests/runtime/test_read_c4_sparse_state.py::test_c4_sparse_state_read_excludes_empty_channels` | ✅ |
| **A2** | `.get("llm_calls", 0) == 0` | 同上 | 同上 | ✅ |
| **A3** | **输出状态**一致 | `langgraph/pregel/_io.py:23-36` + `stream(stream_mode="values")` —— **1.2.11** | `tests/differential/test_differential.py::test_the_three_projections_are_identical_on_both_sides` | ✅ |
| **A4** | **事件序列**一致 | `langgraph/pregel/_algo.py`（`stream_mode="updates"` ⇒ `{node: writes}`）—— **1.2.11** | 同上（字段 `事件序列[0..2]`） | ✅ |
| **A5** | `langgraph` **不入** `Requires-Dist` | `importlib.metadata.requires("freegraph")` == `[]` | `tests/runtime/test_read_contract.py::test_the_release_metadata_declares_no_requirement_at_all` | ✅ |

### 5.2 · 全部成功标准（**SC-001 … SC-033**）

| SC | 摘要 | 承载 | 实测 | 结论 |
|---|---|---|---|---|
| SC-001 | C4 · 空 channel 的 key **不出现** | T011 | §2.1 | ✅ |
| SC-002 | C4 · `.get(key, default)` 返回 **default** | T011 | §2.1 | ✅ |
| SC-003 | 稀疏语义（key 集合 / `None` 值 / `skip_empty` 两分支） | T012 / T013 | §2.3 | ✅ |
| SC-004 | 结果形态（普通 `dict` / 同一对象 / 保序） | T015 / T016 / T017 | §2.3 | ✅ |
| SC-005 | fresh 读（视图 / **零污染** / 合并语义 / 未知 key） | T023 / T024 / T025 / T026 | §2.4 | ✅ |
| SC-006 | **输出状态**投影差异 == 0 | T021 / T045 / T046 | §2.5（字段 `输出状态.*`） | ✅ |
| SC-007 | **事件序列**投影差异 == 0 | T021 / T045 / T046 | §2.5（字段 `事件序列.*`） | ✅ |
| SC-008 | 发行依赖**零新增**（`Requires-Dist` 整体为空） | T001 / T029 | §2.6（`[]`） | ✅ |
| SC-009 | **缺席即跳过**（失败数 == 0） | T008 / T050 | §2.12（**3 skipped / 0 failed**） | ✅ |
| SC-010 | 内核**零**上游导入 + 零第三方导入 | T027 / T029 | §2.6（`OK：无上游导入`） | ✅ |
| SC-011 | 冻结面零变更（14 / 18 / 7 · 层注册表 · 门禁编号 30） | T010 / T030 / T034 / T040 | §2.8 / §2.10 | ✅ |
| SC-012 | 读取入口的**实现点数 == 1** | T028 / T029 | `test_the_state_reading_entry_points_have_exactly_one_implementation` | ✅ |
| SC-013 | 差分覆盖「有归约器 + 无归约器 + 空 key」 | T009 / T018 / T020 | §2.5（**空 key** 在入参与输出状态里**均出现**） | ✅ |
| SC-014 | 差分夹具在 CI 里**真实执行** | T035 / T036 / T038 | ⚠️ **CI 侧证据待 CI 跑过**（§4 #4）⇒ 本地等价实测（§2.5 / §2.13） | ⚠️ **待 CI** |
| SC-015 | C4 挂载点 `landed` · C8 **不变** | T014 / T034 / T048 | §2.2 | ✅ |
| SC-016 | 零出站 / 零环境变量（子进程三断言） | T027 | §2.4 / §2.8（G27） | ✅ |
| SC-017 | 节点**纯本地**（零网络） | T009 | **人工审查**（§5.4） | ✅ |
| SC-018 | `read.py` 行 / 分支覆盖 == 100% | T028 / T032 | §2.9 | ✅ |
| SC-019 | 判定记录含**比对字段名** + **逐项结果** | T021 / T031 | §2.5（**17 个字段逐项**） | ✅ |
| SC-020 | 期望值与**上游实测基线**对齐 | T022 / T040 / T044 | §3.1 | ✅ |
| SC-021 | 初始输入按「一次写入」进通道 · 两侧通道状态差异 == 0 | T019 | §2.5（`输出状态.*`） | ✅ |
| SC-022 | 节点入参的观测 == 节点**实际收到**的 | T020 / T021 | §2.5（`节点入参.*`） | ✅ |
| SC-023 | 跨 feature 承接条款**指名**（B7F1 / B8F1） | T037 / T039 | §2.11（**含 B8F1 的第五处**） | ✅ |
| SC-024 | fresh 读的边界（未知 key ⇒ **显式失败**） | T023 / T025 / T044 | §2.4 | ✅ |
| SC-025 | `tests/contracts/**` 内部 import 违规 == 0 | T014 | §2.2（G2 绿） | ✅ |
| SC-026 | 两侧消费的 `TypedDict` 是**同一个对象** | T019 | `test_the_mixed_spec_exercises_reducer_cover_and_empty_key` + 实现（**一份** `schema_typed` 传给两侧） | ✅ |
| SC-027 | `skip_empty` 两分支 | T013 | §2.3 | ✅ |
| SC-028 | 事件口径的**实测与冻结** | T021 / T045 | §2.5（`事件序列[2]` ⇒ `None`）+ §3.1 | ✅ |
| SC-029 | `freegraph.runtime.__all__` == **14** | T003 / T030 | §2.10 | ✅ |
| SC-030 | 模型工厂钩子**恒空** ⇒ 非空即**显式失败** | T009 / T019 / T039 / T047 | §2.5（`test_a_non_empty_model_factory_is_an_explicit_failure`） | ✅ |
| SC-031 | 既有依赖判据**拆分取样范围**后五条断言全成立 | T041 / T042 / T043 | §2.7（**五条逐条 ✅**） | ✅ |
| SC-032 | **节点入参投影**差异 == 0 | T021 / T045 / T046 | §2.5（`节点入参.*` **9 个字段**逐项相等） | ✅ |
| SC-033 | **两个稀疏入口的结果逐字相等** | T023 / T024 / T028 | §2.4 + `test_the_two_sparse_entries_are_byte_identical` + `test_i11_the_two_sparse_entries_are_byte_identical` | ✅ |
| SC-034 | **独立验收脚本**（一条命令跑完全部验收闸口） | T051 | §1.0（**88 条硬断言 · PASS · 退出码 0**） | ✅ |

⇒ **SC 33/33 全覆盖**（除 **SC-014** 的 **CI 侧证据**待 CI 实跑 ⇒ 见 §4 #4）。

### 5.3 · 全部功能需求（**FR-001 … FR-038**）

| FR | 摘要 | 断言落点 | 结论 |
|---|---|---|---|
| FR-001 | 状态读取的**唯一实现点** | `test_the_state_reading_entry_points_have_exactly_one_implementation` | ✅ |
| FR-002 | 名字与签名**逐字冻结** | `test_the_two_entry_names_and_signatures_match_the_contract_verbatim`（期望值**取自契约文本**） | ✅ |
| FR-003 | 稀疏读取（C4） | `test_result_key_set_equals_the_available_channel_set` | ✅ |
| FR-004 | 结果 = 普通 `dict` | `test_result_is_exactly_a_plain_dict` | ✅ |
| FR-005 | 值的引用语义 | `test_result_values_are_the_very_same_objects_as_the_channel_values` | ✅ |
| FR-006 | 「空」= 「无值」 | `test_channel_holding_none_is_present_in_the_result` | ✅ |
| FR-007 | `skip_empty` 两分支 | `test_skip_empty_false_raises_empty_channel_error_for_the_empty_key` | ✅ |
| FR-008 | fresh 读视图 | `test_fresh_view_contains_this_writes_values` | ✅ |
| FR-009 | fresh 读**零污染**（绑定与可用性判定） | `test_binding_and_availability_are_unchanged_by_a_fresh_read` | ✅ |
| FR-010 | 合并语义**复用** `update()` | `test_reducing_channel_fresh_view_equals_the_reduced_result` | ✅ |
| FR-011 | fresh 读的边界（**显式失败**） | `test_unknown_write_key_raises_invalid_channel_update_error` | ✅ |
| FR-012 | C4 独立回归测试 | `tests/runtime/test_read_c4_sparse_state.py` | ✅ |
| FR-013 | C4 挂载点接线 | `tests/contracts/test_contract_regressions.py`（`status=landed`） | ✅ |
| FR-014 | 差分夹具 | `tests/differential/`（**12 条用例**） | ✅ |
| FR-015 | 夹具**可复用** | `runner.run_differential`（**一个纯函数入口**） | ✅ |
| FR-016 | **三项投影** | `runner.compare_projections`（**恰好 3 项**） | ✅ |
| FR-017 | 证据门禁（字段名 + 逐项结果） | `DiffReport.to_dict()`（**17 个字段**） | ✅ |
| FR-018 | 依赖隔离（**PEP 735 组** · 不进 `Requires-Dist`） | `test_only_the_differential_group_may_declare_an_upstream_package` | ✅ |
| FR-019 | 缺席**优雅跳过** | §2.12（**3 skipped / 0 failed**） | ✅ |
| FR-020 | 内核**零**上游导入 | `test_the_kernel_imports_no_upstream_package` | ✅ |
| FR-021 | 层纪律（L2 → L3/L4/L5 边数 == 0） | 门禁 **G25**（§2.8） | ✅ |
| FR-022 | 只依赖**标准库** | `read.py` 的 import 面（`collections.abc` / `copy` / `typing`） | ✅ |
| FR-023 | 零出站 / 零环境变量 | `test_reading_layer_has_no_side_effects`（子进程三断言） | ✅ |
| FR-024 | **不越界**（夹具在测试侧 · 无调度逻辑） | `tests/differential/**`（**不在 `src/`**）· 驱动器**只**用通道层 + 读取层 | ✅ |
| FR-025 | 零新增门禁 + **专门步骤 5.6**（**位于步骤 6 之前**） | §2.8（门禁编号 30 + 位置校验 OK） | ✅ |
| FR-026 | 既有冻结面零改动 | §4 / §5.4 | ✅ |
| FR-027 | 纯单元可测 · 覆盖率 | §2.9（`read.py` **100%**） | ✅ |
| FR-028 | 署名头 · 引用纪律 | 门禁 **G30**（**100%**） | ✅ |
| FR-029 | 初始输入的写入语义 | §2.5（`输出状态.*`）+ `test_an_initial_input_key_outside_the_schema_is_an_explicit_failure` | ✅ |
| FR-030 | 节点入参的观测方式 | `driver.record_node_input`（**函数内部** · **执行前**的副本） | ✅ |
| FR-031 | 承接条款（节点边界断言归 B7F1 + `local_read` 调用口径归 B8F1） | §2.11（**五处接线**） | ✅ |
| FR-032 | 挂载点元测试 · G2 约束 | §2.2 | ✅ |
| FR-033 | 图规格的 schema 承载形态（**同一** `TypedDict`） | `spec_builder.build_schema_typed`（**函数式** `TypedDict`） | ✅ |
| FR-034 | 事件序列的「空更新」口径（**已冻结**） | §2.5（`事件序列[2]` ⇒ `None`） | ✅ |
| FR-035 | 读取层的模块名与导出面（**14**） | §2.10 | ✅ |
| FR-036 | 「模型工厂」钩子（**预留 · 恒空**） | §2.5（`test_a_non_empty_model_factory_is_an_explicit_failure`） | ✅ |
| FR-037 | 既有依赖判据的**取样范围拆分** + **正向枚举** | §2.7（**五条断言全成立**） | ✅ |
| FR-038 | **两个稀疏入口 MUST 逐字相等** | §2.4 + `test_i11_the_two_sparse_entries_are_byte_identical` | ✅ |
| FR-039 | **独立验收脚本**（零第三方 · 一条命令跑完全部闸口） | `harness/verification/B5F2/acceptance.py`（§1.0） | ✅ |

⇒ **FR 38/38 全覆盖**。

### 5.4 · 冻结面与纪律的复核（**零改动清单**）

| 文件 | 状态 |
|---|---|
| `src/freegraph/__init__.py` | ✅ **零改动**（顶层包惰性 · 门禁 G1 / L-1） |
| `src/freegraph/graph.py` | ✅ **零改动**（门面 **7** 符号面） |
| `src/freegraph/contracts/**` | ✅ **零改动**（**18** 符号面） |
| `src/freegraph/runtime/{channel,mapping,errors,schema,reducer}.py` | ✅ **零改动**（B4F1 / B5F1 的冻结面） |
| `src/freegraph/runtime/__init__.py` | ✅ **仅追加**导出（12 → **14**） |
| `src/freegraph/runtime/read.py` | ★ **新建**（L2 · 只依赖标准库） |
| `tests/contracts/test_architecture.py` · `tests/facade/**` · `tests/gates/**` | ✅ **零改动** |
| `tests/contracts/test_contract_regressions.py` | ✅ **仅** C4 标记 + **元测试**（**零** `freegraph.*` import） |
| `tests/runtime/conftest.py` + 既有测试模块 | ✅ **零改动**（**复用** `run_in_subprocess` 夹具） |
| `tests/runtime/test_parse_contract.py` | ✅ **仅** 两条依赖判据按 **R-3** **拆分取样范围**（**原断言逐字保留**） |
| `README.md`（兼容矩阵） | ✅ **零改动**（**零新增行**） |
| `THIRD_PARTY_NOTICES` | ✅ **零改动**（上游**不进发行元数据** ⇒ 无需新增登记） |
| `harness/demo/target.py` | ✅ **零改动**（G29-01 只读基准 diff 断言 ✅） |
| `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` | ✅ **零改动** |
| `.specify/memory/constitution.md` | ✅ **门禁编号 G1–G30 与原则 I–X 一字未动**（工作区里的 **v1.8.0** 修订 = **2026-11-09 发起者批准**的**上一轮**工作 ⇒ **不属**本 feature 的改动） |
| `pyproject.toml` 的 `[project]` 段 | ✅ **零改动**（**仅**追加 `[dependency-groups] differential`） |
| `.github/workflows/ci.yml` | ✅ **仅新增步骤 5.6**（**步骤 5.5 一字不动** · **7 个作业形状**与 **7 个 required check 名零变更**） |
| `harness/verification/B5F2/acceptance.py` | ★ **新建**（**单文件** · 零第三方依赖 · 过 **G30**） |
| `harness/proposals/立项书.md` | ✅ **零改动**（§4.2 S5 / §5.2 B5F2 行 / §9.2 落点的回改**已在工作区** ⇒ **只接线 · 无需再改**） |
| `harness/features/**` | ✅ **仅** B8F1 补入**第五处接线**（**只接线 · 逐条最小改动**） |
| `harness/scripts/gates/gate_G29_contract_carrier.py` | ✅ **判定代码零改动**（**docstring** 的两态口径**已在工作区**） |
| `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` | ✅ **G29 判定 3** 的两态口径**已在工作区**（**判定代码零改动**） |
| `specs/b3f1-scaffold-ci-gates/contracts/ci-matrix.md` | ✅ **步骤 5.6 行 + 位置约束 + §2.1 修订记录已在工作区** ⇒ **仅**补**实测结论回填**（**未追加第二条 5.6 行**） |

**人工审查项**（SC-017 · 节点**纯本地**）：差分夹具的节点函数**全部**是**纯本地的确定性**函数
（`return {"messages": ["a"]}` 一类）⇒ **零网络调用** · **零模型调用** · **零 I/O**
⇒ 另由门禁 **G26**（静态扫描）与 **G27**（动态 socket 监测）双重覆盖。

---

## 6. 发起者追认（**R-1 / R-2 / R-3 / R-4**）

> ⚠️ **宪法 v1.6.0**：「追认文字 + 发起者确认 + 日期 MUST 落在
> `harness/verification/<feature>/manual-verification.md`；**未追认前 MUST NOT 合入**；
> **MUST NOT** 由实现者代签。」
> ⇒ **本节由实现者备料，追认栏留空** —— 等**发起者本人**作出。

| 登记项 | 追认对象 | 状态 |
|---|---|---|
| **R-1** | 宪法「质量门禁 3 / 4 / 5」的偏离登记（**C4 的节点边界** · **C8** · **fake 轮** · **真实模型轮**） | ✅ **已追认**（2026-11-10） |
| **R-2** | `ci-matrix` 契约修订（**步骤 5.6** · 方案 **α′**） | ✅ **已追认**（2026-11-10） |
| **R-3** | 既有 B4F1 依赖判据的**取样范围拆分**（**取样范围 bug 修复** · **无需宪法修订**） | ✅ **已追认**（2026-11-10） |
| **R-4** | **G29 冻结契约**的最小修订（两态 + `landed` 语义 · **判定代码零改动**） | ✅ **已追认**（2026-11-10） |

### 6.1 · 追认所需的**备料**（各登记项的偏离登记已在 `plan.md` 落定）

| 登记项 | 被偏离的判据 | 根因 | 判据未被放宽的论证 | 承接方 |
|---|---|---|---|---|
| **R-1 ①** | 门禁 3 的 **C4**（**完整**形态） | 本 feature 只交付**读取层**（调度循环属 **B7F1**） | C4 的判据**一字未改**（**否定式**逐字落地） | **B7F1**（M1） |
| **R-1 ②** | 门禁 3 的 **C8** | fresh 读**原语**在本 feature；**路由语义 + 回归测试**属 **B8F1** | 本 feature 交付 C8 的**读取原语** | **B8F1**（M2） |
| **R-1 ③** | 门禁 4 的 **fake 轮** + 门禁 5 的**真实模型轮** | 验收基线跑通需要**完整内核运行时**（**B7F2 / B7F3**） | CI **不写**永久红的断言；五段式记录照常落地 | **B7F2 / B7F3 / B25F1** |
| **R-2** | `ci-matrix` 冻结面（**新增步骤 5.6**） | 差分夹具在**无上游**的环境必然 **skip** ⇒ SC-014 不可达 | **零新增 job 名** ⇒ **分支保护零变更** · 步骤 5.5 **一字不动** | 本 feature 内落地（**T035 / T036**） |
| **R-3** | 既有 B4F1 的两条依赖判据的**取样范围** | 原判据把**开发工具链**与**发行面**混为一谈 | **发行面断言逐字保留** + **新增**等效正向约束 ⇒ **红线总量不减** | 本 feature 内落地（**T041 / T042**）· **无需宪法修订** |
| **R-4** | `architecture-gates.md` **G29 判定 3** + `gate_G29` docstring | 旧措辞是 B3F1 时期的**单态快照** | **判定代码一行未改**（两态皆接受）⇒ **零新判据、零放宽** | 本 feature 内落地（**T048**）· **无需宪法修订** |

### 6.2 · **追认栏**

> **🔓 追认栏 ——【已由发起者追认 · 2026-11-10】**
>
> | 项 | 内容 |
> |---|---|
> | **追认对象** | plan.md 的**登记项 R-1 / R-2 / R-3 / R-4**（**四条全部**） |
> | **追认人（发起者）** | **杨家成**（仓库发起者）—— 依宪法 v1.6.0 由**发起者本人**作出；实现者**未代签** |
> | **追认结论** | ✅ **追认全部四条** —— ① **R-1**：门禁 3 / 4 / 5 的四部分在 B5F2 **物理不可达成**（根因：**本 feature 按里程碑只交付读取层** —— 节点边界断言 = **B7F1** · C8 = **B8F1** · fake 轮 = **B7F2 / B7F3** · 真实模型轮 = **B25F1**）；**C4 的判据一字未改**（**否定式**逐字落地 · 挂载点 C4 = `landed` · C8 仍 `not-landed`）；② **R-2**：`ci-matrix` 的**步骤 5.6** 修订（**既有作业内的专门步骤** · **零新增 job 名** ⇒ **分支保护零变更** · 步骤 5.5 **一字不动**）⇒ 差分夹具在 CI **真实执行**（`SC-014` 可达）；③ **R-3**：既有 B4F1 两条依赖判据的**取样范围拆分**（**发行面断言逐字保留** + `[dependency-groups]` 改**正向枚举** + **新增**等效正向约束 ⇒ **红线总量不减**）⇒ **原断言一条未放宽**；④ **R-4**：**G29 冻结契约**的**最小修订**（判定 3 改**两态**口径 + 定义 `landed` 语义 · **判定代码一行未改** ⇒ **零新判据、零放宽**） |
> | **追认日期** | **2026-11-10** |
> | **签署** | 发起者于本会话中明示「**追认全部四条**」（**未另留书面签名** —— 实现者**不得**代签 · 宪法 v1.6.0） |
>
> **⇒ 追认完成，执行闸口 A7 通过 ⇒ 本 feature 达「可合入」状态。**
> ⚠️ 实现者**未**改宪法正文（**v1.8.0 的跨 feature 承接通则**是 2026-11-09 发起者批准的
> **上一轮**修订，**不属**本 feature 的改动）· **未**写一条永久红的 CI · **未**把
> `GATE-MOUNT: C8` 改成 `landed`（C8 **未**由本 feature 落地）· **未**新增门禁编号
> （**G1–G30** 连续性不变）· **未**把上游写进**发行依赖声明**。

---

## 7. 移交后续 feature

| 下游 | 承接的内容 | 落点 |
|---|---|---|
| **B7F1**（调度层 · M1） | **C4 的节点边界断言**（把该用例改为断言**真实节点收到的入参**） | `harness/features/B7F1_任务准备与super-step循环.md:41` · spec FR-031 / 裁定 18 |
| **B8F1**（条件边 · M2） | **填条件边字段**复用同一夹具 + **显式传 `fresh=True`** | `harness/features/B8F1_条件边路由与fresh读.md:42` · **第五处接线** |
| **B25F1**（双跑验收 · M4） | **fake 模型工厂**的实现 ⇒ 让差分夹具能跑**模型形状**的图规格 | `harness/features/B25F1_双跑验收与迁移说明.md:55` · spec FR-036 / 裁定 26 |
| **B4F1**（上一棒 · 同一形态接线） | 既有依赖判据的**取样范围拆分**（**发行面断言逐字保留**） | `harness/features/B4F1_schema解析与归约器提取.md:40` · spec FR-037 / 裁定 27 |
| **B14F1**（checkpoint · M4） | 通道的 `copy()` / checkpoint 级复制（**勿与**读取层的**读侧副本**混淆） | 契约 §5 · research **D-07** / **D-09** |
