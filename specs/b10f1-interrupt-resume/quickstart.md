# Quickstart · B10F1 · `interrupt()` + `resume`（HITL 中断与恢复闭环）

**Spec**: [`spec.md`](./spec.md) · **Plan**: [`plan.md`](./plan.md) · **Contract**:
[`contracts/interrupt-resume-contract.md`](./contracts/interrupt-resume-contract.md)

> ⚠️ 本文件是**验收 / 跑通指南**（**可执行**）⇒ **不含**实现代码 ⇒ ⇒ 实现细节归 `tasks.md`。
> ⚠️ **本 feature 在 M1 阶段**没有**可用的 checkpointer 实现**（`MemorySaver` 属 B14F1 / M3）⇒
> ⇒ 恢复侧用**桩**（记录调用的测试替身）验证 ⇒ ⇒ **人工验证**的「恢复侧真跑一轮」按
> **偏离登记 V-1** 延期到 B14F1。

---

## 0. 前置条件（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（B3F1 的既有结论）
python3.11 -m venv .venv

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --python .venv -r pyproject.toml --group dev

# ③ 本 feature 包（editable）
uv pip install --python .venv -e .

# ④ （可选）上游（**仅差分测试侧** · 不进发行面 ⇒ 缺席即 skip）
uv pip install --python .venv langgraph==1.2.11
```

⚠️ **不需要**上游（**除差分闸口外**）⇒ ⇒ 上游缺席 ⇒ 差分场景 **skip**（非失败）。

---

## 1. 中断后结果含 `__interrupt__`，元素带 `.value` / `.id`（**SC-001 / A3**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_basic.py -v -k "value_and_id"
```

| 项 | 期望 |
|---|---|
| 断言 | 结果含 `__interrupt__` 键；`[0].value == "approve?"`；`[0].id` 匹配 `^[0-9a-f]{32}$` |
| 判据 | SC-001 · 契约 §4 / §5 · data-model **V-3 / V-6** |

---

## 2. 恢复后跑到结束态，状态含 resume 值（**SC-002 / A1**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_resume.py -v -k "resume_completes"
```

| 项 | 期望 |
|---|---|
| 前置 | 挂了**桩** checkpointer |
| 断言 | 二次调用结果**无** `__interrupt__`；状态含 resume 值；节点内计数 == 2 |
| 判据 | SC-002 · 契约 §6 · data-model **SM-4** |

---

## 3. 恢复时节点**从节点起点重跑**（**SC-003 / A2**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_resume.py -v -k "reruns_from_start"
```

| 项 | 期望 |
|---|---|
| 断言 | 节点内**前半段**的副作用**再次出现**（`['enter', 'enter', 'got yes']`）⇒ **不**是从中断点继续 |
| 判据 | SC-003 · 契约 §6.3 · **I-6** · 上游实测 **E-8** |

---

## 4. 中断前的写入**不丢失**（**SC-004**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_basic.py -v -k "writes_preserved"
```

| 项 | 期望 |
|---|---|
| 断言 | 挂起结果含中断前的写入；恢复后节点读到的入参**含**那些写入 |
| 判据 | SC-004 · 契约 **I-7 / I-8** · 上游实测 **E-16 / E-21** |

---

## 5. ★ 恢复**确实经由 checkpointer**（**SC-005 / A4**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_checkpoint.py -v -k "reads_snapshot_and_pending_writes"
```

| 项 | 期望 |
|---|---|
| 夹具 | **桩** checkpointer（记录 `get_tuple` / `put` / `put_writes` 的调用与参数） |
| 断言 | 恢复时桩记录到**该 `thread_id`** 的 `get_tuple` 调用；返回的 `.snapshot` / `.pending_writes` / `.scheduler` **三**项**均被读取** |
| 判据 | SC-005 · 契约 **I-12** · [`contracts/checkpoint-contract.md`](./contracts/checkpoint-contract.md) §2 |

⚠️ **未挂** checkpointer 的对照用例 ⇒ 见 §6。

---

## 6. 未挂 checkpointer ⇒ **明确异常**（**SC-011 / A4②**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_errors.py -v -k "checkpointer_required"
```

| 项 | 期望 |
|---|---|
| 断言 | 抛 `InterruptError`；`.reason == "checkpointer_required"`；消息指明「恢复需要 checkpointer」 |
| 判据 | SC-011 · 契约 §7 · data-model **V-9 / V-10** |

---

## 7. 「未提供恢复值」的**写死**行为（**SC-012**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_errors.py -v -k "resume_value_required"
```

| 项 | 期望 |
|---|---|
| 断言 | `Command(resume=None)` 与 `Command()` ⇒ 均抛 `InterruptError(reason="resume_value_required")` |
| 判据 | SC-012 · 契约 §7 · spec 裁定 4 |

---

## 8. 同一节点内**多个** `interrupt()` ⇒ 按**节点内顺序**匹配（**SC-014**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_resume.py -v -k "multiple_interrupts_in_one_node"
```

| 项 | 期望 |
|---|---|
| 断言 | 第 1 个恢复值落在第 1 个 `interrupt()`、第 2 个落在第 2 个；恢复值**不足** ⇒ **再次挂起**（**不**报错） |
| 判据 | SC-014 · 契约 §4 / §6.3 · 上游实测 **E-17** |

---

## 9. 跨节点多挂起中断 ⇒ 单值**失败** / 按 id **成功**（**SC-015**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_resume.py -v -k "multiple_pending_interrupts"
```

| 项 | 期望 |
|---|---|
| 断言 | 单值 ⇒ `InterruptError(reason="ambiguous_resume")`；按 id 的映射 ⇒ 未指定的**仍挂起**、指定的**已恢复** |
| 判据 | SC-015 · 契约 §6.1 · 上游实测 **E-12 / E-19 / E-20** |
| ⚠️ 覆盖 | 该用例由 **`tasks.md` T052** 覆盖（**三组**补漏用例：映射恢复成功 · FR-013 ⑦「dict 非 map」· 补记 F-2「resume 与 update 并存」）|

---

## 10. 挂起后**再次挂起** ⇒ 闭环**可重复**（**SC-013**）

```bash
.venv/bin/python -m pytest tests/runtime/test_interrupt_resume.py -v -k "resume_then_interrupt_again"
```

| 项 | 期望 |
|---|---|
| 断言 | 第二次挂起产生**新的**中断载荷（`.value` 不同）· `.id` 与第一次**逐字相同**；第三次提交恢复值后**跑完** |
| 判据 | SC-013 · 契约 §4.1 步 4 / §6.3 · **I-6** · 上游实测 **E-17 / E-18** |

---

## 11. ★ 差分探针场景组（**SC-016** · 宪法原则 XI 的「可验证出口」）

```bash
# 上游已安装 ⇒ 真跑；上游缺席 ⇒ skip（非失败）
.venv/bin/python harness/scripts/diff_parity.py -v -k 中断

# （CLI 同源）
.venv/bin/python -m pytest tests/differential/test_parity_probe.py -v
```

| 项 | 期望 |
|---|---|
| 断言 | **DI-01…DI-08** **8** 条全部符合判词（**SAME** **6** 条 · **STRICTER** **2** 条）⇒ ⇒ ⚠️ **`DI-` 前缀**（探针内**已有** B12F1 的 `D-01…D-15` 与 B7F4 的 `D-16…D-28` ⇒ **MUST NOT** 用 `D-` 前缀）|
| 回归 | 既有 **43** 条场景**逐字不变** ⇒ **恒绿**（**实测** `parity_probe._scenarios()` == 43）|
| 判据 | SC-016 · [`contracts/upstream-parity.md`](./contracts/upstream-parity.md) §3 |

---

## 12. **结构纪律**（导出面 / 层依赖 / 零依赖 / 零环境变量）

```bash
# 导出面：runtime.__all__ 的符号集合 + L1 的 20 符号面（**集合相等** · 不硬编码数字）
.venv/bin/python -m pytest tests/runtime/test_interrupt_contract.py -v -k "runtime_all"

# L2 → L4 的依赖边数 == 0（导入图断言 · 门禁 G25）
.venv/bin/python -m pytest tests/contracts/test_architecture.py -v -k "layer"

# 零环境变量 / 零出站（门禁 G24 / G26）
.venv/bin/python -m pytest tests/gates/test_gates.py -v
```

| 项 | 期望 |
|---|---|
| 断言 | `runtime.__all__` == **预期清单**（**23** 项 = 20 + `InterruptResult` / `InterruptError` / `run_graph` · ⚠️ **断言里 MUST NOT 写死数字**）· **L1 的 20 符号面零改动**（**集合相等**）|
| 判据 | SC-006 / SC-007 / SC-017 / SC-018 · 契约 §1 |

### 12.1 门禁 **G25**（导入图单向）+ 门禁 7（兼容矩阵）

```bash
# G25 —— `interrupt()` 的落点合规（**PR-4** / **DR-13**）
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py --root .

# 门禁 7 —— README「API 兼容矩阵」的 `interrupt` 行已更新（**FR-026 / SC-022**）
.venv/bin/python -m pytest tests/facade/test_facade_gates.py -v -k "compat or export"
```

| 项 | 期望 |
|---|---|
| G25 | 退出码 == **0** ⇒ ⇒ `_primitives.py` **零** import `runtime/` · `graph.py` 的 `interrupt` 来自**模块级** `from .runtime._interrupt import interrupt` |
| 门禁 7 | 兼容矩阵的 `interrupt` 行已改为「**中断 / 恢复行为已落地**（B10F1）」⇒ ⇒ **MUST NOT** 增删行 |

---

## 13. **人工验证**（原则 V）+ **偏离登记 V-1** + **发起者追认**

```bash
# 机械层的一键验收入口（实现阶段产出）
.venv/bin/python harness/verification/B10F1/acceptance.py
```

| 项 | 期望 |
|---|---|
| 期望 | 退出码 == **0**（全部闸口全绿） |
| 人工记录 | `harness/verification/B10F1/manual-verification.md` **五段式齐全**（验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题） |
| ⚠️ **V-1** | 「**恢复侧真跑一轮**」（挂**真实** saver）**延期到 B14F1 / M3** ⇒ ⇒ 记录里**如实写明** ⇒ ⇒ **追认文字**（发起者确认 + 日期）**落盘** ⇒ **未追认前 MUST NOT 合入** |

---

## 14. 全量套件（**零回归**）

```bash
.venv/bin/python -m pytest -q
```

| 项 | 期望 |
|---|---|
| 期望 | **零回归**（既有套件全绿）· 新增用例全绿 · 差分闸口 **43 + 8** 条符合判词 |
| 依据 | SC-016 / SC-019 · 契约门禁（C4 / C6 / C8 零破坏） |
