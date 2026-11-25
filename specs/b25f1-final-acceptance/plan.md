# Implementation Plan: B25F1 · 双跑验收（fake CI + 真实模型人工）+ 迁移说明 + README 收口

**Branch**: `b25f1-final-acceptance`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_plan` 钩子；当前实际分支为 `main`，既有 feature 同样在 `main` 上开发）

**Date**: 2026-11-25 | **Status**: Completed / Accepted（2026-11-26） | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b25f1-final-acceptance/spec.md`

**Feature ID**: `B25F1`（M4 生态 · **第 32 个** · 前置：**B24F1**；承接 **B8F1 / B23F1 / B20F1 / B20F2 / B21F1 / B15F1 / B14F1 / B16F1 / B24F1 / B5F2 / B7F1**）

> **范围提醒**：本 feature 是**交付 / 验收单元**（跨层 · 层 =「—」），**不新增运行时能力**、
> **不新增契约条目**、**不新增门禁编号**。`src/freegraph/` **零改动**；`harness/demo/target.py`
> **零改动**（只读基准，双重基线）。本 feature 只交付：
> ① fake 注入 + **CI fake 轮验收**；② 真实模型人工轮的两段式探针与证据；
> ③ 只观测不阻断的零出站监测与断网等价性；④ `harness/demo/diagnostics.py`；
> ⑤ 《人工验收记录》；⑥ 迁移说明与最终 README。

---

## Summary

让固定脚本 `harness/demo/target.py` **原样**跑通两轮：**fake 轮（CI）** 与 **真实模型轮（人工）**，
并交付可复核的证据、迁移说明与最终 README。判定：**双跑通过；框架零出站断言通过**。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **fake 注入** | 测试 / 验收层的 `FakeModel` + `init_chat_model` 猴补 | 固定 2 轮序列（tool_call → 文本答案）；**不改 `target.py`**；与路由函数**正交** |
| **固定断言点** | `messages == 4` · `llm_calls == 2` · 工具结果 `== 7`（归一为 int）· 完整状态含两键 | `SystemMessage` **不进状态**（简报的「3」是三点投影；上游已定） |
| **零出站夹具** | 只观测不阻断 + 按发起方归因 | **框架出站 == 0**；用户出站**逐条记录、不判失败、不设目标白名单**（通用型图框架） |
| **断网等价性** | 进程内 socket 禁用（必做）+ OS 级 `unshare --net`（条件增强） | 复用既有 **G28** 的 Linux 网络命名空间能力；不新增门禁编号 |
| **`diagnostics.py`** | trace / checkpoint / 时间旅行验收 | 只用 `freegraph` + 标准库；纳入 `harness/demo/acceptance.py` 编排 |
| **一键验收** | `harness/verification/B25F1/acceptance.py` | `0 = PASS` / `1 = 断言失败` / `2 = 环境未就绪` |
| **真实轮探针** | 固定脚本段 + 专用探针段（两段式） | `FileTraceStore` / `SqliteTraceStore` / `OtlpExporter` / `SqliteSaver` / 时间旅行；**B14F1 记录 + `harness/verification/B14F1/acceptance.py` 纳入发布前人工验收清单** |
| **人工验收记录** | `harness/verification/B25F1/manual-verification.md` | 五要素 + 三附件；实际输出非空；环境偏离须写明范围 |
| **迁移说明** | `harness/proposals/更名与迁移说明.md` 的 v1 章节 | 同名可用 / 同名有差异 / 需改写；保留 **Y-01** |
| **最终 README** | 快速上手 + 三条承诺 + 能力处置表 + 独立实现声明 | `COMPAT.md` **绝对链接**；**不复制**完整矩阵 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| fake 注入 | `harness/verification/B25F1/fake_model.py`（`FakeModel` + `install()`）· `tests/runtime/conftest.py`（**仅 B25F1 用例启用**的 fixture）· `tests/runtime/test_b25f1_target_fake.py` |
| 外部注入等价 | `harness/verification/B25F1/fake_round.py` 生成临时 `sitecustomize.py` + 子进程跑 `target.py`（证明「不改进程也能注入」） |
| 固定脚本防御 | `tests/runtime/test_b25f1_target_guard.py` + `tests/runtime/data/b25f1_target_py.sha256`（SHA-256）+ 基线 ref `git diff` |
| 零出站 | 复用 `harness/scripts/gates/_gatekit.py` 的「第一个非标准库帧」归因（G27 权威口径）；`harness/demo/acceptance.py` 的内联 `EgressProbe` 对齐同一规则（仍只用标准库） |
| 验收编排 | `harness/demo/acceptance.py`（新增 `diagnostics` 组、target fake 组、清理 `LANGSMITH_*`、记录模板更新） |
| 诊断脚本 | **新增** `harness/demo/diagnostics.py`（trace / checkpoint / 时间旅行；`freegraph` + 标准库） |
| 真实轮 | **新增** `harness/verification/B25F1/real_round.py`（两段式；默认 `exporter=` 记录型 exporter，可选 `endpoint=` 本地 gRPC 接收端） |
| 一键验收 | **新增** `harness/verification/B25F1/acceptance.py`（A1/A3/A4/A5 自动；A2 由 `--real` 或人工记录守卫覆盖） |
| 差分 | **新增** `tests/differential/test_b25f1_final_acceptance.py`（`B25F1-D-01…D-03`；D-04 落入 model factory 测试）· **新增** `tests/differential/_b25f1_model_factory.py` · **修改** `tests/differential/spec_builder.py`（**新增** `build_model_graph_spec`，不改 B5F2 纯本地拒绝语义） |
| CI | `pyproject.toml` 新增 **`acceptance`** 依赖组（`langchain` / `IPython`）· `.github/workflows/ci.yml` 在 **Linux x86 全量档（`ubuntu-24.04` 3.11/3.14）**新增安装步与 B25F1 验收步（同一 `if:`；**不改 job 名**） |
| 文档 | `README.md` 最终收口 · `harness/demo/README.md` 标记 diagnostics 已交付 · `harness/proposals/更名与迁移说明.md` 新增 v1 迁移章节 |

**关键研究结论（详见 [research.md](./research.md)）**：

1. **`target.py` 的最终 `messages` 长度 = 4**（Human → AI(tool_call) → ToolMessage → AI 最终答案）；
   `SystemMessage` 只进入模型输入、**不进入状态**（`MessagesState.messages` 用 `operator.add`）。
   ⇒ 简报 / **立项书 §4.2 S4 / §9.2** 的「3（System + AI + Tool）」是三点投影，**不得**作为长度断言；
   立项书已事实性更正为 **4**（2026-11-25 发起者确认）。
2. **fake 注入必须发生在 `target.py` 导入期之前**：脚本在 `target.py:23` 解析
   `from langchain.chat_models import init_chat_model`，`target.py:26-29` 立即调用。
   ⇒ 同进程用 `runpy.run_path()` 前先猴补；子进程用临时 `sitecustomize.py`。
3. **零出站归因以 G27 为权威**：`_gatekit` 的「第一个非标准库帧」规则（裁定 19）
   比「栈里出现 `freegraph`」更准确，可避免用户节点经框架调用被误判为框架出站。
   ⇒ B25F1 新探针复用 `_gatekit`；demo 内联实现**对齐同一规则**，仍只用标准库。
4. **断网等价性已有 OS 级载体**：CI 的 G28 已在 `unshare --net --map-root-user` 下跑全量
   `tests/`。B25F1 只需补**进程内层**，并确保新测试在断网下可跑；真实模型轮是**人工脚本**，
   **不进入** `tests/`（避免 G28 / G27 误伤）。
5. **B5F2 的模型工厂钩子只能「新增入口」而不能「放宽旧入口」**：`spec_builder.py:128-131`
   与 `test_differential.py:111-119` 明确「纯本地规格的 `model_factory` 非空 ⇒ 显式失败」。
   ⇒ B25F1 新增 `build_model_graph_spec(...)`（显式 `model_factory=`）承载**模型形状**规格；
   **不改** `build_graph_spec` 的纯本地拒绝语义，B5F2 的既有测试仍绿。
6. **CI 依赖组**：`target.py` 自带 `langchain.*`，fake 轮需要 `langchain` 与 `IPython`。
   ⇒ 新增 **`acceptance`** 依赖组（PEP 735，不进 `Requires-Dist`）；只在 **Linux x86 全量档（`ubuntu-24.04` 3.11/3.14）**安装，
   其余档 `importorskip` ⇒ skip（非失败）。G21 / G23 只扫描发行依赖，不受影响。
7. **`target.py` 双重基线**：SHA-256 作为内容真值（离线可判）；`origin/main` diff 作为历史真值。
   CI 的 `actions/checkout` 需 `fetch-depth: 0`；浅克隆 / 无基线 ref 时**显式跳过并登记环境偏离**，
   保留 SHA-256 断言，**MUST NOT** 静默通过。
8. **真实轮两段式**：固定脚本段（A2 / 零出站 / PNG）与专用探针段（trace / OTLP / checkpoint /
   时间旅行）分离；后者复用 `B15F1 / B16F1 / B20F1 / B20F2 / B21F1` 已验证的 API 形态与
   一键验收脚本的构造方式，但**不替代**它们的一键验收。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（与 `requires-python` 一致；本机 `.venv` 为 3.11）。

**Primary Dependencies**:
- 运行时：**零第三方依赖**（`dependencies = []`；本 feature 不改）。
- 唯一 extra：`[otlp]`（本 feature 只在真实轮探针中使用，**不改元数据**）。
- 测试 / 验收（**不进发行包**）：
  - `dev`：`pytest` / `packaging`（既有）。
  - `differential`：`langgraph==1.2.11`（既有）。
  - **新增 `acceptance`**：`langchain`（v1，固定脚本自身依赖）+ `IPython`（固定脚本
    `from IPython.display import ...` 自身依赖）；可选复用 `langgraph==1.2.11`。
  - `[otlp]` 依赖用于真实轮 OTLP 探针（已由 CI 的 extras 预验证步骤安装）。

**Storage**:
- **无仓库内持久化**。探针使用临时目录：
  - `FileTraceStore(directory=tmp_path)` → `trace-<run_id>.jsonl`
  - `SqliteTraceStore(database=tmp_path/"traces.sqlite3")`
  - `SqliteSaver.from_conn_string(tmp_path/"checkpoints.sqlite3")` / `:memory:`
- 人工轮证据写入 `harness/verification/B25F1/` 的记录文件（Markdown），不写入 `src/`。

**Testing**:
- 既有测试套件：`pytest tests/`（G27 全程监测；G28 Linux 断网全量）。
- **新增 / 修改**：
  - `tests/runtime/test_b25f1_target_fake.py`（A1 / 固定断言点 / PNG / 框架出站 = 0）
  - `tests/runtime/test_b25f1_target_guard.py`（SHA-256 + 基线 ref diff）
  - `tests/runtime/test_b25f1_diagnostics.py`（`diagnostics.py` 退出码 0 + 三组标记）
  - `tests/runtime/test_b25f1_offline_equivalence.py`（进程内断网核心用例全绿）
  - `tests/runtime/test_b25f1_zero_egress.py`（框架 0 / 用户出站任意目标、不判失败、不设白名单）
  - `tests/runtime/test_b25f1_docs_guard.py`（迁移说明三类 + Y-01；README 绝对 `COMPAT.md` 链接、无完整矩阵）
  - `tests/runtime/test_b25f1_acceptance.py`（`harness/verification/B25F1/acceptance.py --skip-real`；exit 2 ⇒ skip）
  - `tests/runtime/test_b25f1_manual_record_guard.py`（SC-004 自动文档守卫；常驻 CI 在记录未就绪 / 仅有环境偏离时 skip；T052 的严格模式仅在发布 / 人工门禁执行）
  - `tests/differential/test_b25f1_final_acceptance.py`（`B25F1-D-01…D-03`；上游缺席 skip）
  - `tests/differential/test_b25f1_model_factory.py`（模型形状规格 + 纯本地拒绝语义不变）
  - **修改** `tests/differential/spec_builder.py`（新增 `build_model_graph_spec`）
  - **修改** `tests/runtime/conftest.py`（新增 B25F1 专用 fake 注入 fixture；非 autouse）
- 验收脚本：`harness/demo/acceptance.py` · `harness/demo/diagnostics.py` ·
  `harness/verification/B25F1/{acceptance,fake_round,real_round}.py`。
- **两个 `acceptance.py` 的职责（MUST 用全路径）**：
  - `harness/demo/acceptance.py` = **四组验收脚本**（`graph_core` / `agent_loop` / `visualization` / `diagnostics`）的**编排器**（A4；自身检查计入退出码）；
  - `harness/verification/B25F1/acceptance.py` = **B25F1 一键验收**（A1/A3/A4/A5；
    `--real` 跑 A2；`--skip-real` 供 CI）；**MUST NOT** 用裸 `acceptance.py` 指代。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+；**OS 级断网**仅 Linux
（复用 G28）；真实模型轮为人工、单次、环境显式配置。

**Project Type**: library（运行时）+ verification harness（交付 / 验收单元）。

**Performance Goals**: **N/A**（不设墙钟预算）。真实轮限制为**两个段、少量模型调用**；
诊断脚本无外部调用。

**Constraints**（主要来自 spec）：

| 约束 | spec 条目 |
|---|---|
| fake 注入不改 `target.py`；与路由函数正交 | FR-001 / FR-020 · H-1 |
| fake 固定 2 轮序列 + `tool_calls` | FR-002 |
| 固定断言点：`messages == 4` · `llm_calls == 2` · 工具结果 `== 7` · 完整状态两键 | FR-003 · A1 |
| 零出站只观测不阻断；框架 0；用户出站不判失败、不设白名单 | FR-004 · SC-002 · A3 |
| 断网等价性：进程内必做 + OS 级条件增强 | FR-005 |
| `diagnostics.py` 纳入编排 | FR-006 |
| 退出码 0/1/2 可区分 | FR-007 |
| 人工记录五要素 + 三附件 | FR-008 · SC-004 · A2 |
| 迁移说明三类 + Y-01 | FR-009 · SC-005 |
| README 绝对 `COMPAT.md` 链接、不复制矩阵 | FR-010 · SC-005 |
| 双重基线 | FR-011 · A5 |
| 真实轮两段式 + 实际输出 + 环境偏离 | FR-012 |
| B20F1 / B20F2 trace 实测 | FR-013 |
| B21F1 OTLP 实测 | FR-014 |
| B15F1 / B16F1 checkpoint + 时间旅行 | FR-015 |
| B23F1 PNG 实测 | FR-016 |
| B24F1 发行产物 + Y-01 | FR-017 |
| B5F2 / B7F1 模型工厂 + 上游差分跑比对 | FR-018 · SC-006 |
| B14F1 发布前人工验收清单 | FR-019 |
| 依赖红线 + 反向断言 | FR-020 |
| 清空 `LANGSMITH_*` | FR-021 |
| 不新增运行时改动 / 门禁编号 | FR-022 |

> **无未决澄清**：spec 的 Clarifications（17 条）已收敛全部功能决策；本 plan 只落实现方法、
> 证据与验收。**无未决澄清。**

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | 框架出站 = 0；`LANGSMITH_*` 清空；用户出站只记录；真实轮的两段式证据 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | `src/freegraph/` 零改动；`langchain` / `IPython` 仅在 `acceptance` 测试组；运行时 `sys.modules` 反向断言 | 通过（测试侧依赖不进 `Requires-Dist`） |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` 零改动；SHA-256 + 基线 ref diff 双重基线 | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | 新增 `diagnostics.py`（trace / checkpoint / 时间旅行）；PNG 实测记录 | 通过 |
| 原则 V（人工验收） | 真实模型轮两段式 + 五要素记录 + 三附件；**无真实轮不得宣布完成** | 通过（人工门禁） |
| 原则 VI（规格驱动 · 判据级覆盖） | FR-001…FR-022 / SC-001…SC-006 / A1–A5；tasks 将双向追溯；人工记录守卫 | 通过 |
| 原则 VII（职责边界 · 不扩内核） | 不新增契约 / 运行时符号；`Store` / 子图 / async / Postgres 仍不做 | 通过 |
| 原则 VIII（证据与术语） | 记录中的事实带来源；既有记录不回改；Y-01 只记录 | 通过 |
| 原则 IX（许可证 / 商标） | 不新增运行时依赖；测试组不进发行包；README 无品牌资产 | 通过 |
| 原则 X（文档合规 / 署名头） | README / 迁移说明 / 验收记录；所有新 `.py` 带署名头（G30） | 通过 |
| 原则 XI（上游优先） | `langgraph==1.2.11`；`B25F1-D-01…D-04`；Y-01 保留；**零运行时改动** | 通过 |
| 原则 XII（最优设计 · 零重复载体） | 不复制 `COMPAT.md`；复用 `_gatekit` 归因而非另写一套；复用既有 G28 | 通过 |
| 立项书 ARCH-1 / ARCH-2 / ARCH-3 | 无跨层 import / 顶层惰性 / 运行时语义变更 | 通过（零改动） |
| 质量门禁 3（`target.py` 原样可跑） | 双重基线 + fake 轮原样执行 | 通过（本 feature 兑现） |
| 质量门禁 4（CI fake 轮 + 零出站） | fake 轮 CI + 框架出站 = 0 | 通过（本 feature 兑现） |
| 质量门禁 5（人工真实模型轮） | 真实模型轮两段式 + 人工记录 | 通过（本 feature 兑现） |
| G22 / G27 / G28 | 不新增门禁编号；新测试在 G27 监测下无框架出站；真实轮脚本不进 `tests/`，G28 不受影响 | 通过 |
| 发布门禁（Release Gate） | 本 feature 的产物是**仓库文档 / 验收材料**，不进发行包；纯度门禁不变 | 通过 |

### Complexity Tracking

| 复杂点 | 为何需要 | 更简单的替代为何不可行 |
|---|---|---|
| **新增 `acceptance` 依赖组** | `target.py` 自带 `langchain.*` 与 `IPython`；fake 轮必须原样跑脚本 | 把 `langchain` 加入运行时依赖 ⇒ 直接违反零依赖承诺；不装则 fake 轮无法执行 |
| **双重基线** | 只比 `git diff HEAD` 检测不到已提交篡改（spec A5） | 只用 SHA-256 可行但无法证明「历史基线未漂移」；只用 git 基线在浅克隆 / 本地不可用 |
| **B5F2 新增入口而非放宽旧入口** | B5F2 的纯本地规格必须继续拒绝非空 `model_factory` | 直接放宽 `validate_graph_spec` ⇒ B5F2 的 `test_a_non_empty_model_factory_is_an_explicit_failure` 必红，且纯本地契约被削弱 |
| **真实轮两段式** | 固定脚本不能猴补 `compile` / `invoke`（避免「表面没改」争议）；观测 / 持久化需要额外图实例 | 全塞进固定脚本 ⇒ 需要猴补固定脚本的编译 / 调用；每组件独立真实调用 ⇒ 成本高且证据碎片化 |
| **零出站归因复用 `_gatekit`** | G27 已锁定「第一个非标准库帧」规则；另写一套会与门禁漂移 | demo 内联实现继续用「栈含 freegraph」⇒ 用户经框架调用会被误判为框架出站 |
| **真实轮 OTLP 用 `exporter=` 记录型 exporter** | 人工环境不一定有 OTLP 后端；`endpoint=` 需本地接收端 | 强制要求运行后端 ⇒ 人工轮不可复现；只写「符合预期」⇒ 违反证据门禁 |

### 质量门禁偏离

**无新增偏离**。本 feature 是 **B20F1 / B20F2 / B21F1 / B24F1 的质量门禁 5 真实模型轮承接方**；
本 plan 将用两段式真实轮与人工记录**关闭**这些偏离（不是再次登记偏离）。
正式闭合文字 MUST 落 `harness/verification/B25F1/manual-verification.md`，并**引用**既有
B14F1 / B15F1 / B16F1 / B20F1 / B20F2 / B21F1 / B23F1 / B24F1 的记录（**不回改**）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b25f1-final-acceptance/
├── plan.md                               # 本文件
├── research.md                           # Phase 0：决策与证据
├── data-model.md                         # Phase 1：实体 / 校验规则
├── quickstart.md                         # Phase 1：可执行验收手册
├── contracts/
│   ├── fake-injection-contract.md        # fake 序列 / 注入时机 / 正交性 / 断言
│   ├── target-baseline-contract.md       # SHA-256 + 基线 ref diff
│   ├── acceptance-egress-contract.md     # 退出码 / 编排 / 零出站 / 记录 / 环境偏离
│   ├── diagnostics-contract.md           # trace / checkpoint / 时间旅行用例
│   └── docs-migration-contract.md        # 迁移说明 / README / COMPAT 指针
└── checklists/requirements.md            # /speckit.specify 产出（已存在）
```

### Source Code / Repository Layout

```text
harness/
├── demo/
│   ├── acceptance.py                     # 修改：diagnostics 组 / target fake 组 / LANGSMITH_* 清理 / 记录模板
│   ├── diagnostics.py                    # 新增：trace / checkpoint / 时间旅行
│   ├── README.md                         # 修改：标记 diagnostics 已交付；补双跑 / 上游差分跑说明
│   └── target.py                         # **零改动**（只读基准）
├── proposals/
│   └── 更名与迁移说明.md                  # 修改：新增 v1 迁移章节（三类 + Y-01 + COMPAT 链接）
└── verification/
    └── B25F1/
        ├── acceptance.py                 # 新增：A1/A3/A4/A5 自动；--real 跑 A2
        ├── fake_model.py                 # 新增：FakeModel + install()
        ├── fake_round.py                 # 新增：同进程 fake 轮 + 外部 sitecustomize 等价轮
        ├── real_round.py                 # 新增：真实模型两段式探针
        └── manual-verification.md        # 新增：五要素 + 三附件（人工填写 / --record 生成草稿）

README.md                                 # 修改：快速上手 + 三条承诺 + 能力表 + 绝对 COMPAT 链接
COMPAT.md                                 # 只校验（Y-01 保留；不复制到 README）
pyproject.toml                            # 修改：新增 acceptance 依赖组（PEP 735 · 不进发行包）
.github/workflows/ci.yml                  # 修改：checkout fetch-depth: 0；安装 acceptance 组；B25F1 验收步

tests/
├── conftest.py                           # 不改（全局诊断通道）
├── runtime/
│   ├── conftest.py                       # 修改：新增 B25F1 fake 注入 fixture（非 autouse）
│   ├── data/b25f1_target_py.sha256       # 新增：target.py 内容真值
│   ├── test_b25f1_target_fake.py         # 新增：A1 + 固定断言点 + PNG + 框架出站
│   ├── test_b25f1_target_guard.py        # 新增：SHA-256 + 基线 ref diff
│   ├── test_b25f1_diagnostics.py         # 新增：diagnostics.py 退出码 / 标记
│   ├── test_b25f1_offline_equivalence.py # 新增：进程内断网核心用例
│   ├── test_b25f1_zero_egress.py         # 新增：框架 0 / 用户出站任意目标
│   ├── test_b25f1_docs_guard.py          # 新增：迁移说明 + README 守卫
│   ├── test_b25f1_acceptance.py          # 新增：B25F1 一键验收 --skip-real（exit 2 ⇒ skip）
│   └── test_b25f1_manual_record_guard.py # 新增：SC-004 自动文档守卫（记录未就绪 skip）
└── differential/
    ├── spec_builder.py                   # 修改：新增 build_model_graph_spec（不改纯本地拒绝）
    ├── _b25f1_model_factory.py           # 新增：差分用 fake 模型工厂
    ├── test_b25f1_final_acceptance.py    # 新增：B25F1-D-01…D-03（D-04 在 model factory 测试）
    └── test_b25f1_model_factory.py       # 新增：模型形状规格 + 纯本地拒绝语义不变
```

**Structure Decision**：沿用既有单项目 / 库布局。本 feature **不新增 `src/` 文件**；
新增的是验收脚本、测试、CI 接线与文档。`harness/demo/` 保持「验收脚本 + 只读基准」定位；
B25F1 的专用探针放在 `harness/verification/B25F1/`，不污染 demo 的零依赖脚本集。

---

## Phase 0 · Research（摘要）

完整决策与证据见 [research.md](./research.md)。核心结论：

| 决策 | 结论 |
|---|---|
| **D-01 fake 注入机制** | 同进程：`runpy.run_path` 前猴补 `langchain.chat_models.init_chat_model`；子进程：临时 `sitecustomize.py` + `PYTHONPATH`。两条路径都**不改 `target.py`** |
| **D-02 固定断言点** | `messages == 4`（System 不进入状态）、`llm_calls == 2`、工具结果 `== 7`（**归一为 int**；`ToolMessage.content` 实测为 `"7"`）、完整状态含两键 |
| **D-03 零出站归因** | 复用 G27 的 `_gatekit`「第一个非标准库帧」；demo 内联 `EgressProbe` 对齐同一规则；只观测不阻断 |
| **D-04 双重基线** | `tests/runtime/data/b25f1_target_py.sha256` + 基线 ref（默认 `origin/main`，可由 `B25F1_BASELINE_REF` 覆盖）；基线不可用 ⇒ 显式 skip / 环境偏离，SHA 仍判 |
| **D-05 模型工厂** | 新增 `build_model_graph_spec(..., model_factory=...)`；`build_graph_spec` 的纯本地 `model_factory` 非空 ⇒ 显式失败**保持不变** |
| **D-06 diagnostics** | 三组：trace（JSONL + SQLite + `query()` 过滤）/ checkpoint（`MemorySaver` + `SqliteSaver` + 历史倒序）/ 时间旅行（重放 / 分叉 / 中断组合） |
| **D-07 真实轮两段式** | 固定脚本段（A2 / 零出站 / PNG）+ 专用探针段（trace / OTLP / checkpoint / 时间旅行）；两段均使用**真实模型**；trace 的 File / SQLite 为**两次独立运行**（`RunConfig(thread_id=...)`，捕获 `run_id` / 时间窗）；OTLP 默认使用脚本内定义的 `RecordingSpanExporter`（无网络），可选 `endpoint=` 本地 gRPC 接收端；真实调用少量、证据非空 |
| **D-08 断网等价** | 进程内 socket 禁用（必做）；OS 级复用 G28；真实轮脚本不进 `tests/`，不触发 G28 假红 |
| **D-09 CI 依赖组** | 新增 `acceptance` 组（`langchain` / `IPython`）；仅 **Linux x86 全量档（`ubuntu-24.04` 3.11/3.14）**安装；其余档 `importorskip` |
| **D-10 一键验收 / 记录** | `harness/verification/B25F1/acceptance.py --skip-real` 供 CI；`--real` 跑人工轮；`--record` 生成记录草稿；五要素 + 三附件；**常驻 CI 的文档守卫在记录未收口 / 仅有环境偏离时 skip；T052 严格模式仅在发布 / 人工门禁执行**（宪法 v1.13.0） |
| **D-11 文档** | 迁移说明三类 + Y-01；README 绝对 `COMPAT.md` 链接、不复制矩阵；demo README 标记 diagnostics 已交付 |
| **D-12 证据纪律** | 所有实测输出非空；`json.dumps` / 文件行数 / span 数 / 历史条目计数；环境偏离写明完成与未完成范围 |

**无未决澄清。**

---

## Phase 1 · Design & Contracts

已生成：

- [data-model.md](./data-model.md) —— 固定脚本基线 / fake 注入 / 双跑结果 / 出站记录 /
  验收运行 / 人工记录 / 真实轮证据 / 诊断用例 / 模型工厂规格。
- [contracts/fake-injection-contract.md](./contracts/fake-injection-contract.md) —— fake 序列、
  注入时机、与路由函数正交、外部注入等价、失败语义。
- [contracts/target-baseline-contract.md](./contracts/target-baseline-contract.md) —— SHA-256
  文件格式、基线 ref 解析、双重判定、不可用时的处置。
- [contracts/acceptance-egress-contract.md](./contracts/acceptance-egress-contract.md) ——
  退出码 / 编排顺序 / 零出站监测 / 用户出站口径 / 人工记录 / 环境偏离。
- [contracts/diagnostics-contract.md](./contracts/diagnostics-contract.md) —— trace / checkpoint /
  时间旅行的 API 形态、断言与退出码。
- [contracts/docs-migration-contract.md](./contracts/docs-migration-contract.md) —— 迁移说明三类、
  `Y-01`、README 结构、`COMPAT.md` 绝对链接与「不复制矩阵」。
- [quickstart.md](./quickstart.md) —— fake 轮、固定脚本防御、一键验收、真实轮、断网、依赖断言、
  文档核对、CI 接线。

---

## Post-Design Re-check（Phase 1 后）

| 检查 | 结果 |
|---|---|
| fake 注入在 `target.py` 导入前生效；同进程 / 子进程两条路径均可跑 | 计划验证（`fake_model.install()` + `sitecustomize`） |
| `target.py` 零改动；SHA-256 与基线 ref 双重基线可判定 | 计划验证（`test_b25f1_target_guard.py`） |
| 固定断言点：`messages == 4` / `llm_calls == 2` / 工具结果 `== 7` / 两键 | 计划验证（`test_b25f1_target_fake.py`） |
| fake 必须产生 `tool_calls`，且 `tool_call.id` 与 `ToolMessage.tool_call_id` 对齐 | 计划验证（fake 序列 + 断言） |
| fake 注入与路由函数正交；`should_continue` 仍读最新 state | 计划验证（fake 只替换模型；B8F1 D-5） |
| 框架出站 = 0；用户出站记录、不判失败、不设白名单 | 计划验证（`_gatekit` + demo 内联对齐） |
| 断网等价：进程内全绿；OS 级复用 G28；真实轮不在 `tests/` | 计划验证（`test_b25f1_offline_equivalence.py` + G28） |
| `diagnostics.py` 覆盖 trace / checkpoint / 时间旅行并纳入 `harness/demo/acceptance.py` | 计划验证（`diagnostics` 组 + `test_b25f1_diagnostics.py`） |
| 退出码 0/1/2 在 `harness/demo/acceptance.py` / `harness/verification/B25F1/acceptance.py` / `diagnostics.py` / `fake_round.py` 可区分 | 计划验证（各脚本 `main()` + 测试） |
| 真实轮两段式；`FileTraceStore` / `SqliteTraceStore` / `OtlpExporter` / `SqliteSaver` / 时间旅行证据非空 | 计划验证（`real_round.py` + 人工记录守卫） |
| B15F1 / B16F1 / B20F1 / B20F2 / B21F1 / B23F1 / B24F1 的承接证据逐条齐备 | 计划验证（记录守卫 + 交叉引用） |
| B5F2 模型工厂钩子：模型形状规格可跑；纯本地非空仍失败 | 计划验证（`build_model_graph_spec` + 既有测试保持绿） |
| `B25F1-D-01…D-04` 可执行；上游缺席 skip；不改运行时 | 计划验证（`test_b25f1_final_acceptance.py` + `test_b25f1_model_factory.py`） |
| 人工记录五要素 + 三附件；事实带来源；遗留问题逐条 | 计划验证（记录守卫 + 人工复核） |
| 常驻 CI 的记录守卫在记录未就绪 / 仅有环境偏离时 `skip`；T052 严格模式仅在发布 / 人工门禁执行；T034 / T048 不因未收口记录假红 | 计划验证（T019 / T052；宪法 v1.13.0） |
| 迁移说明三类 + Y-01；README 绝对链接、无完整矩阵 | 计划验证（docs guard + 人工复核） |
| `target.py` 的 PNG 实测（字节数 / 结构 / 框架出站 = 0） | 计划验证（fake 轮捕获 + 真实轮记录） |
| 依赖闭包无 `langsmith` / `langchain*` / `langgraph*`；运行时 `sys.modules` 反向断言 | 计划验证（既有 G21 / G25 + 新记录附件） |
| `LANGSMITH_*` 清空；三轮验收环境记录 | 计划验证（`collect_env` + 子进程 env 清理） |
| 新 `.py` 带署名头；G30 不红 | 计划验证（G30） |
| **Linux x86 全量档**安装 `acceptance` 组且 `harness/verification/B25F1/acceptance.py --skip-real` 绿；其余档 skip；job 名不变 | 计划验证（`.github/workflows/ci.yml`） |
| `src/freegraph/` 零改动；不新增门禁编号 | 计划验证（git diff + 门禁清单） |

---

## 实施阶段（供 `/speckit.tasks` 拆分）

| 阶段 | 目标 | 主要产物 |
|---|---|---|
| **A · 基座** | 固定脚本防御 + 出站归因对齐 + 记录模板 | `b25f1_target_py.sha256` · `test_b25f1_target_guard.py` · `harness/demo/acceptance.py` 的 `EgressProbe` / `collect_env` / 记录模板更新 |
| **B · fake 轮** | A1 + A5 可自动判定 | `fake_model.py` · `fake_round.py` · `test_b25f1_target_fake.py` · `tests/runtime/conftest.py` fixture |
| **C · diagnostics** | trace / checkpoint / 时间旅行 | `harness/demo/diagnostics.py` · `tests/runtime/test_b25f1_diagnostics.py` · `harness/demo/acceptance.py` 纳入 `diagnostics` 组 |
| **D · 一键验收** | A1/A3/A4/A5 + 记录草稿 | `harness/verification/B25F1/acceptance.py` · `test_b25f1_acceptance.py` · `test_b25f1_manual_record_guard.py` |
| **E · 真实轮** | A2 + 承接证据 | `real_round.py` · `manual-verification.md`（两段式证据 / 环境偏离 / 遗留问题） |
| **F · 差分与模型工厂** | `B25F1-D-01…D-04` | `spec_builder.py` 新增入口 · `_b25f1_model_factory.py` · 两个差分测试文件 |
| **G · 文档** | 迁移说明 + README 收口 | `更名与迁移说明.md` · `README.md` · `harness/demo/README.md` |
| **H · CI / 收口** | 自动验收进 CI + 全量回归 | `pyproject.toml`（`acceptance` 组）· `.github/workflows/ci.yml` · 全量 pytest / 门禁 / G27 / G28 |

**依赖顺序**：A → B → C → D → E；F 可与 C/D 并行；G 可与 E 并行；H 最后。

**记录守卫顺序（宪法 v1.13.0）**：`tests/runtime/test_b25f1_manual_record_guard.py` 在记录未收口 /
仅有环境偏离时 `skip`（不判失败，避免永久红 CI）；**T052 的严格模式仅在发布 / 人工门禁执行**，
不在常驻 CI 移除 skip。T034 / T048 的 G28 / 全量 pytest 可在 skip 状态先跑；最终发布判定以
T052（发布门禁）为准。

---

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| `langchain` v1 / `langchain-core` 版本不兼容（本机实测系统环境出现过） | `acceptance` 组用 `uv` 解析并锁定；CI Linux x86 全量档真实安装；其余档 skip |
| `target.py` 的 `IPython.display` 缺失 | `acceptance` 组安装 `IPython`；缺失 ⇒ 退出码 2 / skip（不判断言失败） |
| 真实模型无凭据 / 网络受限 | 两段式；`--real` 可分段执行；环境偏离写明范围；**无真实轮不得宣布完成** |
| 无 OTLP 后端 | 默认 `exporter=` 记录型官方 `SpanExporter`（无网络）；可选 `endpoint=` 本地 gRPC 接收端 |
| 浅克隆 / 无 `origin/main` | SHA-256 仍判；基线 ref 不可用 ⇒ 显式 skip + 环境偏离；CI 用 `fetch-depth: 0` |
| G27 / G28 误伤真实轮 | 真实轮是 `harness/verification/B25F1/real_round.py` 人工脚本，**不进 `tests/`**；新测试离线安全 |
| 用户出站被误判为框架出站 | 复用 G27 的「第一个非标准库帧」；demo 内联对齐；误判即判实现错误 |
| 模型工厂改动导致 B5F2 测试红 | **新增** `build_model_graph_spec`，**不放宽** `build_graph_spec` 的纯本地拒绝 |
| 人工记录被「自动验收通过」冒充 | 记录守卫要求**真实轮实际输出**；B14F1 记录不可回改；环境偏离须写明。**常驻 CI 在记录未就绪 / 仅有环境偏离时保持 skip（T019）；T052 的严格模式仅在发布 / 人工门禁执行**；T034 / T048 的全量套件可在 skip 状态下先跑，最终发布判定以 T052 为准（宪法 v1.13.0） |

---

## 后续

- **`/speckit.tasks`**：把本 plan 拆成可勾选任务（A–H 八阶段；每条 FR / SC / A 判据双向追溯；
  含 fake 轮、diagnostics、双重基线、真实轮两段式、B5F2 模型工厂、迁移说明、README、CI 接线、
  人工记录守卫）。
- **实现顺序建议**：A → B → C → D → E；F 与 G 可并行；H 收口。
- **完成判定**：A1–A5 全成立 + SC-001…SC-006 + 人工记录五要素 / 三附件；**真实模型轮未完成
  不得宣布 v1.0 收口**（原则 V）。
