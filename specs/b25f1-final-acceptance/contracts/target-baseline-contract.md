# Contract: `target.py` 只读基准（双重基线）

**Feature**: B25F1 · **Date**: 2026-11-25
**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)

> 锁定 FR-011 / A5：`harness/demo/target.py` MUST 零改动。
> 判定 = **内容真值（SHA-256）** + **历史真值（基线 ref diff）**。

---

## 1. 内容真值

**文件**：`tests/runtime/data/b25f1_target_py.sha256`

**格式**（单行）：

```text
<64 位小写 hex>  harness/demo/target.py
```

**读取规则**：

- 测试读取该文件，取第一个字段作为期望 SHA-256；
- 用 `hashlib.sha256(Path("harness/demo/target.py").read_bytes()).hexdigest()` 比对；
- 大小写归一为小写；分隔符允许两个空格或一个空格（兼容 `sha256sum` 输出）。

**失败语义**：

- 哈希不匹配 ⇒ **失败**（即使语义等价，格式化 / 换行 / 注释改动也算）。
- 哈希文件缺失 / 格式非法 ⇒ **失败**（不得静默跳过）。

---

## 2. 历史真值

**命令**：

```bash
git diff --exit-code "${B25F1_BASELINE_REF:-origin/main}" -- harness/demo/target.py
```

**基线 ref 解析**：

1. 若环境变量 `B25F1_BASELINE_REF` 非空 ⇒ 使用它；
2. 否则依次尝试 `origin/main`、`main`；
3. 都不可用 ⇒ `ref_status = "unavailable"`。

**失败语义**：

| 情形 | 判定 |
|---|---|
| `git diff` 退出码 0 | 历史真值通过 |
| `git diff` 退出码 1（有差异） | **失败** |
| 不在 git 仓库 / `git` 不可用 | `ref_status = "not_git"` ⇒ **环境偏离** |
| 基线 ref 不存在 | `ref_status = "unavailable"` ⇒ **环境偏离** |

**MUST NOT**：

- 只依赖 `git diff HEAD`（无法发现已提交篡改）；
- 在基线 ref 不可用时把「无法比较」当成「通过」；
- 静默 `skip` 而不记录原因。

---

## 3. 双重判定

| SHA-256 | 基线 ref diff | 结果 |
|---|---|---|
| 一致 | 为空 | **PASS** |
| 一致 | 不可用 | **环境偏离**（记录原因；SHA 仍为 PASS） |
| 不一致 | 任意 | **FAIL** |
| 任意 | 非空 | **FAIL** |

---

## 4. CI 接线

`.github/workflows/ci.yml` 的 `actions/checkout@v7` MUST 设：

```yaml
with:
  fetch-depth: 0
```

理由：默认浅克隆可能没有 `origin/main`，基线 ref 不可用。`fetch-depth: 0` 不改变 job 名，
不新增门禁编号。

---

## 5. 测试入口

| 测试 | 覆盖 |
|---|---|
| `tests/runtime/test_b25f1_target_guard.py::test_target_py_matches_recorded_sha256` | 内容真值 |
| `tests/runtime/test_b25f1_target_guard.py::test_target_py_matches_baseline_ref` | 历史真值（不可用 ⇒ skip + 理由） |
| `harness/verification/B25F1/acceptance.py` 的 `A5` | 双重判定 + 环境偏离记录 |

---

## 6. 失败示例

```text
[FAIL] A5 target.py SHA-256 不一致
  期望：<hex>
  实际：<hex>
  修复：恢复 harness/demo/target.py（只读基准，MUST NOT 修改）
```

```text
[ENV]  A5 基线 ref 不可用（origin/main 不存在；浅克隆？）
  已完成：SHA-256 一致
  未完成：历史 ref diff
  处置：登记环境偏离；CI 需 fetch-depth: 0
```
