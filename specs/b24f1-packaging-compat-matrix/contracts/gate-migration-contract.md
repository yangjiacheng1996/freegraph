# Contract: G8 / G19 / G29 权威源迁移 + `Command` 例外

**Feature**: B24F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> **性质**：**破冻结面 · 已由发起者 2026-11-24 选项 A 追认**。
> 只更新**既有** G8 / G19 / G29，**不新增门禁编号**；判据强度 **不降**。

---

## 1. 迁移前 → 迁移后

| 门禁 | 迁移前 | 迁移后 |
|---|---|---|
| **G8** | 从 `README.md` 的「## API 兼容矩阵」取行，断言契约层符号齐备 | 从 **`COMPAT.md`** 机读段取行；新增「README 只能有指针、不得有完整矩阵」断言 |
| **G19** | 从 README 取行；门面层符号覆盖 + 整表恰为两层 + 禁止等价程度降级 | 从 **`COMPAT.md`** 机读段取行；新增 **B24F1 `Command` 定向例外**（仅 `行为等价 → 部分等价`，不整体移出单调检查）；其余判据不变 |
| **G29** `--check-compat` | `COMPAT.md` 存在 ⇒ 与 README 逐格比对 | `COMPAT.md` 存在 ⇒ 校验其覆盖两层清单 + `Command` = 部分等价 + README 指针；**仍复用** `_gatesupport` 取行 |

**共同实现**：取行与清单解析收敛到 `tests/facade/_gatesupport.py`（既有判据来源），
G8 / G19 / G29 **共用**，MUST NOT 各写一份。`tests/` 不是包（无 `tests/__init__.py`），
G8（`tests/contracts/`）MUST 采用与 G29 相同的 `sys.path` 注入方式复用该模块，
MUST NOT 复制一份取行实现。

---

## 2. G8 的新判据（`tests/contracts/test_architecture.py`）

保留（逐字或等价强度）：

1. `COMPAT.md` 存在，且含 `## API 兼容矩阵`；
2. 契约层符号在机读段**齐备**；
3. 每行**恰 4 列**（不得多列或少列）；
4. 无重复行；
5. 机读段含「不构成 affiliation」。

新增：

6. `README.md` 存在 `## API 兼容矩阵` 章节，但内容为**指针**（含 **绝对 GitHub URL**
   的 `COMPAT.md` 链接 / `COMPAT.md` 文件名），**不得**含完整符号表（机读取行数为 0）。
7. `THIRD_PARTY_NOTICES` 存在（既有判据保留）。

> **G8 取行 / affiliation 的迁移必须彻底**：`test_readme_has_compat_matrix_section` 改为
> 只验 README 指针；`test_compat_matrix_declares_no_affiliation` 改为读 **COMPAT**
> 机读段；`test_compat_matrix_rows_are_within_the_manifest` 等取行测试、**以及 `test_architecture.py`
> 内所有读取 README **矩阵行**的自检 / 反向用例**全部改读 COMPAT；
> **非矩阵** README 检查（如 `test_readme_contains_independence_statement`）保持不变。

**MUST NOT**：放宽「契约层齐备」「恰 4 列」「无重复」中任何一条。

---

## 3. G19 的新判据（`tests/facade/test_facade_gates.py`）

保留：

1. 门面清单（`facade-api.md` §0，**manifest 驱动、当前 8 个**）在机读段各恰一行；
2. 整表符号集合 == 契约层清单 ∪ 门面层清单；
3. 新增行等价程度与来源；
4. 白名单外既有契约层行「逐字未改」（baseline 取法见 §3.7：`HEAD:COMPAT.md` 优先、
   `HEAD:README.md` 回退；都无则 skip）。

新增 / 修改：

5. 取行源改为 `COMPAT.md`；
6. **B24F1 定向例外**：`MATRIX_ROWS_UPDATABLE_BY_B24F1 = frozenset({"Command"})`；
   对 `Command` 允许 **行为等价 → 部分等价** 的**纠漂移**（这是恢复 B9F1 定稿值，
   不是产品能力降级）。**`Command` MUST NOT 整体移出**「等价程度 MUST NOT 变差」的单调检查；
   实现 MUST 增加专用分支：仅当 `previous == 行为等价` 且 `current == 部分等价` 时放行，
   **任何其它等级变化（含 `部分等价 → 不支持`）MUST 失败**；
   **其它白名单行仍走原单调检查，MUST NOT 放宽为任意降级**；并 MUST 新增负向自检：
   把 `Send` 降级为「不支持」⇒ 门禁必须失败；把 `Command` 从「部分等价」降为「不支持」⇒ 也必须失败。
7. `README` 的完整矩阵移除后，`test_existing_contract_rows_are_unchanged` 的
   **current** 侧改为读 `COMPAT.md`，**baseline** 侧 MUST 按以下顺序取：
   ① `git show HEAD:COMPAT.md`（**存在且含机读段行** ⇒ 用它）；
   ② 否则 `git show HEAD:README.md`（迁移前旧矩阵）；
   ③ 两者都无矩阵行 ⇒ `pytest.skip`。
   **MUST NOT** 固定写死 `HEAD:README.md`：README 重写提交后该来源已无矩阵 ⇒ `previous` 为空
   ⇒ `assert previous` 会失败（不是 skip）⇒ CI 永久红，且门禁失去回归保护。
8. **G19 内所有读取 README 的自检 / 反向用例**（如 `test_selfcheck_detects_a_missing_row`）
   MUST 同批改为读 `COMPAT.md`。

**MUST NOT**：把例外扩大到 `Command` 之外的任何符号。

---

## 4. G29 `--check-compat` 的新判据

### 4.1 不存在 `COMPAT.md`

- 输出「**未落地**」并 **退出码 0**（与现状一致，MUST NOT 静默跳过）。

### 4.2 存在 `COMPAT.md`

校验以下全部成立，任一失败 ⇒ **退出码非 0** 并指名违规：

1. 机读段存在且可解析（4 列 / 首列反引号标识符）；
2. 符号集合 == 契约层清单 ∪ 门面层清单（复用 `_gatesupport` 的清单解析）；
3. `Command` 行第三列为 **部分等价**；
4. 机读段含「不构成 affiliation」；
5. `README.md`：
   - 含 `## API 兼容矩阵` 章节；
   - 章节内含 **绝对 GitHub URL** 的 `COMPAT.md` 链接（`https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`）；
   - 章节内**机读取行数 == 0**（不得有完整矩阵）。

### 4.3 与 G8 / G19 的分工

- G29 **MUST** 引用 `tests/facade/_gatesupport.py` 的取行 / 清单解析；
- G29 **MUST NOT** 重复实现矩阵取行；
- G29 不替代 G8 / G19 的 pytest 步骤（两者仍跑）。

---

## 5. 回溯修订与追认

| 项 | 落点 |
|---|---|
| 契约文本 | `specs/b2f1-contracts-protocols/contracts/architecture-gates.md` §G8 · `specs/b2f2-public-api-facade/contracts/architecture-gates.md` §G19 · `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 总览 / G29 |
| 门禁实现 | `tests/contracts/test_architecture.py` · `tests/facade/test_facade_gates.py` · `tests/facade/_gatesupport.py` · `harness/scripts/gates/gate_G29_contract_carrier.py` · `tests/runtime/test_parse_contract.py`（同批迁移） |
| spec 冻结面表 | `specs/b24f1-packaging-compat-matrix/spec.md` 的「破冻结面的回溯修订清单」**已回写**为 G8 / G19 / G29 三项 |
| 追认文字 | `harness/verification/B24F1/manual-verification.md`（2026-11-24 · 选项 A · 发起者） |

**追认口径**：用户于 2026-11-24 在 clarify 后明确选择 **A**（`COMPAT.md` 唯一权威；
README 只留能力表 + 链接；同步改写 G8 / G19 / G29）。本契约是该选择的落地形式。

---

## 6. 不变量

- 门禁编号 **零新增**（仍为 G8 / G19 / G29）。
- 判据 **不降**：覆盖面的「不多 / 不少」、4 列、无重复、affiliation、`Command` 纠偏均保留。
- **G19 的 `Command` 例外是单点定向例外**：仅 `Command` 可从 `行为等价` 降为 `部分等价`；
  `Command` **不整体移出**单调检查，其它任何等级变化（含 `部分等价 → 不支持`）仍失败；
  其它白名单行仍不可降级；负向自检证明 `Send` 降级与 `Command` 的其它降级都会失败。
- G21 / G23 / G26 / G30 与发布门禁的判据 **一字不动**。
- `harness/demo/target.py` **零改动**。

---

## 7. 其他 README 矩阵消费者（必须同批迁移）

`tests/runtime/test_parse_contract.py::test_compat_matrix_has_no_new_row_for_this_feature`
也直接读取 **README** 的 `## API 兼容矩阵` 章节，并要求符号集合 == 契约层 ∪ 门面层。
T004 把 README 改为指针（或 T033 重写 README）后，该测试**必红**（`names` 为空）。因此：

- 该测试 MUST 改为读取 **`COMPAT.md`** 的机读段（复用 `_gatesupport` / 同一 `sys.path` 注入）；
- **MUST 保留** exact two-layer symbol-set 断言（不得删除；G19 是同源判据，但本测试同时守护「零新增行」语义）；
- `tasks.md` 的 Phase 2 MUST 有对应任务（T043），且纳入原子提交。
