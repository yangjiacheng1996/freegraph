# B8F2 人工验证记录

## §1 环境与基线

- 分支 / 特性：`b8f2-stream-modes`（B8F2 · M2）
- 上游：`langgraph 1.2.11` / `langchain-core 1.7.6`（CPython 3.11）
- 绿基线（实施前）：`1607 passed / 4 skipped / 0 failed`（2026-11-19）
- 实施后实测：`1661 passed / 4 skipped / 0 failed`（2026-11-20）；一键验收 `B8F2 acceptance: PASS`
- `pyproject.toml` 零改动；运行时依赖 = 空。
- `Requires-Dist` 仍为空（零运行时依赖）——T003 复核通过。

## §2 七种 mode 实测输出

以下为 `harness/verification/B8F2/acceptance.py` 与 `tests/facade/test_stream_modes.py` 的真实输出摘要：

| mode | 实测结果 |
|---|---|
| `values` | 两节点线性图 3 条（初始 + 2 步）；最后一条 `payload == invoke` |
| `updates` | 2 条；`{"a": {"x": ...}}` / `{"b": {"x": ...}}`；可按通道归约合并回终态 |
| `tasks` | 2 条 `PregelTask`（每完成 task 一条） |
| `debug` | 2 条 `{step, timestamp, type:"task_result", payload}` |
| `checkpoints` | 0 条（能力边界 · B14F1） |
| `messages` | 0 条（能力边界 · freechain） |
| `custom` | writer 写入原样出现；顺序 = TaskId 升序 + 任务内写入序 |

`writer` 注入实测：`def node(state, writer)` / `def node(state, writer: StreamWriter)` / `def node(state, *, writer)` 均注入；`stream_writer` 名称不注入；`invoke()` 注入 no-op。

## §3 差分结果

D-121…D-136 全绿（上游缺席即 skip）。判词分布：

- SAME：10
- DIFF：4（D-125 tasks / D-126 debug / D-127 多 mode / D-128 事件 id）
- STRICTER：2（D-129 非法 mode / D-134 `RunConfig.run_id`）

`custom` 产出时机差异归 **P-23 / X-6**（轮末批量），D-124 只比载荷。

## §4 门禁 / 偏离登记

- **R-5（门禁 3/4/5 的物理不可达部分）**：`target.py` 在 PNG（B23F1）处不可达；真实模型轮环境不具备；固定脚本零改动，图能力侧证据由 `visualization.py` / `graph_core.py` / `acceptance.py` 承担。
- **R-6（ARCH-3 例外）**：L5 的 B18F1 / B19F1 读取 L2 私有 `_STREAM_RUN_ID` / `_STREAM_THREAD_ID`；载荷为 `str | None` 运行期元数据；不新增公开符号；若未来升级为公开 API，另走契约修订。
- 其余偏离：X-1…X-6 已在 spec / `upstream-parity.md` 双侧登记。

## §5 破冻结面追认与规模实测

以下为本 feature 的**唯一一次**追认额度（T-1…T-5 共同使用）：

- **T-1**：B7F1 `SuperStepResult` 原 4 字段逐字保留，末尾追加 `tasks`（缺省 `()`）。
- **T-2**：B12F1「四字段零改动」只补注记，原描述不改写。
- **T-3**：`CompiledGraph.stream` 的 `config` 注解放宽 + `stream_mode` 默认 `None ⇒ "updates"`；原 `RunConfig | None` 仍为子集；B7F2 原描述只补注记。
- **T-4**：B10F1「线程池不继承 contextvars」只补注记；每任务 `copy_context()` 后继承；两级机制照常工作。
- **T-5**：门面 7 → 8、契约 21 → 22；原符号一个不删；源码模块 docstring 同步。

**发起者确认**：用户（本次会话明确授权修复与实施） · **日期：2026-11-20**。

**人工验收结论**：验收输出全部 PASS（A1–A3 / V1–V21）；`B8F2 acceptance: PASS`（2026-11-20）。

规模实测：以实现期实测为准；立项书 §5.2 的「1,180 行 · 3 人日」不单方面修改，修订属发起者职权。
