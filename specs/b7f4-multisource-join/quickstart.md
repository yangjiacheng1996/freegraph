# 快速验收指南（B7F4 · 多源汇合边 · AND / 屏障）

**Feature**: `B7F4` · **Spec**: [spec.md](./spec.md) · **契约**: [contracts/superstep-multisource-contract.md](./contracts/superstep-multisource-contract.md) · **数据模型**: [data-model.md](./data-model.md)

> **本文件是「怎么验证 B7F4 真的跑通了」的**可跑指南**（**不是**实现教程 · **不是**测试套件）。
> ⇒ 每条场景只给**最小可跑片段** + **期望结果** + **判据出处**；
> ⇒ **完整测试套件**落在 `tasks.md` 指向的**单元用例文件**与**差分探针**里。
> ⚠️ **本 feature 只交付 L2 运行时** ⇒ 图规格**手写**（`GraphSpec`）⇒ **无** `StateGraph` / `compile()` / `invoke()`
> 可用（那属 **B6F1 / B7F2 / B7F3**）⇒ ⇒ **本文件全部场景用手写图规格**。

---

## 0. 环境与前置

```bash
cd <repo>
.venv/bin/python --version          # CPython >= 3.11（本机 3.12）
.venv/bin/python -m pytest --version
.venv/bin/python -c "import langgraph, sys; print(langgraph.__file__)"  # 上游（**仅**差分用）
```

| 前置 | 状态 | 说明 |
|---|---|---|
| **B7F1**（调度内核） | ✅ 已落地 | `run_super_step` / `run_super_steps` / `GraphSpec` / `SchedulerState` |
| **B12F1**（并发执行器） | ✅ 已落地 | 同轮并发 + `max_concurrency` |
| 上游 `langgraph` | 可选 | **缺席时差分场景 skip**（沿用 B5F2 纪律）⇒ **不**影响单元验收 |

> ⚠️ **零出站 / 零环境变量 / 零第三方运行时依赖** ⇒ 上面三条命令**不联网**。

---

## 1. 一句话冒烟（**先跑这个**）

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

**期望输出**：`['a', 'b', 'c']` ⇒ `c` **最后**执行 ⇒ 屏障成立。

> ⚠️ `executed` 的口径 = **节点名序**（B12F1 已落地）⇒ `calls` 的**顺序**在**并发**下**不保证**
> ⇒ 断言时 MUST 用「**`c` 在 `a` / `b` 之后**」而**不是**「`a` 在 `b` 之前」。

---

## 2. 验收场景（**A1…A10** · 逐条可判定）

### **A1 · 多源边可表达**

```python
GraphSpec(channels={...}, nodes={...}, edges={("a", "b"): ("c",)})   # ⇒ 构造成功（不抛错）
```

**期望**：**构造成功** ⇒ 无异常。
**判据**：spec **A1** · 契约 §2.1 · 不变量 **M-1**。

---

### **A2 · 屏障语义正确**（**两段**）

**第 1 段**：`a`、`b` 都可达 ⇒ `c` 执行且**在二者之后**。

```python
# edges={"__start__": ("a", "b"), ("a", "b"): ("c",)}
# ⇒ 执行序列里 c 的位置晚于 a 与 b
```

**第 2 段**：只让 `a` 可达 ⇒ `c` **不执行**。

```python
# edges={"__start__": ("a",), ("a", "b"): ("c",)}    # b 永不可达
# ⇒ c 的执行计数 == 0；图正常收敛（不抛错）
```

> ⚠️ **前置限定**：第 2 段里 `c` **只有**这一条多源入边 ⇒ 若 `c` 另有**单源入边** ⇒ 按「**组间任一**」
> 它**仍会被触发**（那是 **D-18** 的场景 · 澄清轮 **C-Q1**）。

**判据**：spec **A2** / **SC-001** / **SC-002** · 不变量 **M-2 / M-3**。

---

### **A3 · 与上游同款**（**差分探针**）

```bash
.venv/bin/python -m pytest tests/differential/ -v
```

| 场景 | 断言 | 判词 |
|---|---|---|
| **D-16** | 标准屏障（`("a","b") → c`）⇒ 两侧**节点序列 + 最终状态**逐字一致（上游基线 `{'msgs': ['a','b','c']}`） | **SAME** |
| **D-17** | 屏障不齐 ⇒ 两侧的 `c` **都不执行** | **SAME** |
| **D-18** | 单源边 + 屏障边并存（屏障不齐）⇒ 两侧的 `c` **都执行一次** | **SAME** |
| **D-19** | 屏障**后齐** ⇒ 两侧的 `c` **都执行两次** | **SAME** |
| **D-20** | 并发档 vs 串行档（`max_concurrency=1`）⇒ freegraph 两侧**最终状态 + 待写入序列**逐字相等 | **SAME** |
| **D-21** | 两条屏障并存（一条不齐）⇒ 两侧的 `c` **都执行一次** | **SAME** |
| **D-22** | 缺源的多源边 ⇒ 两侧都**构造期失败** | **SAME** |
| **D-23** | `("a","b")` vs `("b","a")` ⇒ 执行序列**逐字相等** | **SAME** |
| **D-24** | **参数化**（屏障形态 × 通道类型 × 源可达性）⇒ 两侧**节点序列 + 最终状态**逐字一致 | **SAME** |
| **D-25** | 多源边指向 **`__end__`** ⇒ 上游**接受但静默 no-op**（**E-9**）· freegraph**构造期显式失败** | **STRICTER**（**X-04**） |
| **D-26** | **空**的多源边 `()` ⇒ 上游**接受但静默**（**E-6**）· freegraph**构造期显式失败** | **STRICTER**（**X-02**） |
| **D-27** | 两条**同成员不同序**的多源边并存 ⇒ 两侧的屏障目标**都只执行 1 次**（**E-11**） | **SAME** |
| **D-28** | **边键类型非法**（`123 → ("a",)`）⇒ 两侧**均抛内置 `TypeError`**（上游 **E-10** 同族） | **SAME**（澄清轮 **C-Q14**） |

**判据**：spec **A3** / **SC-004** / **SC-011** / **SC-013** · 不变量 **M-11 / M-13** · 契约 §7。
⚠️ **判词分布** = **SAME 11 条**（**D-16…D-24 / D-27 / D-28**）+ **STRICTER 2 条**（**D-25 / D-26**）⇒ ⇒ **DIFF == 0 条**。
⚠️ **上游缺席即 skip**（**不**是失败）⇒ ⇒ **CI 的 Linux 全量档**才是阻断门禁。

---

### **A4 · 既有断言零削弱**

```bash
# ① 既有触发判定用例：原文件**逐字未变**（澄清轮 C-Q5 的机械判据）
#    ⚠️ MUST 用 `git diff HEAD --stat`（**不是** `git diff --stat`）—— 后者不比对**已暂存**的改动 ⇒ 可假通过
#    ⚠️ MUST 查**全部 10 个**冻结断言文件（清单见 tasks.md T007）⇒ **MUST NOT** 只查其中一个
for f in test_superstep_trigger test_superstep_contract test_command_contract \
         test_command_goto_semantics test_command_noop test_command_purity \
         test_superstep_concurrency test_command_list test_command_merge_parity \
         test_read_c4_sparse_state; do
  git diff HEAD --stat -- "tests/runtime/$f.py"     # ⇒ **必须为空**
done
# ② 既有用例全绿
.venv/bin/python -m pytest tests/runtime/ -v
# ③ 多源口径的用例（新文件）
.venv/bin/python -m pytest tests/runtime/test_superstep_multisource.py -v
```

**期望**：① **10 个** `git diff HEAD --stat` **全为空**；② 全绿；③ 全绿。
**判据**：spec **A4** / **SC-005** · 不变量 **M-6** · 裁定 16。

---

### **A5 · 冻结面追认**

```bash
test -f harness/verification/B7F4/manual-verification.md
grep -n "追认" harness/verification/B7F4/manual-verification.md
```

**期望**：文件存在 + 五段式齐全 + **含发起者追认文字**（追认 + 发起者确认 + 日期）。
**判据**：spec **A5** / **SC-009** · FR-012 / FR-015。

---

### **A6 · 导出面零新增**

```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import freegraph.runtime as r; print(len(r.__all__))"
# ⇒ 20
.venv/bin/python -c "import sys; sys.path.insert(0,'src'); import freegraph.contracts as c; print(len(c.__all__))"
# ⇒ 20
```

**期望**：`20` / `20` ⇒ **零新增导出符号** · **零新增通道类型**。
**判据**：spec **A6** / **SC-006** · 不变量 **M-9** · FR-006。

---

### **A7 · 回溯修订落全**（**R-1…R-10**）

```bash
# 逐条核对（位置见 spec 的「破冻结面的回溯修订清单」）
grep -n "tuple\[str" specs/b7f1-superstep-loop/contracts/superstep-contract.md      # R-1
grep -n "触发源组\|groups(N)" specs/b7f1-superstep-loop/contracts/superstep-contract.md  # R-2 / R-3
grep -n "只消费\|已满足的组" specs/b7f1-superstep-loop/contracts/superstep-contract.md   # R-5
grep -n "屏障" specs/b7f1-superstep-loop/contracts/superstep-contract.md            # R-4 / R-6
grep -n "V-16" specs/b7f1-superstep-loop/data-model.md                              # R-8
grep -n "2026-11-13 · B7F4" specs/b7f1-superstep-loop/tasks.md specs/b7f1-superstep-loop/research.md  # R-10
```

**期望**：每条**命中** ⇒ **R-1…R-10 逐条落全**；且 B7F1 的既有内容**只增不改**。
**判据**：spec **A7** / **SC-008** · FR-013。

---

### **A8 · 形态校验生效**

```python
GraphSpec(..., edges={(): ("c",)})                    # ⇒ ValueError（空元组 · V-16）
GraphSpec(..., edges={("__start__", "b"): ("c",)})    # ⇒ ValueError（含入口哨兵 · V-16）
GraphSpec(..., edges={("a", "b"): ("c", "d")})        # ⇒ ValueError（目标数 ≠ 1 · V-16）
GraphSpec(..., edges={("a", "b"): ("__end__",)})      # ⇒ ValueError（目标为 __end__ · V-16 · X-04）
GraphSpec(..., edges={("a", "zz"): ("c",)})           # ⇒ ValueError（缺源 · V-2 同族 · 点名 zz）
GraphSpec(..., edges={123: ("c",)})                   # ⇒ TypeError（边键类型非法 · FR-021）
GraphSpec(..., edges={("a", "b"): ("nope",)})         # ⇒ ValueError（多源边目标不存在 · V-2 同族 · 点名 nope）
```

**期望**：前六条**全部**抛**内置 `ValueError`**、第七条抛**内置 `TypeError`**
（**零新增错误类型**）⇒ 消息**点名**问题源。
⚠️ **追加（澄清轮 C-Q18 / C-Q20）**：第七条（**多源边的目标不存在**）**归 `V-2`**（语义校验族）
⇒ ⇒ **NOT** `V-16`（形态校验族）⇒ ⇒ 校验顺序：形态 `V-16` **先于** 缺源 / 缺目标 `V-2`。
**另两条 Edge Case（**T086 / T087**）**不属构造期失败** ⇒ 属**运行期行为**：
① **源重复** `edges={("a","a"): ("c",)}` ⇒ **构造成功**（**MUST NOT** 报错）⇒ 行为与
`edges={"a": ("c",)}` **逐字一致**（**去重保序** · 裁定 2）；② **环图** `("a","b") → c` 且 `c → a`
⇒ 屏障**照常判定** ⇒ 收敛由**既有步数上限**兜底（**MUST NOT** 抛环检测类异常 · research **DR-9**）。
**判据**：spec **A8** / **SC-008** · 裁定 5 / 6 / 7 / 8 / **17** · 语义点 **P-15 / P-16** ·
任务 **T024 / T037 / T086 / T087**。

---

### **A9 · 参数化场景全绿**（**H-6** · 立项书 §4.2 **S5 ③** 的最小增量）

```bash
# D-24（参数化：屏障形态 × 通道类型 × 源可达性）在 CI 的 Linux 全量档真跑
.venv/bin/python -m pytest tests/differential/ -v -k "param"
```

**期望**：**全绿**（上游缺席即 **skip** ⇒ 不是失败）⇒ 判词 = **SAME**。
**判据**：spec **A9** / **SC-013** · 不变量 **M-13** · 承接 **H-6** · 任务 **T050**。

---

### **A10 · 门禁偏离已登记**（**PR-5** · 宪法 v1.6.0）

```bash
# ① 门禁 3 / 4 / 5 / 7 的「物理不可达成」必须**如实登记**（MUST NOT 伪装成「已通过」）
grep -n "门禁 3\|门禁 4\|门禁 5\|门禁 7\|物理不可达成" harness/verification/B7F4/manual-verification.md
# ② 四条门禁的判据**一字未改** ⇒ MUST NOT 写成永久红的 CI
grep -rn "gate_G3\|gate_G4\|gate_G5" harness/scripts/gates/ | head
# ③ 门禁 7 的根因取证：**API 兼容矩阵尚未落库**（首次落库属 B24F1 / M4）
find . -path ./.git -prune -o -iname "*compat*" -print | grep -v node_modules | grep -v "\.venv" | head
```

**期望**：人工验证记录的「**遗留问题**」段含**逐条点名**的登记（被偏离项 · 根因 · **判据未被放宽**的论证 ·
承接方 **B6F1 / B7F3 / B25F1 / B24F1** · 落点）⇒ 且**并入**同一次追认（**PR-1…PR-8** 打包成 1 次）。
⚠️ **追加（澄清轮 C-Q19）**：**门禁 7** 的「**API 兼容矩阵已更新**」这一部分在本 feature
**物理不可达成**（**根因**：兼容矩阵**尚未落库** ⇒ 首次落库属 **B24F1 / M4**）⇒ ⇒ 一并如实登记
⇒ ⇒ 宪法侧已配套澄清（**v1.10.2** · 「适用范围」的两要件为准）⇒ ⇒ **判据零放宽**。
**判据**：spec **A10** / **FR-019** / **SC-009** · 登记项 **PR-5** · 任务 **T008 / T070 / T080** · **MUST NOT** 写永久红 CI。

---

## 3. 门禁与回归（**零新增门禁编号**）

```bash
# 依赖 / 许可证 / 商标 / 零出站 / 层纪律（既有门禁 G1–G30 ⇒ **不新增编号**）
.venv/bin/python -m pytest tests/contracts/ -v      # 含 test_architecture.py（G7 / G25 等）
.venv/bin/python -m pytest tests/ -v                # 全量
```

| 门禁 | 本 feature 的关系 |
|---|---|
| **G1–G30** | **零新增编号**（FR-011 / SC-007）⇒ 屏障的正确性由**差分探针**与**既有门禁**覆盖 |
| **G7**（公开符号面） | 基线 == **20**（runtime）· **20**（L1）⇒ **零改动** |
| **G25**（层注册表） | **零改动**（**不新增模块** ⇒ `runtime/` 的目录条目已登记） |
| 依赖 / 许可证 / 商标 / 零出站 | **照常执行**（内核路径**零** `langchain*` / `langgraph*` / `langsmith` · **零**环境变量 · **零**文件 I/O） |
| 门禁 **3 / 4 / 5** 的「物理不可达成」部分 | **如实登记**（**PR-5**）⇒ 判据**一字不改** ⇒ **MUST NOT** 写永久红 CI（⇒ **不占用**任何 G 编号） |

---

## 4. 一键验收（**机械层** · 沿用仓库先例）

```bash
.venv/bin/python harness/verification/B7F4/acceptance.py
```

**期望**：全部闸口**绿**（每条断言都**复用**既有判据的**同一口径** ⇒ **零新增判据**）。
⚠️ 该脚本**不是门禁** ⇒ **不占用** G 编号 ⇒ **零新增门禁编号**。

---

## 5. 人工验证（**最终验收标准** · 原则 V）

```bash
less harness/verification/B7F4/manual-verification.md
```

**五段式**（缺一不可）：**验证环境** / **验证步骤** / **实际输出** / **结论** / **遗留问题**
⇒ 且 MUST 含 **发起者追认**文字（**破冻结面**的代价 · FR-012 / SC-009）。

---

## 6. 常见问与答（**排障**）

| 现象 | 原因 | 处理 |
|---|---|---|
| `c` 在 `a` 之前就跑了 | 检查 `edges` 的键**是不是元组**（写成 `"a"` ⇒ 单源边 ⇒ 无屏障） | 键必须是 `("a", "b")` |
| `c` **一次都没跑** | 屏障**不齐** ⇒ 某个源**永不可达**（或它**没被边触发**） | 查该源的入边；或对照上游 **E-2** |
| `c` 跑了**两次** | **正常**：屏障**后齐** ⇒ 上游**同款**（**E-5**） | 判据见 **M-5** · 差分 **D-19** |
| `c` 明明屏障不齐却跑了 | 它**另有单源入边** ⇒ **组间任一**（**E-3**） | 判据见 **M-8** · 差分 **D-18** |
| 构造时报 `ValueError` | 形态非法：空元组 / 含 `__start__` / 目标数 ≠ 1 / **目标为 `__end__`** / 缺源 | **A8** 五条逐条核对 |
| 构造时报 `TypeError` | **边键类型非法**（既非 `str` 亦非 `tuple`） | **A8** 第六条 · **FR-021** |
| 差分场景 **skip** | 上游**未安装** ⇒ 「缺席即 skip」纪律 | 装上游后重跑（**不**是失败） |

---

## 7. 参考

| 项 | 落点 |
|---|---|
| 需求与判据（**唯一权威**） | [spec.md](./spec.md) |
| 契约（**逐字冻结的数据契约**） | [contracts/superstep-multisource-contract.md](./contracts/superstep-multisource-contract.md) |
| 上游证据表 | [contracts/upstream-parity.md](./contracts/upstream-parity.md) |
| 实测与设计决策 | [research.md](./research.md) |
| 实体 / 状态机 / 不变量 | [data-model.md](./data-model.md) |
| 任务清单（**Phase 2**） | [tasks.md](./tasks.md) · **由 `/speckit.tasks` 生成** |
