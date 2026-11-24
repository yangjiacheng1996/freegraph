# Implementation Plan: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Branch**: `b24f1-packaging-compat-matrix`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；当前实际分支为 `main`，既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b24f1-packaging-compat-matrix/spec.md`

**Feature ID**: `B24F1`（M4 生态 · **第 31 个** · 前置：**B23F1 / B16F1**；承接 **B7F4 / B9F1 / B11F1 / B13F1 / B14F1 / B15F1 / B16F1 / B21F1 / B23F1**）

> **范围提醒**：本 feature 是**发行单元**（跨层 · 层 =「—」），**不新增 / 不修改任何运行时语义**。
> `src/freegraph/` **零改动**；只做：① 打包元数据与 extras 收口；② 纯度门禁接入与负向验证；
> ③ **首次落库 `COMPAT.md`**（18 项 + 全量契约 / 门面符号 + 下游承接行）；④ README 与
> `THIRD_PARTY_NOTICES` 定稿；⑤ **兼容矩阵权威源从 README 迁移到 `COMPAT.md`**（已由发起者
> 2026-11-24 选项 A 追认）⇒ 同步更新 G8 / G19 / G29 的取行源（**不新增门禁编号**）。

---

## Summary

把 freegraph 打成**可发布**的 wheel + sdist，交付**唯一权威**的 API 兼容矩阵
`COMPAT.md`、定稿 `THIRD_PARTY_NOTICES` 与 README，并把**发行产物纯度门禁**接入发布流水线、
完成正向与负向验证。基础安装保持**零第三方运行时依赖**；发行元数据**只允许 `[otlp]`** 一个 extra。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **wheel + sdist** | PyPI 发行产物 | 仅含 `src/freegraph/` + 必要元数据；`COMPAT.md` / `THIRD_PARTY_NOTICES` **不进包** |
| **`COMPAT.md`** | **唯一权威**兼容矩阵 | 18 项 + 全量契约 / 门面符号 + 下游承接行 + 证据；`Command` = **部分等价**（`goto` 缺省 = DIFF / Y-01；失败信号 = STRICTER / X-06）；`Send` 不可变 = DIFF（Y-03）/ `NodeFunc` 无上游对应 = 不支持；下游档位按 B15F1 / B16F1 钉死（`get_state` 部分等价 / `get_state_history` 行为等价 / `update_state` 与时间旅行属 v1 能力边界）；`Store` 澄清在「证据与来源」，**不改机读行** |
| **README** | PyPI 落地页 | 中文为主 + 英文关键段落；独立实现声明；三条承诺；**能力 → 处置表**；**绝对链接** `COMPAT.md`；保留 OTLP 三后端（无默认推荐） |
| **`THIRD_PARTY_NOTICES`** | 第三方归属 | `SqliteSaver` MIT 改编 + `[otlp]` 闭包逐包登记 |
| **纯度门禁** | 发布前置机械拦截 | 独立于构建配置；`uv publish` 之前执行；负向用例必失败 |
| **门禁迁移** | G8 / G19 / G29 取行源改为 `COMPAT.md` | 不新增门禁编号；`Command` 恢复「部分等价」加例外；**破冻结面 · 已追认** |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 打包配置 | `pyproject.toml`（验证 `[otlp]` 唯一 extra；sdist `only-include` 已排除 `COMPAT.md` / `THIRD_PARTY_NOTICES`；`.gitignore` 需显式 `exclude` 兜底） |
| 纯度门禁 | `harness/scripts/check_dist_purity.py`（**已存在** · 独立于配置）· `.github/workflows/publish.yml`（**已有** build → purity → publish 顺序） |
| 兼容矩阵 | **新增** `COMPAT.md`（根目录）——机读段 `## API 兼容矩阵` + 18 项表 + 下游承接表 + 证据 |
| 权威源迁移 | `tests/facade/_gatesupport.py` 收敛取行 + 清单解析；`tests/contracts/test_architecture.py`（G8 · 经 `sys.path` 注入复用，与 G29 同法）· `tests/facade/test_facade_gates.py`（G19）· `harness/scripts/gates/gate_G29_contract_carrier.py`（G29）· **`tests/runtime/test_parse_contract.py` 的 README 矩阵读取同步迁到 `COMPAT.md`** |
| G19 基线 | `test_existing_contract_rows_are_unchanged` 的 baseline **改为 `HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退**（都无则 skip）——不能固定 `HEAD:README.md`，否则 README 重写提交后基线为空、CI 必红 |
| `Command` 纠偏 | `COMPAT.md` 的 `Command` 行（迁自 README）第三列恢复 **部分等价**；`goto` 缺省差异标 **DIFF（Y-01）**、失败信号标 **STRICTER（X-06）**；G19 增加 B24F1 定向例外（仅 `Command` 的 `行为等价 → 部分等价`） |
| README | **修改** `README.md`：删完整矩阵 → 能力处置表 + **绝对 GitHub URL** 的 `COMPAT.md` 链接；更新状态说明；补英文关键段落；**保留 OTLP 三后端（OpenLIT / Langfuse / Phoenix，无默认推荐）** 与既有 doc guard 所需字符串 |
| 归属清单 | **修改 / 定稿** `THIRD_PARTY_NOTICES`：核对 `SqliteSaver` / `[otlp]` / v2 extra 说明 |
| 测试 | **新增** `tests/contracts/test_b24f1_*.py` · **新增** `tests/runtime/test_b24f1_manual_record_guard.py` · **修改** `tests/runtime/test_parse_contract.py` · 纯度为临时产物负向用例 |
| 验收 | **新增** `harness/verification/B24F1/acceptance.py`（**T049 顶层编排**）+ `manual-verification.md`（记录 + **自动文档守卫**） |

**关键研究结论（详见 [research.md](./research.md)）**：

1. **门禁已存在，且设计与「`COMPAT.md` 终版」兼容**：G29 的 `--check-compat` 在
   `COMPAT.md` 不存在时报告「未落地」并退出 0；存在时做严格比对。G8 / G19 目前从
   **README** 取行。⇒ 按 A-3 迁移权威源时，**必须同步更新 G8 / G19 / G29 的取行源**，
   否则「README 不再有完整矩阵」会使三门禁永久红。**此外**，`tests/runtime/test_parse_contract.py`
   也直接读 README 矩阵，必须同批迁到 `COMPAT.md`（否则 T033 后必红）。
   **G19 的 baseline MUST NOT 固定为 `HEAD:README.md`**：README 重写提交后基线为空 ⇒
   `assert previous` 失败。应使用 `HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退。
   **README 指针改写 MUST 与 T004 同批**（或另设 T004b 放在 T010 之前）：G8 / G29 在 Phase 2
   就要求「README 无完整矩阵」，若等到 T033 才改，T010 不可能绿。
2. **`Command` 的漂移已被门禁自己记录**：`tests/facade/test_facade_gates.py:464` 的注解
   明写「`Command` = 部分等价」，而 `MATRIX_NEW_EQUIVALENCE` / 当前 README 已变成
   「行为等价」；`test_existing_contract_rows_are_unchanged` 的「MUST NOT 变差」会拦住
   `行为等价 → 部分等价`。⇒ 需一条 **B24F1 定向例外**：只放行 `Command` 的
   `行为等价 → 部分等价`；`Command` **不整体移出**单调检查，其它等级变化 MUST 继续失败，
   并在契约里登记。
   **`goto` 缺省 `()` vs `None` 是成功路径 DIFF（Y-01），不得并入 X-06 的 STRICTER**。
3. **构建产物天然不含仓库文档**：`[tool.hatch.build.targets.wheel] packages = ["src/freegraph"]`
   与 `[tool.hatch.build.targets.sdist] only-include = ["src/freegraph", "README.md", "LICENSE"]`
   已排除 `COMPAT.md` / `THIRD_PARTY_NOTICES` / `harness/` / `.specify/`；**`.gitignore` 由 hatchling
   默认附带，T016 必须显式 `exclude` 并移除脚本允许项**；纯度脚本再做独立断言。
4. **发布流水线已就位**：`.github/workflows/publish.yml` 已是 `uv build` → `Verify artifact purity`
   → `uv publish`；本 feature 只补**负向用例**与**顺序断言**，不改发布通道。
5. **18 项与下游行不能塞进机读段**：G8 / G19 只解析「## API 兼容矩阵」章节内首列为
   `` `标识符` `` 的 4 列行（**G8 现状为 `>=4`，T006 收紧为 `==4`**），且 G19 要求符号集合**恰为**契约层 ∪ 门面层。⇒ 18 项表与
   下游承接行（`MemorySaver` 等）MUST 放在**独立章节**，避免污染机读符号集合。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`，无上限；本机 `.venv` 为 3.11）。

**Primary Dependencies**:
- 基础安装：**零第三方运行时依赖**（`dependencies = []`）。
- 唯一 extra：**`[otlp]`**（`opentelemetry-api` / `opentelemetry-sdk` /
  `opentelemetry-exporter-otlp-proto-grpc`）；其余四个 extra 仍归 v2.0，**不进 v1.0 发行元数据**。
- 开发期：`pytest`（`dev`）；差分：`langgraph==1.2.11`（`differential`）——**不进发行包**。

**Storage**: **N/A**（本 feature 不落盘、不读写运行时状态）。

**Testing**: pytest + 既有门禁脚本 ——
- `tests/contracts/test_architecture.py`（G8 · 改读 `COMPAT.md`）
- `tests/facade/test_facade_gates.py`（G19 · 改读 `COMPAT.md` + B24F1 `Command` 例外 + `HEAD:COMPAT.md` 基线）
- `tests/runtime/test_parse_contract.py`（**修改**：README 矩阵读取迁到 `COMPAT.md`）
- `tests/facade/test_compiled_graph.py`（**保留** README 的 `Store` / `MemorySaver` 既有 doc guard 字符串）
- `harness/scripts/gates/gate_G29_contract_carrier.py --check-compat`（权威源校验）
- `harness/scripts/check_dist_purity.py`（正向 + 负向）
- **新增** `tests/contracts/test_b24f1_packaging.py`（基础元数据 / py.typed）
- **新增** `tests/contracts/test_b24f1_otlp_meta.py`（`[otlp]` 元数据 / 禁用包）
- **新增** `tests/contracts/test_b24f1_purity.py`（正向合成产物）
- **新增** `tests/contracts/test_b24f1_purity_negative.py`（负向合成产物）
- **新增** `tests/contracts/test_b24f1_publish_order.py`（publish.yml 顺序）
- **新增** `tests/contracts/test_b24f1_compat.py`（18 项 / 下游行 / 证据 / 唯一权威）
- **新增** `tests/contracts/test_b24f1_docs.py`（README 状态 / 双语 / 5 列能力表 / 商标扫描）
- **新增** `tests/contracts/test_b24f1_notices.py`（`THIRD_PARTY_NOTICES` 必需条目 + affiliation）
- **新增** `tests/differential/test_b24f1_matrix_parity.py`（**宪法原则 XI 最小差分组 B24F1-D-01…D-03**：`Command.goto` 缺省 / `Send` 不可变 / `get_state` 无快照；上游缺席 skip，不改运行时）
- **新增** `tests/runtime/test_b24f1_manual_record_guard.py`（**SC-008 自动文档守卫**：记录存在 / 五段式 / 实测输出 / 非空 / 追认 / Y-01、Y-02、Y-03 遗留项）
- **修改** `tests/runtime/test_acceptance_script.py`（追加 B24F1 一键验收守卫；`exit 2` 时 skip）

**Target Platform**: Linux / macOS / Windows · CPython 3.11+；本 feature 无平台专属逻辑。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A**（纯文档 / 打包 / 门禁接线；不设墙钟预算）。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| wheel + sdist；基础依赖为空；`[otlp]` 为唯一 extra | FR-001 · SC-005 |
| 产物仅含包代码 + 必要元数据；`COMPAT.md` / `THIRD_PARTY_NOTICES` 不进包 | FR-002 |
| 纯度脚本独立于构建配置；上传前执行；失败即中止 | FR-003 · FR-010 · SC-003 |
| `COMPAT.md` 为唯一权威；覆盖 18 项 + 全量符号（并集 27 = 契约层 22 ∪ 门面层 8）+ 下游行；`Command` = 部分等价；`goto` 缺省 = DIFF（Y-01）、失败信号 = STRICTER（X-06）；`Send` 不可变 = DIFF（Y-03）；`get_state` = 部分等价（Y-02）；`update_state` / 时间旅行 = v1 能力边界 | FR-004 · FR-012 · SC-004 |
| `THIRD_PARTY_NOTICES` 登记引入代码与 `[otlp]` 闭包 | FR-005 · SC-004 |
| README：中文为主 + 英文关键段；独立实现声明；三条承诺；能力表；状态修正；OTLP 三后端（无默认推荐）；`COMPAT.md` **绝对链接** | FR-006 / FR-007 · SC-007 |
| `py.typed`；无第三方品牌资产；纯文字产品名允许 | FR-008 · SC-007 |
| `requires-python = ">=3.11"` 且不设上限 | FR-009 |
| 隔离安装 / `[otlp]` 安装且无 `certifi` 等 | FR-011 · SC-001 / SC-006 |
| 许可证白名单；`protobuf` 具名归一；MIT 保持 | FR-013 · SC-005 |
| 人工验收记录 | FR-014 · SC-008 |
| 新 `.py` MUST 带署名头（G30 扫描全部 tracked `.py`） | 原则 X |
| acceptance 脚本跨平台（Windows / macOS / Linux） | 原则 V · SC-001 / SC-008 |
| 证据可追溯；不回退既有门禁例外；门禁编号零新增 | FR-015 / FR-016 / FR-019 |

> **无未决澄清**：spec 的 Clarifications（8 条）已收敛全部功能决策；本 plan 只落实现方法、
> 门禁迁移、证据与验收。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 本 feature 不新增运行时；`[otlp]` 默认关闭；G24 / G26 / G27 判据不变 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | `src/freegraph/` 零改动；`langgraph` 仅测试侧 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` 零改动；G29 只读基准判据不变 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 矩阵记录 PNG 占位语义；不改运行时 | 通过 |
| 原则 V（人工验收） | `harness/verification/B24F1/manual-verification.md`（含实测输出） | 计划交付；**质量门禁 5 真实模型轮 → B25F1 承接**（见「质量门禁偏离」） |
| 原则 VI（规格驱动 · 判据级覆盖） | 19 FR / 8 SC；新增**人工记录文档守卫**（SC-008）与负向测试；tasks 双向追溯 | 通过（T042 守卫 + 正向表补齐） |
| 原则 VII（职责边界 · 不扩内核） | 无新增契约 / 运行时符号 | 通过 |
| 原则 VIII（证据与术语） | 每条矩阵行可追溯到 Q3 §3.4 / 上游 `路径:行号` / feature 实测；D3 按「已决 2026-11-05」表述 | 通过 |
| 原则 IX（许可证 / 商标） | LICENSE 保持 MIT（D3 已决）；`[otlp]` 闭包白名单；`protobuf` 具名归一；无品牌资产 | 通过 |
| 原则 X（文档合规 / 署名头） | `COMPAT.md` / `THIRD_PARTY_NOTICES` / README；新 `.py` 带署名头 | 通过 |
| 原则 XI（上游优先） | 不改运行时；`Command` 纠偏回到 B9F1 定稿值；X-06 = STRICTER（失败面）；**Y-01 / Y-02 / Y-03 = 既有 DIFF（成功路径 · 只登记）**；`update_state` 无 `task_id` / 时间旅行线性重放 = v1 能力边界（非「更严」）；三态逐项一致；**新增最小差分组 `B24F1-D-01…D-03`（T050）** | 通过（**本 feature 零运行时改动**；Y-01/Y-02/Y-03 为既有偏差，已如实登记且不改写为 STRICTER；**Y-01 具名承接 B25F1（M4）**，Y-02/Y-03 只登记；运行时对齐归 v2 契约修订；**差分组只断言既有差异，不要求对齐运行时**） |
| 原则 XII（最优设计 · 零重复载体） | **单一权威** `COMPAT.md`；README 不维护第二份完整矩阵 | 通过 |
| 立项书 ARCH-1 / ARCH-2 / ARCH-3 | 无跨层 import / 顶层惰性 / 运行时语义变更 | 通过（零改动） |
| **发布门禁（Release Gate）** | `check_dist_purity.py` + `publish.yml` 的「build → purity → publish」 | 通过（接线 + 负向） |
| **G8（文档合规门禁）** | 取行源 **README → `COMPAT.md`**；`COMPAT.md` 唯一权威 | **破冻结面 · 已追认（选项 A）** |
| **G19（门面矩阵覆盖）** | 取行源 **README → `COMPAT.md`**；`Command` 恢复「部分等价」加 B24F1 定向例外 | **破冻结面 · 已追认（选项 A）** |
| **G29 `--check-compat`（分层判定）** | 由「COMPAT vs README」改为「COMPAT 为权威 + README 仅指针」 | **破冻结面 · 已追认（选项 A）** |
| **门禁编号零新增** | 只更新既有 G8 / G19 / G29 的**取行源**与已登记例外；不新增编号、不放宽判据 | 通过（FR-019） |

### 破冻结面 / 回溯修订清单

> **依据**：用户 2026-11-24 在 clarify 后明确选择 **A**（`COMPAT.md` 唯一权威；README 只留
> 能力表 + 链接；同步改写 G8 / G19 / G29）。⇒ 本清单是**已获追认**的破冻结面登记；
> 正式追认文字 MUST 落 `harness/verification/B24F1/manual-verification.md`。

| 冻结面 | 回溯修订位置 | 处置 | 追认 |
|---|---|---|---|
| **G8** 从 README 取行 | `tests/contracts/test_architecture.py` · `specs/b2f1-contracts-protocols/contracts/architecture-gates.md` §G8 · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览 | 取行源改为 `COMPAT.md`；新增「README 只能有指针、不得有完整矩阵」断言；**判据强度不降**（仍逐符号覆盖 + 4 列 + 无重复 + affiliation） | 2026-11-24 · 选项 A |
| **G19** 从 README 取行 + 禁止降级 | `tests/facade/test_facade_gates.py` · `_gatesupport.py` · `specs/b2f2-public-api-facade/contracts/architecture-gates.md` §G19 · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览 | 取行源改为 `COMPAT.md`；与 G8 共用取行实现；**新增 B24F1 定向例外**：仅 `Command` 允许「行为等价 → 部分等价」的**纠漂移**（不是产品降级，是恢复 B9F1 定稿值）；`Command` **不整体移出**单调检查，其它任何等级变化（含 `部分等价 → 不支持`）MUST 失败；baseline 改为 `HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退（都无则 skip） | 2026-11-24 · 选项 A |
| **其他 README 矩阵消费者** | `tests/runtime/test_parse_contract.py` | 同步改为读 `COMPAT.md` 机读段；否则 README 重写后该测试必红 | 2026-11-24 · 选项 A（同一 authorized 迁移） |
| **G29 `--check-compat`** | `harness/scripts/gates/gate_G29_contract_carrier.py` · `architecture-gates.md` §G29 判定 4 | 由「COMPAT.md 与 README 逐格比对」改为「COMPAT.md 为权威 + 校验其覆盖契约 / 门面清单 + README 链接且无完整矩阵」；**仍复用** `_gatesupport` 的取行实现（不重复实现） | 2026-11-24 · 选项 A |
| **spec §破冻结面表** | `spec.md` 的「破冻结面的回溯修订清单」 | 已由「无新增破面」**更新**为上列 G8 / G19 / G29 三项（**已回写** · 2026-11-24 · 本 plan 生成时） | 2026-11-24 · 选项 A |
| **不破** | `src/freegraph/**` 运行时 · `harness/demo/target.py` · 契约层 / 门面符号面 · `pyproject.toml` 的 `dependencies` / `[otlp]` · 既有 G21 / G23 / G26 / G30 判据 | 零改动 | — |

> **实测义务（宪法 v1.9.0 / v1.11.0）**：T002 / T010 MUST 在临时副本中按本 feature 的落地形态改动
> `COMPAT.md` / README / 门禁取行源，跑既有测试套件，记录**变红的断言清单**（逐条 `文件:行号` +
> 变红原因），并落 `manual-verification.md` 附录。至少覆盖 G8 / G19（含 `Command` 定向例外
> ——仅 `行为等价 → 部分等价` 放行、其它等级变化失败——与 `Send` 降级负向自检）/
> `test_parse_contract.py` / `gate_G29_contract_carrier.py --check-compat`。

> **上位文档同步（T048 · 非破冻结面）**：立项书 §6.2.1 第 6 条与 D7 的注记已在本轮分析修复中
> 同步为：**能力处置表仍在 README**（D7），**逐符号 API 兼容矩阵位于 `COMPAT.md`**；
> T048 负责实现期复核（若漂移则修正）。该同步不改变任何门禁判据，也不新增门禁编号。

### Complexity Tracking

| 复杂点 | 为何需要 | 更简单的替代为何不可行 |
|---|---|---|
| 改 G8 / G19 / G29 取行源 | 你已拍板 `COMPAT.md` 唯一权威、README 不留完整矩阵（A-3） | 保留 README 完整矩阵（方案 B）会直接违背 A-3；让 README 自动生成完整矩阵（方案 C）仍保留第二份完整矩阵 |
| `Command` 从「行为等价」改回「部分等价」 | 上游实测 `Command().goto == ()` vs `None`（**成功路径 DIFF · Y-01**）+ B9F1 parity 的 X-1 / X-4（**STRICTER · X-06**）；G19 注解本身写明应为部分等价 | 不回改则矩阵与上游事实、B9F1 定稿、G19 自身注解三处冲突；且属于原则 X 的「清单过期」 |
| 18 项 / 下游行放独立章节 | G8 / G19 的机读段只接受契约层 ∪ 门面层符号，多一行即失败 | 塞进同一表格会使 G19 的「整表恰为两层」判据失败；放宽 G19 反而削弱门禁 |
| **文档 / 发行 feature 的最小差分组** | 宪法原则 XI 要求每个 feature 交付一组差分场景，而本 feature 零运行时改动 | 不新增运行时能力时，用 `B24F1-D-01…D-03` 对**矩阵所陈述的既有差异**做「上游 ↔ freegraph」对跑；只断言既有差异，不要求对齐运行时 |
| 纯度负向用合成产物 | 避免在单元测试里 `uv build`（慢 / 依赖工具链），同时保证「混入仓库文件必失败」可判定 | 只靠 CI 的真实构建无法在本地快速回归；只测正向无法证明门禁「有效」 |
| 质量门禁 5 偏离（真实模型轮 → B25F1） | B24F1 不交付 MVP 双跑轮；真实模型轮是 B25F1 的 MVP 判据（SC-001 / A2） | 在本 feature 硬跑真实模型会引入 provider 依赖与成本，且与 B25F1 的双跑验收重复；按 v1.6.0「按里程碑不交付其前置能力」登记偏离 + 具名承接 B25F1 即可 |
| README 指针改写前移到 Phase 2 | G8 / G29 在 T006 / T008 新增「README 无完整矩阵」断言，而 T033 在 Phase 7 | 若不在 T004 一并把 README 改为指针，T010「迁源后全绿」不可能成立，T004–T010 原子提交会写红 CI |
| **`uv build` 的 `dist/.gitignore`** | 与旧规则「`dist/` 内任何非 `.whl` / `.tar.gz` 文件 ⇒ 失败」直接冲突 | 显式豁免该构建工具标记；「额外产物」只针对归档类文件（`.zip` / `.tar` / `.tgz` / `.tar.bz2`） |
| **US1 / US3 的构建产物** | T013 / T014 / T022 需要真实 wheel / sdist，但只有 T018 执行 `uv build` | 在 Setup 增加构建产物，或让 T013 / T014 / T022 各自 `uv build` 到临时目录；不假设 US2 已先完成 |

### 质量门禁偏离（2026-11-24 · 沿用 B19F1 / B20F1 / B20F2 / B21F1 先例 · 已追认）

> 依据宪法「质量门禁的分阶段落地与发起者追认」（v1.6.0）。本偏离**不降低**任何红线判据；
> 正式追认文字 MUST 落 `harness/verification/B24F1/manual-verification.md`。

| 项 | 内容 |
|---|---|
| 被偏离门禁 | **质量门禁 5**「人工验证记录，含真实模型一轮」 |
| 根因 | B24F1 是**发行 / 文档单元**（跨层 · 不新增运行时行为），**不交付 MVP 双跑轮**；真实模型轮是 **B25F1（M4）的 MVP 判据**（B25F1 SC-001 / A2），B24F1 无对应的运行期判据 ⇒ 按 v1.6.0「按里程碑不交付其前置能力」的同类处置，登记偏离并具名承接 **B25F1**。先例：B19F1 / B20F1 / B20F2 / B21F1 已按同一口径追认；本偏离**不降低**任何红线判据。 |
| 判据未放宽 | 本 feature 的人工记录仍按原则 V 五段式、含**实际输出**；文档守卫 T042 照常；质量门禁 1–4 / 6–7 照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收与迁移说明）**：fake / 真实模型两轮覆盖 B24F1 的发行产物与 `COMPAT.md` 声明；承接条款 MUST 写入 `harness/features/B25F1_双跑验收与迁移说明.md` 的「下游承接（B24F1）」（**已在本轮分析修复中接线；T047 复核**）。 |
| 追认 | **已由发起者于 2026-11-24 确认**（B24F1 analyse 轮）；文字落 `harness/verification/B24F1/manual-verification.md`。 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b24f1-packaging-compat-matrix/
├── plan.md                          # 本文件
├── research.md                      # Phase 0：决策与证据
├── data-model.md                    # Phase 1：实体 / 校验规则
├── quickstart.md                    # Phase 1：可执行验收手册
├── contracts/
│   ├── compat-matrix-contract.md    # COMPAT.md 结构 / 行格式 / 18 项 / 下游行
│   ├── gate-migration-contract.md   # G8 / G19 / G29 迁移 + Command 例外
│   ├── packaging-purity-contract.md # wheel / sdist / 纯度 / 发布顺序
│   └── docs-compliance-contract.md  # README / NOTICES / 商标 / 双语
└── checklists/requirements.md       # /speckit.specify 产出（已存在）
```

### Source Code / Repository Layout

```text
COMPAT.md                            # 新增（唯一权威兼容矩阵）
README.md                            # 修改（能力表 + 绝对链接；删完整矩阵；状态修正；保留 OTLP 三后端）
THIRD_PARTY_NOTICES                  # 修改 / 定稿
pyproject.toml                       # 验证 / 可选显式 exclude（不改依赖面）

harness/
├── scripts/
│   ├── check_dist_purity.py         # 已存在；本 feature 验证 + 负向
│   └── gates/
│       └── gate_G29_contract_carrier.py   # 更新 --check-compat
└── verification/
    └── B24F1/
        ├── acceptance.py            # 新增
        └── manual-verification.md   # 新增

tests/
├── contracts/
│   ├── test_architecture.py         # G8：改读 COMPAT.md
│   ├── test_b24f1_compat.py         # 新增：18 项 / 下游行 / 证据
│   ├── test_b24f1_packaging.py      # 新增：基础元数据 / py.typed
│   ├── test_b24f1_otlp_meta.py      # 新增：[otlp] 元数据 / 禁用包
│   ├── test_b24f1_purity.py         # 新增：正向合成产物
│   ├── test_b24f1_purity_negative.py # 新增：负向合成产物
│   ├── test_b24f1_publish_order.py  # 新增：publish.yml 顺序
│   ├── test_b24f1_docs.py           # 新增：README / 双语 / 状态 / 5 列能力表
│   └── test_b24f1_notices.py        # 新增：归属清单 + affiliation
├── facade/
│   ├── _gatesupport.py              # 收敛取行 + 清单解析
│   └── test_facade_gates.py         # G19：改读 COMPAT.md + Command 例外
├── differential/
│   └── test_b24f1_matrix_parity.py  # 新增：B24F1-D-01…D-03（原则 XI 最小差分组；上游缺席 skip）
└── runtime/
    ├── test_acceptance_script.py    # 追加 B24F1 一键验收守卫（exit 2 ⇒ skip）
    ├── test_b24f1_manual_record_guard.py  # 新增：SC-008 自动文档守卫
    └── test_parse_contract.py       # 修改：README 矩阵读取迁到 COMPAT.md

specs/b2f1-contracts-protocols/contracts/architecture-gates.md  # 回溯修订 G8
specs/b2f2-public-api-facade/contracts/architecture-gates.md    # 回溯修订 G19
specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md    # 总览 + G29
.github/workflows/publish.yml        # 验证（不预期改动）
```

**Structure Decision**：单项目 / 库布局（沿用既有仓库结构）。本 feature **不新增 `src/` 文件**；
新增的是根目录文档、测试与门禁适配。

---

## Phase 0 · Research（摘要）

完整决策与证据见 [research.md](./research.md)。核心结论：

| 决策 | 结论 |
|---|---|
| **D-01 权威源** | `COMPAT.md` 唯一权威；README 只留「能力 → 处置」表 + 链接；G8 / G19 / G29 迁移（选项 A · 已追认） |
| **D-02 Command** | 恢复 **部分等价**；G19 增加 B24F1 定向例外；依据上游实测 + B9F1 parity + G19 自身注解 |
| **D-03 打包** | 沿用 hatchling；wheel `packages=["src/freegraph"]`；sdist `only-include` 已排除仓库文档；可加显式 `exclude` 兜底；**hatchling 会强制把根 `.gitignore` 加入 sdist（VCS 忽略文件）⇒ 用 sdist-only 构建钩子 `harness/build_hooks/sdist_prune.py` 在 `finalize` 移除** |
| **D-04 纯度** | 脚本已独立于配置；发布流水线顺序已正确；补负向（合成产物）与顺序断言；**补 wheel `METADATA` extras 检查 + 收紧 wheel 根级前缀（T045）**；METADATA 检查**只用标准库**解析 `Provides-Extra` / `Requires-Dist`（**MUST NOT import `packaging`**） |
| **D-05 依赖 / 许可证** | 基础零依赖；`[otlp]` 唯一 extra；`protobuf` 具名归一既有；无 MPL / ELv2 |
| **D-06 README** | 能力表取自立项书 §3.2；中文为主 + 英文关键段；状态说明修正；链接 COMPAT.md |
| **D-07 NOTICES** | 定稿：`SqliteSaver` MIT 改编 + `[otlp]` 闭包；dev / differential 不登记 |
| **D-08 COMPAT 结构** | 机读段（契约 ∪ 门面）+ 18 项表 + 下游表 + 证据段；三段分离 |
| **D-09 证据** | 每行可追溯 Q3 §3.4 / 上游 `路径:行号` / feature 实测 |
| **D-10 负向** | 用 `zipfile` / `tarfile` 合成产物，注入 `harness/` 文件，断言退出码 1 |

**无 `[NEEDS CLARIFICATION]`**。

---

## Phase 1 · Design & Contracts

已生成：

- [data-model.md](./data-model.md) —— 发行产物 / 兼容矩阵行 / 归属条目 / 能力处置 / 纯度结果 / 负向用例。
- [contracts/compat-matrix-contract.md](./contracts/compat-matrix-contract.md) —— `COMPAT.md` 六段结构、
  机读段行格式、18 项、下游行、证据与维护规则。
- [contracts/gate-migration-contract.md](./contracts/gate-migration-contract.md) —— G8 / G19 / G29
  的新取行源、`Command` 例外、README 指针断言、追认与回溯修订。
- [contracts/packaging-purity-contract.md](./contracts/packaging-purity-contract.md) —— wheel / sdist
  允许与禁止内容、`[otlp]`、发布流水线顺序、负向用例。
- [contracts/docs-compliance-contract.md](./contracts/docs-compliance-contract.md) —— README 结构 /
  双语 / 状态 / 能力表、`THIRD_PARTY_NOTICES`、商标与 nominative use。
- [quickstart.md](./quickstart.md) —— 构建、纯度正 / 负向、隔离安装、`[otlp]` 安装、矩阵与门禁核对。

---

## Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| `COMPAT.md` 机读段符号集合 == 契约层 ∪ 门面层（与 G8 / G19 同源） | 计划验证（G8 / G19 迁源后） |
| 所有 README 矩阵消费者（G8 / G19 / G29 / `test_parse_contract.py`）均迁到 `COMPAT.md` | 计划验证（新增迁移断言 + 全量 pytest） |
| README 无完整矩阵、含**绝对 GitHub URL** 的 `COMPAT.md` 链接、能力表、OTLP 三后端 | 计划验证（新增 docs 守卫 + 既有 B21F1 守卫） |
| 18 项 + 下游承接行全部存在且每行有证据 | 计划验证（新增 `test_b24f1_compat.py`） |
| 宪法原则 XI 的最小差分组 `B24F1-D-01…D-03` 可执行且上游缺席 skip | 计划验证（新增 `tests/differential/test_b24f1_matrix_parity.py` · T050） |
| `Command` = 部分等价；`goto` 缺省 = DIFF（Y-01）、失败信号 = STRICTER（X-06）；`Send` 不可变 = DIFF（Y-03）；`get_state` = 部分等价（Y-02） | 计划验证（G19 **定向例外** + 新增断言） |
| H-4 `StateGraph` 行含 `recursion_limit`；H-9 / FR-018 `Graph` 行含 v2 `[png]`；H-3 `Send` 行措辞 + **`Send` 类型定义住 L1** | 计划验证（T004 写入 + T027 断言） |
| 下游 `CompiledGraph.get_state` = 部分等价（含 Y-02）、`CompiledGraph.get_state_history` = 行为等价；`CompiledGraph` 机读行亦含 Y-02 / v1 能力边界；`Store` 澄清在「证据与来源」且机读行逐字不改 | 计划验证（T025 / T027；**Store 由 T027 的专用 baseline 断言核验，不依赖 G19 白名单**） |
| SC-008 人工记录由自动文档守卫判定（存在 / 五段式 / 实测输出 / 非空） | 计划验证（新增 `test_b24f1_manual_record_guard.py`，排在 **T046 → T039 → T047** 之后） |
| G19 baseline 用 `HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退 | 计划验证（迁移后重跑 + README 重写提交后重跑） |
| 基础依赖为空；`[otlp]` 为唯一 extra；`protobuf` 归一不变 | 计划验证（G21 / G23 `--project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` + packaging 测试） |
| wheel `METADATA` 只含 `[otlp]` extra；`[otlp]` 闭包无 `certifi` / HTTP exporter / 元包 | 计划验证（T045 + `test_b24f1_purity_negative.py`） |
| wheel / sdist 不含 `COMPAT.md` / `THIRD_PARTY_NOTICES` / `harness/` 等 | 计划验证（纯度脚本 + packaging 测试） |
| 发布流水线「build → purity → publish」顺序 | 计划验证（工作流顺序断言） |
| `src/freegraph/` 零改动；`target.py` 零改动 | 计划验证（git diff + G29） |
| 新 `.py` 全部带署名头；无第三方品牌资产 | 计划验证（G30；新增测试文件逐个覆盖） |
| 零出站 / 隔离环境 / 断网等价 | 计划验证（G22 / G27 / G28 · **Linux 专属**；非 Linux 由 CI 对应作业覆盖） |
| G8 / G19 / G29 迁移不新增门禁编号 | 计划验证（FR-019 + 契约回溯修订） |
| G24 / G25 不回退（B19F1 的 L5 import 例外） | 计划验证（T036 增加 G24 / G25；CI Linux 作业亦跑） |
| 验收脚本由顶层编排统一输出 `B24F1 acceptance: PASS` | 计划验证（T049 依赖 T013 / T014 / T018 / T022 / T030 / T034；T040 依赖 T049） |
| B25F1 提示词含「下游承接（B24F1）」且覆盖真实模型轮 + Y-01；B24F1 记录覆盖 Y-01 / Y-02 / Y-03 | 计划验证（T047 + T042 守卫） |
| 立项书 §6.2.1 第 6 条与 D7 的 COMPAT / README 分工已同步 | 计划验证（T048；不改判据） |
| `uv build` 生成的 `dist/.gitignore` 不被判为额外产物；负向 `evil.zip` 仍失败 | 计划验证（T018 / T020 / T045；归档类判定 + `.gitignore` 豁免） |
| US1 / US3 在无预构建 `dist/` 时可自行 `uv build`（不假设 US2 先完成） | 计划验证（T013 / T014 / T022 + Dependencies） |

---

## 后续

- **/speckit.tasks**：把本 plan 拆成可勾选任务（含 G8 / G19 / G29 迁移、`test_parse_contract`
  迁移、README 指针前移、18 项 / 下游行落库、H-4/H-9 措辞、负向纯度、README 重写、
  NOTICES 定稿、人工验收 + **人工记录守卫**；另含 **T047 B25F1 承接接线**、
  **T048 立项书 §6.2.1 / D7 复核**、**T049 acceptance 顶层编排**、
  **T050 宪法原则 XI 最小差分组 `B24F1-D-01…D-03`**）。
- **B25F1**：双跑验收 + 迁移说明 + 文档最终收口（本 feature 只交付发布基线）；
  **承接 B24F1 的质量门禁 5 真实模型轮与 Y-01 文档记录**（已由 T047 写入其提示词初稿）。
