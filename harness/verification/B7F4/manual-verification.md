# B7F4 · 多源汇合边（AND / 屏障）—— 人工验证记录

**Feature**: `B7F4` · **Spec**: [spec.md](../../specs/b7f4-multisource-join/spec.md) ·
**Plan**: [plan.md](../../specs/b7f4-multisource-join/plan.md) ·
**契约权威**: [superstep-multisource-contract.md](../../specs/b7f4-multisource-join/contracts/superstep-multisource-contract.md) ·
**上游对照**: [upstream-parity.md](../../specs/b7f4-multisource-join/contracts/upstream-parity.md) ·
**验收脚本**: [acceptance.py](./acceptance.py) ·
**日期**: **2026-11-13**

> ⚠️ **本 feature 破 B7F1 的冻结面**（**发起者 2026-11-12 已同意**）⇒ ⇒
> **本记录 MUST 含发起者追认**（宪法 v1.8.0「破冻结面的三条」）⇒ ⇒
> **未追认前 MUST NOT 合入**。
> ⚠️ **追认次数 == 1** ⇒ **八项登记项（PR-1…PR-8）打包成一次**（澄清轮 **C-Q13**）。

---

## 1. 验证环境

| 项 | 值 |
|---|---|
| 仓库根 | `/home/ctyun/workspace/github/freegraph` |
| 分支 | `b7f4-multisource-join` |
| Python | CPython **3.11.16**（`.venv/bin/python`） |
| 平台 | `Linux-6.8.0-139-generic-x86_64-with-glibc2.39` |
| 上游 `langgraph` | **1.2.11**（**仅**差分用 · **不进**发行面 · PEP 735 依赖组） |
| 被验产物 | `src/freegraph/runtime/superstep.py`（**L2** · **唯一**改动文件） |
| 改动面 | `src/freegraph/runtime/superstep.py` · `tests/runtime/test_superstep_multisource.py`（**新增**）· `tests/differential/parity_probe.py` · `tests/differential/test_parity_probe.py` · `specs/b7f1-superstep-loop/**`（**只增不改**）· `specs/b7f4-multisource-join/**` · `harness/features/**`（**只接线**）· `harness/verification/B7F4/**`（**新增**） |
| 零改动面 | `src/freegraph/contracts/**`（L1 冻结面）· `src/freegraph/runtime/channel.py` · `src/freegraph/runtime/read.py` · `src/freegraph/runtime/__init__.py`（导出面 **20**）· `src/freegraph/runtime/_concurrency.py` · `src/freegraph/graph.py` · `pyproject.toml` · `THIRD_PARTY_NOTICES` · **API 兼容矩阵**（**尚未落库** ⇒ 归 **B24F1**）· `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（层注册表） |

> ⚠️ **零出站 / 零环境变量 / 零文件 I/O**（L2 路径）⇒ 下面每条命令都**不联网**。

---

## 2. 验证步骤

### 2.1 **机械层**一键验收（**A1…A10**）

```bash
.venv/bin/python harness/verification/B7F4/acceptance.py
```

### 2.2 全量回归 + 门禁 + 差分

```bash
.venv/bin/python -m pytest tests/ -v                                  # 全量
.venv/bin/python -m pytest tests/differential/ -v                     # 差分场景组（D-16…D-28）
.venv/bin/python -m pytest tests/differential/ -v -k "param"          # D-24 参数化
.venv/bin/python -m pytest tests/runtime/test_superstep_contract.py -v   # 契约守卫回归（T085）
```

### 2.3 **既有断言零削弱**（**A4** · SC-005 · **R-9** 的机械判据）

```bash
# ⚠️ MUST 用 `git diff HEAD --stat`（**不是** `git diff --stat` —— 后者不比对**已暂存**的改动 ⇒ 可假通过）
# ⚠️ MUST 查**全部 10 个**冻结断言文件（**MUST NOT** 只查其中一个）
for f in test_superstep_trigger test_superstep_contract test_command_contract \
         test_command_goto_semantics test_command_noop test_command_purity \
         test_superstep_concurrency test_command_list test_command_merge_parity \
         test_read_c4_sparse_state; do
  git diff HEAD --stat -- "tests/runtime/$f.py"     # ⇒ **必须为空**
done
```

**实测结果**：**10 个**全部**为空**（**R-9** 的机械证据 ⇒ **既有断言一条不删**）。

### 2.4 **quickstart §1 冒烟** + **§2 的 A1…A10**

```bash
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "src")
from freegraph.runtime import GraphSpec, NodeSpec, SchedulerState, LastValue, run_super_steps

calls = []
def mk(name):
    def run(state):
        calls.append(name)
        return {}
    return NodeSpec(subscribes=(), run=run)

spec = GraphSpec(
    channels={"log": LastValue("log", str)},
    nodes={"a": mk("a"), "b": mk("b"), "c": mk("c")},
    edges={"__start__": ("a", "b"), ("a", "b"): ("c",)},   # ★ 多源汇合边
)
run_super_steps(spec, SchedulerState())
print(calls)
PY
```

### 2.5 **A8** 形态校验逐条（**V-16** 四条 · **V-2** 两条 · 边键**类型**非法）

### 2.6 **上游对照**的取证复核（**A3** · 差分场景组实跑）

---

## 3. 实际输出

### 3.1 机械层一键验收（**A1…A10**）

```text
==============================================================================
B7F4 人工验收 · 判据 A1–A10（对照 specs/b7f4-multisource-join/quickstart.md §2）
==============================================================================
仓库根    : /home/ctyun/workspace/github/freegraph
Python    : /home/ctyun/workspace/github/freegraph/.venv/bin/python
平台      : Linux-6.8.0-139-generic-x86_64-with-glibc2.39
上游 langgraph: 已安装

[PASS] A1   多源边可表达（FR-001 · M-1）  1 passed, 19 deselected in 0.06s
[PASS] A2   屏障语义正确（FR-003 / FR-004 · M-2 / M-3 / M-4 / M-5 / M-8）  10 passed, 10 deselected in 0.12s
[PASS] A3   与上游同款（差分场景组 D-16…D-28 · SC-004 / SC-011）  14 passed in 26.67s
[PASS] A4a  既有单源口径用例全绿（SC-005 · M-6）  720 passed in 28.43s
[PASS] A4b  10 个冻结断言文件的 diff 全为空（R-9）  10 个冻结断言文件的 `git diff HEAD --stat` 全为空
[PASS] A6   导出面零新增（runtime / contracts == 20 · SC-006 · M-9）  runtime.__all__ / contracts.__all__ = 20 20（期望 20 / 20）
[PASS] A7   回溯修订 R-1…R-10 逐条命中（FR-013 · SC-008）  R-1…R-10 的 10 个落点逐条命中
[PASS] A8   形态校验生效（V-16 / V-2 / 边键类型非法 · FR-017 / FR-021）  8 passed, 12 deselected in 0.07s
[PASS] A9   参数化场景全绿（D-24 · 屏障形态 × 通道类型 × 源可达性 · SC-013 · M-13）  12 passed, 2 deselected in 0.91s
```

> ⚠️ **A5 / A10 的首次实跑**（本记录落盘**之前**）= **FAIL**（「人工验证记录缺失」）
> ⇒ ⇒ 本记录落盘后**复跑**即全绿（见 §3.6）⇒ ⇒ **「追认 MUST 在合入前落盘」**的时序**可机械复核**。

### 3.2 全量回归

```text
.venv/bin/python -m pytest tests/ -q
⇒ 1153 passed, 3 skipped in 80.49s (0:01:20)
   SKIPPED [1] tests/contracts/test_contract_regressions.py:85 —— 未落地（C8 · 由 B8F1（M2）建立）
   SKIPPED [1] tests/contracts/test_protocols.py:382 —— mypy 未装（开发期工具 ⇒ skip · 不判失败）
   SKIPPED [1] tests/facade/test_api_snapshot.py:189 —— 未开启 --update-api-snapshot（默认关闭）
```

### 3.3 差分场景组（**A3** · **SC-004** / **SC-011**）

```text
.venv/bin/python -m pytest tests/differential/ -q
⇒ 26 passed in 25.96s（14 条探针包装 + 12 条 D-24 参数化）

判词分布（探针内 43 个场景）：
  既有 30 个场景 ⇒ 逐字未变（三元组快照 SHA-256 前后一致
    = 705768d0c52c84b47a0f17b796a29e6443db80a82cb18a1def8b29b78e1ebd61）
  新增 D-16…D-28（13 个）⇒ SAME 11 条（D-16…D-24 / D-27 / D-28）
                                + STRICTER 2 条（D-25 / D-26 · 各带 note）
```

**两侧的**实际**结果对照**（实测 · 与 research **E-1…E-11** 的上游基线**逐字一致**）：

| 差分场景 | freegraph 侧 | 上游侧 | 判词 |
|---|---|---|---|
| **D-16**（标准屏障 · E-1） | `{'msgs': ['a', 'b', 'c']}` | `{'msgs': ['a', 'b', 'c']}` | **SAME** |
| **D-17**（屏障不齐 · E-2） | `{'msgs': ['a', 'b']}` | `{'msgs': ['a', 'b']}` | **SAME** |
| **D-18**（组间任一 · E-3） | `{'msgs': ['a', 'b', 'c']}` | `{'msgs': ['a', 'b', 'c']}` | **SAME** |
| **D-19**（屏障后齐 · E-5） | `{'msgs': ['a', 'b', 'c', 'd', 'c']}` | `{'msgs': ['a', 'b', 'c', 'd', 'c']}` | **SAME** |
| **D-21**（两条屏障并存 · E-4） | `{'msgs': ['a', 'b', 'd', 'c']}` | `{'msgs': ['a', 'b', 'd', 'c']}` | **SAME** |
| **D-22**（缺源 · E-8） | `ERROR ValueError`（构造期） | `ERROR ValueError`（构造期） | **SAME** |
| **D-23**（元组顺序无关 · P-14） | `('a','b')` ≡ `('b','a')` | ——（freegraph 内部对照） | **SAME** |
| **D-24**（参数化 12 组 · **H-6**） | 12 组**逐字一致** | 12 组**逐字一致** | **SAME** |
| **D-25**（目标为 `__end__` · E-9） | `ERROR ValueError`（构造期） | `OK {'msgs': ['a','b']}`（**静默 no-op**） | **STRICTER**（**X-04**） |
| **D-26**（空的多源边 · E-6） | `ERROR ValueError`（构造期） | `OK {'msgs': ['a','b']}`（**静默**） | **STRICTER**（**X-02**） |
| **D-27**（同成员不同序的两条边 · E-11） | `{'msgs': ['a', 'b', 'c']}` | `{'msgs': ['a', 'b', 'c']}` | **SAME** |
| **D-28**（边键类型非法 · E-10） | `ERROR TypeError`（构造期） | `ERROR TypeError`（构造期） | **SAME** |

### 3.4 **契约守卫回归**（**T085** · R-1…R-6 改契约后）

```text
.venv/bin/python -m pytest tests/runtime/test_superstep_contract.py -v
⇒ 49 passed in 0.43s
```

> ⚠️ **顺序缺口的封堵**：该守卫会**解析**契约 §7 的**不变量编号表**（首格
> `fullmatch(r"I-\d+")` ⇒ 断言 == **I-1…I-16**）⇒ ⇒ **R-6 的补注 MUST NOT** 写成
> **新的不变量行** ⇒ ⇒ 本次**只**在 **I-12 行内**追加说明 ⇒ ⇒ **49 条全绿** ✓。

### 3.5 quickstart §1 冒烟 + **A8** 形态校验逐条

```text
§1 冒烟 calls = ['a', 'b', 'c']      ⇒ c **最后**执行 ⇒ 屏障成立 ✓

A8 形态校验：
  空元组              ⇒ ValueError ✓ · Multi-source edge () must have at least one source (V-16)
  含 __start__        ⇒ ValueError ✓ · Multi-source edge ('__start__', 'b') must not contain the entry marker
  目标数=2            ⇒ ValueError ✓ · Multi-source edge ('a', 'b') must have exactly one target, got 2 (V-16
  目标数=0            ⇒ ValueError ✓ · Multi-source edge ('a', 'b') must have exactly one target, got 0 (V-16)
  目标为 __end__      ⇒ ValueError ✓ · Multi-source edge ('a', 'b') must not target the terminal marker '__end__' (V-16)
  缺源                ⇒ ValueError ✓ · Multi-source edge ('a', 'zz') has sources not in the node table: ['zz'] (V-2)
  目标不存在          ⇒ ValueError ✓ · Multi-source edge target 'nope' is not in the node table (V-2)
  键类型非法          ⇒ TypeError  ✓ · GraphSpec edge key must be a str or a tuple of str, got int
```

> ⚠️ **断言纪律**：测试**只**断言**异常类型**与**点名** ⇒ ⇒ **MUST NOT** 断言消息的
> **逐字文本**（澄清轮 **C-Q15**）⇒ ⇒ 上表的**消息**仅作**人工留痕**。

### 3.6 **本记录落盘后**的一键验收复跑

```text
.venv/bin/python harness/verification/B7F4/acceptance.py
⇒ [PASS] A1 … [PASS] A10 ⇒ 总闸口 11 · 失败 0 · 跳过 0 ⇒ **PASS**
```

---

## 4. 结论

| 判据 | 结论 | 证据 |
|---|---|---|
| **A1** 多源边可表达 | ✅ **PASS** | `edges={("a","b"): ("c",)}` ⇒ 构造成功（**M-1**） |
| **A2** 屏障语义正确 | ✅ **PASS** | 目标**严格晚于**所有源（**M-2**）· 不齐 ⇒ 静默等待（**M-3**）· 后齐 ⇒ 再执行一次（**M-5**）· 同一轮至多一次（**M-4**）· 组间任一（**M-8**） |
| **A3** 与上游同款 | ✅ **PASS** | **D-16…D-28** 全绿 · **SAME 11 条 + STRICTER 2 条** · 行为面分叉 == **0** |
| **A4** 既有断言零削弱 | ✅ **PASS** | **10 个**冻结断言文件的 `git diff HEAD --stat` **全为空** + 全量绿（**M-6**） |
| **A5** 冻结面追认 | ✅ **PASS** | 本记录**五段式**齐全 + **PR-1…PR-8** 八项**打包成一次**的追认文字**已由发起者签字落盘**（**2026-11-13** · 见 §4.1）⇒ ⇒ **合入闸口 G-f 已开** |
| **A6** 导出面零新增 | ✅ **PASS** | `runtime.__all__ == 20` · `contracts.__all__ == 20`（**M-9**） |
| **A7** 回溯修订落全 | ✅ **PASS** | **R-1…R-10** 的 **10 个**落点**逐条命中** |
| **A8** 形态校验生效 | ✅ **PASS** | **V-16** 四条 + **V-2** 两条 + 边键**类型**非法 ⇒ 内置 `TypeError` |
| **A9** 参数化场景全绿 | ✅ **PASS** | **D-24** 的 **12 组**（屏障形态 × 通道类型 × 源可达性）全绿（**H-6** · **M-13**） |
| **A10** 门禁偏离已登记 | ✅ **PASS** | 门禁 **3 / 4 / 5 / 7** 的「**物理不可达成**」**逐条点名**登记（见 §4.2） |

### 4.1 **发起者追认**（**八项打包成一次** · 登记项 **PR-1…PR-8**）

> ⚠️ **MUST NOT** 由实现者代签（宪法原则 V / v1.6.0 / v1.8.0）⇒ ⇒ 本段**只登记**
> ⇒ ⇒ **追认由发起者落笔**（签字 + 日期）⇒ ⇒ **未落笔前 MUST NOT 合入**。

**发起者追认（一次 · 打包 PR-1…PR-8 八项）**：

> 我（**发起者**）确认并追认 **B7F4** 的下列**八项**登记项（**一次**追认 ⇒
> **追认次数 == 1**）⇒ ⇒ 授权合入：
>
> 1. **PR-1** —— **破 B7F1 冻结面**的**回溯修订 R-1…R-10**（**拆分而不删** · 既有断言**一条不删**）
>    ⇒ 确认「**上游有此项** ⇒ freegraph 原先**缺**」是**能力缺口**（非「偏离」）⇒ ⇒ 破冻结面是「**补能力**」的**必要代价**；
> 2. **PR-2** —— **X-02**「**空的多源边**」的**更严失败信号**（freegraph **构造期显式失败** · 上游**静默**）；
> 3. **PR-3** —— **触发判定式**由「∃ 触发源」改写为「**∃** 组 g：**∀** s∈g」（**单源口径逐字退化** ⇒ 既有断言**一条不删**）；
> 4. **PR-4** —— **下游承接 D-1…D-7** 的**跨 feature 文档改动**（含 **D-5 → B7F2** · **D-6 → B24F1** · **D-7 → B19F1**）；
> 5. **PR-5** —— **质量门禁 3 / 4 / 5 / 7** 的相关部分在本 feature **物理不可达成**（**判据一字未改** · 见 §4.2）；
> 6. **PR-6** —— **立项书 §4.2 S5 ③** 的**最小增量**（= **D-24** 的**参数化**场景组）；
> 7. **PR-7** —— **X-04**「**多源边的目标为 `__end__`**」的**更严失败信号**（freegraph **构造期显式失败** · 上游**静默 no-op**）；
> 8. **PR-8** —— **FR-021**「**边键类型非法** ⇒ 内置 `TypeError`」（**上游同族** · 实测 **E-10**）。
>
> **发起者签字**：杨家成（仓库 owner / 发起者）　**日期**：**2026-11-13**
>
> ⚠️ **追认已落盘** ⇒ ⇒ 本段由「**已登记 · 未追认**」转入「**已追认**」状态 ⇒ ⇒
> ⇒ ⇒ **合入闸口（G-f）已开** ⇒ ⇒ **PR-1…PR-8 八项打包成一次**（**追认次数 == 1**）⇒ ⇒
> ⇒ ⇒ **判据只收紧、不放宽**（依赖 / 许可证 / 商标 / 零出站**四条红线照常执行**）⇒ ⇒
> ⇒ ⇒ **破冻结面的代价已付** ⇒ ⇒ **授权合入**。

### 4.2 **门禁项偏离登记**（登记项 **PR-5** · 宪法 v1.6.0）

| # | 被偏离的门禁项 | 根因（**物理不可达成**的取证） | 判据未被放宽的论证 | 承接方 |
|---|---|---|---|---|
| ① | **门禁 3**（固定脚本原样可跑）的相应部分 | 本 feature 按立项书 §5.2 **只交付 L2**（`GraphSpec` 元组键 + 触发层屏障语义）⇒ ⇒ `StateGraph` / `compile()` / `invoke()` **未落地** ⇒ ⇒ **无图可跑** ⇒ ⇒ 实测：`freegraph.graph.StateGraph(...).add_edge("a","b")` ⇒ `NotImplementedError: add_edge 尚未接线（由 B6F1 交付）`；`.compile()` ⇒ `NotImplementedError: compile 尚未接线（由 B7F2 交付）` ⇒ `.compile().invoke()` **同样不可达** | 门禁 3 的判据**一字未改** ⇒ ⇒ **MUST NOT** 伪装成「已通过」⇒ ⇒ **MUST NOT** 写一条**永久红**的 CI ⇒ ⇒ **零放宽** | **B6F1 / B7F3**（M2） |
| ② | **门禁 4**（fake 模型跑通验收基线的一轮）的相应部分 | 同 ①（**同一根因**）⇒ ⇒ **无图可跑** ⇒ ⇒ fake 模型**无入口** | 同 ① | **B6F1 / B7F3**（M2）· **B25F1**（M4） |
| ③ | **门禁 5** + 原则 V 的「人工验证记录含真实模型一轮」的相应部分 | 同 ① ⇒ ⇒ **真实模型**同样**无入口** | 同 ① | **B6F1 / B7F3**（M2）· **B25F1**（M4） |
| ④ | **门禁 7**（文档合规门禁）的「**API 兼容矩阵已更新**」这一部分 | **兼容矩阵尚未落库**（全仓无该文件 ⇒ `find -iname "*compat*"` 仅命中 `harness/docs/oss/python/langgraph/backward-compatibility.md` = **上游文档** ⇒ 非本仓矩阵）⇒ ⇒ 首次落库属 **B24F1 / M4** ⇒ ⇒ 本 feature 按里程碑**同样不交付其前置能力** | 门禁 7 的判据**一字未改** ⇒ ⇒ **MUST NOT** 伪装成「已通过」⇒ ⇒ **MUST NOT** 写**永久红**的 CI ⇒ ⇒ **零放宽** | **B24F1 / M4**（已有下游承接 **D-6**） |

> ⚠️ **红线照常执行**：依赖 / 许可证 / 商标 / 零出站**四条红线**在本 feature **照常执行**
> ⇒ ⇒ 且**手工验证记录照常五段式**（本文件）。
> ⚠️ **本登记并入 §4.1 的同一次追认** ⇒ ⇒ **追认次数仍 == 1** ⇒ ⇒ **零新增登记项**。

---

## 5. 遗留问题

| # | 遗留项 | 性质 | 处置 |
|---|---|---|---|
| ① | **立项书 §5.2** 的 **620 行 / 3 人日** 与本 feature 的**实际规模**（**78** 条任务）**体量口径不同** | **上位文档的**规模估算**与实际不符** | ⇒ **MUST 由发起者**在 feature 收尾时**重估回写** ⇒ ⇒ 本 feature **MUST NOT** 单方面改上位文档 |
| ② | **立项书 §5.2** 与 `harness/features/README.md` 的 B7F4 描述仍写「**所有**源跑完后才被触发」⇒ 比澄清轮 **C-Q1** 的口径（**组内全 · 组间任一**）**更窄** | **口径描述**未更新 | ⇒ ⇒ **只登记不代改**（§4.1 的追认已按拍板口径落地实现）⇒ ⇒ **MUST 由发起者**回写 ⇒ ⇒ `harness/features/README.md` 与 `harness/features/B7F4_多源汇合边与屏障.md` 的**注记**已由本 feature 补上（**只补注记 · 不改写原描述**） |
| ③ | **API 兼容矩阵**尚未落库 ⇒ 「**多源汇合边**」条目归 **B24F1**（**D-6**）⇒ 本 feature **未**代改 ⇒ ⇒ **门禁 7** 的「**兼容矩阵已更新**」在本 feature **物理不可达成** | **门禁偏离**（**已登记**） | ⇒ ⇒ 已按 **PR-5** **如实登记**（§4.2 ④）⇒ ⇒ 承接方 = **B24F1 / M4** |
| ④ | 门禁 **3 / 4 / 5** 的相应部分在本 feature **物理不可达成** | **门禁偏离**（**已登记**） | ⇒ ⇒ 已按 **PR-5** **如实登记**（§4.2 ①…③）⇒ ⇒ 承接方 = **B6F1 / B7F3 / B25F1** |
| ⑤ | **上游行号**的两处**订正**：`state.py:968` ⇒ **`:969`** · `state.py:975` ⇒ **`:976`** | **事实性引用**的订正（已逐条对照本机 `langgraph 1.2.11` 源码核验） | ⇒ ⇒ 已**同步**到 `spec.md` / `plan.md` / `tasks.md` / `research.md` / `contracts/upstream-parity.md` ⇒ ⇒ **不改任何口径**（取证见 `research.md` §4 的 **C-11** 行） |
| ⑥ | **B3F1 的门禁契约文档**（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` §0）仍写「**G7** 契约层公开符号面**恰为 18 个**」⇒ 而 `public-api.md` §0 与 `tests/contracts/test_architecture.py` 均已升为 **20** | **上游遗留**（**非本 feature 引入**） | ⇒ ⇒ **本 feature MUST NOT 代改** ⇒ ⇒ **应由 B3F1 单独回修** ⇒ ⇒ 本 feature 的 **G7 判定基线以 `public-api.md` §0 == 20** 为准 |
| ⑦ | **B22F1**（`get_graph` 与 `draw_mermaid`）的 **FR-002** 仍写「`edges` 的元素含**边起止**」⇒ ⇒ **单源**形态 ⇒ ⇒ **多源汇合边**的 `edges` 元素需要**多源**的表达（**起止**如何表达 ⇒ 由 B22F1 自行裁定）⇒ ⇒ **本 feature MUST NOT 代改**（**不在 D-1…D-7 的承接清单内** ⇒ **零新增**下游承接条款）⇒ ⇒ **只登记** | **后续 feature 的知情面** | ⇒ ⇒ **由发起者**决定是否在 **B22F1** 的 spec 阶段**立项承接**（⇒ 本 feature **MUST NOT** 越界改动 `harness/features/B22F1_*.md`） |
| ⑧ | **B11F1**（`Send` 动态 fan-out）的背景段仍写「静态边 `add_edge(src, dst)` **总是**用同一份状态调用 `dst`」⇒ ⇒ 该表述对**单源**静态边成立 ⇒ ⇒ **多源**静态边的**触发时机**（**全部**源跑完后才调 `dst`）**未**在该段体现 ⇒ ⇒ **本 feature MUST NOT 代改**（**不在 D-1…D-7 的承接清单内**）⇒ ⇒ **只登记** | **后续 feature 的知情面** | ⇒ ⇒ **由发起者**决定是否在 **B11F1** 的 spec 阶段**立项承接** |

---

## 6. 来源覆盖表

| 来源 | 覆盖的判据 | 落点 |
|---|---|---|
| `specs/b7f4-multisource-join/spec.md`（**FR-001…FR-022** · **SC-001…SC-013** · 裁定 1…18） | 全部 | §2 / §3 / §4 |
| `specs/b7f4-multisource-join/contracts/superstep-multisource-contract.md`（**M-1…M-16**） | 全部 | §3 / §4 |
| `specs/b7f4-multisource-join/contracts/upstream-parity.md`（**P-01…P-16** · **E-1…E-11**） | **A3** | §3.3 |
| `specs/b7f4-multisource-join/research.md`（**DR-1…DR-13** · §4 取证） | 全部 | §2 / §3 |
| `specs/b7f4-multisource-join/quickstart.md`（**A1…A10**） | 全部 | §2.4 / §2.5 / §4 |
| `specs/b7f1-superstep-loop/contracts/superstep-contract.md`（**R-1…R-6**） | **A4 / A7** | §3.4 |
| `specs/b7f1-superstep-loop/spec.md` · `data-model.md`（**R-7 / R-8**） | **A7** | §2.3 / §4 |
| `specs/b7f1-superstep-loop/tasks.md` · `research.md`（**R-10**） | **A7** | §2.3 / §4 |
| `harness/features/**`（**D-1…D-7**） | **PR-4** | §4.1 ④ |
| `.specify/memory/constitution.md`（原则 V / v1.6.0 / v1.8.0 / v1.9.0） | **A5 / A10** | §4.1 / §4.2 |
