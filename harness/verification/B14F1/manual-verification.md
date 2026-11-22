# B14F1 · 人工验证记录（Checkpointer + MemorySaver）

## 环境

- 日期：2026-11-22
- Python：`.venv/bin/python --version` ⇒ `Python 3.11.16`
- 上游（仅差分测试侧）：`langgraph==1.2.11`
- 实施前基线：`.venv/bin/python -m pytest -q --tb=no` ⇒ `2111 passed, 8 skipped`
- 基线（实施后实跑）：`.venv/bin/python -m pytest -q --tb=no` ⇒ `2191 passed, 8 skipped`
- 工作目录：仓库根目录 `freegraph`

## 步骤

1. 使用真实 `freegraph.persistence.MemorySaver` 编译一张单节点图：
   `g.compile(checkpointer=MemorySaver())`。
2. 第一次 `invoke` 让节点内的 `interrupt("approve?")` 挂起。
3. 通过 `get_tuple` 检查挂起快照：`next == ("ask",)`，pending writes 含
   `("ask", "__interrupt__", (...))`。
4. 第二次 `invoke(Command(resume="yes"), 同一 RunConfig(thread_id=...))` 恢复。
5. 检查恢复后状态含 `answer="yes"`，且快照数从 2 增加到 3。

执行脚本（临时脚本，验证后已清理；等价命令如下）：

```bash
.venv/bin/python /tmp/b14f1_manual.py
```

## 实际输出

```text
[first] interrupt= (Interrupt(value='approve?', id='8bceb300ae171f34e75bcc671d1278e1'),)
[suspend] next= ('ask',)
[suspend] pending= (('ask', '__interrupt__', (Interrupt(value='approve?', id='8bceb300ae171f34e75bcc671d1278e1'),)),)
[suspend] snapshot_count= 2
[node] resumed answer='yes'
[second] state= {'answer': 'yes'}
[second] snapshot_count= 3
```

## 结论

- 真实 `MemorySaver` 的「`interrupt` → 挂起 → `Command(resume=...)` → 跑完」链路通过。
- 恢复只重跑被中断的 `ask` 节点，`interrupt()` 之后代码执行一次。
- 挂起态有快照与 pending writes 双层数据；恢复后历史快照继续追加。
- B10F1 的人工验证承接项 V-1（恢复侧真跑一轮）已补齐。

## 遗留问题

- `MemorySaver` 仅用于开发 / 调试，不保证跨进程 / 跨重启；生产由 B15F1 `SqliteSaver` 承担。
- `stream(checkpoints)` 的消费端接线仍归 B8F2 / B15F1；本记录只验证数据源与恢复闭环。
- `delete_for_runs` / `copy_thread` 在 v1 按约定抛 `NotImplementedError`。

## 一键验收与签署

- 一键验收命令：`.venv/bin/python harness/verification/B14F1/acceptance.py`
- 一键验收结果：**48 条断言 · 失败 0 条 · B14F1 acceptance: PASS**
- 全量测试：`.venv/bin/python -m pytest -q --tb=no` ⇒ **2191 passed, 8 skipped**
- 行数登记：实现 **986** / 测试 **1,767** / 合计 **2,753**；超立项书 1,200 行预算，
  已按 plan **R-7** 如实登记，**未削减任何 FR / SC**。
- 验收结论：**人工验收通过**。
- 发起者确认：**杨家成** · **2026-11-22**
