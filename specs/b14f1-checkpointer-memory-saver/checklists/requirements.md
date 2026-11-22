# Specification Quality Checklist: B14F1 · Checkpointer 协议 + `MemorySaver`（快照 + pending writes 双层持久化）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-22
**Feature**: [spec.md](../spec.md)

> **记注（与 B1F1 / B2F1 / B7F1 / B9F1 / B10F1 / B18F1 同例）**：
> 本清单是 `/speckit.specify` 维护的**规格质量**复核产物；
> 标记 `[x]` 表示该项「需求质量」已被复核满足，**不表示实现工作已完成**。

## Content Quality

- [x] CHK001 No implementation details (languages, frameworks, APIs) — **豁免通过（记注 1）**：本 feature 的需求本体
  就是**持久化协议的方法面 + 快照 / 写入的分层语义 + 运行期落盘时机**，与 B9F1 / B10F1 同例。
  已核对：spec 未规定测试框架、CI 配置写法、内部数据结构的具体类层次；`freegraph.persistence.MemorySaver`
  与 `CheckpointTuple` 是**用户可见的 API 形态**（形态锁定裁定 1 / 3，提示词 §10 强制要求锁定），
  不是内部实现细节；`src/freegraph/persistence/memory.py` 仅作落点说明，实现结构由 plan 定。
- [x] CHK002 Focused on user value and business needs — 通过：6 个用户故事均以「谁 + 为何」表述
  （P1 复盘每一步状态 / P2 崩溃后重放未落地写入 / P3 多会话互不干扰 / P4 挂起后用真实 saver 恢复 /
  P5 静态挂起与 fan-out / 屏障不丢现场 / P6 trace 与状态历史按 checkpoint id 对齐）。
- [x] CHK003 Written for non-technical stakeholders — **豁免通过（记注 1）**：「super-step」「pending writes」
  「调度账本」「保留通道名」无法用非技术语言表述；但每个故事先讲用户视角的结果
  （「每一步都看得到」「未落地的写入也记下来」「两个会话互不干扰」「审批后能从断点跑完」），
  再给技术判据。
- [x] CHK004 All mandatory sections completed — 通过：`## User Scenarios & Testing`（**6** 个用户故事 +
  **18** 条 Given/When/Then + **31** 条 Edge Cases）/ `## Upstream Parity`（**21** 条语义点 +
  **15** 条差分场景 + **8** 条偏离登记 + **6** 条回溯修订）/ `## Requirements`（**35** 条 FR +
  Key Entities **8** 项 + 追溯表 **35** 行 + Out of Scope **10** 条）/ `## Success Criteria`
  （**25** 条 SC）/ `## Assumptions`（**15** 条）/ `## 依据` 齐备；另含抬头「承接条款」**12** 条
  （H-1…H-12）+「形态锁定裁定」**13** 条 +「下游承接」**8** 条（D-01…D-08）。
  FR / SC / 裁定 / X 编号**完整无跳号**（FR-001…FR-035 · SC-001…SC-025 · 裁定 1…13 · X-01…X-08）。
- [x] CHK005 No [NEEDS CLARIFICATION] markers remain — 通过：spec 正文**无未闭合标记**
  （实测 `grep -c 'NEEDS CLARIFICATION' spec.md` == **0**）；**5 处**关键多解点已向发起者提问并获拍板
  （见 `## Clarifications` → `### Session 2026-11-22`），其余多解处由 **13 条形态锁定裁定**
  拍板并逐条给出「锁定值 / 备选 / 理由 / 落点」；**8 条偏离登记**逐条写明类别、被偏离判据、
  理由与承接方；**6 条破冻结面回溯修订**逐条写明「拆分而不删」的处置。

## Requirement Completeness

- [x] CHK006 Requirements are testable and unambiguous — 通过：FR-001…FR-035 全部「MUST + 可判定动作」；
  排他性表述消除了歧义（「MUST 原样保存 scheduler」「MUST NOT 改写调度版本」⇒ 排除双版本源；
  「挂起写计入该轮」⇒ 排除重复快照；「MUST 先 put_writes 再原样抛」⇒ 排除异常包装；
  「MUST NOT 为 fan-out 另立载体」⇒ 排除第二套持久化；「`context` MUST NOT 出现」⇒ 排除旁路）。
- [x] CHK007 Success criteria are measurable — 通过：SC-001…SC-025 均含可数判据
  （快照数 == 轮数 + 1 / 差异项 == 0 / 命中率 == 100% / 残留 == 0 / 串扰次数 == 0 /
  回滚次数 == 0 / 伪造事件数 == 0 / 新增门禁编号数 == 0），并含**负向**判据
  （互不可见 · 不重复 · 不改写 · 不包装 · 不伪造 · 不自创留痕）。
- [x] CHK008 Success criteria are technology-agnostic (no implementation details) — **部分豁免（记注 2）**：
  SC-004 的「调度版本逐 key 相等」、SC-006 的协议结构检查、SC-008 的 `StateSnapshot` 8 字段、
  SC-012 的模块路径、SC-019 的 `Span` 11 字段、SC-024 的 G25 / L1 符号面 —— 这些是**宪法红线**
  （原则 VII / XI · ARCH-1 · G25）与**验收判据 A1–A4** 的唯一可判定口径，无法技术无关化；
  其余 SC 均以「对外可观察的结果」表述（每一步可见 · 写入可重放 · 会话隔离 · 恢复跑完 ·
  屏障不重触发 · trace 对齐）。
- [x] CHK009 All acceptance scenarios are defined — 通过：6 个用户故事共 **18** 条 Given/When/Then
  （US1 **3** · US2 **3** · US3 **3** · US4 **3** · US5 **3** · US6 **3**，其中 US2 第 2 条与
  US3 第 3 条各覆盖两条子断言），每条独立可测，且覆盖正向、冲突与失败路径
  （未知线程 ⇒ `None` · 缺 `checkpoint_id` ⇒ `KeyError` / 指定 id 不存在 ⇒ `ValueError` · 非法 saver ⇒ `TypeError` ·
  未挂 saver 的恢复 ⇒ `InterruptError` · 真异常 + 中断 ⇒ 留痕后原样抛）。
- [x] CHK010 Edge cases are identified — 通过：Edge Cases 段 **31** 条，覆盖未知线程 / 空写入 /
  缺 `checkpoint_id` / 指定 id 不存在 / 重复写入 / metadata 缺键 / list 归一 / 非 Mapping / 深拷贝失败 /
  缺 thread_id / 空串 thread_id / 版本号类型 / id 排序 / before / limit / filter / delete 后重建 /
  `NotImplementedError` 两方法 / 编译期非法值 / `True` / `False` / `None` / `context` /
  静态挂起空 interrupts / 首轮前静态挂起 / interrupt_after / 真异常 + 中断 / fan-out 多任务 /
  屏障恢复 / 回调抛错 / 回调重入 / 并发 / 上游版本漂移。
- [x] CHK011 Scope is clearly bounded — 通过：Out of Scope **10** 条 + FR-025 / FR-034；明确排除
  `SqliteSaver` 与历史对外方法（B15F1）· `update_state` / 时间旅行（B16F1）· `Store`（B17 已砍）·
  Postgres / 跨进程（v2）· `stream(checkpoints)` 消费端（B8F2 / B15F1）· async saver ·
  `delete_for_runs` / `copy_thread` 语义 · 子图 checkpointer 继承（C26 · v2）· 序列化格式（B15F1）。
- [x] CHK012 Dependencies and assumptions identified — 通过：Assumptions **15** 条
  （上游取证环境 / spec 目录命名 / 分支 / Python 基线 / 规模 / 开发调试定位 / 别名 / 无 async /
  两方法边界 / context / stream 边界 / 深拷贝 / 无 thread_id / 差分测试 / 人工验证 / 版本漂移）+
  抬头「承接条款」**12** 条（H-1…H-12，各含承接方 + 里程碑 + 动作 + 来源 + 落点）。

## Feature Readiness

- [x] CHK013 All functional requirements have clear acceptance criteria — 通过：spec 内含
  「需求 ↔ 成功标准追溯表」，**FR-001…FR-035** 逐条映射 SC 与判据 **A1–A4**
  （A1 快照持久化 ↔ SC-001 / SC-008 · A2 pending writes ↔ SC-002 · A3 thread 隔离 ↔ SC-003 ·
  A4 协议满足 ↔ SC-006）；表内 **35** 行 · **35** 条 FR 全部在表 · 引用的 **25** 条 SC 全部已定义
  ⇒ **双向覆盖无空缺**。
- [x] CHK014 User scenarios cover primary flows — 通过：主流程（每步快照 / pending writes 分层 /
  两种输入形态（快照 / 写入）· 两 thread 隔离 / 挂起恢复跑完 / 静态挂起与 fan-out / 屏障不重触发 /
  span 与事件按 checkpoint id 对齐）全覆盖，且每条可独立验收
  （US2 只做「写入后取回」即成立；US3 只做「两会话互不可见」即成立；
  US5 只做「静态挂起现场往返」即成立）。
- [x] CHK015 Feature meets measurable outcomes defined in Success Criteria — 通过：
  **A1** ↔ SC-001 / SC-008（快照数量 + 8 字段）· **A2** ↔ SC-002（pending writes 逐项相等）·
  **A3** ↔ SC-003（两 thread 互不可见）· **A4** ↔ SC-006（八方法 + 结构化子类型检查），
  逐条对齐且均为可数判据；提示词 §6 的四条验收判据 A1–A4 在 SC 中**逐条可判定**。
- [x] CHK016 No implementation details leak into specification — **豁免通过（记注 1）** —— 同 CHK001；
  已核对无库选型、无模块内部实现规定、无测试实现细节、无 CI 配置写法；只冻结**用户可见形态**
  （`MemorySaver` 模块路径 / 构造签名 / `CheckpointTuple` 三字段 / 写侧关键字）与**可观察语义**
  （快照计数 / 取回 / 隔离 / 恢复 / 版本一致）。

## Notes

- 标记 `[x]` 表示该项「需求质量」已被复核满足，不表示实现工作已完成。
- **记注 1（豁免项 · CHK001 / CHK003 / CHK016）**：本 feature 与 B9F1 / B10F1 / B18F1 同例 ——
  需求本体即**持久化协议的方法面、快照 / 写入分层与运行期落盘时机**。`MemorySaver` /
  `CheckpointTuple` 的模块路径与字段是**提示词 §10 强制要求锁定的公开形态**，不是内部实现；
  已核对 spec 未规定内部数据结构、序列化方案、测试框架、CI 配置写法。
- **记注 2（部分豁免 · CHK008）**：`StateSnapshot` 8 字段、`Checkpointer` 8 方法、
  `Span` 11 字段、G25 层方向、L1 符号面差异 == 0、协议结构检查、模块路径 —— 这些是
  **宪法红线**（原则 VII / XI · ARCH-1）与**验收判据 A1–A4** 的唯一可判定口径，
  技术无关化后即失去判据能力 ⇒ 保留原样并在此登记。
- **记注 3（裁定轮 · 本 spec 阶段 · 2026-11-22）**：**13 条形态锁定裁定**（编号连续无跳号）
  逐条含「锁定值 / 备选 / 理由 / 落点」。影响面最大的五条：
  ① **裁定 1**（模块路径锁 `freegraph.persistence.MemorySaver`）—— 层注册表已固定 L4 = `persistence`，
  门面不得 import L4（G18 ⇒ 不放在 `freegraph.graph`）；
  ② **裁定 2**（编译期校验）—— 校验在 L3 边界、用 L1 协议，**不让 L3 import L4**（向上 import 违规）；
  ③ **裁定 4**（双版本命名空间）—— `get_next_version` 用 `int+1`，**不**抄上游 memory 的字符串，
  否则与 B7F1 的触发版本漂移（X-02）；
  ④ **裁定 5**（每轮快照策略）—— 初始惰性写、挂起写计入该轮、收敛空轮不写 ⇒ 计数可判定；
  ⑤ **裁定 10**（真异常 + 中断留痕）—— 先 `put_writes` 再原样抛，异常 identity 不变
  ⇒ 消解 B10F1 X-5 / B12F1 X-4，且不把「留痕」宣传为新能力。
- **记注 4（未闭合项）**：**无**。spec 正文无 `[NEEDS CLARIFICATION]` 标记（实测 == 0）·
  **13 条裁定全部闭合** · **35 条 FR 全部挂到 SC** · **25 条 SC 全部被 FR 覆盖**。
  **8 条偏离登记**均属宪法允许的三类（自研区 / 更明确的失败信号 / 破已冻结契约面）·
  **6 条破冻结面回溯修订**均按「拆分而不删」处置。
- **记注 5（偏离登记 · spec 目录命名）**：speckit 通用规则为 `NNN-<short-name>`；
  本仓库既有 feature 全部采用 `<b<N>f<M>-<slug>`（宪法 v1.4.2 的目录约定）⇒ 本 feature 用
  `specs/b14f1-checkpointer-memory-saver`（**已偏离 · 已登记**）。
- **记注 6（上游取证 · 本轮已闭合）**：本机 `.venv` **已安装** `langgraph 1.2.11` ⇒ 本 spec 引用的
  行号（`checkpoint/base/__init__.py` · `checkpoint/memory/__init__.py` · `pregel/_checkpoint.py` ·
  `pregel/_runner.py` · `pregel/_loop.py` · `pregel/debug.py` · `types.py` · `graph/state.py`）
  均为 **2026-11-22 本轮实际核对**所得；差分场景 D-01…D-15 的「上游在场」路径由
  `tests/differential/parity_probe.py` 承担（上游缺席 ⇒ skip）。⚠️ 换上游版本 MUST 重新核实全部行号。
- **记注 7（跨 feature 承接 · 十二条上游 + 八条下游）**：抬头「承接条款」表列 **H-1…H-12**；
  「下游承接」表列 **D-01…D-08**。宪法「只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽任何门禁判据」
  三条**均未破**；本 spec 未动 `src/**` 与 `tests/**`。
- **记注 8（plan / tasks 阶段的三条待办）**：
  ① **偏离登记 + 发起者追认**（宪法 v1.6.0）—— 本 feature **不交付** `target.py` 的固定脚本端到端
  （依赖 M4 的 release 链）⇒ 宪法质量门禁的固定脚本项**物理不可达成** ⇒ MUST 落 `plan.md` 的
  偏离登记项 + `tasks.md` 的阻断合入的追认任务 + `manual-verification.md` 的追认文字
  （**MUST NOT** 代签 · MUST NOT 以此放宽任何门禁判据）；
  ② **运行期落盘接线的冻结面核对** —— 在 `_run_graph_loop` / `_run_round` / `_stream.py` 的既有
  冻结断言上**只增不改**；任何需要改 B10F1 / B13F1 写侧的调整 MUST 走「回溯修订 + 拆分而不删」；
  ③ **上游行号的换版重核**（FR-035）⇒ 换上游版本时的取证动作。
- **记注 9（编号连续性快照）**：FR-001…FR-035（**35** 条）· SC-001…SC-025（**25** 条）·
  裁定 1…13（**13** 条）· 偏离 X-01…X-08（**8** 条）· 承接 H-1…H-12（**12** 条）+
  下游 D-01…D-08（**8** 条）· 用户故事 **6** 个 · 验收场景 **18** 条 · Edge Cases **31** 条 ·
  Key Entities **8** 项 · Out of Scope **10** 条 · Assumptions **15** 条 · 追溯表 **35** 行 ·
  差分场景 D-01…D-15（**15** 条）—— 全部**编号完整无跳号**。
- **记注 10（与既有 feature 的一致性核对）**：本 spec 引用的 B1F1 冻结面（`StateSnapshot` 8 字段 ·
  含 `parent_config`）与 `src/freegraph/contracts/types.py` **逐条一致**；B2F1 冻结面
  （`Checkpointer` **8** 方法 · 含 `delete_for_runs` / `copy_thread`）与
  `src/freegraph/contracts/protocols.py` **逐条一致**（并**事实订正**提示词的六方法简写）；
  B10F1 的读侧 / 写侧接缝与 `specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md`
  §2…§6 **逐条一致**；B12F1 / B13F1 / B11F1 / B7F4 / B7F2 / B8F2 / B8F3 / B18F1 的下游承接
  逐条落成 FR；门禁编号（G1–G30）与 `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`
  一致 ⇒ **零新增门禁编号**。
- **记注 11（实现落点的层方向核对）**：`src/freegraph/persistence/**` 是 **L4**，只 import
  **L1 + 标准库**；运行期接线（L2 / L3）通过**鸭子类型**调用 `checkpointer`，
  **MUST NOT** import L4；`compile()` 的校验在 L3、用 L1 协议，**MUST NOT** import L4
  （否则 L3 → L4 是向上 import，G25 判红）。该三条方向均已写入裁定 1 / 2 / FR-008 / SC-024。
- **记注 12（澄清轮 · 2026-11-22 · 已向发起者提问 5 次）**：本轮就 **5** 处关键多解点提问并全部获拍板
  **选项 A**：① `checkpoints` 事件数据源的公开形态（`on_checkpoint` + `list()`）·
  ② `get_next_version` 返回 `int` · ③ `CheckpointTuple` 恰好 3 字段 ·
  ④ 无 `thread_id` 时运行期跳过落盘、直接调用 saver 抛 `ValueError` ·
  ⑤ 静态挂起的快照计数 / 去重策略（见 `spec.md` 的 `## Clarifications` → `### Session 2026-11-22`）
  ⇒ 其余多解处均按「上游优先 + 已冻结契约」直接裁定（提示词已把「interrupt 恢复必须依赖
  checkpointer」等关键形态拍板）⇒ **零未闭合项**；若 plan / tasks 阶段发现新的跨 feature 冲突，
  MUST 走「回溯修订 + 拆分而不删」，**MUST NOT** 静默放宽本 spec 的判据。
