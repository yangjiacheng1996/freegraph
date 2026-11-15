# B11F1 人工验证记录

## 环境

- 日期：2026-11-14
- Python：3.11.16（`.venv`）
- 绿基线（改动前）：`1184 passed / 4 skipped`
- 本轮全量：`1203 passed / 4 skipped`

## 步骤

1. `.venv/bin/python -m pytest -q`（全量套件）
2. `.venv/bin/python harness/verification/B11F1/acceptance.py`
3. `.venv/bin/python -m pytest -q tests/runtime/test_send_fanout.py tests/runtime/test_send_contract.py`
4. 手工核对 C18 形态：节点返回 `[Send("worker", {"n": 1}), Send("worker", {"n": 2})]`，且存在静态边 `fan → worker`。

## 实际输出

- 全量：`1203 passed, 4 skipped`
- B11F1 用例：`20 passed`
- 覆盖率（新增模块 `_fanout.py`）：行 / 分支 **100%**（`coverage run --branch` + `coverage report`）
- acceptance.py：`B11F1 acceptance: PASS`
- C18 形态（手写图规格）：`worker` 被调用 **2** 次，入参分别为 `{"n": 1}` / `{"n": 2}`，无标准入参那次。

## 结论

- A1：map-reduce 模式可运行 ✅
- A2：产出按归约器汇合 ✅
- A3：`Send` 目标不存在时明确报错（同时点名产生者与目标）✅
- 载体 A / 载体 B / 静态边抑制 / 未知目标 / 原子性 / 独立中断 id 均有用例覆盖。

## 遗留问题

- `harness/demo/graph_core.py` 的 C18 用例仍受 B6F1 / B7F2 / B7F3 未接线影响而**不可跑**；本 feature 已用**手写图规格**验证同一形态。
- 立项书 §5.2 的 980 行口径为初版估计，实际规模以 `tasks.md` / 实现为准，待发起者在 feature 收尾时重估回写。
- DR-02：fan-out 载荷不落盘（归 B14F1）。
- DR-03：载体 A 叠加 / 载体 B 胜出的口径差异，已写入 quickstart 与本记录。
- DR-04：`Send` 的可变性 / 哈希性 / `timeout` 与上游差异（归上游对齐批次 P3-8）。
- DR-05：条件边返回 `Send` 的运行期语义归 B8F1（已接线）。
- DR-06：静态中断点 × fan-out 的交互归 B13F1（已接线）。

## 来源覆盖表

| 判据 | 覆盖 |
|---|---|
| A1 / A2 / A3 | 已覆盖（见上） |
| SC-001…SC-022 | 由 `tests/runtime/test_send_fanout.py` / `test_send_contract.py` 与既有套件覆盖 |
| FR-001…FR-024 | 由 tasks.md 的「FR → 任务」表逐条覆盖 |

## 发起者追认

**追认文字（2026-11-15 · 发起者：杨家成）**

本人已完成 B11F1 的人工验收（全量测试 `1203 passed / 4 skipped`，B11F1 用例 `20 passed`，
`acceptance.py` 输出 `PASS`，差分探针 `60 / 60` 符合判词），并确认：

- 追认 **PR-1 / PR-2 / PR-3 / PR-9 / PR-13 / PR-14**；
- 追认回溯修订 **F-1…F-14**（`Send` 归 L1 · L1 符号面 20 → 21 · `Command.goto` / `NodeFunc` 放宽 · B10F1 任务标识 / 中断现场 · B7F1/B9F1/B12F1/B10F1 顺序 / 阶段 / 执行次数）；
- 追认偏离登记 **X-1 / X-3 / X-6**；
- 知悉并接受 **DR-03**（载体 A 叠加 · 载体 B `Send` 胜出）的口径差异。

⇒ **追认完成 · 可合入。**
