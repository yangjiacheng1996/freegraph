---

description: "Task list for B24F1 · 打包分发 + API 兼容矩阵 + THIRD_PARTY_NOTICES"
---

# Tasks: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Input**: Design documents from `/specs/b24f1-packaging-compat-matrix/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **包含**。spec 定义了 SC-001…SC-008，且宪法原则 VI 要求「判据级可追溯」；
每个用户故事 MUST 有**测试 / 可执行验收**任务；具体实现与测试顺序见各故事（US2 / US4 允许先落文档再补断言），Phase 8 补全量门禁与人工记录。

**Organization**: 任务按用户故事分组；**US1–US3 在 Setup + 构建产物就绪后可独立实现 / 测试，US4–US5 在 Foundational 完成后可独立实现 / 测试**。
Phase 2（G8 / G19 / G29 迁移 + `COMPAT.md` 机读段）是所有矩阵 / 文档故事的前置；
Phase 8 为跨切面收口。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: `US1` / `US2` / `US3` / `US4` / `US5`；Setup / Foundational / Phase 8 不带故事标签
- 每个任务都带**精确文件路径**或**精确命令**；末尾 `→ FR-xxx / SC-xxx` 是**反向追溯**。

---

## 追溯表（FR → 任务）

| FR | 任务 |
|---|---|
| FR-001 | T003 / T011 / T012 / T016 / T018 / T019 / T045 |
| FR-002 | T016 / T017 / T018 / T019 / T020 / T022 / T023 / T045 |
| FR-003 | T020 / T021 / T022 / T023 / T036 |
| FR-004 | T004 / T005 / T006 / T007 / T010 / T024 / T025 / T026 / T027 / T030 / T031 / T043 / T048 / T050 |
| FR-005 | T028 / T029 / T030 / T031 |
| FR-006 | T032 / T033 / T034 / T035 / T044 |
| FR-007 | T032 / T033 / T034 / T035 / T044 / T048 |
| FR-008 | T011 / T032 / T033 / T036 |
| FR-009 | T003 / T011 / T018 |
| FR-010 | T020 / T022 / T023 / T045 |
| FR-011 | T013 / T014 / T015 |
| FR-012 | T004 / T024 / T025 / T027 / T043 / T050 |
| FR-013 | T011 / T012 / T029 / T036 |
| FR-014 | T001 / T002 / T039 / T040 / T041 / T042 / T046 / T047 / T049 |
| FR-015 | T024 / T026 / T027 / T050 |
| FR-016 | T008 / T009 / T036 / T038 |
| FR-017 | T011 / T012 / T018 / T036 / T045 |
| FR-018 | T024 / T025 / T027 / T032 / T033 / T038 |
| FR-019 | T005 / T006 / T007 / T008 / T009 / T036 / T038 / T043 |

## 追溯表（SC → 任务）

| SC | 任务 |
|---|---|
| SC-001 | T013 / T015 / T037 / T040 |
| SC-002 | T017 / T018 / T019 / T037 / T045 |
| SC-003 | T020 / T021 / T022 / T023 / T037 / T045 |
| SC-004 | T004 / T010 / T024 / T025 / T026 / T027 / T028 / T029 / T030 / T031 / T037 / T043 / T048 / T050 |
| SC-005 | T011 / T012 / T016 / T036 / T037 / T045 |
| SC-006 | T012 / T014 / T015 / T037 / T040 |
| SC-007 | T032 / T033 / T034 / T035 / T037 / T044 / T048 |
| SC-008 | T001 / T015 / T019 / T023 / T031 / T035 / T037 / T039 / T040 / T041 / T042 / T046 / T047 / T049 |

> **双向追溯**：上两表是 FR/SC → 任务；每条任务末尾的 `→ FR-xxx / SC-xxx` 是任务 → 判据。
> 每条 SC 至少挂一条**测试 / 可执行验收**任务（非实现任务冒充）。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立验收骨架、记录迁移前基线，确认零运行时改动。

- [X] T001 Create `harness/verification/B24F1/` with `acceptance.py`（带署名头 + 五段式 `--record` 骨架）and `manual-verification.md` skeleton; follow `harness/verification/README.md`；并把 B24F1 的记录 / 验收脚本入口补入 `harness/verification/README.md` 的「当前已有记录」表（索引一致性，非门禁） → FR-014
- [X] T002 Record pre-migration baseline in `harness/verification/B24F1/manual-verification.md`: existing `uv build` / `check_dist_purity.py dist/` results; `publish.yml` step order; `git show HEAD:README.md` matrix row count and `Command` = 行为等价; current G8 / G19 / G29 behavior; **并在临时副本执行迁移后测试，记录变红断言清单（逐条 `文件:行号` + 变红原因）** → FR-014
- [X] T003 [P] Record zero-runtime baseline: `git diff -- src/freegraph harness/demo/target.py` is empty; `pyproject.toml` has `dependencies = []` and only `otlp` extra; `src/freegraph/py.typed` exists → FR-001 / FR-009

**Checkpoint**: 验收骨架就绪；基线可追溯；运行时零改动。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立 `COMPAT.md` 机读段，并把 G8 / G19 / G29 **以及 `test_parse_contract.py`** 的取行源迁到它。**所有矩阵 / 文档故事都依赖本阶段。**

**⚠️ CRITICAL**: 本阶段完成前，US4 / US5 不得开始；US1–US3 不受阻，但建议先完成本阶段以免 CI 红。

- [X] T004 Create `COMPAT.md` with header + affiliation（**放在机读段内**）+ `## API 兼容矩阵` section migrated from the current README matrix (all contract ∪ facade rows, **恰 4 列**, no duplicate); use **manifest-driven** counts（**并集 27 = 契约层 22 ∪ 门面层 8**；`Command` / `RunConfig` / `Send` 去重；**不得**沿用旧「18/7」「20/7」「20/8」）; **既有行保留原引用版本（如 `StateDict` 的 `1.2.19`）；新增 / 复核行以 `1.2.11` 为准，且每行 `路径:行号` MUST 与声明版本一致**; correct `Command` to **部分等价** and add the P3/`99d43aa` drift-correction note in its difference cell (B22F1 仅措辞); **split the Command note**: `goto` 缺省 = **DIFF（Y-01）**, 非法 `goto` / 非 dict `update` = **STRICTER（X-06）**, **X-2 / X-3 异常类型差异（B9F1 编号）**; **按 B11F1 在 `Send` 行补「freegraph 侧不可变（上游可变）」（Y-03）；按 C5/C6 在 `NodeFunc` 行补「无上游同名协议」**; **按 H-4 在 `StateGraph`（`compile`）行补 `recursion_limit` 的 dict 载体；按 H-9 / FR-018 在 `Graph` 行补 v2 `[png]` 升级路径；按 H-3 在 `Send` 行补「运行期语义已落地」并注明 `Send` 类型定义住 L1（`freegraph/contracts/types.py`）；**按 H-6 / H-7 在机读段 `CompiledGraph` 行补：`get_state` 无快照返回 `None` vs 上游空 `StateSnapshot` = DIFF（Y-02）；`update_state` / 时间旅行 = v1 能力边界（非「更严」）。下游 `get_state` / `get_state_history` / `update_state` / 时间旅行行由 T025 落库；本任务只建 `## 下游承接行` 标题、不填下游数据行**; add placeholder headings `## 18 项覆盖表` / `## 下游承接行` / `## 证据与来源` / `## 维护规则`; **`Store` 的「协议等价 · v1 无实现 · batch 挂起 v2」澄清写入 `## 证据与来源`（MUST NOT 改动 `Store` 机读行；该「逐字不改」由 T027 的专用 baseline 断言核验——G19 的既有白名单只保证等价程度不变差，不保证差异说明逐字不变）**; **同批把 README 的 `## API 兼容矩阵` 改为指针（说明唯一权威在 `COMPAT.md` + 绝对 GitHub URL + 零完整矩阵行），并在指针段保留「兼容意图为互操作，不构成 affiliation」声明**（FR-006 / T032），使 Phase 2 的 G8 / G29 断言可绿 → FR-004 / FR-012 / SC-004
- [X] T005 [P] In `tests/facade/_gatesupport.py`, add shared constants/helpers: `COMPAT_RELPATH = "COMPAT.md"`, read-text helper, degree-rank helper (`不支持=0` / `部分等价=1` / `行为等价=2`), and keep `compat_matrix_rows` as the single row parser → FR-004 / FR-019
- [X] T006 [P] Update G8 in `tests/contracts/test_architecture.py`: read rows from `COMPAT.md` (via `sys.path` injection to reuse `_gatesupport`, same as G29); keep contract-symbol coverage / **恰 4 列（不得多列或少列；现状测试为 `>=4`，本任务收紧为 `==4`；测试方法名由 `test_compat_matrix_rows_have_three_columns` 改为 `test_compat_matrix_rows_have_four_columns`）** / no duplicate / affiliation; **move the affiliation check to the COMPAT machine section**; **迁移本文件中所有「从 README 读取兼容矩阵行」的断言与自检 / 负向用例；`test_readme_contains_independence_statement` 等非矩阵 README 检查保持不变（README 仍须有独立实现声明 / affiliation，见 FR-006 / US4#4）**; keep `test_readme_has_compat_matrix_section` but change it to assert README only has the **pointer** section (link + zero full-matrix rows); **清理本文件注释 / docstring 中的旧计数（「契约层 18/7」「20/7」等），改为 manifest 驱动（并集 27 = 契约层 22 ∪ 门面层 8）** → FR-004 / FR-019
- [X] T007 [P] Update G19 in `tests/facade/test_facade_gates.py`: read rows from `COMPAT.md`; keep facade coverage / exact two-layer set / new-row source checks; **迁移本文件中所有「从 README 读取矩阵行」的断言（含 `test_selfcheck_detects_a_missing_row`）；非矩阵 README 检查保持不变**; add `MATRIX_ROWS_UPDATABLE_BY_B24F1 = frozenset({"Command"})` and allow only `Command` `行为等价 → 部分等价`; **`Command` MUST NOT 整体移出 `test_existing_contract_rows_are_unchanged` 的「等价程度 MUST NOT 变差」单调检查；改为专用分支：仅当 `previous == 行为等价` 且 `current == 部分等价` 时放行，其它任何等级变化（含 `部分等价 → 不支持`）必须失败；其它白名单行仍走原单调检查；新增负向自检：`Send` 降级为「不支持」必须失败，且 `Command` 从「部分等价」降为「不支持」也必须失败**; change `test_existing_contract_rows_are_unchanged` current side to `COMPAT.md`, and baseline side to **`HEAD:COMPAT.md` if present AND contains machine-section rows, else `HEAD:README.md`; if neither has matrix rows ⇒ skip** (MUST NOT hard-code `HEAD:README.md`, because the README rewrite commit makes that baseline empty and the test red); **清理旧计数注释（18/7、20/7 等）** → FR-004 / FR-019
- [X] T008 [P] Update `harness/scripts/gates/gate_G29_contract_carrier.py --check-compat`: `COMPAT.md` missing ⇒ still “未落地” exit 0; exists ⇒ validate machine section covers contract ∪ facade manifests (reuse `_gatesupport`), `Command` = 部分等价, affiliation（**机读段内**）, README has an **absolute GitHub URL** to `COMPAT.md` and **zero** full-matrix rows → FR-016 / FR-019
- [X] T009 [P] Backtrack-revise gate contracts: `specs/b2f1-contracts-protocols/contracts/architecture-gates.md` §G8 + `specs/b2f2-public-api-facade/contracts/architecture-gates.md` §G19 + `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览/G29 — new source = `COMPAT.md`; G19 B24F1 `Command` 定向例外 **（仅允许 `行为等价 → 部分等价`；`Command` 不整体移出单调检查，其它任何等级变化必须失败；其它行仍不可降级）+ 负向自检（`Send` 降级必须失败，且 `Command` 从 `部分等价` 降为 `不支持` 也必须失败）** + **baseline = `HEAD:COMPAT.md` 优先（存在且有机读段行）→ `HEAD:README.md` 回退 → 都无则 skip（MUST NOT 写死 `HEAD:README.md`）**; G29 new `--check-compat` criteria; **门面/契约符号数以 manifest 驱动、不硬编码（并集 27 = 契约层 22 ∪ 门面层 8）；订正 `b3f1` 总览表的 G7/G8/G19 计数与 G8/G19 取行源（清理 18/7、20/7、20/8 旧口径）；`b3f1` 总览表 G7 行与 `b2f2` G7 / G8 行改为「清单（manifest 驱动）」；`b2f2` G19 判定 3 改为 `StateGraph` = 行为等价、`Send` / `interrupt` = 部分等价（与 `MATRIX_NEW_EQUIVALENCE` 一致）；`b2f2` / `b3f1` 的 G19 标题去掉「门面 7 个」**; record 2026-11-24 option A approval → FR-016 / FR-019
- [X] T010 Run `tests/contracts/test_architecture.py` + `tests/facade/test_facade_gates.py` + `tests/runtime/test_parse_contract.py` + `gate_G29_contract_carrier.py --check-compat` against the `COMPAT.md` skeleton; fix until green; record commands and outputs；**若 T002 未记录，MUST 在临时副本补录变红断言清单（`文件:行号` + 原因）** → FR-004 / SC-004
- [X] T043 [P] Update `tests/runtime/test_parse_contract.py::test_compat_matrix_has_no_new_row_for_this_feature`: read the `## API 兼容矩阵` machine section from **`COMPAT.md`** instead of `README.md` (reuse `_gatesupport` via `sys.path` or a shared helper); **MUST 保留迁移后的 exact two-layer symbol-set 断言**（不得删除；G19 是同源判据，但本测试同时守护「零新增行」语义）；**顺带把该测试 docstring / 错误消息里的「契约层 18 + 门面 7」「20 + 7」改为 manifest 驱动（并集 27 = 契约层 22 ∪ 门面层 8）** → FR-004 / FR-012 / FR-019 / SC-004

**Checkpoint**: `COMPAT.md` 机读段已落库；G8 / G19 / G29 与 `test_parse_contract.py` 已迁源且绿；US4 / US5 可开始。

---

## Phase 3: User Story 1 - 装上就能用，且基础安装无第三方依赖 (Priority: P1) 🎯 MVP

**Goal**: 隔离环境安装 wheel 成功、`import freegraph` 成功、基础依赖闭包为空；
`[otlp]` 可安装且不拉入 `certifi` / HTTP exporter / 元包。

**Independent Test**: 在隔离 venv 安装 `dist/*.whl` → `import freegraph` → `pip freeze` 只含
`freegraph`（及 `pip`）；另建 venv 安装 `freegraph[otlp]` → 无 `certifi` / `requests` /
`opentelemetry-exporter-otlp`（元包；`...-proto-grpc` 允许）。

### Tests for User Story 1

- [X] T011 [P] [US1] Add `tests/contracts/test_b24f1_packaging.py`: assert `requires-python == ">=3.11"`, `dependencies == []`, `[project.optional-dependencies]` keys == `{"otlp"}`, `src/freegraph/py.typed` exists, no `pydantic` / `checkpoint` / `otel` / `png` extras; **assert `pyproject.toml` 的 `license` / `License-Expression` == MIT，且 `LICENSE` 文本含 MIT 条款**（新建 `.py` MUST 带署名头） → FR-001 / FR-008 / FR-009 / FR-013 / FR-017 / SC-005
- [X] T012 [P] [US1] Add `tests/contracts/test_b24f1_otlp_meta.py`: assert `[otlp]` declares only `opentelemetry-api` / `opentelemetry-sdk` / `opentelemetry-exporter-otlp-proto-grpc`; MUST NOT declare **精确包名** `opentelemetry-exporter-otlp` 元包 / `opentelemetry-exporter-otlp-proto-http` / `requests` / `certifi`（不得用子串；`opentelemetry-exporter-otlp-proto-grpc` 允许；新建 `.py` MUST 带署名头） → FR-001 / FR-013 / FR-017 / SC-005 / SC-006

### Implementation for User Story 1

- [X] T013 [US1] Implement isolated base-install check in `harness/verification/B24F1/acceptance.py`: 用 `tempfile.TemporaryDirectory` + `venv.EnvBuilder` + `sys.executable`（**跨平台**：Windows `Scripts/python.exe` / POSIX `bin/python`；带超时与清理），安装 built wheel（**若 `dist/` 无 wheel，先 `uv build --out-dir <临时目录>`**），`import freegraph`，断言 `pip freeze` 无第三方运行时依赖 → FR-011 / SC-001
- [X] T014 [US1] Implement `[otlp]` isolated-install check in `harness/verification/B24F1/acceptance.py`: 同一跨平台 venv 工具，**复用 T013 的 wheel / 临时构建目录**，安装 `freegraph[otlp]`（**依赖来源 MUST 明确：联网 / uv 或 PIP 缓存 / 预置 wheel；不得假设 CI `.venv` 已装 extras 会被新建隔离 venv 继承**），按**精确包名**断言无 `certifi` / `requests` / `opentelemetry-exporter-otlp` 元包（`opentelemetry-exporter-otlp-proto-grpc` 允许；不得用子串匹配）；**离线且缺依赖 ⇒ 环境未就绪（exit 2）+ 记录**，不得伪 PASS（CI Linux 作业具备网络 / 缓存时提供真实证据，记录 MUST 写明依赖来源） → FR-011 / SC-006
- [X] T015 [US1] Run US1 checks and record **actual outputs**（`pip freeze` 文本 / import 结果 / 命令）in `harness/verification/B24F1/manual-verification.md` → SC-001 / SC-006 / SC-008

**Checkpoint**: 零依赖安装与 `[otlp]` 安装均可独立验证。

---

## Phase 4: User Story 2 - 发行包里没有仓库杂物 (Priority: P1)

**Goal**: wheel / sdist 只含包代码 + 必要元数据；仓库内容命中数为 0。

**Independent Test**: 构建 wheel + sdist → `check_dist_purity.py dist/` 退出码 0；
逐个列出产物成员，断言无 `harness/` / `.specify/` / `COMPAT.md` / `THIRD_PARTY_NOTICES`；
另在临时副本混入 `evil.zip` ⇒ 退出码非 0。

### Tests for User Story 2

- [X] T016 [US2] In `pyproject.toml` `[tool.hatch.build.targets.sdist]`, add explicit `exclude` entries for `COMPAT.md` / `THIRD_PARTY_NOTICES` / `.gitignore` (belt-and-suspenders; dependency face unchanged)；**由于 hatchling 会把 VCS 忽略文件（根 `.gitignore`）强制加入 sdist、`exclude` 无法拦截，新增 sdist-only 构建钩子 `harness/build_hooks/sdist_prune.py`（`[tool.hatch.build.targets.sdist.hooks.custom]`）在 `finalize` 阶段从 tar.gz 移除 `.gitignore`；钩子文件不得进入 sdist** → FR-002
- [X] T017 [P] [US2] Add `tests/contracts/test_b24f1_purity.py` positive synthetic-artifact cases: minimal allowed wheel and sdist（sdist 必需文件含 `pyproject.toml`）⇒ exit 0; wheel missing `py.typed` ⇒ exit 1; use `zipfile` / `tarfile` in `tmp_path`（新建 `.py` MUST 带署名头） → FR-002 / SC-002

### Implementation for User Story 2

- [X] T018 [US2] Implement real-artifact content check in `harness/verification/B24F1/acceptance.py`: `uv build`, list wheel / sdist members, assert only allowed paths + required files（wheel 根级仅 `freegraph/` + `freegraph-*.dist-info/`；sdist 含 `pyproject.toml` 且不含 `.gitignore`）, no repo content and no `COMPAT.md` / `THIRD_PARTY_NOTICES`; **`dist/` 内出现任何归档类非 `.whl` / `.tar.gz` 文件（`.zip` / `.tar` / `.tgz` / `.tar.bz2`）⇒ 失败；`dist/.gitignore` 标记 MUST 豁免**（复用 T045 的脚本检查；若 T018 先于 T045，T018 MUST 在 acceptance 中自带等价断言） → FR-002 / FR-009 / FR-017 / SC-002
- [X] T019 [US2] Run US2 checks and record actual artifact member listings + purity exit code in `manual-verification.md` → SC-002 / SC-008

**Checkpoint**: 发行产物干净可判定；仓库文档不随包分发。

---

## Phase 5: User Story 3 - 发布前有一道机械拦截 (Priority: P1)

**Goal**: 产物混入仓库文件 ⇒ 纯度断言失败并中止发布；工作流顺序为 build → purity → publish。

**Independent Test**: 在临时产物副本注入 `harness/report.md` ⇒ 退出码 1；解析
`publish.yml` 断言 `Verify artifact purity` 在 `Publish to PyPI` 之前。

### Tests for User Story 3

- [X] T020 [P] [US3] Add `tests/contracts/test_b24f1_purity_negative.py`: synthesize wheel / sdist, inject `harness/report.md` and `specs/x/spec.md` ⇒ exit 1 with path; **sdist missing `pyproject.toml` / `LICENSE` / `PKG-INFO` ⇒ exit 1**; **sdist containing `.gitignore`（或 `harness\\report.md` 风格 Windows 路径）⇒ exit 1**; **a stray non-`.whl` / non-`.tar.gz` 归档类 artifact（如 `evil.zip`）in `dist/` ⇒ exit 1，不得静默忽略**; **合法产物 + `dist/.gitignore` 标记 ⇒ exit 0（不得判为额外产物）**; empty / missing `dist` ⇒ exit 2; MUST NOT touch real `dist/`（新建 `.py` MUST 带署名头） → FR-002 / FR-010 / SC-003
- [X] T021 [P] [US3] Add `tests/contracts/test_b24f1_publish_order.py`: parse `.github/workflows/publish.yml`, assert `Build` < `Verify artifact purity` < `Publish to PyPI`, and the purity step invokes `harness/scripts/check_dist_purity.py`（新建 `.py` MUST 带署名头） → FR-003 / SC-003

### Implementation for User Story 3

- [X] T045 [US3] Extend `harness/scripts/check_dist_purity.py` to inspect wheel `freegraph-*.dist-info/METADATA` (depends on T020's test file): **只用标准库解析 METADATA（`email.parser.Parser`），MUST NOT `import packaging`**；对 `Provides-Extra` / `Requires-Dist` 做 PEP 503 规范化的精确包名比较（小写，`-`/`_`/`.` 统一为 `-`；不得用子串）：`Provides-Extra` ⊆ `{"otlp"}`；无 `extra` marker 的 `Requires-Dist` 归为基础依赖且 MUST 为空；marker 含 `extra == "otlp"` 的项才归入 `[otlp]` 闭包；`[otlp]` extras MUST NOT contain **精确包名** `certifi` / `requests` / `opentelemetry-exporter-otlp` 元包 / `opentelemetry-exporter-otlp-proto-http`（`opentelemetry-exporter-otlp-proto-grpc` 允许）; **remove `.gitignore` from `SDIST_ALLOWED_FILES`**; **add `pyproject.toml` to `SDIST_REQUIRED`**; **assert `dist/` 内任何归档类非 `.whl` / `.tar.gz` 文件（`.zip` / `.tar` / `.tgz` / `.tar.bz2`）⇒ exit 1；`dist/.gitignore` 标记 MUST 豁免**; **tighten wheel root allowlist to `freegraph/` + `freegraph-*.dist-info/`（`freegraph-evil.txt` ⇒ exit 1）**; in `tests/contracts/test_b24f1_purity_negative.py` add only the **METADATA / wheel-root** cases (`Provides-Extra: png` ⇒ exit 1; `Requires-Dist: requests; extra == "otlp"` ⇒ exit 1; `freegraph-evil.txt` ⇒ exit 1); **sdist missing `pyproject.toml`、stray `evil.zip` 与 `.gitignore` 用例由 T020 负责，MUST NOT 重复编写**; update `contracts/packaging-purity-contract.md` §4/§6 → FR-001 / FR-002 / FR-010 / FR-017 / SC-002 / SC-003 / SC-005
- [X] T022 [US3] Implement negative purity check in `harness/verification/B24F1/acceptance.py`: **若 `dist/` 无产物，先 `uv build`**；copy real artifacts to temp, inject a repo file, assert script exits non-zero and prints 「拒绝发布」/ violation path; verify real `dist/` unchanged → FR-003 / FR-010 / SC-003
- [X] T023 [US3] Run US3 checks and record actual negative exit codes / output + workflow order in `manual-verification.md` → SC-003 / SC-008

**Checkpoint**: 发布前机械拦截可独立证明；负向不污染真实产物。

---

## Phase 6: User Story 4 - 我能查 freegraph 与 LangGraph 的兼容程度 (Priority: P2)

**Goal**: `COMPAT.md` 覆盖 18 项 + 全量契约 / 门面符号 + 下游承接行 + 证据；
`THIRD_PARTY_NOTICES` 定稿。

**Independent Test**: 打开 `COMPAT.md`，18 行逐项可核对；下游 10 行齐全；
`Command` = 部分等价；每行有来源；`THIRD_PARTY_NOTICES` 含 `SqliteSaver` MIT 改编与
`[otlp]` 闭包；`B24F1-D-01…D-03` 差分组在上游可用时通过、缺席时 skip。

### Implementation for User Story 4

- [X] T024 [US4] Fill `## 18 项覆盖表` in `COMPAT.md`: 18 rows, columns `# | target.py API 元素 | 上游是否直接提供 | freegraph 处置 | 等价程度 | 证据`; #1–#7 行为等价, #8–#12 行为等价, #13 部分等价（处置含 v1 占位 PNG / v2 `[png]` 升级路径）, #14–#18 **行为等价**（处置列注明原样承载 · 不属范围）; **#4 处置列 MUST 含「多源汇合边支持（H-1）」，证据列 MUST 引 B7F4 D-6**; 每行必须有「证据」列（Q3 §3.4 # / B7F4 / B13F1 / B23F1）→ FR-004 / FR-012 / FR-015 / FR-018 / SC-004
- [X] T025 [US4] Fill `## 下游承接行` in `COMPAT.md`: 多源汇合边 / `MemorySaver` / `InMemorySaver` / `CheckpointTuple` / `SqliteSaver` / `CompiledGraph.get_state` / `CompiledGraph.get_state_history` / `CompiledGraph.update_state` / 时间旅行重放分叉 / `OtlpExporter`; 档位 MUST 为：多源汇合边 = **行为等价**；`MemorySaver` / `InMemorySaver`（同一对象别名）/ `CheckpointTuple` = **行为等价**；`SqliteSaver` = **部分等价**（MIT 改编 · `json` 序列化差异 · X-07）；`CompiledGraph.get_state` = **部分等价**（行内 MUST 含 **Y-02**：无快照返回 `None` vs 上游空 `StateSnapshot` · B15F1 P-02 / X-01）；`CompiledGraph.get_state_history` = **行为等价**（P-04 / P-05，注明 B14F1 冻结差异）；`CompiledGraph.update_state` = **部分等价**（返回 `RunConfig` · `as_node` · 无 `task_id`）；时间旅行 = **部分等价**；`OtlpExporter` = **不支持**（无上游对应 / 自由设计）；each with source → FR-004 / FR-012 / FR-018 / SC-004
- [X] T026 [US4] Fill `## 证据与来源` and `## 维护规则` in `COMPAT.md`: per-row anchors (Q3 §3.4 / upstream `path:line` / feature spec); for G-01…G-07 覆盖映射，行内 MUST 引用 `tests/differential/` 中**实际存在的场景名**（MUST NOT 把 `G-xx` 当作测试用例名）；update obligations, README link rule → FR-004 / FR-015 / SC-004
- [X] T027 [P] [US4] Add `tests/contracts/test_b24f1_compat.py`: assert 18 rows (1–18), downstream symbols present, every row has evidence, affiliation string, machine section covers contract ∪ facade (via `_gatesupport`); **对 G-01…G-07 的覆盖映射，断言 `COMPAT.md` 引用的是 `tests/differential/` 中真实存在的场景名（不得仅写 `G-xx`）**; **`Command` = 部分等价 且差异说明分别含 `Y-01`/`DIFF`、`X-06`/`STRICTER`、`X-2`/`X-3`（不得把 `goto` 缺省写成「更严」），并含 `P3` / `99d43aa` 的纠正来源注记**; **`NodeFunc` 含「命令列表」与 `Send`/`list[Send]`/`tuple[Send, ...]`（H-2/H-3）且档位 = 不支持**; **`NodeFunc` 含「无上游同名协议」；`Send` 含 fan-out/运行期语义已落地（H-3）、「freegraph 侧不可变（上游可变）」（Y-03）且注明类型定义住 L1（`freegraph/contracts/types.py`）**; **`StateGraph`（`compile`）含 `interrupt_before`/`interrupt_after`/`recursion_limit`（H-4）**; **`Graph` 含 v1 占位 PNG 与 v2 `[png]` 升级路径（FR-018）**; **`CompiledGraph` 机读行的差异说明 MUST 同时含 `Y-02` / `None` / `StateSnapshot`，并含 `update_state` / 时间旅行 = v1 能力边界（非「更严」）；下游 `CompiledGraph.get_state` = 部分等价（行内含 Y-02）、`CompiledGraph.get_state_history` = 行为等价、`CompiledGraph.update_state` / 时间旅行注明 v1 能力边界（非「更严」）**; **`Store` 机读行 MUST 与 baseline（`HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退；两者都无则 skip，不判失败）逐字节相等，由本测试的专用断言核验（MUST NOT 依赖 G19 的等价程度检查）**; **`## 证据与来源` 含 `Store` 的「协议等价 · v1 无实现」澄清（MUST NOT 依赖机读行改动）**; **18 项表 #4 行 MUST 含「多源汇合边」与 `B7F4`（H-1）**（新建 `.py` MUST 带署名头） → FR-004 / FR-012 / FR-015 / FR-018 / SC-004
- [X] T050 [P] [US4] Add `tests/differential/test_b24f1_matrix_parity.py` covering **宪法原则 XI 最小差分组 `B24F1-D-01…D-03`**: `Command().goto` 缺省（上游 `()` vs freegraph `None` · DIFF / Y-01）、`Send` 可变性（上游可变 vs freegraph 不可变 · DIFF / Y-03）、`get_state` 无快照（上游空 `StateSnapshot` vs freegraph `None` · DIFF / Y-02）；**MUST NOT 修改运行时**；上游缺席 ⇒ `pytest.skip`（不是失败）；断言 `COMPAT.md` 对应行含 `Y-01` / `Y-02` / `Y-03`；新建 `.py` MUST 带署名头 → FR-004 / FR-015 / SC-004（宪法原则 XI）
- [X] T028 [P] [US4] Add `tests/contracts/test_b24f1_notices.py`: assert `THIRD_PARTY_NOTICES` exists; §1 contains `langgraph-checkpoint-sqlite` / MIT / LangChain, Inc.; §2 contains `[otlp]` packages + `protobuf` → `BSD-3-Clause`; base install has no data rows; `langgraph==1.2.11` not registered; §3 contains 「不构成 affiliation」**且指向 `COMPAT.md`（MUST NOT 再把 README 当逐符号权威）**; 新建 `.py` MUST 带署名头 → FR-005 / SC-004
- [X] T029 [US4] Finalize `THIRD_PARTY_NOTICES`: add B24F1 maintenance note; verify `SqliteSaver` MIT adaptation, `[otlp]` closure, `protobuf` normalization, v2 extras plan; no dev / differential dependency rows; **update §3's per-symbol pointer 与 §4 的矩阵维护规则 from `README.md` to `COMPAT.md`（README 只保留指针）**; **把 §1 / §4 的旧 feature 编号 `F1P1` / `F24P1` 替换为 `B1F1` / `B24F1`（历史说明可保留括注）** → FR-005 / SC-004
- [X] T030 [US4] Implement COMPAT / NOTICES checks in `harness/verification/B24F1/acceptance.py`: 18 rows, downstream 10, `Command`, affiliation, NOTICES required entries → FR-004 / FR-005 / SC-004
- [X] T031 [US4] Run US4 checks and record actual cross-check results (18 / downstream / Command / NOTICES) in `manual-verification.md` → SC-004 / SC-008

**Checkpoint**: 兼容矩阵与归属清单齐备、逐项可核对；最小差分组 `B24F1-D-01…D-03` 可执行（上游缺席 skip）。

---

## Phase 7: User Story 5 - README 能让新用户一眼看懂边界 (Priority: P2)

**Goal**: README 中文为主 + 英文关键段落；独立实现声明；三条承诺；
「能力 → freegraph 处置」表；`COMPAT.md` 链接；顶部状态与当前能力一致。

**Independent Test**: 通读 README，检查状态 / 声明 / 承诺 / 能力表 / 链接 / 英文关键段；
确认 README **没有**完整矩阵（`## API 兼容矩阵` 章节只是指针）。

### Tests for User Story 5

- [X] T032 [US5] Add `tests/contracts/test_b24f1_docs.py` **（依赖 T033 的 README 重写；不得与 T033 并行）**: README contains 「独立实现、非 LangChain Inc. 产品」+ **「兼容意图为互操作，不构成 affiliation」**+ three promises（零账号（含零 license key）/ 零出站 / 零第三方运行时依赖）+ English key sections + `## 能力 → freegraph 处置`（**5 列 + 8 行 + as-of 2026-11-01**；表头逐字为 `能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1`）+ **absolute GitHub URL** to `COMPAT.md`; **按 FR-006 结构化断言「中文为主」**（非英文 `##` 标题含中文；英文只在 `## English` / `## English Summary` / `[English]` 段；非英文段不得连续 3 段纯英文）; status has no 「内核尚未实现 / 没有任何图运行时能力 / 请勿用于生产 / 请勿当作可用替代品 / 不要把它当作…可用替代品」; OTLP section contains **OpenLIT / Langfuse / Phoenix** and **无默认推荐**; **brand-asset scan（logo / 品牌色 / 官方文案）命中 0**; `## API 兼容矩阵` section has **zero** full-matrix rows; **README MUST NOT 含旧计数「31 个 feature」「93 人日」「契约层 20 / 21」「门面 7」（改用 32 / 96 / 契约层 22 / 门面 8 / 去重 27）**（新建 `.py` MUST 带署名头） → FR-006 / FR-007 / FR-008 / FR-018 / SC-007

### Implementation for User Story 5

- [X] T033 [US5] Rewrite `README.md`: remove the full symbol matrix → pointer to `COMPAT.md` (**absolute GitHub URL**); **逐字复刻 §3.2 的 5 列**（能力 / Developer `$0` / Plus `$39/seat/月` / Enterprise / freegraph v1）**8 行** + `as-of 2026-11-01`; update the status block（含订正过时的「31 个 feature / 93 人日」为立项书口径 32 / 96；并把「契约层 **20** / **21** 个、门面 **7** / **8** 个」等旧计数统一改为 **manifest 驱动**：当前契约层 **22** ∪ 门面 **8**，去重后 **27**，不得保留 18/20/21/7 等旧口径；status 的 31/93 一并改为 32/96）; add English key sections（以显式 `## English` / `## English Summary` 段呈现：声明 / 承诺 / 安装与 `[otlp]` / 能力摘要 / `COMPAT.md` 链接）; 三条承诺 = 零账号（含零 license key）/ 零出站 / 零第三方运行时依赖; **preserve the OTLP section with OpenLIT / Langfuse / Phoenix and「无默认推荐」**; **preserve 依赖面 / 开发与验收等既有章节**; **保留「兼容意图为互操作，不构成 affiliation」声明**; **preserve the existing README doc-guard strings（含 `tests/facade/test_compiled_graph.py` 所需「v1 不支持 `Store`」「checkpointer…B14F1 的 `MemorySaver` 落地」）**; 其余章节保持中文为主，英文只覆盖列出的关键段落; **MUST 保留 T004 建立的 README 指针，MUST NOT 重新引入完整矩阵**（A-3） → FR-006 / FR-007 / FR-008 / SC-007
- [X] T044 [US5] Preserve existing README doc-guard markers while rewriting: run `tests/runtime/test_parse_contract.py` (matrix reader, migrated by T043), `tests/runtime/test_b16f1_doc_guard.py` (`update_state` / `时间旅行已交付`), `tests/facade/test_invoke_purity.py`（`只读快照` / `不要原样回喂`）, **`tests/facade/test_compiled_graph.py`（`v1 不支持 \`Store\`` / `checkpointer 的行为已由 B14F1 的 \`MemorySaver\` 落地`）**, `tests/runtime/test_b21f1_manual_record_guard.py`（`OTLP 导出（B21F1` / `freegraph[otlp]` / `无默认推荐`）; preserve the required strings or update the guard with explicit rationale → FR-006 / FR-007 / SC-007
- [X] T034 [US5] Implement README checks in `harness/verification/B24F1/acceptance.py`: status / declaration / three promises / **5 列 + 8 行 + as-of** capability table（表头含 `Developer $0` / `Plus $39/seat/月`）/ **按 FR-006 结构化断言中文为主** / absolute link / no full matrix / OTLP three backends → FR-006 / FR-007 / SC-007
- [X] T049 [US5] Implement the top-level orchestrator in `harness/verification/B24F1/acceptance.py`: 按 A1–A3 与 US1–US5 子检查顺序执行并汇总（**A1–A3 = 提示词 §6 的三项验收判据：A1 发行包就绪 / A2 兼容矩阵与归属清单齐备 / A3 纯度门禁通过**）；全部通过时打印逐字 `B24F1 acceptance: PASS` 并退出 0；断言失败退出 1；`[otlp]` / 网络 / 构建环境未就绪退出 2；`--record` 输出五段式记录片段。**T040 依赖本任务完成** → FR-014 / SC-008
- [X] T035 [US5] Run US5 checks and record actual README cross-check (section presence / row counts / link) in `manual-verification.md` → SC-007 / SC-008

**Checkpoint**: README 为发布基线；能力边界首屏可见；矩阵唯一权威指向 `COMPAT.md`。

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 全量门禁、快速验收、零改动审计、人工记录收口。

- [X] T036 [P] Run full `pytest tests/ -ra` + `gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + `gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + `gate_G24_config_layer.py` + `gate_G25_import_graph.py` + `gate_G26_network_static.py` + `gate_G29_contract_carrier.py --check-compat` + `gate_G30_attribution.py` + Linux-only `gate_G22_isolated_env.py` / `gate_G27_zero_egress.py` / `unshare --net --map-root-user ... gate_G28_offline_equiv.py`（非 Linux 或 `unshare` 不被允许 ⇒ 标记环境未就绪，由 CI Linux 作业覆盖；本机实测 G22 / G27 通过）; record commands / outputs → FR-003 / FR-008 / FR-013 / FR-016 / FR-017 / FR-019 / SC-005
- [X] T037 [P] Run [quickstart.md](./quickstart.md) end-to-end (build / purity positive+negative / isolated install / `[otlp]` / matrix checks) and record actual outputs → SC-001…SC-008
- [X] T038 [P] Audit `git diff -- src/freegraph harness/demo/target.py` is empty; run B23F1 PNG tests (`tests/contracts/test_graph_png.py`) to confirm `draw_mermaid_png()` 调用面（零必需参数、返回 `bytes`）未破; confirm no new gate number (only G8 / G19 / G29 updated); confirm `COMPAT.md` / `THIRD_PARTY_NOTICES` absent from `dist/` → FR-016 / FR-018 / FR-019
- [X] T039 Finalize `harness/verification/B24F1/manual-verification.md` five sections (环境 / 步骤 / 实际输出 / 结论 / 遗留问题); include formal ratification text for G8 / G19 / G29 migration + `Command` exception (2026-11-24 · 选项 A); **include the 质量门禁 5 deviation + B25F1 承接追认（内容由 T046 提供；T046 MUST 先于本任务完成，T039 唯一写入）**; include **B15F1 / B16F1 的人工验收证据（或链接）**; include actual outputs for SC-001…SC-008; **`B24F1 acceptance: PASS` MUST 来自环境就绪的实际运行（CI Linux 作业具备网络 / 缓存、可安装 `[otlp]` 依赖，或本地已就绪环境；不得假设 CI `.venv` 的 extras 会被隔离 venv 继承；本地 `exit 2` 不得替代 PASS；记录 MUST 写明环境 / 命令 / `[otlp]` 依赖来源 / 若引用 CI 则写作业名与运行标识）**; **在「遗留问题」显式登记 Y-01（`Command.goto` 缺省 `()` vs `None` = 既有 DIFF · 具名承接 B25F1（M4）· 运行时对齐归 v2）、Y-02（`get_state` 无快照 `None` vs 上游空 `StateSnapshot` · B15F1 X-01）与 Y-03（`Send` 不可变 vs 上游可变 · B11F1）** → FR-014 / SC-008
- [X] T046 Author the **质量门禁 5 deviation**（真实模型轮 → B25F1）ratification text: 发起者 2026-11-24 追认文字 + 确认人 + 日期 + B25F1（M4）承接条款；**本任务 MUST 先于 T039 完成**；交给 T039 **作为唯一写入者**并入 `manual-verification.md`（MUST NOT 两处重复写）。spec/plan 已记录追认；**追认文字缺失则阻断合入**（不是「未追认」） → FR-014 / SC-008
- [X] T047 Verify `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B24F1 · M4 · 只接线）」小节（**已在本轮分析修复中接线**；实现期若被覆盖则补回）：须含质量门禁 5 真实模型轮承接、`COMPAT.md` 声明覆盖、Y-01（`Command.goto` 缺省 `()` vs `None` · 既有 DIFF）的记录义务；并在 `tests/runtime/test_b24f1_manual_record_guard.py` 断言该小节存在且含 `B24F1` / `Y-01` / `真实模型轮` 字样 → FR-014 / SC-008
- [X] T048 Verify `harness/proposals/立项书.md` §6.2.1 第 6 条与 D7 注记（**已在本轮分析修复中同步**；实现期若漂移则修正）：README 只保留「能力 → freegraph 处置」表 + `COMPAT.md` 指针，逐符号 API 兼容矩阵以 `COMPAT.md` 为唯一权威；该同步不改变任何门禁判据、不新增门禁编号；复核文字落 `manual-verification.md` → FR-004 / FR-007 / SC-004 / SC-007
- [X] T042 Add `tests/runtime/test_b24f1_manual_record_guard.py` **after T046 / T039 / T047** (宪法 v1.13.0 · 人工门禁类 SC 的可自动核验判据)：断言 `harness/verification/B24F1/manual-verification.md` 存在、五段式标题齐备、正文非空、含必需实测输出（`B24F1 acceptance: PASS` / `pip freeze` / 纯度正负向退出码 / `COMPAT.md` 18 项与下游行核对 / G8-G19-G29 追认文字 / **质量门禁 5 偏离 + B25F1 承接追认** / **Y-01 / Y-02 / Y-03** 遗留项 / **B15F1 与 B16F1 人工验收证据（或链接）**），且不含 `待填`；**PASS 不得以「环境未就绪」替代**; **MUST 同时断言 `harness/features/B25F1_双跑验收与迁移说明.md` 含「下游承接（B24F1」与 `Y-01` / `真实模型轮` 字样（T047）**；**MUST NOT** 在此之前让该守卫进入 CI（避免永久红） → FR-014 / SC-008
- [X] T040 Add B24F1 to `tests/runtime/test_acceptance_script.py`: run `harness/verification/B24F1/acceptance.py`; **若退出码为 2（环境未就绪 / 离线缺 `[otlp]` 依赖）⇒ `pytest.skip` 并记录原因**；仅在环境就绪时断言 `B24F1 acceptance: PASS`；设置足够 timeout 并避免把构建 / 网络失败伪装成 PASS；**该 skip 只针对本地测试执行，不得用于豁免 T039 记录中的 PASS 取证** → FR-014 / SC-008
- [X] T041 Final traceability audit: every FR / SC maps to at least one task and every task has `→ FR/SC`; **双向核验**：每个任务末尾的 `→ FR/SC` MUST 出现在正向表中，且正向表中的每个任务 MUST 在该任务的末尾标签中出现；**verify T042/T043/T044/T045/T046/T047/T048/T049/T050/T005-T010 are present in the forward tables**; **re-run `pytest tests/ -ra`（尤其 `tests/runtime/test_b24f1_manual_record_guard.py`）after T042 is added**; mark completed checkboxes; update `spec.md` / `plan.md` status only if needed → FR-014 / SC-008（原则 VI 追溯收口）

**Checkpoint**: 全部门禁绿；人工记录含实测输出与追认；追溯闭合。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖，可立即开始。
- **Foundational (Phase 2)**: 依赖 Setup；**阻塞 US4 / US5**（矩阵 / README 依赖 `COMPAT.md` 机读段与门禁迁源）。
- **US1 / US2 / US3（P1）**: 只依赖 **Setup + 构建产物**；不被 Foundational 阻塞，但 **US1 / US3 的 T013 / T014 / T022 依赖真实 wheel/sdist**（由 T018 或各自 `uv build --out-dir <tmp>` 提供）；不得假设 `dist/` 已存在。
- **US4 / US5（P2）**: 依赖 Foundational；US4 与 US5 可并行（README 链接的是 `COMPAT.md` 机读段，不依赖 18 项 / 下游段）。
- **Polish (Phase 8)**: 依赖全部目标故事完成。

### Within Each Story

- **US1**: T011 / T012 [P] → T013（先 `uv build` 到临时目录）→ T014 → T015。
- **US2**: T016 → T017 [P] → T018 → T019（T018 的 stray-artifact 断言 MUST 与 T045 的脚本判据同口径；若 T018 先于 T045，T018 自带断言）。
- **US3**: T020 / T021 [P] → T045（依赖 T020 的测试文件） → T022（先 `uv build` 到临时目录） → T023。
- **US4**: T024 → T025 → T026（同一文件，顺序）→ T027 [P] / T028 [P] / T050 [P] → T029 → T030 → T031。
- **US5**: T033 → T032（README 重写后补断言）→ T044（既有 doc guard 复核）→ T034 → T049（顶层编排）→ T035。
- **Polish（必须遵守）**: **T046 → T039 → T047 / T048 → T042**；T049 依赖 **T013 / T014 / T018 / T022 / T030 / T034**（它要汇总 A1–A3 与 US1–US5 的子检查）。

### Critical Path

```text
T001 → T004 → T005 → T006/T007/T008/T009/T043 → T010
     → T024/T025/T026 → T027/T028/T050 → T029/T030 → T031
     → T033 → T032 → T044 → T034 → T049（顶层编排）→ T035
     → T036/T037/T038 → T046（质量门禁 5 追认文字）
     → T039（人工记录收口）→ T047/T048（B25F1 / 立项书复核）
     → T042（人工记录守卫）→ T040/T041
```

US1（T011–T015）、US2（T016–T019）、US3（T020–T023 / T045）可与 US4 / US5 并行，
但 **T049 依赖 T013 / T014 / T018 / T022 / T030 / T034**，T036 的全量门禁也依赖它们全部完成。

---

## Parallel Opportunities

| 组 | 可并行任务 | 说明 |
|---|---|---|
| Setup | T003 | 与 T001 / T002 不同文件 |
| Foundational helpers | T005 → T006 / T007 / T008 / T009 / T043 | T005 先落；后五条改不同文件 |
| US1 测试 | T011 / T012 | 不同测试文件 |
| US2 / US3 测试 | T017 / T020 / T021 | 不同测试文件；T045 在 T020 之后（复用其测试文件） |
| US4 测试 | T027 / T028 / T050 | 不同测试文件；T050 是宪法原则 XI 的最小差分组 |
| US5 | T033 → T032 → T044 | 先重写 README，再补断言并复核既有 doc guard；T049 依赖 T013 / T014 / T018 / T022 / T030 / T034（汇总全部子检查） |
| Polish | T036 / T037 / T038 | 不同验证面 |
| Polish（串行） | T046 → T039 → T047 / T048 → T042 | T046 先产出追认文字；T039 唯一写入记录；T047 复核 B25F1 承接、T048 复核立项书口径；T042 是文档守卫，**MUST 排在 T039 与 T047 之后** |

**Parallel Example: Foundational**

```bash
# T005 first, then these five can run in parallel:
#   tests/contracts/test_architecture.py        (G8)
#   tests/facade/test_facade_gates.py           (G19)
#   harness/scripts/gates/gate_G29_contract_carrier.py  (G29)
#   specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md  (契约回溯)
#   tests/runtime/test_parse_contract.py        (其他 README 矩阵消费者)
```

**Parallel Example: US1 / US2 / US3**

```bash
# After Foundational, P1 stories can run in parallel:
#   Developer A: US1 (T011–T015) 零依赖安装（T013/T014 先 uv build 到临时目录）
#   Developer B: US2 (T016–T019) 产物干净
#   Developer C: US3 (T020–T023 / T045) 负向拦截 + METADATA extras（T022 先 uv build）
```

---

## Implementation Strategy

### MVP First (P1 = US1 + US2 + US3)

本 feature 的「发行就绪」由三条 P1 共同定义，缺一不可：

1. **US1**：装上就能用、基础零依赖（否则发行承诺不成立）。
2. **US2**：产物里没有仓库杂物（否则不可逆发布事故）。
3. **US3**：发布前机械拦截（否则 US2 无法持续保证）。

> 模板通常把 US1 单独作为 MVP；本 feature 的判定「发行包就绪 + 纯度门禁通过」要求
> 三条 P1 同时成立，故 MVP = US1 + US2 + US3。

### Incremental Delivery

1. Setup + Foundational → `COMPAT.md` 机读段 + 门禁迁源就绪。
2. US1 → 零依赖安装可验证。
3. US2 → 产物干净可验证。
4. US3 → 负向拦截可验证。
5. US4 → 18 项 + 下游行 + NOTICES 定稿 + 最小差分组 `B24F1-D-01…D-03`。
6. US5 → README 发布基线。
7. Phase 8 → 全量门禁 + quickstart + 人工记录 + 追溯闭合。

### Parallel Team Strategy

1. 全员完成 Setup + Foundational（一人主 T004–T010 + T043，其余复核）。
2. Foundational 后：
   - Developer A：US1（安装 / 依赖）。
   - Developer B：US2 + US3（产物 / 负向 / 工作流）。
   - Developer C：US4（矩阵 / 归属）。
   - Developer D：US5（README）。
3. Phase 8 由一人统一收口（保证证据 / 追认一致）。

---

## Notes

- **[P] tasks** = 不同文件、无未完成依赖。
- **[Story] label** = US1–US5，保证每段可独立实现 / 测试。
- **Tests are included** because spec SC-001…SC-008 + 宪法原则 VI require judged coverage.
- **MUST NOT** 新增门禁编号；只更新既有 G8 / G19 / G29。
- **MUST NOT** 放宽 G8 / G19 / G29 的覆盖面 / 列数 / 不重复 / affiliation 判据。
- **MUST NOT** 把 18 项 / 下游行塞进 `## API 兼容矩阵` 机读段（会破坏 G19 的两层集合判据）。
- **MUST NOT** 在 README 保留完整兼容矩阵；唯一权威是 `COMPAT.md`。
- **MUST NOT** 把 `COMPAT.md` / `THIRD_PARTY_NOTICES` 打进 wheel / sdist。
- **MUST NOT** 改 `src/freegraph/**` 或 `harness/demo/target.py`。
- **MUST** 在 `manual-verification.md` 写**实际输出**（不得只写「符合预期」）；**SC-008 的判据 MUST 由 T042 的自动文档守卫承担**（写记录 / 审计任务不算判据覆盖）。
- **MUST** 在 Phase 8 内完成 G8 / G19 / G29 迁移的正式追认文字（2026-11-24 · 选项 A）：顺序为 **T046 先产出质量门禁 5 追认文字 → T039 唯一写入 `manual-verification.md`**；T042 守卫在其后。
- **MUST** 在 `manual-verification.md` 遗留问题登记 **Y-01**（`Command.goto` 缺省 `()` vs `None` = 既有 DIFF，**具名承接 B25F1（M4）**，运行时对齐归 v2）、**Y-02**（`get_state` 无快照 `None` vs 上游空 `StateSnapshot` · B15F1 X-01）与 **Y-03**（`Send` 不可变 vs 上游可变 · B11F1）。
- **每个新建 `.py` MUST 带署名头**（G30 扫描全部 tracked `.py`）；T011 / T012 / T017 / T020 /
  T021 / T027 / T028 / T032 / T042 / **T050** 的「新建 `.py`」均须逐文件添加，MUST NOT 依赖事后补。
- **T050 是宪法原则 XI 的最小差分组**（`B24F1-D-01…D-03`）：只断言既有差异，**MUST NOT** 改运行时；上游缺席 MUST skip。
- **T004–T010 + T043 作为一个原子提交**；不得在中途推送 / 合并（`COMPAT.md` 已建、G8/G19 尚未迁源时
  CI 会短暂红；原子提交保证任一提交点都可回退到全绿）。**T004 必须同批把 README 的完整矩阵改为指针**，
  否则 T006 / T008 的「README 无完整矩阵」断言会让 T010 永久红。
- **T046 的合入阻断口径**：spec/plan 已记录发起者 2026-11-24 追认；**追认文字缺失时 MUST NOT 合入**（不是「未追认」）。
- **T047 / T048 是文档复核任务**：两者已在本轮分析修复中接线（B25F1 承接小节 + 立项书 §6.2.1 / D7 口径）；实现期只复核，若漂移则补回。
- **T049 是验收编排任务**：统一输出 `B24F1 acceptance: PASS`；T040 依赖 T049。
- **T040 遇到环境未就绪（exit 2）⇒ skip，不得判失败**；真实构建 / 网络失败必须与「环境未就绪」区分。
- Full regression baseline: 记录 `pytest tests/ -ra` 的通过 / 跳过数（实施时以实际为准）。
