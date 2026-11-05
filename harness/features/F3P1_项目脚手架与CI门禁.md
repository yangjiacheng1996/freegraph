# F3P1 · 项目脚手架 + extras 划分 + CI 门禁

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | Phase ID | `F3P1` |
> | 所属 Feature | F3（项目脚手架 + CI 门禁） |
> | 架构层 | 跨层单元（层 =「—」，工程设施） |
> | 里程碑 | M0 地基（第 4 个） |
> | 前置依赖 | **F1P1, F2P1** |
> | 规模 | 1,100 行（实现 620 / 测试 480）· 3 人日 |
> | 建议 short-name | `p04-scaffold-ci-gates` |
> | MVP 必需（★） | 否（**但它是全部后续 Phase 的守门人**） |
> | ⚠️ 前置决策 | **D12**（零出站与依赖门禁的作用域定义）须随本 Phase 落地 |

---

## 提示词正文

### 1. 目标

把 freegraph 的**工程设施**一次性建起来：项目脚手架（`pyproject.toml` 的 extras 划分、
`src/` 布局、类型标记、Python 版本矩阵）与 **7 项 CI 门禁的自动化落地**。本 Phase 的
交付判据是**反向的**：**故意引入 `langchain` 依赖 → CI 必须失败**。

### 2. 背景与上下文

- 本项目的核心资产是「**可审计的契约**」——零依赖红线、API 同名对齐。门禁不是配套工程，
  而是**契约的执行机制**。没有门禁，红线只是文档里的许诺。
- **依赖红线的作用域**（立项书 §9.2，D12）：约束对象是 **freegraph 自己**——
  它的依赖声明、它的 import、它的网络行为；**不**约束用户脚本装了什么。
  因此门禁需要**两个环境、两套断言**：

  | 环境 | 装什么 | 断言 |
  |---|---|---|
  | ① 依赖断言环境（隔离 venv） | 只装 freegraph 基础包（唯一必装依赖 `typing-extensions`） | 递归展开 freegraph 自身 `Requires-Dist`（含全部 extras 变体）无 `langsmith` / `langchain*` / `langgraph*`；`import freegraph` 后 `sys.modules` 中无 `langsmith` / `langchain_core` / `langgraph` |
  | ② 验收环境 | freegraph + **脚本自带的** `langchain` 系 | **反向断言**：freegraph 运行期从不 import `langchain` / `langchain_core`；freegraph 自身零出站 |

- **「零出站」的实现口径**（立项书 §9.2 + 风险 R11）：**只观测、不阻断 + 按发起方归因**。
  socket 夹具只包装 `socket.connect` / `socket.create_connection` 以**记录**目标与调用栈，
  **放行**所有连接；调用栈中出现 `freegraph/` 包路径 → 判「框架出站」，否则判「用户出站」；
  **只对前者断言 = 0**。freegraph **不安装、不启用任何出网拦截机制**——用户节点访问
  外网、调用真实模型、工具访问第三方 API 一律照常。
- **CI 矩阵**：Linux + macOS + Windows × 最低版本（3.10）+ 最高版本（3.13）；Linux 额外跑
  完整门禁，其余平台跑子集。

### 3. 用户场景

**P1 — 破坏红线会立刻被拦住**
作为项目发起者，我希望能保证任何人（人或 AI 代理）不小心 `pip install langchain-core`
进 freegraph 的依赖、或 `import langchain` 进内核时，**CI 立刻失败并指出是哪条规则**，
而不是等到发版后才发现。

- **独立验收**：在依赖声明里故意加入 `langchain-core`，CI 必须失败并输出违规条目。

**P2 — freegraph 自己不偷偷联网**
作为用户，我希望能保证 freegraph 运行时不发起任何出站连接（连 `mermaid.ink` 也不发），
而且这个保证是**可判定的**，不是口头承诺。

- **独立验收**：运行验收脚本时，socket 监测夹具记录的「框架出站」条目数为 0。

**P3 — 基础安装足够轻**
作为内网/离线环境的用户，我希望能 `pip install freegraph` 只装上一个包
（`typing-extensions`），其余全部是可选 extra，需要时再装。

- **独立验收**：隔离 venv 中 `pip install freegraph` 后 `pip freeze` 只列出
  `typing-extensions` 与 `freegraph`。

### 4. 功能需求

- **FR-001**：系统 MUST 提供完整 `pyproject.toml`：基础依赖仅 `typing-extensions`；
  可选 extra 至少包含 `[pydantic]` / `[checkpoint]`（`ormsgpack`）/ `[otel]`
  （`opentelemetry-exporter-otlp`）/ `[png]`（本地渲染，默认关闭）。
- **FR-002**：系统 MUST 发布 `py.typed`（PEP 561）并使用 `src/` 布局。
- **FR-003**：系统 MUST 声明 `requires-python = ">=3.10"`，且**不设上限**。
- **FR-004**：CI MUST 实现**依赖门禁**：递归展开 freegraph 自身声明的依赖（含全部 extras
  变体），断言无 `langsmith` / `langchain*` / `langgraph*`；并在隔离 venv 中断言
  `import freegraph` 后 `sys.modules` 无 `langsmith` / `langchain_core` / `langgraph`。
- **FR-005**：CI MUST 实现**许可证白名单门禁**：依赖许可证 ∈ {MIT, Apache-2.0, BSD-2/3,
  PSF}；出现 Elastic-2.0 / AGPL / SSPL / BUSL 即失败（额外点名 `langgraph-api` /
  `langgraph-runtime-inmem` / Phoenix）。
- **FR-006**：CI MUST 实现**配置层门禁**：静态扫描 freegraph 包内无 `LANGSMITH_*` /
  `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` 读取，且
  **freegraph 内核不读任何环境变量**。
- **FR-007**：CI MUST 实现**导入图单向门禁（ARCH-1）**：L1→L6 编号递增方向即允许方向；
  反向 import 视为违规；跨层单元只能 import L1 与更低层，且不得被 L2–L5 import。
- **FR-008**：CI MUST 实现**网络门禁**：socket 监测夹具（只观测不阻断 + 按调用栈归因）
  断言「框架出站数 = 0」；并做静态扫描，`freegraph/**`（排除可选 OTLP exporter 模块）
  不得出现 `socket` / `requests` / `httpx` / `urllib.request` 等网络客户端调用。
- **FR-009**：CI MUST 提供**断网等价性任务**：把全部网络接口置为不可用后重跑核心用例，
  确认 freegraph 自身功能完整可用。
- **FR-010**：CI MUST 实现**契约门禁的载体**：`harness/demo/target.py` 的 diff 断言
  （只读基准，改动即失败）；并预留 C4 / C8 两条回归测试的挂载点（M1 建立）。
- **FR-011**：CI MUST 实现**API 快照检查**（F2P2 已入库的快照）与 **`COMPAT.md` 一致性
  检查**的挂载点。
- **FR-012**：CI MUST 采用 OS 矩阵（Linux/macOS/Windows × 3.10/3.13），Linux 跑全量门禁，
  其余平台跑子集。
- **FR-013**：CI MUST 提供**源文件署名头检查**（静态扫描 `src/**/*.py` 与仓库内脚本）：
  每个源文件顶部 MUST 含 `Copyright (c) 2026 杨家成 · MIT License · <项目地址>`；
  **例外**：`py.typed`（PEP 561 要求为空）与 `harness/demo/target.py`（只读基准）。
  该检查**MUST** 在 CI 中失败即报错——它是宪法原则 X「源文件署名头」义务的执行手段，
  也是「个人作品集」定位下署名可追溯的机械保障。
- **FR-014**：CI MUST 提供**「故意引入 `langchain` 依赖 → 必须失败」的负向验证用例**
  （本 Phase 的验收判据本体）。

### 5. 成功标准

- **SC-001**：负向验证通过——依赖声明中加入 `langchain-core` 时，CI 的依赖门禁**必须
  失败**并输出违规条目；撤销后恢复通过。
- **SC-002**：隔离 venv 中 `pip install freegraph` 后，依赖闭包仅含 `typing-extensions`；
  `import freegraph` 后 `sys.modules` 中无 `langsmith` / `langchain_core`。
- **SC-003**：全部 7 项质量门禁在 CI 中有**可自动执行的断言**落地（不是人工 checklist）。
- **SC-004**：核心用例在「全部网络接口不可用」的任务中仍然全绿。
- **SC-005**：`pip install freegraph` 后的包内容**不含** `harness/` / `.specify/` /
  `.opencode/` 等仓库内容（发布门禁的先行检查）。

### 6. 验收判据（= 立项书 §5.2 F3P1 小目标，逐条可判定）

> 小目标原文：门禁生效：故意引入 `langchain` 依赖 → CI 必须失败

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 门禁生效 | 负向验证用例：依赖声明加 `langchain-core` → CI **失败**且报错可读；撤销 → 通过 |
| A2 | 依赖闭包干净 | 隔离 venv 断言（SC-002） |
| A3 | 零出站可判定 | socket 监测夹具记录「框架出站 = 0」 |
| A4 | 导入图单向 | AST 扫描断言（ARCH-1） |
| A5 | **源文件署名头齐备** | 静态扫描：每个源文件含署名头（`py.typed` / `target.py` 除外）；负向验证——删掉某文件的头 → 检查失败 |

### 7. 关键实体与门禁清单

| 门禁 | 内容 | 落地方式 | 本 Phase 状态 |
|---|---|---|---|
| 1 规格门禁 | 有 proposal 与 spec，tasks 可逐条勾选 | 人工评审 | 流程已存在 |
| 2 **依赖门禁（阻断）** | 依赖闭包无 `langsmith`/`langchain-core`/ELv2/AGPL/SSPL；无 `LANGSMITH_*` 读取；freegraph 自身不向 `*.langchain.com` / `mermaid.ink` 出站；无第三方商标资产 | 自动执行 | ✅ 本 Phase 建立 |
| 3 契约门禁 | 固定脚本原样可跑；diff 断言；C4 / C8 独立回归测试 | CI | 挂载点建立，回归测试 M1 补 |
| 4 自动门禁 | CI 全绿 + fake 模型跑通验收基线 + 零出站断言 | CI | ✅ 本 Phase 建立（fake 轮在 F25P1 落地） |
| 5 人工门禁 | `harness/features/<feature>/manual-verification.md` 完整 | 人工评审 | 流程已存在 |
| 6 证据门禁 | 新增结论带来源标记，术语准确 | 人工评审 | 流程已存在 |
| 7 文档合规门禁 | `THIRD_PARTY_NOTICES` 已登记、API 兼容矩阵已更新 | 人工评审 | 矩阵 F24P1 落终版 |
| **发布门禁** | 发行产物纯度（只含 `src/` 包代码与必要元数据） | `harness/scripts/check_dist_purity.py` | 脚本已存在，流水线在 F24P1 接入 |

### 8. 边界（本 Phase 明确不做）

- 不实现内核功能（本 Phase 只建工程设施）。
- 不接入发布流水线（`uv publish` 前的纯度断言）——属 **F24P1**。
- 不编写 fake 模型注入（`conftest.py` 猴补 `init_chat_model`）——属 **F25P1**。
- 不实现 `COMPAT.md` 的完整兼容矩阵内容——属 **F24P1**。
- 不实现本地 trace / checkpointer 的 CI 专用后端——属 M3。

### 9. 红线与质量门禁

- 本 Phase 自身即门禁的红线：**不得**为了让门禁好过而放宽白名单；
  **不得**在 CI 中加入任何「例外名单 / 白名单豁免」机制（原则 I 不接受临时豁免）。
- **零出站的口径**：只观测不阻断——freegraph 不安装任何出网拦截机制，不改变宿主程序
  的语义（这是**产品设计立场**，不是实现细节）。
- **D12**：零出站与依赖门禁的作用域定义须随本 Phase 一并落地（表述与立项书 §12 一致）。

### 10. 交付物与后续

- **交付物**：完整 `pyproject.toml`（extras 划分）、CI workflow（矩阵 + 7 项门禁 +
  负向验证用例）、`harness/scripts/` 下的门禁脚本、人工验证记录。
- **后续解锁**：**M1 全部 9 个 Phase**——门禁一旦生效，M1 的每一次提交都会被自动检查。
- **注意**：本 Phase 排在 M0 最后，因此**M0 的三个 Phase（F1P1 / F2P1 / F2P2）没有被
  门禁守护过**——人工复核这三者的依赖声明与 import 图是本 Phase 的必要动作。

---

## 依据

- 立项书 §5.1（ARCH-1/2/3/4）、§5.5（依赖三层黑白名单）、§9.1（7 项质量门禁 + 发布门禁）、
  §9.2（依赖红线作用域 / 零出站验证方法）、§10（R11 拦截式守卫的反直觉设计风险）、
  §12（D12）、§3.5（运行环境与支持矩阵）。
- 宪法 `.specify/memory/constitution.md`：原则 I（零 LangSmith 依赖）、原则 II、
  原则 IX（许可证与商标红线）、原则 V（人工验收）、质量门禁与发布门禁章节。
- 已有脚本：`harness/scripts/check_dist_purity.py`。
