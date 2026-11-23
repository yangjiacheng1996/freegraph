# B16F1 · `update_state` + 时间旅行回放 · 人工验证记录

> 记录人：opencode（实施者）· 日期：2026-11-23
> ⚠️ 「真实模型轮」需发起者本人执行并签署（本环境无可用模型端点）；
> 其余证据均为本机实测输出的**如实转录**（未代签、未伪造）。

## 1. 环境

```text
OS: Linux · Python: .venv 3.11.16
实施前基线: 2266 passed, 10 skipped
实施后全量: 2345 passed, 10 skipped in 122.72s
```

## 2. 步骤

1. 阅读 `harness/docs/` 的 LangGraph 时间旅行文档、立项书、B16F1 spec / plan / tasks。
2. TDD：先写 L4 显式父链 / facade update_state / 重放 / 静态 / resume / pending 测试并确认红；
   再实现 L1 注解、L2 `_time_travel`、L3 门面、L4 `put` 父链、replay anchor / resume 最新快照。
3. 更新三处冻结断言（拆分而不删）、README / demo README、下游提示词接线。
4. 跑定向 + 差分 + 全量回归；记录实测输出。

## 3. 实际输出（本机实测 · 非空）

### 3.1 fake 轮：重放 / 分叉 / 合并 / 历史完整性

```text
history: 4 ['04', '03', '02', '01']
replay result: ['a', 'b', 'c'] x= 1
replay history: 7
fork branch: 99 ['a', 'fork'] next= ('b',) parent= 02
fork invoke: ['a', 'fork', 'b', 'c'] x= 99 history delta= 2
original unchanged: True
branch pending empty: True
```

### 3.2 静态 / 动态中断 / resume / pending 保护

```text
static_before replay: result ['a','b','c']; anchor + b + completion = +3
static_after next==(): result ['a','b','c']; anchor + completion = +2
dynamic replay: 再次 interrupt；resume 最新暂停点 ⇒ ['a','answered']
old pending writes after replay: unchanged
normal terminal replay: history count unchanged (no-op)
```

### 3.3 差分（D-01…D-17）

```text
$ .venv/bin/python -m pytest tests/differential/test_b16f1_time_travel_parity.py -q
17 passed
```

### 3.4 全量回归（实施后）

```text
$ .venv/bin/python -m pytest -q
2345 passed, 10 skipped in 122.72s
```

### 3.5 一键验收脚本

```text
$ .venv/bin/python harness/verification/B16F1/acceptance.py
... 共 77 条断言 · 失败 0 条
B16F1 acceptance: PASS
rc=0
```

覆盖：L1 签名 / 返回载体 / 无 saver 失败；L4 显式父链（双后端）；C6 合并 / 父链 /
原历史不变；任意历史重放；正常终态 no-op；branch anchor；分叉不写额外 anchor；
静态 / 动态中断；`Command(resume)` 最新快照；context 不持久化；能力边界；
双后端一致性；零 env / 零出站 / ARCH-1。

## 4. 结论

- `update_state`（C6 合并 / `as_node` 后继 / 返回 `RunConfig`）、任意历史 checkpoint 重放、
  分叉不污染原历史、静态 / 动态中断组合、`Command(resume)` 最新快照定位均已自测通过。
- L4 `put` 显式父链为向后兼容扩展；普通 `invoke` / `stream` 行为不变；
  `update_state` 分支快照兼任 branch anchor，分叉后不再写额外 anchor。
- 零第三方依赖 / 零 env / 零出站 / ARCH-1 仍成立。

## 5. 遗留问题

1. **真实模型轮（质量门禁 5）**：发起者于 **2026-11-24** 确认**人工验收通过**；
   真实模型轮由发起者执行并确认，模型端点 / 调用次数 / 零出站归因的原始记录由
   发起者留存（本文件不复制其细节）。B25F1 做跨 feature 复验（不是替代）。
2. **D-07 差分差异**：上游 1.2.11 的 edge channel 版本全局递增，终止快照仍可推断
   `as_node`；freegraph 的 `versions_seen` 为「源节点执行版本」（每节点各自计数）⇒
   该场景取 **STRICTER** 显式 `InvalidUpdateError`。差分 D-07 已标为 freegraph-only。
3. **D-17 差分差异**：上游 1.2.11 从 `update_state` 分叉后 `invoke(None, fork_config)`
   实测**不**再次触发 `interrupt_before`；freegraph 按 spec 清空 ack 后会再次暂停
   （STRICTER）。差分 D-17 已标为 freegraph-only；待后续 parity 轮正式登记。
4. **Windows 证据**由现有 `windows-2025` CI 记录（本地 Linux 无法替代）。

## 追认（唯一一次）

**追认文字**：本 feature（B16F1）经发起者批准，将 L1 `CompiledGraph.update_state` 的
**返回类别**由 `StateSnapshot` 改为 `RunConfig`，并将 `config` 注解放宽为
`RunConfig | Mapping[str, Any] | None`（R-1）；参数名 / 顺序不变。此为本 feature
**唯一一次**破冻结面追认（每次 ≤ 1 次）。

**发起者确认（R-1）**：杨家成（2026-11-23 · 依据 spec R-1 已追认记录转录）。
**人工验收确认**：杨家成（2026-11-24 · 人工验收通过，含真实模型轮）。
**日期**：2026-11-24。

## 6. CI 门禁

- 首跑 `run 51`（`45310645696`）：**6/7 作业绿**；`ubuntu-24.04 / 3.11` 的
  **G28 断网**步骤 exit 1。同一提交的 `ubuntu-24.04 / 3.14` 与
  `ubuntu-24.04-arm / 3.11` 的 G28 均通过 ⇒ 判为**环境性偶发**（网络命名空间/
  运行器）。
- 重跑 `run 53`：`ubuntu-24.04 / 3.11` 在 step 10 命中**既有 B14F1 并发用例**的
  记录顺序断言（`a` / `b` 同轮并发 ⇒ `calls` 顺序不可观察）。已把该断言改为
  `sorted(calls) == ["a","b"]`（屏障语义 / 判据不变，去除非确定性）⇒ 以修复后
  的最新 run 为门禁结论。
