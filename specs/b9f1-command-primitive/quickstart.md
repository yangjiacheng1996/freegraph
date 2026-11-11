# Quickstart: B9F1 · `Command` 原语（`goto` / `update` + `Command.PARENT`）

**Feature**: `B9F1` · **Spec**: [spec.md](./spec.md) · **契约**: [contracts/command-contract.md](./contracts/command-contract.md)
**核实环境**: CPython **3.12.3**（取证用）· 上游 `langgraph` **1.2.11**（核实于 2026-11-11）

> 本文件是**可照抄的验证手册**（闸口 **V1–V12**）—— 只写**怎么跑**与**期望看到什么**，
> **不含**实现代码（实现属 `tasks.md` 与实现阶段）。
> ⚠️ **本 feature 不交付 `invoke()` / `compile()`** ⇒ **没有** `app.invoke(...)` 可跑；
> 全部闸口用**手写图规格**直接驱动调度内核（这正是 B7F1 留下的**独立可验收性**前提）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（B3F1 的既有结论）
python3 -m venv .venv

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
.venv/bin/python -m pip install -U pip
uv pip install --python .venv --group dev

# ③ 本 feature 包（editable）
uv pip install --python .venv --editable .

# ④（**可选**）覆盖率工具 —— **不进依赖声明**（v1.0 依赖面为零）⇒ 开发期临时安装
uv pip install --python .venv coverage
```

### 0.2 **不需要**上游

本 feature 的内核**零上游依赖** ⇒ **不需要** `differential` 依赖组 ⇒
**断网**也能跑完全部闸口（宪法原则 I / IV · SC-014）。
⚠️ 上游只在 **Phase 0 取证**时用过（**用户 site-packages** · 非仓库依赖）⇒ 见
[research.md](./research.md) §1。

---

## 1. 跳转 + 更新**同时生效**（**验收判据 A1 / A2** · SC-001 / SC-002）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_goto_update.py -v
```

**期望**：

| 项 | 期望值 |
|---|---|
| `Command(goto=END, update={...})` | 状态**含**该更新（**按归约器合并**）**且** 流程**按 `goto` 终止**（之后无节点被执行） |
| `Command(goto="next", update={...})` | `"next"` **被执行**（跳转生效）**且** 状态含该更新（更新生效）⇒ **两条断言同时成立** |
| 「只生效其一」的现象 | **0** 次 |

⚠️ **不得**出现 `StateGraph` / `compile()` / `invoke()` —— 闸口 **V3** 会静态扫描（**A3** · SC-016）。

---

## 2. `Command.update` 与普通 `dict` 返回**共用同一条合并路径**（**验收判据 A3** · SC-003）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_merge_parity.py -v
```

**期望**：

| 写法 | 期望值 |
|---|---|
| 返回 `dict` | 合并结果 **R** |
| 返回 `Command(update=同一份)` | 合并结果 **R**（**逐项相等**） |
| 返回 `Command(update=同一份, goto=...)` | 合并结果 **R**（**逐项相等**） |
| 返回 `Command(update=同一份)`（**列表形态**） | 合并结果 **R**（**逐项相等**） |
| 未知 key（四种写法） | **都**抛 `InvalidUpdateError` · `invalid_keys` **一致** |
| 「行为分叉」的现象 | **0** 次 |

⚠️ **归约型通道**必须**按序归约**（不是覆盖）⇒ 期望值用「`operator.add` 的逐元素拼接」逐项比对。

---

## 3. 归约器、未知 key、覆盖型冲突（**C6** · SC-004 / SC-023）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_merge_parity.py -k "reducer or unknown or overwrite" -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 归约型通道 + `Command.update` | 与「按序逐条写入」**逐元素相等** |
| 未知 key | `InvalidUpdateError` · `invalid_keys` == 实际未知 key 集合（顺序保持） |
| 覆盖型通道同轮多写 | `InvalidChannelUpdateError`（B5F1 既有类型 · **零新增错误类型**） |
| 静默丢弃未知 key | **0** 次 |

---

## 4. `Command.PARENT` 的 v1 行为**可判定**（SC-005）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_parent.py tests/runtime/test_command_goto_errors.py -v
```

> `test_command_parent.py` = **`PARENT` + 保留名**；`test_command_goto_errors.py` = **非法目标 / 非法形态**。

**期望**：

| 场景 | 期望值 |
|---|---|
| `Command(goto=Command.PARENT)` | 抛 **`NotImplementedError`** · 消息点名 `__parent__` 与「子图属 v2 能力」 |
| 图规格含名为 `__parent__` 的节点 | **构造期**即抛 **`ValueError`**（保留名） |
| `Command(goto="不存在的节点")` | 抛 **`ValueError`** · 消息**点名该目标** |
| 「静默失效」的现象 | **0** 次 |
| `NotImplementedError` 与 `ValueError` **可区分** | 两条用例的异常类型**不同** |

---

## 5. 跳转与静态边**叠加**（SC-007）· `END` **不终止**（SC-008）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_goto_semantics.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 节点 X 有静态边 X→Y 且返回 `Command(goto="Z")` | **Y 与 Z** 在**下一轮****都**被执行 |
| 同一对 (源, 目标) 在一轮内被触发 | **恰好 1** 次 |
| `Command(goto=END)` + 静态边 | 静态边目标**照常执行**（`END` **不**终止整张图） |
| `Command(goto=END)` + `update` | 更新**照常生效** |
| `goto` 的目标在**同一轮**内被执行 | **0** 次 |

---

## 6. 目标的**触发与入参**（SC-023）· **生命周期**（SC-010）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_goto_semantics.py -k "input or lifecycle" -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 目标订阅的通道**都没值** | 目标**照跑**（入参为空 `dict`）⇒ 「因为入参为空而没跑」**0** 次 |
| 目标的入参 | == `read_channels(子映射)` 的结果（**逐字相等** · 子映射按**通道映射顺序**构造） |
| 源节点 `goto` + `update` | 目标**读得到**这次 `update` 的内容 |
| 源节点再次执行且**不**给 `goto` | 旧目标**不再**被触发（残留触发 **0** 次） |

---

## 7. **命令列表** 与 **空操作**（上游同款 · SC-021 / SC-006 / SC-012）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_list.py tests/runtime/test_command_noop.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| `return [Command(goto="a"), Command(update={...})]` | 目标 **a** 被执行 + 更新生效 |
| 列表里**每条**命令的 `goto` | **全部**目标在下一轮被执行 |
| 列表里**混入 `dict`** | 其写入按**所在位置**生效（与「单独返回该 dict」**逐项一致**） |
| **空列表** | 零写入 + 零跳转 + 节点**仍计入执行记录** |
| 元素类型非法 | 抛 **`TypeError`** |
| 列表写入的**合并顺序** | == 「按列表顺序逐条写入」的归约结果（**逐元素相等**） |
| **空槽位**（`update={}` / `goto=()` / 两者皆空） | 零写入 + 零跳转 + 节点**仍计入执行记录** |
| **空列表** `[]` | 零写入 + 零跳转 + 节点**仍计入执行记录** |
| `Command(resume="x")` | **被接受**（不抛错）+ 产生写入 **0** 次 + 产生跳转 **0** 次 |

---

## 8. **原子性**覆盖 `Command` 路径（SC-013）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_atomicity.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| `Command.update` 含未知 key | 出错后**全部**通道的值与**轮初**逐字相等 |
| 同上 | 通道的**写入版本未推进** |
| 同上 | 「一部分通道已更新、一部分没更新」的用例数 == **0** |
| 覆盖型冲突 / 归约器抛错 | **同款**处置 |

---

## 9. **纯净性**（零上游导入 / 零环境变量 / 零出站 / 无构建器依赖）（SC-014 / SC-016）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_purity.py -v
```

**期望**：

| 项 | 期望值 |
|---|---|
| `src/freegraph/**` 对 `langgraph` / `langchain*` / `langsmith` 的导入 | **0** 次 |
| 环境变量读取 | **0** 次 |
| 出站 | **0** 次 |
| `StateGraph` / `compile()` / `invoke()` 的出现 | **0** 次 |
| `SuperStepResult` 的字段数 | == **4**（**MUST NOT** 为记录跳转而扩字段 · 裁定 18） |
| `freegraph.runtime.__all__` 的符号数 | == **20**（**零新增** · 裁定 13） |
| L1 契约层 / 门面的符号面 | **18** / **7**（**一字不动**） |

⚠️ 「内核路径零上游导入 / 零环境变量 / 零出站」**必须在子进程中执行**
⇒ **复用** B4F1 已有的 `tests/runtime/conftest.py` 夹具 `run_in_subprocess`（session 级）
⇒ **既有 conftest 零改动**。

---

## 10. **确定性**与**调度状态不串扰**（SC-019）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_determinism.py -v
```

**期望**：

| 场景 | 期望值 |
|---|---|
| 同一份规格重复执行 **≥ 3** 次 | 合并后状态与执行序列**逐项相等**（差异 == **0**） |
| 两次**独立**运行（各自新建调度状态） | **互不影响**（比率 == **100%**） |
| 多轮入口**省略**调度状态 | 内部自洽（**不**继承此前任何调用的消费记录） |

---

## 11. **契约守卫**（解析 `contracts/command-contract.md` 的 I-1…I-14）

```bash
.venv/bin/python -m pytest tests/runtime/test_command_contract.py -v
```

**期望**：契约中的 **14** 条不变量**逐条**有对应的行为断言；契约里若出现与 spec 冲突的表述 ⇒
该守卫**失败**（提示「契约与 spec 冲突 ⇒ 以 spec 为准」）。

---

## 12. **人工验证**（原则 V · SC-017）· **偏离登记 + 发起者追认**（SC-018）

```bash
# 人工验证记录（五段式 + 来源覆盖表）落在：
#   harness/verification/B9F1/manual-verification.md
#
# ⚠️ 本 feature **不交付** `compile()` / `invoke()` ⇒ 宪法质量门禁第 3 / 4 / 5 项中
#    「target.py 原样可跑」「fake 模型跑通验收基线」「真实模型一轮」
#    在本 feature **物理不可达成** ⇒ 走宪法 v1.6.0 的通则（登记项 **R-1**）：
#    ① plan.md 的**偏离登记项** ② tasks.md 的**阻断合入的追认任务**
#    ③ 追认文字落在 manual-verification.md
```

**期望**：

| 项 | 期望值 |
|---|---|
| `harness/verification/B9F1/manual-verification.md` **存在**且**五段式**齐全 | 环境 / 步骤 / 实际输出 / 结论 / 遗留问题 |
| 来源覆盖表（判据 **A1–A3** + SC + FR） | 覆盖率 == **100%**（无来源项数 == **0**） |
| 未实跑的项 | MUST 显式记入「遗留问题」（MUST NOT 伪造输出） |
| 发起者追认文字 | 落在同一文件（**MUST NOT** 由实现者代签） |

---

## 13. 门禁与静态检查（**零新增门禁编号**）

```bash
# 既有门禁 **自动覆盖**本 feature 的新代码 ⇒ **零改动**：
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py --registry specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py
.venv/bin/python harness/scripts/gates/gate_G24_config_layer.py
.venv/bin/python harness/scripts/gates/gate_G26_network_static.py
```

**期望**：

| 项 | 期望值 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | L2 → L3 / L4 / L5 的边数 == **0**（`runtime/` 是**目录条目** ⇒ 新代码自动被覆盖） |
| **G30**（署名头） | 新源文件署名头覆盖率 == **100%** |
| **G24 / G26** | 零环境变量 / 零出站 |
| 门禁编号总数 | == **30** 且**连续无跳号**（**MUST NOT** 新增编号） |
| 层注册表 | **零改动**（`runtime/` 已是目录条目 ⇒ MUST NOT 单独立条目） |

---

## 14. 覆盖率取证（SC-016）

```bash
# 覆盖率工具**不进依赖声明** ⇒ 开发期临时安装 ⇒ 实测输出记入人工验证记录
uv pip install --python .venv coverage
.venv/bin/python -m coverage run --branch -m pytest tests/runtime -q
.venv/bin/python -m coverage report -m --include="src/freegraph/runtime/*"
```

**期望**：`src/freegraph/runtime/` 下**本 feature 新增 / 修改**的代码 **行 / 分支覆盖率 == 100%**
（⚠️ 「新增代码」的范围 = 本 feature 在 `src/freegraph/runtime/` 下**新增 / 修改**的文件
· **测试代码本身不计入**该判据）。

---

## 15. 与上游的对照（**证据** · 非门禁）

```bash
# 上游对照表在 contracts/upstream-parity.md（**证据** · MUST NOT 被测试解析）
# 复核上游行为（**可选** · 需要上游已安装 · 不进仓库依赖）：
cd /tmp/opencode && python3.12 lg_b9f1_probe.py
```

**期望**：输出与 [contracts/upstream-parity.md](./contracts/upstream-parity.md) **§3 的 8 组实测基线逐字一致**
⇒ 确认 freegraph 的对齐口径**未漂移**。

⚠️ 本闸口**不是门禁**（**零新增门禁编号**）⇒ 上游未安装时**跳过即可**，**不判失败**。
