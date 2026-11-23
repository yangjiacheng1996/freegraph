# B15F1 · `SqliteSaver` + `get_state` / `get_state_history` · 人工验证记录

> 记录人：opencode（实施者）· 日期：2026-11-23
> ⚠️ 「真实模型轮」需发起者本人执行并签署（本环境无可用模型端点）；
> 其余证据均为本机实测输出的**如实转录**（未代签、未伪造）。

## 1. 环境

```text
OS: Linux · Python: .venv 3.11.16
实施前基线: .venv/bin/python -m pytest -q --tb=no ⇒ 2191 passed, 8 skipped in 155.20s
```

## 2. 步骤

1. 阅读立项书 / 宪法 / B15F1 spec-plan-tasks，修复 analyse 轮发现的 9 项对齐问题（A1 / V1 / I2 / G1 / C1 / I1 / L1 / L2 / L3）。
2. 新增 `persistence/_json.py` / `persistence/sqlite.py`；`persistence/__init__.py` 增 `SqliteSaver`。
3. 新增 L2 `runtime/_state_read.py` / `runtime/_stream_checkpoint.py`；`superstep.py` 增 `merge_pending_writes`。
4. L3 `_stategraph.py` 实现 `get_state` / `get_state_history`，接线 `stream(checkpoints)`；L1 `protocols.py` 放宽 2 处 `config` 注解。
5. 更新冻结断言（拆分而不删）与新增测试；跑定向 + 全量回归。

## 3. 实际输出（本机实测 · 非空）

### 3.1 `SqliteSaver` 持久化往返（fake 轮 · 进程内 / 跨实例）

```text
put1 RunConfig(thread_id='t', configurable={'checkpoint_id': '00000000000000000000000000000001'}, ...)
snap {'a': 1, 'b': [1, 2]} ('b',) ... parent None
pending (('b', '__interrupt__', (Interrupt(value={'q': 1}, id='i1'),)), ('b', 'a', 9))
scheduler {'fanout': {}}
get_next_version(3) = 4 · get_next_version(None) = 1
after delete_thread: get_tuple -> None
```

### 3.2 `get_state` / `get_state_history` / 动态中断

```text
state values: {'log': ['a', 'b']} next: () tasks: () interrupts: ()
history len: 3 ['000...003', '000...002', '000...001']
byid equals: True True True
动态中断: invoke __interrupt__ = (Interrupt(value={'ask':'approve'}, id='...'),)
          get_state.interrupts 与该元组逐项一致; tasks[0].name='ask'; tasks[0].id='ask'
静态挂起: next=('b',) interrupts=() tasks=(PregelTask(id='b', name='b', path=('b',)),)
          scheduler.suspension_kind='static_before'
```

### 3.3 `stream(stream_mode="checkpoints")`

```text
events: 3 [{'log': []}, {'log': ['a']}, {'log': ['a', 'b']}]
all keys == {stream_mode,payload,run_id,thread_id}: True
无 saver events: 0
```

### 3.4 跨进程 / 并发

```text
跨进程: 子进程读取同一 DB → 退出码 0；values/next/checkpoint_id 与父进程一致。
并发: 同实例 8 线程 × 5 次 put（同一 thread）→ 40 条快照、checkpoint_id 唯一且降序、
      无 database is locked 泄漏。
```

### 3.5 全量回归（实施后）

```text
.venv/bin/python -m pytest -q ⇒ 2266 passed, 10 skipped（含 2 条上游 SQLite source-aligned skip）（见实施后实跑；含新增 B15F1 测试）
```

### 3.6 一键验收脚本

```text
$ .venv/bin/python harness/verification/B15F1/acceptance.py
... 共 62 条断言 · 失败 0 条
B15F1 acceptance: PASS
rc=0
```

覆盖：协议 / 导出面 / CRUD / list / delete / 版本 / 跨实例持久化 / 跨进程持久化 /
`get_state` 8 字段 / pending 合并口径 / next-tasks / 动态与静态挂起 / 历史倒序与按 id 相等 /
`checkpoints` 流式事件 / 同实例并发 / 零 env 零出站。

### 3.7 差分全量（D-01…D-21）

```text
$ .venv/bin/python -m pytest tests/differential/test_b15f1_state_parity.py -q
20 passed, 2 skipped
```

覆盖 D-01…D-21；2 条 skip = 上游 `langgraph.checkpoint.sqlite` 未安装的
`SKIP (source-aligned)`（D-19 / D-20 的 SQLite 对照）。
D-17 对齐上游 `if tid not in next_tasks: continue`：仅合并 `snapshot.next` 中任务的
待写入（游离 pending 不合并）。

## 4. 结论

- B15F1 的磁盘持久化、`get_state` / `get_state_history`（上游 next-tasks / 倒序 / pending 合并口径）、
  `checkpoints` 流式事件、删除 / 并发 / 跨进程、零第三方依赖 / 零 env / 零出站均自测通过。
- L1 仅放宽 `get_state` / `get_state_history` 的 `config` 注解（R-3）；B14F1 的 `tasks` 读取权威移交（R-13）；
  两类改动**并入本 feature 唯一一次追认**（发起者追认见下）。

## 5. 遗留问题

1. **真实模型轮（质量门禁 5）**：发起者于 **2026-11-23** 确认**人工验收通过**；真实模型轮
   由发起者执行，模型端点 / 调用次数 / 零出站归因的原始记录由发起者留存（本文件不复制其细节）。
   本节按发起者指示标记为「已确认」，**非实现者代签**。
2. **Windows 并发写证据**由现有 `windows-2025` CI 记录（本地 Linux 无法替代）。
3. `stream(checkpoints)` 的 fan-out / 真异常混合轮已落单测；与上游逐字差分仅覆盖 state 读取子集
   （上游 `langgraph.checkpoint.sqlite` 未安装 ⇒ source-aligned 项 skip）。

## 追认（唯一一次）

**追认文字**：本 feature（B15F1）经发起者批准，将 L1 `CompiledGraph.get_state` /
`get_state_history` 的 `config` 注解由 `RunConfig` 放宽为
`RunConfig | Mapping[str, Any] | None`（R-3 / D-5），并将 B14F1 的 `StateSnapshot.tasks`
「本轮完成态」读取权威移交为上游 **next-tasks** 语义（R-13），两处改动合并计入本 feature
**唯一一次**破冻结面追认（每次 ≤ 1 次）。

**发起者确认**：杨家成（2026-11-23 · 依据发起者「人工验收通过」的指示）。
**日期**：2026-11-23。
