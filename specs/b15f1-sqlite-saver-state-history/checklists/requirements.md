# Specification Quality Checklist: B15F1 · `SqliteSaver` + `get_state` / `get_state_history`

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-22
**Feature**: [spec.md](../spec.md)

> **记注（与 B14F1 / B20F2 同例）**：本清单是 `/speckit.specify` 维护的**规格质量**复核产物；
> 标记 `[x]` 表示该项「需求质量」已被复核满足，**不表示实现工作已完成**。

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注 1）**：本 feature 的需求本体
  就是**持久化后端的注入形态 + 读侧 / 写侧契约 + 对外状态读取**，与 B14F1 / B20F2 同例。
  已核对：spec 未规定测试框架、CI 配置写法、内部表结构 / SQL / 连接参数；`freegraph.persistence.SqliteSaver`
  与 `CompiledGraph.get_state` / `get_state_history` 是**提示词 §7 与 §10 强制要求锁定的公开形态**，
  不是内部实现细节；`src/freegraph/persistence/**` 仅作层归属说明，实现结构由 plan 定。
- [x] CHK002 Focused on user value and business needs — 通过：6 个用户故事均以「谁 + 为何」表述
  （P1 进程重启后状态还在 / P2 看当前状态 / P3 枚举历史做时间旅行 / P4 删除会话数据 /
  P5 并发写不破坏 / P6 `checkpoints` 流式事件）。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注 1）**：「checkpoint」「pending writes」
  「调度账本」「WAL / 文件锁」无法用非技术语言表述；但每个故事先讲用户视角的结果
  （「重启后还在」「看当前停在哪」「列出全部历史」「删掉会话」「并发不坏」），再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：`## 承接条款`（**H-1…H-11**）/ `## 形态锁定裁定`
  （**裁定 1…13**）/ `## User Scenarios & Testing`（**6** 个用户故事 + **18** 条 Given/When/Then +
  **43** 条 Edge Cases）/ `## Upstream Parity`（**25** 条语义点 + **21** 条差分场景 + **8** 条偏离登记（含 2 条已撤销）+
  **7** 条回溯修订）/ `## Requirements`（**37** 条 FR + Key Entities **5** 项 + 追溯表 **37** 行）/
  `## Success Criteria`（**27** 条 SC + A1–A4 判据映射）/ `## Assumptions` / `## 依据` /
  `## 下游承接`（**D-01…D-06**）+ 上游承接状态表齐备。编号**完整无跳号**。
- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：spec 正文**无未闭合标记**
  （实测 `grep -c 'NEEDS CLARIFICATION' spec.md` == **0**）；所有多解点由 **13 条形态锁定裁定**
  拍板并逐条给出「锁定值 / 理由」；**8 条偏离登记**逐条写明类别、被偏离判据、理由与承接方；
  **7 条破冻结面回溯修订**逐条写明「拆分而不删」的处置。

## Requirement Completeness

- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-037 全部「MUST + 可判定动作」；
  排他性表述消除歧义（「MUST NOT 另立 id 空间」「无 `checkpoint_id` 才合并 pending / 历史不合并」
  「MUST NOT 在门面层翻译成 `RunConfig`」「MUST NOT 伪造 checkpoint 事件」
  「MUST NOT 回改 `MemorySaver`」）。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-027 均含可数判据
  （数量 == `put` 次数 / 差异项 == 0 / 命中率 == 100% / 泄漏次数 == 0 / 残留 == 0 /
  伪造事件数 == 0 / 新增门禁编号数 == 0），并含**负向**判据（不合并 · 不伪造 · 不吞掉 · 不重建）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注 2）**：
  SC-002 的 `StateSnapshot` 8 字段、SC-005 的 G21/G23/G24/G25/G26/G27、SC-006 的协议结构检查、
  SC-021 的模块路径、SC-022 的 `setup()` / WAL、SC-023 的 L1 符号面 —— 这些是**宪法红线**
  （原则 VII / X / XI · ARCH-1）与验收判据 A1–A4 的唯一可判定口径，无法技术无关化；
  其余 SC 均以「对外可观察的结果」表述（重启后还在 · 当前状态可读 · 历史可枚举 ·
  并发不坏 · 流事件可消费）。
- [x] CHK009 All acceptance scenarios are defined — 通过：6 个用户故事共 **18** 条 Given/When/Then
  （US1 **3** · US2 **3** · US3 **3** · US4 **3** · US5 **3** · US6 **3**），覆盖正向、
  冲突与失败路径（未知线程 ⇒ `None` / 空 · 缺 `thread_id` ⇒ `ValueError` · 无 saver ⇒ `ValueError` ·
  裸 `str` ⇒ `TypeError` · 不可序列化 ⇒ `TypeError` · SQLite 锁 / 关闭连接 ⇒ 原样传播）。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **43** 条，覆盖未知线程 / 指定 id 不存在 /
  缺 `thread_id` / 非空 `checkpoint_ns` / 未挂 saver / 裸 `str` / `:memory:` / 数据库不存在 / 路径不可打开 /
  磁盘满 / 权限 / 损坏 / 锁 / 关闭连接 / `filter` 非法 key / 非 `Mapping` filter / 不可序列化 / `tasks.error` / `PregelTask.state` /
  metadata 缺键 / list 归一 / 重复写入 / `put_writes` 目标 / fan-out 多任务 /
  静态挂起空 interrupts / 真异常 + 中断 / `get_state` pending 合并 / `context` / 空历史 /
  `limit` / `before` / `list(None)` / 删除重建 / `NotImplementedError` / 回调抛错 /
  跨进程读取 / Windows 文件锁 / 上游版本漂移。
- [x] CHK011 Scope is clearly bounded — 通过：`## 范围提醒` + Assumptions + FR-010 / FR-025 / FR-036；
  明确排除 `update_state` / 时间旅行（B16F1）· `Store`（B17 已砍）· Postgres / async（v2）·
  trace 存储（B20F1 / B20F2）· 子图 / config 级 checkpointer（C26 · v2）·
  运行级删除 / 线程复制（v1 未实现）· retention / vacuum / 加密 / 迁移。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **20** 条（上游取证环境（含 SQLite 源码缓存） /
  spec 目录命名 / 分支 / Python 基线 / 规模 / 低并发定位 / 纯数据载荷 / `context` / 无 async /
  `NotImplementedError` / `stream(checkpoints)` / 跨进程测试 / Windows CI / 文件权限 /
  差分测试 / 人工验证 / API 兼容矩阵）+ 承接条款 **11** 条（H-1…H-11，各含承接方 + 里程碑 +
  动作 + 来源 + 落点；H-10 = B10F1 F-3 的 `tasks` 重建；H-11 = B14F1 `tasks` 读取权威移交）。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内含
  「需求 ↔ 成功标准追溯表」，**FR-001…FR-037** 逐条映射 SC 与判据 **A1–A4**；表内 **37** 行 ·
  **37** 条 FR 全部在表 · 引用的 **27** 条 SC 全部已定义 ⇒ **双向覆盖无空缺**。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（磁盘持久化 / 当前状态 / 历史枚举 /
  删除 / 并发 / 流式 checkpoint）全覆盖，且每条可独立验收（US2 只做「`get_state` 返回 8 字段」
  即成立；US3 只做「历史数量 + 倒序」即成立；US6 只做「事件数 == `put` 次数」即成立）。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：
  **A1** ↔ SC-001 / SC-016（历史数量 + 顺序）· **A2** ↔ SC-002 / SC-008（8 字段 + 中断投影）·
  **A3** ↔ SC-003 / SC-019 / SC-022（跨实例 / 跨进程 / setup + WAL）·
  **A4** ↔ SC-004 / SC-005（Windows 并发 + 零依赖），逐条对齐且均为可数判据。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注 1）** —— 同 CHK001；
  已核对无库选型（`sqlite3` / `json` 是提示词与零依赖红线的指定约束，不是自由选型）、
  无内部表结构 / SQL、无测试实现细节、无 CI 配置写法；只冻结**用户可见形态**
  （`SqliteSaver` 模块路径 / 构造签名 / `get_state` 调用形态 / 历史排序）与**可观察语义**。

## Notes

- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
- **记注 1（豁免项 · CHK001 / CHK003 / CHK016）**：本 feature 与 B14F1 / B20F2 同例 ——
  需求本体即**持久化协议方法与状态读取面**。`SqliteSaver` 的模块路径 / 构造参数与
  `get_state` / `get_state_history` 的调用形态是**提示词强制要求锁定的公开形态**；
  已核对 spec 未规定内部数据结构、序列化格式（除「标准库 JSON、纯数据」这一红线）、
  测试框架、CI 配置写法。
- **记注 2（部分豁免 · CHK008）**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、
  `setup()` / WAL、G21/G23/G24/G25/G26/G27、L1 符号面差异 == 0 —— 这些是**宪法红线**
  （原则 VII / X / XI · ARCH-1）与验收判据 A1–A4 的唯一可判定口径，技术无关化后即失去判据能力
  ⇒ 保留原样并在此登记。
- **记注 3（形态锁定轮 · 本 spec 阶段 · 2026-11-22）**：**13 条裁定**（编号连续无跳号）
  逐条含「锁定值 / 理由」。影响面最大的七条：
  ① **裁定 1**（读取面在 `CompiledGraph`，`SqliteSaver` 只做 8 方法）—— 与上游同款、
  不新增第二套读取入口；
  ② **裁定 2**（`SqliteSaver(conn)` / `from_conn_string(...)` · 单连接 + 锁 + WAL · `:memory:`）——
  全面对齐上游（clarify 轮确认）；
  ③ **裁定 3**（标准库 JSON 纯数据）—— 零依赖 + C19 纯数据约束；
  ④ **裁定 8**（`get_state` 无 id 合并 pending / 有 id 不合并；历史不合并；`tasks` 上游
  **next-tasks**；`interrupts` 按任务顺序展平）—— 全面对齐上游，同时满足 B12F1 的 D-7；
  ⑤ **裁定 9**（历史按 `checkpoint_id` 倒序）—— 与上游文档 / E8 一致；
  ⑥ **裁定 10**（`checkpoints` 四键信封 + `StateSnapshot` payload；`tasks` / `interrupts`
  为 next-tasks 投影）—— 关闭 B14F1 D-02 / B8F2 D-2，且不改 B8F2 的七档语义；
  ⑦ **裁定 13**（上游 next-tasks：`next` + `.scheduler["fanout"]` + pending `__interrupt__`）——
  承接 B10F1 F-3 的节点名，彻底替换 B14F1 的「本轮完成态」读取权威。
- **记注 4（未闭合项）**：**无**。spec 正文无 `[NEEDS CLARIFICATION]` 标记（实测 == 0）·
  **13 条裁定全部闭合** · **37 条 FR 全部挂到 SC** · **27 条 SC 全部被 FR 覆盖** ·
  **8 条偏离登记（X-02 / X-06 已撤销 ⇒ 当前有效 6 条）**均属宪法允许的三类 ·
  **7 条破冻结面回溯修订**（新增 B14F1 `tasks` 语义移交）均按「拆分而不删」处置。
- **记注 5（偏离登记 · spec 目录命名）**：speckit 通用规则为 `NNN-<short-name>`；
  本仓库既有 feature 全部采用 `<b<N>f<M>-<slug>`（宪法 v1.4.2 的目录约定）⇒ 本 feature 用
  `specs/b15f1-sqlite-saver-state-history`（**已偏离通用规则 · 已登记**）。
- **记注 6（上游证据边界 · 2026-11-22 clarify 后更新）**：上游 SQLite 后端
  `langgraph-checkpoint-sqlite 3.1.1`（MIT）源码在 uv 缓存中，已作为**连接 / 并发 / WAL / 构造入口**
  的行为锚点；该发行包未安装进 `.venv` ⇒ 差分运行时不可导入则 skip。
  `get_state` / `get_state_history` 的排序与调用形态用已安装的 `langgraph 1.2.11` +
  官方文档 + E8 实测取证。序列化仍归**必须自研区 ③**（X-05）。
- **记注 7（clarify 轮决议 · 2026-11-22）**：用户确认「有上游参考」且选择**全面对齐上游**；
  已把连接模型、`from_conn_string`、`:memory:`、WAL、`get_state` 的 pending 合并改为上游同款；
  X-02 / X-06 撤销；仅保留 B14F1 冻结契约与零依赖 / `context` 红线造成的差异。
  第二轮确认：早期口径为「`get_state` 与历史都从 pending `__interrupt__` 重建 `tasks`」；
  **2026-11-23 修订**：按宪法原则 XII / XI 彻底改为上游 **next-tasks**（裁定 8 / 13 / FR-037 /
  SC-027），`pending __interrupt__` 只用于给 next task 附加 `interrupts`；`__interrupt__` 值采用
  channel-aware 编码；`config=None` 仅在类型层接受（解析后缺 `thread_id` ⇒ `ValueError`）。
