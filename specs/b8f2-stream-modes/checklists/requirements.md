# Specification Quality Checklist: B8F2 · `stream()`：多模式流式输出 + `StreamWriter`

**Purpose**: 本仓宪法口径的规格质量自检（**替代** speckit 的通用模板 —— 本仓 spec **必然**含
实现细节与上游锚点，见宪法原则 VIII / XI）
**Created**: 2026-11-19
**Feature**: [spec.md](../spec.md)

> ⚠️ **通用模板项（"No implementation details" / "technology-agnostic"）在本仓**不适用**：
> 本仓 spec 的**判据级**要求（原则 VI）必须点名**文件 / 行号 / 上游锚点**（原则 VIII 证据纪律）
> ⇒ ⇒ 模板项一律**不勾**（**N/A**），改用下列仓库口径条目。

## 1. 规格完整性

- [x] 全部强制章节齐备（承接条款 / 下游承接条款 / Clarifications / User Scenarios /
  Edge Cases / Upstream Parity / Requirements / Key Entities / Out of Scope /
  Success Criteria / 追溯表 / Assumptions）
- [x] 零澄清标记残留（**零** `NEEDS CLARIFICATION` · Q1…Q10 **全部**按原则 XI「上游有答案 ⇒
  照抄」写死 · 裁定 1–10）
- [x] 每个用户故事带 **Independent Test** + **Acceptance Scenarios**
  （US1 `values` P1 / US2 `updates` P1 / US3 `custom` P1 / US4 七 mode P2 /
  US5 `tasks`+`debug` P2 / US6 零副作用 P3）
- [x] Edge Cases 覆盖：非法 / 空 / 重复 mode · 零节点图 · `None` 写入 · 并发 custom 顺序 ·
  中断 · 真实异常 · 惰性 · 提前停止 · `checkpoints`/`messages` 空序列 · `thread_id` 解析 ·
  `RunConfig.run_id` 不生效 · 大小写敏感 · `run_id` 唯一性 · L2 符号数不变
- [x] Out of Scope 明确点名归属 feature（`astream` / trace span / `TraceSink` /
  `checkpoints` 源 / `messages` 抽取 / `Command` 恢复 / C25 已作废的别名 / UI / 图导出）
- [x] 承接条款 **H-1…H-10** 与下游承接 **D-1…D-4** 逐条可追溯（来源 + 本 spec 落点）

## 2. 判据级可判定性（宪法原则 VI）

- [x] 每条 **FR**（**37** 条）可由测试或人工记录判定
- [x] 每条 **SC**（**23** 条）带**量化**判据（比例 == 100% / 计数 == 0 / 序列逐字相等 /
  符号数 == 23 / 事件键集恰四键）
- [x] spec 的 **FR → SC 追溯表**覆盖 **SC-001…SC-023**；未单列追溯的 FR（如 FR-007 /
  FR-023 / FR-028 / FR-031 的部分子项 / FR-034）由 **SC-005 / SC-013 / SC-019 /
  人工验证**判定；**FR-024** 由 **SC-023 / T074 / T075** 判定；**FR-037** 由
  **SC-022 / T073 / T075** 判定 ⇒ 无「无判据 FR」
- [x] 关键判据由**可观测**量承载（`values` 最后一条 == `invoke` · `updates` 归约合并 ==
  `invoke` · 每条事件恰四键 · 线程数 == 0）
- [x] **载体存在**：`SuperStepResult.tasks`（SC-006）· `values` 收尾 `__interrupt__`
  （SC-017）· 差分探针 D-121…D-136（SC-015）· `acceptance.py`（SC-019）· `writer` 注入
  （SC-021 / T072）· 递归 / 并发（SC-022 / T073）· 路由一致性 + 双参 `config`（SC-023 / T074）·
  **L2 私有 `_run_single_step` / `_stream_tick`（T075）** 均有明确落点
- [x] ⚠️ **破冻结面全登记**：**T-1**（B7F1 `SuperStepResult` 构造签名）· **T-2**（B12F1
  四字段零改动 · **新发现**）· **T-3**（L1 + **L3** `stream` 的 `config` 注解 + `stream_mode`
  默认值 + **B7F2 compile-contract / data-model / plan / tasks T006 注记**）· **T-4**（B10F1 契约 §3 +
  `_interrupt.py` docstring）· **T-5**（B2F2 公开面 7/21 → 8/22）⇒ 全部落在**同一次**追认
- [x] **ARCH-3 例外已登记**（plan R-6）：B18F1 / B19F1 读取 L2 私有运行期 contextvar
  （`str | None` 元数据），不新增公开符号、不改 ARCH-1 方向
- [x] 「拆分而不删」与「原描述不改写」两段义务已写死（T-1…T-5）
- [x] 零「永久红 CI」：`checkpoints` / `messages` 的判据是「零事件且不抛」，不是
  `NotImplementedError`；验收脚本与实现漂移立刻红
- [x] **R-5**（门禁 3/4/5 物理不可达）已登记：引用 B8F1 R-2 / B25F1，写明判据未放宽，
  追认文字与 T-1…T-5 同一次

## 3. 上游优先（宪法原则 XI）

- [x] 上游对照 **P-01…P-23** 齐备，每条带 **版本 + `路径:行号`**
  （`langgraph 1.2.11` / `langchain-core 1.7.6` · 2026-11-19 实测）
- [x] 行为断言有**实测**支撑（**E-1…E-18** · 于本仓库 `.venv` 真跑 `StateGraph`）
- [x] **七种 mode 名逐字钉死**（`StreamMode` · `types.py:122-124`）⇒ 无自造名字
- [x] 偏离登记 **X-1…X-6** 与对照表**逐字一致**：
  **X-1 ↔ P-02 / P-03 / P-06 / P-16** · **X-2 ↔ P-15** · **X-3 ↔ P-07** ·
  **X-4 ↔ P-08** · **X-5 ↔ P-17** · **X-6 ↔ P-23**
- [x] 三态标注一致：DIFF（X-1 / X-3 / X-4 / X-6）· STRICTER（X-2 / X-5）⇒ 无「对照表 STRICTER
  但偏离登记 DIFF」的错配；P-11 仅载体 SAME，`custom` 时机归 P-23 / X-6
- [x] P-20（`StreamWriter` 关键字注入）已由「能力尚未交付」改为 **SAME**：参数名 `writer`
  （上游 `_runnable.py:183-188`）· 无流 no-op · 由 SC-021 判定；`stream_writer` 是 runtime key。
- [x] P-21（默认档 / `None`）为 **SAME**（`updates`；由 SC-001 / D-135 判定）·
  P-22（`stream(Command)`）为「能力尚未交付」（B14F1 / B15F1 · 不记偏离）·
  P-23（`custom` 产出时机）为 **DIFF**（X-6 · 必须自研区 ②：上游并发下的顺序不确定）。
- [x] **「能力尚未交付」未被误记**：`checkpoints`（B14F1）· `messages`（freechain）·
  `Command` 恢复 / 会话连续（B14F1 / B15F1 / B16F1）⇒ 全部走 Out of Scope / 下游承接，
  **不记偏离**；⚠️ 关键字注入**已交付**（参数名 `writer` · FR-036 / SC-021）⇒ 不属
  「能力尚未交付」。
- [x] 差分场景 **D-121…D-136**（**16** 条）齐备；判词分布 == SAME **10** / DIFF **4** /
  STRICTER **2**；非 `SAME` 的 6 条均有非空理由（X-1…X-6；其中 X-6 为 custom 时机，无对应 D 行）
- [x] 差分落点 = `tests/differential/parity_probe.py`（沿用 B5F2「缺席即 skip」纪律）
- [x] **双份维护同步义务**：本 spec 的 P 表 / X 表与 `contracts/upstream-parity.md` MUST
  同时落盘、发现漂移双侧同改（plan 阶段落实）
- [x] 明确记录提示词与实际上游的**九处差异**（引文差异 ①…⑨）与**新发现冻结面**（④）：
  `RunConfig.run_id` 现状冲突 · `tasks` 上游是两条 dict · 「不迭代也跑完」不是惰性行为 ·
  B12F1 的四字段冻结 · 立项书「5 种模式」过期 · 上游参数名是 `writer`（不是 `stream_writer`）·
  `StreamWriter` 关键字注入已交付（P-20 SAME）· `custom` 实时性收敛为轮末批量（P-23 / X-6）·
  **「零新增 L2 入口」解释为「零新增公开入口」**（允许私有 `_stream_tick`）
- [x] 零悬空行号：所有上游锚点均来自 **1.2.11** 的实际安装包（`.venv`）并在 §2 给出实测

## 4. 编号与边界

- [x] 编号域零碰撞：本 spec 自有 = `FR-001…FR-037` / `SC-001…SC-023` / `P-01…P-23` /
  `X-1…X-6` / `H-1…H-10` / `D-1…D-4` / `D-121…D-136` / `T-1…T-5` / 裁定 **1–10** /
  plan 登记 **R-1…R-6** / research 决策 **D-01…D-15**
  ⇒ 上游引用一律带来源 spec 名（如「B7F3 的 D-1」「B8F1 的 D-1」）⇒ 无歧义
- [x] 七种 mode 名作为 **FR-002** 逐一列出；「自造名字 / 静默空流」被 **X-2** 显式禁止
- [x] `values` 的归一**单一实现点**（`_full_state` · L3）已写死；L2 只产出稀疏状态
- [x] `SuperStepResult` **只增字段、不删 4 个既有字段**已写死
- [x] `stream()` 与 `TraceSink` **两条独立通道 + 共享 id** 已写死（H-9 / D-3）
- [x] 规模口径**未单方面修改**（FR-034 · 与 B8F1 的 R-5 同款）

## Notes

- 本 checklist 是**评审者所有**的规格质量工件；`[x]` 表示**需求质量**已评审通过，
  不代表实现完成。
- 通用 speckit 模板中「无实现细节 / 技术无关」两项在本仓**刻意不适用**：本仓的判据必须
  可追溯到**上游文件 / 行号**与**本仓文件 / 行号**（原则 VIII / XI）。
- 实施开始前 MUST 记录绿基线；破冻结面的「冻结断言清单」MUST 实测化（宪法 v1.11.0）。
