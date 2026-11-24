# Data Model: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本 feature **不引入运行时数据结构**。下列实体是**文档 / 构建产物 / 门禁结果**的数据模型，
> 用于把 spec 的实体与验收规则落成可判定的形状。

---

## 1. 实体总览

| 实体 | 载体 | 作用 |
|---|---|---|
| `DistributionArtifact` | wheel / sdist 文件 | 发行产物；被纯度门禁检查 |
| `PurityResult` | 脚本输出 / 退出码 | 一次产物检查的结论 |
| `NegativeCase` | 测试临时产物 | 证明门禁能拦住污染 |
| `CompatRow` | `COMPAT.md` | 兼容矩阵的一行 |
| `CoverageItem` | `COMPAT.md` 18 项表 | `target.py` 的一个 API 元素 |
| `DownstreamRow` | `COMPAT.md` 下游承接段 | 跨 feature 新增的兼容面 |
| `ThirdPartyEntry` | `THIRD_PARTY_NOTICES` | 第三方代码 / 依赖归属 |
| `CapabilityDisposition` | README 能力处置表 | 能力 → 做 / 不做（v2）/ 永不做 |
| `GateSource` | G8 / G19 / G29 取行源 | 机读矩阵的来源（`COMPAT.md`） |

---

## 2. `DistributionArtifact`（发行产物）

| 字段 | 类型 | 规则 |
|---|---|---|
| `kind` | `"wheel" \| "sdist"` | 由文件后缀判定（`.whl` / `.tar.gz`） |
| `path` | 文件路径 | MUST 位于 `dist/`（或负向用例的临时目录） |
| `members` | `list[str]` | wheel = zip 条目；sdist = tar 成员（去掉顶层目录名） |
| `metadata` | 映射 | wheel 的 `freegraph-*.dist-info/`；sdist 的 `PKG-INFO` / `pyproject.toml` |
| `requires_dist` | `list[str]` | wheel 元数据；基础为空；可选仅 `otlp` |
| `has_py_typed` | `bool` | wheel MUST 含 `freegraph/py.typed` |

**校验（来自 FR-001 / FR-002 / FR-009）**：

- wheel 成员只允许 `freegraph/` 前缀与 `freegraph-*.dist-info/` 前缀；
  任何其它 `freegraph-` 前缀文件（如 `freegraph-evil.txt`）⇒ **失败**（前缀本身不构成豁免）；
- sdist 成员只允许 `src/freegraph/` 前缀 + `{README.md, LICENSE, pyproject.toml, PKG-INFO}`；
- 两种产物 MUST NOT 含 `harness/` / `.specify/` / `.opencode/` / `.github/` / `specs/` /
  `tests/` / `test/` / `dist/` / `.venv/` / `node_modules/` / `__pycache__/` / `.gitignore`；
- wheel MUST 含 `freegraph/__init__.py` 与 `freegraph/py.typed`；
- sdist MUST 含 `src/freegraph/__init__.py` / `README.md` / `LICENSE` / `pyproject.toml` / `PKG-INFO`；
- `dist/` 内出现任何**归档类**非 `.whl` / `.tar.gz` 文件（`.zip` / `.tar` / `.tgz` / `.tar.bz2`）⇒ 失败；**`uv build` 自动生成的 `dist/.gitignore` 是构建工具标记，MUST 豁免**（不得静默忽略其它额外产物）；
- `requires-python` = `>=3.11`（无上限）；
- `COMPAT.md` / `THIRD_PARTY_NOTICES` **MUST NOT** 出现。

---

## 3. `PurityResult`（纯度结果）

| 字段 | 类型 | 规则 |
|---|---|---|
| `artifact` | `str` | 产物文件名 |
| `kind` | `"wheel" \| "sdist"` | — |
| `violations` | `list[str]` | 每条含具体路径 / 缺失文件 |
| `exit_code` | `int` | `0` = 干净 · `1` = 有违规 · `2` = 目录 / 产物不存在 |

**校验**：

- 干净产物 ⇒ `violations == []` 且 `exit_code == 0`；
- 任一仓库内容 ⇒ `exit_code == 1` 且至少一条违规指出路径；
- `dist/` 不存在或为空 ⇒ `exit_code == 2`。

---

## 4. `NegativeCase`（负向用例）

| 字段 | 类型 | 规则 |
|---|---|---|
| `base_artifact` | 临时 wheel / sdist | 在 `tmp_path` 合成，含允许内容 |
| `injected_member` | `str` | 如 `harness/report.md` / `specs/x/spec.md` |
| `expected_exit` | `int` | `1` |
| `expected_message` | `str` | 含「拒绝发布」或违规路径 |

**校验**：MUST 在临时目录执行，MUST NOT 触碰仓库根 `dist/`。

---

## 5. `CompatRow`（机读矩阵行）

| 字段 | 类型 | 规则 |
|---|---|---|
| `symbol` | `str` | 契约层 / 门面层的公开符号（首列必须是 `` `标识符` ``） |
| `upstream_symbol` | `str` | 对应上游符号，或「无上游对应（自由设计）」 |
| `degree` | `"行为等价" \| "部分等价" \| "不支持"` | 三档之一 |
| `difference` | `str` | 差异说明 + 证据（上游 `路径:行号` / Q3 裁定 / feature 实测） |
| `section` | `"machine"` | 必须位于 `## API 兼容矩阵` 段 |

**校验**：

- 机读段符号集合 **== 契约层清单 ∪ 门面层清单 = 27**（契约层 22 ∪ 门面层 8；`Command` / `RunConfig` / `Send` 去重；与 G8 / G19 同源）；
- 每行 **恰 4 列**（符号 / 上游 / 等价程度 / 差异说明；不得多列或少列）；
- 无重复行；
- `Command` 的 `degree` **必须**为 `部分等价`；其 `difference` MUST 分开标注：
  `goto` 缺省 = **DIFF（Y-01）**、失败信号 = **STRICTER（X-06）**；
- `Send` 的 `difference` MUST 含「不可变（上游可变）」= **DIFF（Y-03）**；`NodeFunc` MUST 含「无上游同名协议」；
  `CompiledGraph` 机读行的 `difference` MUST 含 **Y-02**（无快照 `None` vs 上游空 `StateSnapshot`）
  与 `update_state` / 时间旅行 = **v1 能力边界**（非「更严」）；下游 `CompiledGraph.get_state` 行亦 MUST 含 **Y-02**；
- 段内含「不构成 affiliation」。

---

## 6. `CoverageItem`（18 项覆盖行）

| 字段 | 类型 | 规则 |
|---|---|---|
| `index` | `int` | 1–18（Q3 §3.4 的 #） |
| `element` | `str` | `target.py` 的 API 元素 |
| `upstream_provides` | `bool` | 上游是否直接提供 |
| `disposition` | `str` | freegraph 处置 |
| `degree` | `"行为等价" \| "部分等价" \| "不支持"` | 三档 |
| `evidence` | `str` | Q3 §3.4 的 # / 路径:行号 |

**校验**：18 行齐全、编号连续、每行有 degree 与 evidence；`#13`（PNG）= `部分等价`；
`#14–#18` = `行为等价`；在「处置」列注明「原样承载 / 脚本自身 / freechain / 不属范围」；
**`#4` 处置列 MUST 含「多源汇合边支持（H-1）」，证据列 MUST 引 B7F4 D-6**。

---

## 7. `DownstreamRow`（下游承接行）

| 字段 | 类型 | 规则 |
|---|---|---|
| `symbol` | `str` | 多源汇合边 / `MemorySaver` / `InMemorySaver` / `CheckpointTuple` / `SqliteSaver` / `CompiledGraph.get_state` / `CompiledGraph.get_state_history` / `CompiledGraph.update_state` / 时间旅行重放-分叉 / `OtlpExporter`（下游行名统一写作 `CompiledGraph.<method>`） |
| `degree` | 三档 | 按 §7 的逐项钉死值（不得写「或」） |
| `difference` | `str` | 差异说明 |
| `source` | `str` | 承接 feature（B7F4 / B14F1 / B15F1 / B16F1 / B21F1） |

**校验（H-1…H-9）**：

- 多源汇合边 = 支持 / 行为等价；`MemorySaver` 与 `InMemorySaver` 是同一对象（别名）；
- `CheckpointTuple` 恰三公开字段；`SqliteSaver` 部分等价（`json` 序列化差异）；
- `CompiledGraph.get_state` = **部分等价**（行内 MUST 含 **Y-02**：无快照返回 `None` vs 上游空
  `StateSnapshot` · B15F1 P-02 / X-01）；`CompiledGraph.get_state_history` = **行为等价**
  （排序 / `filter` / `before` / `limit` 对齐上游 · P-04 / P-05，注明 B14F1 冻结差异）；
  `CompiledGraph.update_state` 部分等价（返回 `RunConfig` · `as_node` · 无 `task_id`）；
  时间旅行 = 部分等价（v1 线性重放 / 无 `task_id`）；
- `OtlpExporter` = 不支持（无上游对应 / 自由设计；Upstream Parity 关系 = DIFF）；「不支持」表示上游无对应物，不表示 freegraph 不提供该能力。

---

## 8. `ThirdPartyEntry`（归属条目）

| 字段 | 类型 | 规则 |
|---|---|---|
| `project` | `str` | 项目 / 包名 |
| `source` | `str` | 来源（路径 / 版本） |
| `license` | `str` | SPDX 或散文标识（`protobuf` 归一说明） |
| `introduction` | `str` | 复制 / 改编 / vendored / 依赖 |
| `modification` | `str` | 修改内容（若有） |
| `copyright_retention` | `str` | 原始版权声明保留位置 |

**校验**：

- §1 MUST 含 `langgraph-checkpoint-sqlite` 的 MIT 改编（LangChain, Inc. 版权）；
- §2 MUST 含 `[otlp]` 闭包逐包（含 `protobuf` 归一说明）；
- `langgraph==1.2.11`（differential）**不登记**（测试侧 · 不进发行包 · A-11）；
- 不得登记虚构依赖。

---

## 9. `CapabilityDisposition`（能力处置行）

> **口径（2026-11-24 拍板）**：README 表**逐字复刻**立项书 §3.2 的 **5 列 + 8 行**，
> 不压缩为 3 列。`as_of` 固定为 `2026-11-01`（与立项书一致；以官方定价页为准）。

| 字段 | 类型 | 规则 |
|---|---|---|
| `capability` | `str` | 能力名（立项书 §3.2） |
| `developer` | `str` | Developer 档位（`✅` / `❌` / `部分`） |
| `plus` | `str` | Plus 档位（`✅` / `❌` / `部分`） |
| `enterprise` | `str` | Enterprise 档位（`✅` / `❌` / `部分`） |
| `freegraph_disposition` | `"做" \| "不做（v2）" \| "永不做"` | freegraph v1 列 |
| `as_of` | `str` | `2026-11-01`（以官方定价页为准） |

**校验**：README 表头 MUST 为
`能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1`；数据行 MUST 为 **8 行**，
与立项书 §3.2 逐格一致（含 mermaid / trace / time-travel / IDE / Deployment / Fleet 等）；
不得遗漏「不做（v2）」与「永不做」；必须附 `as-of 2026-11-01`。

---

## 10. `GateSource`（门禁取行源）

| 字段 | 类型 | 规则 |
|---|---|---|
| `gate` | `"G8" \| "G19" \| "G29"` | 既有门禁编号（**零新增**） |
| `source_path` | `str` | `COMPAT.md` |
| `section` | `str` | `## API 兼容矩阵` |
| `expected_symbols` | `set[str]` | 契约层清单 ∪ 门面层清单（既有 manifest） |
| `readme_role` | `"pointer"` | README 只能有指针 + 能力表；不得有完整矩阵 |
| `baseline_source` | `str` | G19 的基线：`HEAD:COMPAT.md` 优先（**存在且有机读段行**）→ `HEAD:README.md` 回退 → 都无则 skip；**MUST NOT** 固定 `HEAD:README.md` |

**校验**：

- G8 / G19 的取行函数对 `COMPAT.md` 生效；对 README 的完整矩阵行为不再要求；
- G29 `--check-compat` 在 `COMPAT.md` 存在时验证：机读段覆盖两层清单 + `Command` = 部分等价
  + README 有**绝对 GitHub URL** 且无完整矩阵；不存在时仍报告「未落地」退出 0；
- 其他 README 矩阵消费者（`tests/runtime/test_parse_contract.py`）MUST 同批迁到 `COMPAT.md`；
- **MUST NOT** 新增门禁编号。

---

## 11. 关系图（文字）

```text
DistributionArtifact 1 ── * PurityResult
NegativeCase     * ── 1 PurityResult（期望失败）

CompatRow        * ── 1 COMPAT.md「机读段」
CoverageItem     * ── 1 COMPAT.md「18 项表」
DownstreamRow    * ── 1 COMPAT.md「下游承接段」
ThirdPartyEntry  * ── 1 THIRD_PARTY_NOTICES
CapabilityDisposition * ── 1 README「能力处置表」

GateSource(G8/G19/G29) ── 读取 ──> COMPAT.md「机读段」
GateSource(G29)        ── 校验 ──> README 指针 + COMPAT.md 覆盖
```

---

## 12. 状态与生命周期

| 对象 | 状态 | 迁移 |
|---|---|---|
| `COMPAT.md` | 不存在 → 已落地 | 本 feature 首次落库**独立文件** `COMPAT.md`（兼容矩阵本身早已在 README 落库 · B2F2）；G29 从「未落地」转为「严格校验」 |
| `Command` 行 | 行为等价（P3/`99d43aa` 漂移；B22F1 仅措辞） | 本 feature → 部分等价（纠漂移；`goto` 缺省 = DIFF（Y-01）、失败信号 = STRICTER（X-06）） |
| **Y-01**（既有 `goto` 缺省差异） | `Command.goto is None`（B1F1 冻结） | 本 feature **只登记**；**具名承接 B25F1（M4）**，运行时对齐归 v2 |
| **Y-02**（既有 `get_state` 无快照差异） | `get_state` 返回 `None`（B15F1 X-01） | 本 feature **只登记**；`COMPAT.md` 的 `get_state` 行注明 DIFF；运行时对齐归 v2 |
| **Y-03**（既有 `Send` 不可变差异） | `Send` 侧不可变（B11F1） | 本 feature **只登记**；`COMPAT.md` 的 `Send` 行注明 DIFF；运行时对齐归 v2 |
| `update_state` / 时间旅行 | v1 无 `task_id` / 线性重放 | 本 feature 只登记为 **v1 能力边界**（非「更严」）；矩阵标「部分等价」 |
| 纯度门禁 | 已存在 | 本 feature 补负向 / 顺序断言，判据不变 |
| README 矩阵 | 完整矩阵 | 本 feature → 能力表 + 指针；完整矩阵迁入 `COMPAT.md` |
| 最小差分组 | 未落地 | 本 feature 落 `tests/differential/test_b24f1_matrix_parity.py`（**B24F1-D-01…D-03**）：只断言既有差异（Y-01 / Y-02 / Y-03），**不改运行时**；上游缺席 skip |

**不变量**：发行产物纯度判据不变；`src/freegraph/` 零改动；门禁编号零新增；
`[otlp]` 唯一 extra 与基础零依赖不变。
