# Contract: `COMPAT.md`（唯一权威 API 兼容矩阵）

**Feature**: B24F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> 本契约冻结 `COMPAT.md` 的**结构、行格式、覆盖范围与证据规则**。
> G8 / G19 / G29 的取行与校验以本契约为准；README **不得**维护第二份完整矩阵。

---

## 1. 文件位置与角色

| 项 | 值 |
|---|---|
| 路径 | 仓库根 `COMPAT.md` |
| 角色 | **唯一权威**的逐符号 / 逐项兼容矩阵 |
| 发行包 | **MUST NOT** 进入 wheel / sdist（FR-002） |
| 维护 | 活文档：每个扩展公开面 / 兼容面的 feature MUST 更新 |

---

## 2. 章节结构（固定顺序）

```text
# API 兼容矩阵
## API 兼容矩阵            ← 机读段（G8 / G19 / G29 只读这一段；affiliation 声明在段内）
> 兼容意图为互操作，不构成 affiliation ...
## 18 项覆盖表             ← Q3 §3.4（target.py 的 18 个 API 元素）
## 下游承接行              ← H-1…H-9 的跨 feature 新增面
## 证据与来源              ← Q3 裁定 / 上游 路径:行号 / feature 实测
## 维护规则                ← 更新义务与门禁引用
```

- **机读段**的标题 MUST 逐字为 `## API 兼容矩阵`（G8 / G19 / G29 的正则依赖）。
- **affiliation 声明 MUST 位于机读段内**（G8 / G29 只在段内查找该字样）；段外可另留一份，二者不互斥。
- 18 项表 / 下游段 / 证据段 MUST 为**独立 `##` 章节**——不得混入机读段
  （否则 G19 的「符号集合恰为两层」判据会失败）。

---

## 3. 机读段（`## API 兼容矩阵`）

### 3.1 表头与列

```markdown
| freegraph 符号 | 对应上游符号 | 等价程度 | 差异说明 |
|---|---|---|---|
| `Command` | `langgraph.types.Command` | 部分等价 | ... |
```

- 恰 **4 列**；首列 MUST 是单个反引号标识符 `` `Symbol` ``。
- `等价程度` ∈ **{行为等价, 部分等价, 不支持}**。

### 3.2 符号集合

- MUST **恰为**：契约层公开符号清单 ∪ 门面层公开符号清单。
  - 契约层清单：`specs/b2f1-contracts-protocols/contracts/public-api.md`
  - 门面层清单：`specs/b2f2-public-api-facade/contracts/facade-api.md`
- **符号数以 manifest 驱动、不硬编码**（当前：契约层 22 · 门面层 8 · 合计 27）；
  README / `COMPAT.md` 的「公开面」说明 MUST NOT 沿用旧「18/7」「20/7」「20/8」计数。
- MUST NOT 出现清单外符号、MUST NOT 重复。
- 下游承接符号（`MemorySaver` 等）**不进**本段（见 §5）。

### 3.3 关键行（冻结）

| 符号 | 第三列 | 差异说明必须含 |
|---|---|---|
| `Command` | **部分等价** | `goto` 缺省 `()` vs `None` = **DIFF（Y-01 · 成功路径可观察差异 · 不得写成「更严」）** · 非法目标 / 非 dict `update` 的显式失败 = **STRICTER（X-06 · B9F1 X-1 / X-4）** · X-2 / X-3 异常类型差异（B9F1 编号） · 纠正 P3/`99d43aa` 漂移的来源注记（B22F1 仅措辞） |
| `NodeFunc` | **不支持** | 契约 C5 / C6；**无上游同名协议**；返回形态已冻结（含命令列表 / `Send`） |
| `Graph` | **部分等价** | `draw_mermaid()` 本地；`draw_mermaid_png()` v1 占位 PNG；**v2 `[png]` 真实渲染升级路径**（B23F1） |
| `StateGraph` | **行为等价** | **含 `interrupt_before` / `interrupt_after` / `recursion_limit` 的 dict 载体**（B13F1 · H-4） |
| `Send` | **部分等价** | 形状等价；**freegraph 侧不可变（上游可变）**；**fan-out 运行期语义已落地**（B11F1 · H-3） |
| `CompiledGraph` | **部分等价** | `invoke` / `stream` / `get_state` / `get_state_history` / `update_state` 已交付；**`get_state` 无快照返回 `None` vs 上游空 `StateSnapshot` = DIFF（Y-02 · B15F1 X-01）**；`update_state` 无 `task_id` / 时间旅行线性重放属 **v1 能力边界**（非「更严」· B16F1） |
| `Checkpointer` | **行为等价** | 八方法对齐；`MemorySaver` 由 B14F1 落地 |
| `Store` | **行为等价** | **机读行逐字保持既有**；该逐字不变由 `tests/contracts/test_b24f1_compat.py` 对照 baseline（`HEAD:COMPAT.md` 优先、`HEAD:README.md` 回退）**专用断言**核验——`Store` 在既有白名单内，G19 只保证等价程度不变差、**不保证**差异说明逐字不变；「协议等价 · v1 无实现 · `batch` 挂起 v2」的澄清写在本文件 **`## 证据与来源`**，**MUST NOT** 改动机读行 |

### 3.4 affiliation

机读段 MUST 含字样：「**兼容意图为互操作，不构成 affiliation**」。

---

## 4. 18 项覆盖表（`## 18 项覆盖表`）

- 行：**18 行**，`#` 为 1–18，顺序与 `harness/reports/Q3-LangGraph的开源边界.md` §3.4 一致。
- 列：`# | target.py API 元素 | 上游是否直接提供 | freegraph 处置 | 等价程度 | 证据`。
- 判据：
  - `#1–#7`：同名同签名（行为等价）；
  - `#8–#12`：行为等价（归约器 / 稀疏状态 / 合并 / 鸭子类型）；
  - `#13`：**部分等价**（v1 占位 PNG；v2 `[png]` 真实渲染）；
  - `#14–#18`：等价程度 = **行为等价**；在「freegraph 处置」列注明「原样承载 / 脚本自身 / freechain / 不属范围」；
  - **`#4`**：处置列 MUST 含「**多源汇合边支持（H-1）**」，证据列 MUST 引 **B7F4 D-6**。
- `证据` MUST 指向 Q3 §3.4 的 # 或对应 feature。

---

## 5. 下游承接行（`## 下游承接行`）

| 行 | 等价程度 | 证据 / 来源 |
|---|---|---|
| 多源汇合边 `add_edge([a, b], c)` | 行为等价 | B7F4 D-6 · `langgraph/graph/state.py:928` |
| `MemorySaver` | 行为等价 | B14F1 D-07 |
| `InMemorySaver` | 行为等价（与 `MemorySaver` **同一对象 / 别名**） | B14F1 D-07 |
| `CheckpointTuple` | 行为等价（**恰三公开字段**） | B14F1 D-07 |
| `SqliteSaver` | 部分等价（MIT 改编；`json` 序列化差异 · X-07） | B15F1 D-04 |
| `CompiledGraph.get_state` | **部分等价**（**Y-02**：无快照返回 `None` vs 上游空 `StateSnapshot` · B15F1 P-02 / X-01） | B15F1 D-04 |
| `CompiledGraph.get_state_history` | **行为等价**（排序 / `filter` / `before` / `limit` 对齐上游 · P-04 / P-05，注明 B14F1 冻结差异） | B15F1 D-04 |
| `CompiledGraph.update_state` | 部分等价（返回 `RunConfig` · `as_node` · **无 `task_id`**） | B16F1 D-01 |
| 时间旅行重放 / 分叉 | 部分等价（`invoke(None, snapshot.config)` + `update_state` + `Command(resume)`；v1 线性） | B16F1 D-01 |
| `OtlpExporter` | 不支持（无上游对应 / 自由设计；Upstream Parity 关系 = DIFF） | B21F1 D-1 |

- 本段行**不参与**机读段的符号集合判据；由 `tests/contracts/test_b24f1_compat.py` 逐项核验。

---

## 6. 证据与维护

- 每行 MUST 有来源：Q3 §3.4 的 # / 上游 `路径:行号` / 对应 feature 的 spec 或测试。
- MUST NOT 输出无依据的兼容性断言。
- **版本口径**：既有行保留其原先引用的上游版本（如 `StateDict` 的 `1.2.19`）；**新增 / 复核行**与
  **差分测试**统一以 `langgraph 1.2.11` 为准；每行的 `路径:行号` MUST 与其声明版本一致
  （MUST NOT 为统一版本号而改动既有行）。
- **`Store` 的澄清**（「协议等价 · v1 无实现 · `batch` 挂起 v2」）MUST 写在本章节，
  **MUST NOT** 改动 `## API 兼容矩阵` 机读段里的既有行；该逐字不变由
  `tests/contracts/test_b24f1_compat.py` 对照 baseline 的**专用断言**核验（`Store` 在既有白名单内，
  G19 只保证等价程度不变差、不保证差异说明逐字不变）。
- 维护触发：新增公开符号 / 新增兼容面 / 上游版本变化 ⇒ 同一 feature 更新本文件。
- README MUST 链接本文件（**绝对 GitHub URL**）；README MUST NOT 复制完整矩阵。
- **既有行为面差异 Y-01**（`Command.goto` 缺省 `()` vs `None`）MUST 在 `Command` 行内单独标注为 **DIFF**，
  **MUST NOT** 并入 X-06 的 STRICTER；其处置（**具名承接 B25F1（M4）· 运行时对齐归 v2**）MUST 在人工记录遗留问题中登记。
- **既有行为面差异 Y-02 / Y-03**（`get_state` 无快照 `None` vs 上游空 `StateSnapshot` · B15F1 X-01；
  `Send` 侧不可变 vs 上游可变 · B11F1）MUST 标注为 **DIFF**：**Y-02  MUST 在
  `CompiledGraph` 机读行与下游 `CompiledGraph.get_state` 行双处出现**；**Y-03 MUST 在 `Send` 行出现**；
  `update_state` 无 `task_id` / 时间旅行线性重放属 **v1 能力边界**（非「更严」），MUST 在
  `CompiledGraph` 机读行、下游对应行与「证据与来源」注明。
  **Y-02 / Y-03 只在本 feature 登记；不写 B25F1 承接**（仅 **Y-01** 的文档记录由 B25F1 承接）。
- **H-4 / H-9 / H-3** 的事实性措辞更新 MUST 落 `StateGraph` / `Graph` / `Send` 行
  （`recursion_limit` / v2 `[png]` / 运行期语义）；这些行已在既有白名单（B12F1 / B22F1 / B23F1 / B11F1）内，
  允许更新差异说明，等价程度 MUST NOT 变差。

---

## 7. 门禁引用

| 门禁 | 读什么 | 断言 |
|---|---|---|
| G8 | 本文件机读段 | 契约层符号齐备 + 4 列 + 无重复 + affiliation |
| G19 | 本文件机读段 | 门面层符号齐备 + 整表恰为两层 + `Command` **定向例外**（仅 `行为等价 → 部分等价`；不整体移出单调检查，其它等级变化仍失败）+ 既有行未漂移（除白名单） |
| G29 `--check-compat` | 本文件机读段 + README 指针 | 覆盖两层 + `Command` = 部分等价 + README 无完整矩阵 |

> 不新增门禁编号；判据强度不降。
> **其他消费者**：`tests/runtime/test_parse_contract.py` 也必须读本文件机读段（T043）。
> **G19 baseline**：`HEAD:COMPAT.md` 优先 → `HEAD:README.md` 回退 → 都无则 skip。
