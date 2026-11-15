# 上游对照 · B13F1 · 静态中断点 + `recursion_limit`

**Spec**: [../spec.md](../spec.md) · **Research**: [../research.md](../research.md) · **Date**: 2026-11-15
**上游版本**: `langgraph` **1.2.11**（`/home/ctyun/.local/lib/python3.12/site-packages/langgraph`）

> **原则 XI**：上游是**唯一权威**；行为断言 MUST 有**实测**支撑。
> 本文件是 spec 的「上游对照表 + 差分场景组 + 偏离登记」的**取证底稿**；
> 语义以 `spec.md` 为准。

---

## §1 上游对照表（P-01…P-20）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | 有效缺省 = 10007 | `_internal/_config.py:32`（`int(getenv(..., "10007"))`） | 硬编码 10007 · 不读 env | SAME（数值）/ DIFF（env） | 宪法 I ⇒ X-4 |
| P-02 | 载体 = config 的 `recursion_limit` 键 | `_internal/_config.py:184-186` | dict 规范 · `RunConfig` 等价 | SAME | 与 graph_core 一致 |
| P-03 | 上限 ≥ 1 | `pregel/main.py:2563-2564` | `ValueError`；非 int / bool / 浮点 ⇒ `TypeError` | SAME（≥1）/ **STRICTER（类型）** | X-7 |
| P-04 | 按 super-step 轮次计 | `pregel/main.py:3004-3011` · `_loop.py:608` / `:1701` | 每执行轮 1；N 任务同轮仍 1 | SAME | 与 `SchedulerState.step` 对齐 |
| P-05 | 异常类型 / 结构化 | `errors.py:87-99` 类体为空 · 消息 `main.py:3005-3011` | L1 `GraphRecursionError` 结构化 | SAME（类型）/ DIFF（消息） | B1F1 · X-5 |
| P-06 | 静态断点在「图定义侧」 | `graph/state.py:1177-1188` · `main.py:768-769` / `:814-815` | `GraphSpec` 字段；`compile()` 由 B7F2 填 | DIFF（载体） | X-2 |
| P-07 | 断点节点名必须在图里 | `graph/state.py:1177-1188`（compile 校验入口）· 实测 E-10：`ValueError: Interrupt node ... not found` | `GraphSpec` 构造期 `ValueError` | SAME（信号）/ **STRICTER（时机）** | X-3 |
| P-08 | before = 执行前整轮挂起 | `_loop.py:667-670` | 递归检查后、执行前挂起；整轮不执行 | SAME | E-03 |
| P-09 | after = 写合并后挂起 | `_loop.py:720-723` | 执行 + 写合并后、下一轮前挂起 | SAME | E-04 |
| P-10 | 只在上次中断后有更新时触发 | `_algo.py:155-185` | 同一断点无新通道写入时不重复触发 | SAME | 防止恢复即再挂起 |
| P-11 | 静态异常载荷为空 | `_loop.py:670` / `:723` 抛 `GraphInterrupt()` | 内部空载荷 | SAME | 无审批内容 |
| P-12 | 静态结果键 | `_loop.py:667-670` / `:720-723`（静态断点抛空载荷）· `main.py:3938-3954`（结果键装配）· 实测 E-03 / E-04：**无** `__interrupt__` 键 | 返回 `"__interrupt__": ()` | DIFF（结构） | 明确挂起信号 ⇒ X-1 |
| P-13 | 恢复入口 | `_loop.py:861-864`（`is_resuming` 的 `self.input is None`）· `:1030`（`CONFIG_KEY_RESUMING` 缺失才报空输入）· 实测 E-05：`invoke(None, config)` | `run_graph(spec, None, ...)` 同款 | SAME | 会话连续 |
| P-14 | `Command(resume=...)` 值被忽略 | `_loop.py:904-925`（恢复值只按挂起中断投递）· `:667-670` / `:720-723`（静态断点无节点级中断）· 实测 E-06 | 接受但值不投递 | SAME | 无节点级中断 |
| P-15 | fan-out N 任务 × 静态断点 | `_algo.py:962-986`（Send 任务下一轮执行 · 独立 task id）· `:253-256`（任务排序）· `_loop.py:667-670` / `:720-723` · 实测 E-07 / E-08：3 任务（1 标准 + 2 Send）before 全 0 / after 各 1；单个挂起；`interrupts=()` | 同款；N 任务独立 | SAME（任务粒度）/ DIFF（载荷记录） | 裁定 8 · X-1 |
| P-16 | before + after 同节点 | `_loop.py:667-670`（before）· `:720-723`（after）· 实测 E-09：before → 恢复 → 执行 → after | 同款 | SAME | 优先级 |
| P-17 | 裸 `"*"` = All；`["*"]` 非法 | `graph/state.py:1177-1188` · `:1257-1264` · 实测 E-11 | 裸 `"*"` 展开为**可执行节点**；`["*"]` 失败 | SAME | Q13 |
| P-18 | 递归上限先于静态 before | `_loop.py:608-610` 先判 | 递归检查先于 before | SAME | 裁定 7 |
| P-19 | 静态挂起且 `next` 为空 | `_loop.py:720-723`（最后节点 after）· `:904-927`（恢复路径无 `no_pending_interrupt` 信号）· 实测 E-13：最后节点 after `next == ()`；上游无 `no_pending_interrupt` | 增加 `suspension_kind` + `static_ack`；空 `next` 仍可恢复 | DIFF（结构） | X-8 |
| P-20 | 低层手动入口 | **缺席断言**（检索 `langgraph/pregel/` 与 `langgraph/graph/`）：上游**没有** `run_super_step` / `run_super_steps` 这类手动入口 | freegraph 低层入口收到非空静态字段 ⇒ 显式拒绝 | DIFF（自研区 ③） | X-6 |

### §1.1 三态一致性

- 标 **DIFF** 的 P-01 / P-05 / P-06 / P-12 / P-15 / P-19 / P-20 分别对应
  **X-4 / X-5 / X-2 / X-1 / X-1 / X-8 / X-6**；
- 标 **STRICTER** 的 P-03 / P-07 分别对应 **X-7 / X-3**；
- 标 **SAME** 的 P-02 / P-04 / P-08 / P-09 / P-10 / P-11 / P-13 / P-14 / P-16 / P-17 / P-18
  **无**偏离登记行；
- 无孤行、无漏行；同一分叉在「上游对照」与「偏离登记」中只保留一个关系判词。
- ⚠️ **F-3 的 `fanout` 账本持久化**：上游没有 freegraph 的 `SchedulerState` 账本
  （fan-out 任务由上游自身 checkpoint 机制整体处理）⇒ 属**自研区 ③ / 内部契约变更**，
  **不**新增 P 行；该变更登记在 **F-3**（拆 B11F1 的「不落盘」冻结面）。

---

## §2 差分场景（D-38…D-49）

> 落点：`tests/differential/parity_probe.py`（追加）。
> 上游缺席 ⇒ **skip**，不判失败。

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| **D-38** | 自环 + `recursion_limit=3` | 两侧都抛 `GraphRecursionError`；freegraph `.recursion_limit == 3` | SAME |
| **D-39** | 不设上限、跑 >25 轮 | 两侧都不在第 25 轮误报（证明缺省 >25） | SAME |
| **D-40** | 每轮 2 节点自环 + 上限 3 | 两侧都只执行 3 个 super-step（不是 3 次节点调用） | SAME |
| **D-41** | `interrupt_before=["a"]`（两侧统一 list 形态；tuple 仅 `GraphSpec` 接受，见 P-17 / Q13） | 目标 0 次；不合并本轮写入；freegraph `__interrupt__ == ()`，上游无键 | DIFF（仅结果键） |
| **D-42** | `interrupt_after=["a"]`（两侧统一 list 形态；含最后节点 `next==()`） | 目标 1 次；状态含写入；空 `next` 仍可恢复；freegraph 空元组，上游无键 | DIFF（仅结果键） |
| **D-43** | before 挂起后 `input=None` | 两侧目标都恰好执行 1 次 | SAME |
| **D-44** | after 挂起后 `Command(resume="X")` | 两侧继续；`X` 不投递 | SAME |
| **D-45** | `Command(goto=[Send,Send])` · 无静态边 · `interrupt_before=["w"]`（两侧统一 list 形态） | 两侧 `w` 0 次；**只判执行次数**，**不判**上游 `snapshot.next` / 任务保留（E-07 含标准边，纯 fan-out 未实测）；任务保留与恢复由本地 T076 覆盖 | SAME |
| **D-46** | 同 D-45 + `interrupt_after=["w"]`（两侧统一 list 形态） | 两侧 `w` 各 2 次，随后挂起 | SAME |
| **D-47** | 同节点 before + after | 两侧顺序 before → 恢复 → 执行 → after | SAME |
| **D-48** | `["nope"]` / 裸 `"*"` / `["*"]` | 两侧：`nope` 失败点名；裸 `"*"` All；`["*"]` 失败。失败**时机**差异见 X-3，差分只判可观察成败 | SAME |
| **D-49** | 真异常 + `interrupt_after` | 两侧抛原异常，不返回挂起态 | SAME |

---

## §3 偏离登记（X-1…X-8）

| # | 类别 | 被偏离的判据 | 理由 | 承接 / 追认 |
|---|---|---|---|---|
| **X-1** | 破冻结面 / 结构性（DIFF） | P-12 / P-15：静态结果补 `"__interrupt__": ()` | 明确挂起信号 + 共用载体 | B7F3 · 人工验证追认 |
| **X-2** | 结构性 / 自研区 ③（DIFF） | P-06：`GraphSpec` 字段承载 | M1 的 L2 图定义侧；`compile()` 属 B7F2 | B7F2（D-1 / D-2）· 人工验证追认 |
| **X-3** | 更严失败信号（时机 · STRICTER） | P-07：构造期失败（上游 compile 期） | B7F1「构造时显式失败」 | 无需追认 |
| **X-4** | 结构性（零 env 红线 · DIFF） | P-01：硬编码 10007 | 宪法 I | 无需追认 |
| **X-5** | 结构性（异常消息 · DIFF） | P-05：英文摘要 + 结构化 | B1F1 冻结 | 无需追认 |
| **X-6** | 结构性（自研区 ③ · DIFF） | P-20：低层入口显式拒绝 | 上游无此入口；返回类型冻结；显式拒绝更可诊断 | B7F1 契约（F-8）· 人工验证追认 |
| **X-7** | 更严失败信号（类型 · STRICTER） | P-03：拒绝 bool / 浮点 | 布尔 / 小数当上限几乎必然是 bug | 无需追认 |
| **X-8** | 结构性（检查点标记 · DIFF） | P-19：增加 `suspension_kind` / `static_ack` | 空 `next` 的静态挂起必须可恢复；防重复触发需要版本水位 | B14F1 / B15F1 / B16F1 · 人工验证追认 |

---

> ⚠️ **F-3 的 B11F1 冻结面拆分**（`fanout` 不落盘 ⇒ 自 B13F1 起落盘）**不是上游偏离**，
> 而是内部契约的历史变更 ⇒ 记在 **F-3**，**不**新增 X 行；上游对照仍是 P-15 / P-19 的
> 任务粒度差异。

## §4 换版本复核清单

1. 复核 §1 全部行号；
2. 重跑 E-01…E-14（探针脚本不进仓库）；
3. 重判 D-38…D-49 的三态；
4. 复核 `recursion_limit` 的类型宽容度（`bool` / 浮点）；
5. 若上游改变 `"*"` / `["*"]` / 裸字符串的接受形态 ⇒ 重判 P-17 与 X-2。
