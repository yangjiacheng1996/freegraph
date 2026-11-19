# Tasks: B23F1 · `draw_mermaid_png()`：离线不阻断 ★

**Input**: Design documents from `/specs/b23f1-draw-mermaid-png-offline/`

**Prerequisites**: `plan.md`（必需）· `spec.md`（必需）· `research.md` · `data-model.md` ·
`contracts/png-contract.md` · `contracts/upstream-parity.md` · `quickstart.md`

**Tests**: 本 feature **明确要求测试**（spec 的 FR-004 / FR-005 / FR-017 / SC-002 / SC-003 /
SC-010 / SC-016 + plan 的测试清单）⇒ 各 user story 均包含测试任务。

**Organization**: 任务按 user story 分组；US1 = 离线返回字节（P1）· US2 = 合法 PNG / 固定示意图标
（P2）· US3 = 零出站 / 无隐藏网络（P3）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、不依赖未完成任务）
- **[Story]**: `US1` / `US2` / `US3`（仅 user story 阶段）
- 每个任务都含**精确文件路径**

## Path Conventions

- 单项目：`src/freegraph/` + `tests/` + `harness/`（仓库根）

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 确认基线、上游锚点与只读基准；不写业务代码。

- [X] T001 在仓库根目录运行 `.venv/bin/python -m pytest -q tests/`，确认 `tests/` 全量基线为
  `1700 passed, 4 skipped, 0 failed`（约 113.76s）；若基线不同，先查明原因再继续。
- [X] T002 复核 `specs/b23f1-draw-mermaid-png-offline/research.md` §0.1 的上游锚点：
  `langchain-core 1.6.3`（行号取证）与 `1.7.6`（`.venv` 行为复核）；若行号漂移，
  更新 `research.md` §0.1、`contracts/upstream-parity.md` 与 `spec.md` 的 P 表锚点。
- [X] T003 [P] 确认只读基准未改：在仓库根目录运行
  `git diff --exit-code -- harness/demo/target.py pyproject.toml`；若有 diff，先恢复。

**Checkpoint**: 基线 / 上游锚点 / 只读基准均确认；可以开始 Foundational。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: PNG 编码器骨架 + `Graph.draw_mermaid_png()`；这是 US1–US3 的共同前提。

**⚠️ CRITICAL**: 本阶段完成前，任何 user story 都不能独立通过。

- [X] T004 在 `src/freegraph/contracts/graph.py` 顶部加入标准库 `import struct` 与
  `import zlib`，并新增私有常量/助手：`_PNG_SIGNATURE` · `_PLACEHOLDER_WIDTH = 64` ·
  `_PLACEHOLDER_HEIGHT = 64` · `_PNG_COLOR_TYPE = 2` · `_PNG_BIT_DEPTH = 8` ·
  `_png_chunk(type: bytes, data: bytes) -> bytes`（长度 + type + data + CRC）·
  `_encode_placeholder_png(rows: bytes) -> bytes`（`IHDR` / `IDAT` / `IEND`）·
  `_placeholder_rgb_rows() -> bytes`（初始为 64×64 纯色背景；US2 再升级为固定示意图标）。
- [X] T005 在 `src/freegraph/contracts/graph.py` 的 `Graph` 类中追加
  `def draw_mermaid_png(self) -> bytes`：先调用一次 `self.draw_mermaid()`（返回值在 v1 丢弃），
  再返回 `_encode_placeholder_png(_placeholder_rgb_rows())`；**不写** catch-all、
  **不读**环境变量、**不写**文件、**不发起**网络请求。
- [X] T006 [P] 新建 `tests/contracts/test_graph_png.py`，先写共享判据助手（模块私有）：
  `_parse_chunks(data)`（长度 / type / data / CRC）· `_decompress_idat(data)` ·
  `_assert_signature(data)`；文件首行加既有署名头，模块 docstring 为首个语句。

**Checkpoint**: 方法可调用且返回字节；共享 PNG 解析助手就绪。

---

## Phase 3: User Story 1 - 断网环境也能拿到 PNG 字节 (Priority: P1) 🎯 MVP

**Goal**: 离线调用 `get_graph(xray=True).draw_mermaid_png()` 成功返回非空 `bytes`，
不抛阻断性异常；socket 夹具下「框架出站 = 0」。

**Independent Test**: 编译一张含静态边 / 条件边的图，在 socket 守卫下调用
`draw_mermaid_png()`，断言 `type(data) is bytes`、`len(data) > 0`、`guard.calls == 0`；
全程不调用 `invoke()` / `stream()`。

### Tests for User Story 1

- [X] T007 [US1] 在 `tests/contracts/test_graph_png.py` 追加：
  `test_returns_bytes_for_compiled_graph`（`get_graph().draw_mermaid_png()`）·
  `test_empty_graph_returns_bytes`（`Graph()`）·
  `test_degenerate_graph_returns_bytes`（仅 `__start__` / `__end__`）·
  `test_return_type_is_exactly_bytes` · `test_length_is_positive` ·
  `test_extra_arguments_raise_typeerror`（v1 零参数）。
- [X] T008 [P] [US1] 扩展 `tests/runtime/test_graph_offline.py`：在现有 socket 守卫用例中
  追加 `draw_mermaid_png()` 调用，断言 `guard.calls == 0`；新增
  `test_draw_mermaid_png_ignores_proxy_environment`：设置 `HTTP_PROXY` / `HTTPS_PROXY`
  后调用仍成功，且框架不读环境变量。
- [X] T009 [P] [US1] 扩展 `tests/facade/test_get_graph.py`：
  `test_graph_has_draw_mermaid_png` · `test_draw_mermaid_png_returns_bytes_before_invoke` ·
  `test_draw_mermaid_png_available_on_xray_true_and_false`；
  所有调用都在 `invoke()` / `stream()` **之前**完成，并断言节点函数调用次数 == 0。

### Implementation for User Story 1

- [X] T010 [US1] 若 T007–T009 暴露兼容性问题，只在 `src/freegraph/contracts/graph.py`
  修正 `draw_mermaid_png` / 编码器；**MUST NOT** 改 `_stategraph.py` / `graph.py` /
  `contracts/__init__.py`。
- [X] T011 [US1] 运行
  `.venv/bin/python -m pytest -q tests/contracts/test_graph_png.py tests/runtime/test_graph_offline.py tests/facade/test_get_graph.py`，
  记录实际输出（passed / skipped / failed）；失败则先修 US1，不进入 US2。

**Checkpoint**: US1 独立通过 —— 离线返回 `bytes`、`guard.calls == 0`、任何运行之前可用。

---

## Phase 4: User Story 2 - 返回的字节能直接被展示 (Priority: P2)

**Goal**: 返回字节是**结构合法的 PNG**；画面为**固定示意图标**（64×64 · 3 个方框 + 2 条连线 ·
≥3 色 · 非单色）；同图 / 异图逐字节相同；IPython 可用时 `Image(data)` 不抛。

**Independent Test**: 用独立于 IPython / PIL 的 PNG 解析器逐块校验签名 / `IHDR` / CRC /
`IDAT` 解压 / `IEND` / 无尾随；解码像素断言 64×64、≥3 色；两次调用（含不同图）字节相等。

### Tests for User Story 2

- [X] T012 [US2] 在 `tests/contracts/test_graph_png.py` 追加强结构判据：
  `test_signature_and_first_chunk_is_ihdr`（长度 13）·
  `test_ihdr_is_64x64_rgb8`（宽 / 高 / 位深 / 颜色类型 / 压缩 / 过滤 / 交织）·
  `test_all_chunk_crcs_are_valid` ·
  `test_idat_decompresses_to_expected_scanlines`（长度 12,352；每行 filter 0）·
  `test_iend_is_last_and_no_trailing_bytes` ·
  `test_chunk_sequence_is_exactly_ihdr_idat_iend`（无附属块）。
- [X] T013 [US2] 在 `tests/contracts/test_graph_png.py` 追加：
  `test_palette_has_at_least_three_colors`（v1 参考调色板为 `BACKGROUND` / `BOX_FILL` / `INK`）·
  `test_image_is_not_monochrome` · `test_two_calls_are_byte_identical` ·
  `test_different_graphs_are_byte_identical` ·
  `test_special_character_node_names_return_png`（引号 / 换行 / 非 ASCII / emoji）·
  `test_graph_with_conditional_and_declared_edges_returns_png` ·
  `test_graph_with_join_edge_returns_png`。
- [X] T014 [US2] 在 `tests/contracts/test_graph_png.py` 追加唯一图源判据：
  monkeypatch `Graph.draw_mermaid` 统计调用次数并返回特殊文本；
  断言次数 ≥ 1、PNG 字节不变、`draw_mermaid()` 输出在调用前后**逐字相同**。
- [X] T015 [US2] 在 `tests/contracts/test_graph_png.py` 追加 IPython 可选冒烟：
  `pytest.importorskip("IPython")` → `from IPython.display import Image` →
  `Image(data)` 不抛；若 IPython 缺席则 skip（**不判失败**）。

### Implementation for User Story 2

- [X] T016 [US2] 把 `src/freegraph/contracts/graph.py` 的 `_placeholder_rgb_rows()` 从纯色背景
  升级为**固定示意图标**：64×64 RGB8；调色板
  `BACKGROUND=(245,245,245)` / `BOX_FILL=(217,232,255)` / `INK=(51,102,153)`；
  3 个 1px 边框方框 `(8,24)-(19,39)` / `(26,24)-(37,39)` / `(44,24)-(55,39)`；
  2 条 1px 连线 `y=32` · `x=20..25` 与 `x=38..43`；**不读** `self.nodes` / `self.edges`。
- [X] T017 [US2] 确认 `_encode_placeholder_png()` 仍只产出 `IHDR` / `IDAT` / `IEND`
  （无 `tEXt` / `gAMA` / `sRGB`），`zlib.compress(raw, 9)`，每块 CRC 自洽；
  不改 `Graph` 字段 / 构造 / 不可哈希 / `__all__`。
- [X] T018 [US2] 运行
  `.venv/bin/python -m pytest -q tests/contracts/test_graph_png.py`；
  记录实际输出（含 IPython skip 原因）；失败则先修 US2。
- [X] T019 [US2] 运行 `.venv/bin/python harness/demo/visualization.py`，断言退出码 0，
  且 V4 / V6 的 PNG 判据**真跑并通过**；记录实际输出；**MUST NOT** 修改该脚本。
- [X] T020 [US2] 按 `specs/b23f1-draw-mermaid-png-offline/quickstart.md` §1 / §2 / §4
  手工跑最小验收、结构判据与像素颜色检查；记录实际字节数 / ≥3 色结果
  （**不**断言固定字节长度；zlib 版本可能不同）。

**Checkpoint**: US2 独立通过 —— 合法 PNG、固定示意图标、确定性、IPython 可选冒烟。

---

## Phase 5: User Story 3 - 离线场景没有隐藏的兜底网络请求 (Priority: P3)

**Goal**: `src/freegraph/**` 静态扫描零网络客户端调用；socket 夹具「框架出站 = 0」；
不读环境变量；`stream()` 与 PNG 互不影响；G26 / G27 / G28 通过；**无需**新增断网排除项。

**Independent Test**: AST / 文本扫描 `src/freegraph/contracts/graph.py` 与
`_stategraph.py`；socket 守卫调用 PNG；设置代理环境变量后仍成功；G26 / G27 退出码 0；
G28 断网任务全量通过。

### Tests for User Story 3

- [X] T021 [P] [US3] 扩展 `tests/runtime/test_graph_offline.py` 的静态扫描：
  禁止 import `socket` / `http` / `urllib` / `requests` / `httpx` / `aiohttp` / `subprocess`；
  断言 `mermaid.ink` 不出现；断言 `os.environ` / `os.getenv` 不出现；扫描
  `src/freegraph/contracts/graph.py` 与 `src/freegraph/_stategraph.py`。另加一个**子进程**
  用例：导入 `freegraph` 后调用 `draw_mermaid_png()`，断言 `sys.modules` 中无
  `langchain` / `langchain_core` / `langgraph` / `langsmith`（SC-010）。
- [X] T022 [P] [US3] 新建 `tests/runtime/test_graph_png_offline.py`：
  `test_stream_does_not_call_draw_mermaid_png`（monkeypatch `Graph.draw_mermaid_png` 为
  计数/抛错，跑 `stream()` 后计数 == 0）·
  `test_png_is_stable_before_and_after_stream` ·
  `test_png_calls_during_stream_are_safe`（一个线程跑 `stream()`，另一线程并发调用 PNG）·
  `test_concurrent_png_calls_are_deterministic`（≥ 2 线程）·
  `test_png_call_creates_no_files`（在 `tmp_path` 下运行，目录仍为空）。
- [X] T023 [US3] 在 `tests/runtime/test_graph_png_offline.py` 追加
  `test_offline_exclusions_have_no_b23f1_entries`：读
  `tests/gates/data/offline_exclusions.txt`，断言无 `b23f1` / `B23F1` / `png` 相关条目
  （新用例不建立真实连接，MUST NOT 加入排除清单）。
- [X] T024 [P] [US3] 扩展 `tests/differential/parity_probe.py`：新增
  `_run_png_scenarios()` 覆盖 D-01…D-10；D-04 用 monkeypatch 把 `requests.get` 替换为
  抛 `ConnectionError`（不实际联网），断言上游 `ValueError` 且 freegraph 成功；
  网络依赖的上游分支 `pytest.skip`。同步在 `tests/differential/test_parity_probe.py`
  新增 `test_png_parity_scenarios_meet_their_verdicts`。

### Implementation for User Story 3

- [X] T025 [US3] 运行
  `.venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py tests/runtime/test_graph_png_offline.py tests/differential/test_parity_probe.py -k "png or offline"`；
  记录实际输出；失败则先修 US3。
- [X] T026 [US3] 运行
  `.venv/bin/python harness/scripts/gates/gate_G26_network_static.py`；
  断言退出码 0；记录输出。
- [X] T027 [US3] 在支持非特权网络命名空间的环境运行
  `unshare --net --map-root-user .venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py tests/runtime/test_graph_png_offline.py tests/contracts/test_graph_png.py`；
  若本机不支持，记录「交由 CI G28」并确保测试不联网。

**Checkpoint**: US3 独立通过 —— 静态扫描 0、socket 出站 0、G26 / G27 通过、断网任务可执行。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 文档 / 门禁白名单 / 一键验收 / 人工记录 / 全量回归。

- [X] T028 更新 `README.md` 的 `Graph` 矩阵行：补「B23F1 起提供 `draw_mermaid_png()`（v1 占位 PNG，
  零出站）」；等价程度仍「部分等价」；追加「B23F1 公开面增量 == 0 行」注记。
- [X] T029 更新 `tests/facade/test_facade_gates.py`：新增
  `MATRIX_ROWS_UPDATABLE_BY_B23F1 = frozenset({"Graph"})`，并纳入 G19 的 `changed` 过滤；
  **只放行 `Graph` 行**，等价程度不得变差。
- [X] T030 [P] 更新 `tests/runtime/test_conditional_edge_surface.py` 的模块 docstring：
  把「`draw_mermaid_png()` 尚未存在」改为「B23F1 已交付」；**不改任何断言**。
- [X] T031 [P] 更新 `harness/demo/README.md`：把 `draw_mermaid_png` 的未交付描述改为
  「B23F1 已交付」；**不越界**改其他 feature 的状态。
- [X] T032 新建 `harness/verification/B23F1/acceptance.py`：一键验收 A1–A4：
  构建含静态边 / 条件边的图；`get_graph(xray=True).draw_mermaid_png()`；socket 守卫；
  自行解析 PNG（签名 / `IHDR` / CRC / `IDAT` / `IEND` / 64×64 / ≥3 色 / 确定性）；
  检查方法存在 / 返回 `bytes` / 依赖闭包无 LangChain 家族；退出码 0/1/2。
- [X] T033 新建 `tests/runtime/test_graph_png_acceptance.py`：以子进程运行
  `harness/verification/B23F1/acceptance.py`，断言退出码 0 且 stdout 含
  `B23F1 acceptance: PASS`。
- [X] T034 复跑 `harness/verification/B23F1/acceptance.py` 与
  `harness/demo/visualization.py`；记录退出码与实际输出（A1–A4 / V4 / V6）。
- [X] T035 新建 `harness/verification/B23F1/manual-verification.md`（五段式）：
  环境、步骤与实际输出、差分 / 一键验收、结论 A1–A4、遗留问题；写入
  T-1 授权来源（B22F1 契约 §8 + 本 feature 提示词）、`target.py` diff 为空、
  **G26 / G27 / G28** 证据、`sys.modules` 的 SC-010 证据、`visualization.py` 输出；
  **不得**留 `_待填_`。
- [X] T036 新建 `tests/runtime/test_graph_png_manual_record_guard.py`：断言
  `harness/verification/B23F1/manual-verification.md` 存在、五段式标题齐备、
  含 `B23F1 acceptance: PASS`、无 `_待填_`。
- [X] T037 验证公开面零变化：`freegraph.graph.__all__` == 8 ·
  `freegraph.contracts.__all__` == 22 · `freegraph.runtime.__all__` == 23 ·
  `vars(compiled)` 仍 11 键；`tests/facade/test_api_snapshot.py` 的入库快照未改；
  `pyproject.toml` 与 `harness/demo/target.py` diff 为空。
- [X] T038 运行 `.venv/bin/python -m pytest -q tests/` 全量；记录新的 passed / skipped / failed
  （预期 1700 + 本 feature 新增用例，0 failed）；逐条核对 plan 的 R-01…R-11。
- [X] T039 **复跑并扩展门禁**：运行
  `harness/scripts/gates/gate_G21_dependencies.py` ·
  `harness/scripts/gates/gate_G23_licenses.py` ·
  `harness/scripts/gates/gate_G26_network_static.py` ·
  `harness/scripts/gates/gate_G27_zero_egress.py` ·
  `harness/scripts/gates/gate_G29_contract_carrier.py` ·
  `harness/scripts/gates/gate_G30_attribution.py`；Linux 环境另跑
  `gate_G22_isolated_env.py` / `gate_G28_offline_equiv.py`（不支持则记录交由 CI）。
  记录全部退出码。
- [X] T040 按 `specs/b23f1-draw-mermaid-png-offline/quickstart.md` §1–§7 完整跑一遍，
  记录实际输出；若与文档不符，先修实现 / 测试 / 文档，**不得**只改文档掩盖失败。
- [X] T041 复核 spec 的 FR-001…FR-020 / SC-001…SC-016 与本 tasks / 测试的映射；
  确认 A1–A4 均有可判定任务；若发现缺口，追加任务并落测试，**不得**放宽判据。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**：无依赖。
- **Phase 2 Foundational**：依赖 Phase 1；**阻塞**全部 user story。
- **Phase 3 US1**：依赖 Phase 2；US1 是 MVP。
- **Phase 4 US2**：依赖 Phase 2 + US1（同一 `tests/contracts/test_graph_png.py` 顺序编辑；
  US2 的图标升级依赖 T004/T005）。
- **Phase 5 US3**：依赖 Phase 2 + US1/US2（PNG 必须已合法）。
- **Phase 6 Polish**：依赖 US1 + US2 + US3；文档 / 验收 / 人工记录 / 全量回归。

### User Story Dependencies

- **US1 (P1)**：Phase 2 完成后即可开始；不依赖 US2 / US3。
- **US2 (P2)**：Phase 2 + US1 完成后开始；与 US3 可部分并行（不同测试文件）。
- **US3 (P3)**：Phase 2 + US1/US2 完成后开始；差分类可与 US2 的解码测试并行。
- **Polish**：必须在所有 story 完成后开始。

### Within Each User Story

- 测试任务先写，再实现；测试 MUST 先红后绿（本 feature 的测试是交付物）。
- `src/freegraph/contracts/graph.py` 的编辑必须**串行**（T004 → T005 → T016 → T017）。
- 同一测试文件的编辑必须**串行**：
  `tests/contracts/test_graph_png.py`（T006 → T007 → T012 → T013 → T014 → T015）；
  `tests/runtime/test_graph_png_offline.py`（T022 → T023）。
- 不同文件的测试任务可并行（标 `[P]`）。

### Parallel Opportunities

- Phase 1：T003 可与其他 Setup 并行。
- Phase 2：T006 与 T004/T005 可在不同文件并行（但 T006 的判据依赖契约，建议 T005 后）。
- US1：T008 / T009 两个不同测试文件可并行；T007 与 T006 同文件 ⇒ **不标 `[P]`**，
  在 T006 之后串行。
- US2：T012 / T013 / T014 / T015 都在同一文件 ⇒ **不可并行**；T016/T017 串行。
- US3：T021（`test_graph_offline.py`）与 T022（`test_graph_png_offline.py`）可并行；
  T022 → T023 同文件串行；T024（差分两文件）可并行。
- Polish：T028/T029（README/G19）串行；T030/T031 可并行；T032/T033/T036 串行
  （验收脚本 → 守卫测试 → 人工记录）；T037/T038/T039 可顺序执行。

---

## Parallel Example: User Story 1

```text
# T007 与 T006 同文件，必须在 T006 之后串行执行；
# T008 / T009 是不同文件，可与 T007 并行：
Task: "T007 [US1] tests/contracts/test_graph_png.py 的离线字节 / TypeError 用例"
Task: "T008 [P] [US1] tests/runtime/test_graph_offline.py 的 PNG socket 守卫 / 环境变量用例"
Task: "T009 [P] [US1] tests/facade/test_get_graph.py 的运行前可用 / xray 用例"
```

## Parallel Example: User Story 3

```text
Task: "T021 [P] [US3] tests/runtime/test_graph_offline.py 静态扫描 / sys.modules 用例"
Task: "T022 [P] [US3] tests/runtime/test_graph_png_offline.py 新建（stream / 并发 / 无文件）"
Task: "T024 [P] [US3] tests/differential/parity_probe.py + test_parity_probe.py 的 PNG 差分"
# T023 与 T022 同文件 ⇒ 在 T022 之后串行，不标 [P]
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1 Setup。
2. 完成 Phase 2 Foundational（PNG 编码器骨架 + 方法）。
3. 完成 Phase 3 US1（离线返回 `bytes`，socket 出站 0）。
4. **STOP and VALIDATE**：跑 US1 的 Independent Test；此时 PNG 可以是纯色占位，
   但必须是合法 PNG（能过 V4/V6 的最小结构）。
5. 若只为 MVP，可暂时不进入 US2/US3；但本 feature 的 A2/A4 要求合法 PNG 与零出站，
   ⇒ 正式交付必须完成 US2 + US3。

### Incremental Delivery

1. Setup + Foundational → 方法可调用。
2. US1 → 离线返回字节（MVP）。
3. US2 → 合法 PNG + 固定示意图标 + 确定性。
4. US3 → 零出站 / G26 / G27 / G28 / 差分。
5. Polish → README / 验收 / 人工记录 / 全量回归。

### Parallel Team Strategy

- 单人：按 T001 → T041 顺序执行；同一文件串行。
- 双人：Foundational 后，A 做 US2 的 `contracts/test_graph_png.py` 与图标；
  B 做 US1 的 offline / facade 测试，随后做 US3 的差分；Polish 合并。
- **MUST NOT** 两人同时编辑 `src/freegraph/contracts/graph.py` 或
  `tests/contracts/test_graph_png.py`。

---

## Notes

- `[P]` = 不同文件、无未完成依赖；同一文件的任务**不得**标 `[P]`。
- 每个 user story 的 Checkpoint 必须独立通过后才进入下一个。
- 测试是本 feature 的交付物；MUST NOT 用 `pytest.skip` 绕过离线 / 结构判据
  （IPython 冒烟除外）。
- **零出站证据必须包含 observe-only 的 G27 归因**；MUST NOT 用「阻断式 socket 夹具」
  替代 G27。
- 不修改 `harness/demo/target.py`；不新增 `pyproject.toml` 依赖 / extras；
  不新增公开顶层符号。
- 新文件首行必须是仓库既有署名头，模块 docstring 为首个语句（G30）。
- 全量回归命令：`.venv/bin/python -m pytest -q tests/`；门禁：G21 / G22 / G23 / G26 /
  G27 / G28 / G29 / G30。
