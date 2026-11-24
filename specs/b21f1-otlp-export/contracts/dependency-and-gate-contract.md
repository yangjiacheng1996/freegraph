# Contract: 依赖、许可证与门禁

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> 本契约锁定 `[otlp]` 的精确依赖闭包、版本 / 许可证证据、`pyproject` / `extras-v2`
> 形态、G3 / G21 / G23 / G26 / B19F1 import 门禁变更、CI 安装范围、`THIRD_PARTY_NOTICES`
> 与治理追认。**不放宽**任何既有白名单 / 红线。

---

## 1. Extra 声明

```toml
[project.optional-dependencies]
otlp = [
  "opentelemetry-api>=1.20",
  "opentelemetry-sdk>=1.20",
  "opentelemetry-exporter-otlp-proto-grpc>=1.20",
]
```

**MUST NOT 声明**：

- `opentelemetry-exporter-otlp`（元包）
- `opentelemetry-exporter-otlp-proto-http`
- `requests`
- `certifi`

**基础安装**：`dependencies = []` **零变化**；`[otlp]` 默认不安装。

---

## 2. 精确闭包（实测 · as-of 2026-11-24）

| 包 | 版本 | 许可证证据 | 备注 |
|---|---|---|---|
| `opentelemetry-api` | 1.45.2 | `License-Expression: Apache-2.0` | 直接声明 |
| `opentelemetry-sdk` | 1.45.2 | `License-Expression: Apache-2.0` | 直接声明 |
| `opentelemetry-semantic-conventions` | 0.66b2 | `License-Expression: Apache-2.0` | sdk 依赖 |
| `opentelemetry-exporter-otlp-proto-grpc` | 1.45.2 | `License-Expression: Apache-2.0` | 直接声明 |
| `opentelemetry-exporter-otlp-proto-common` | 1.45.2 | `License-Expression: Apache-2.0` | grpc 依赖 |
| `opentelemetry-exporter-otlp-common` | 0.66b2 | `License-Expression: Apache-2.0` | grpc 依赖 |
| `opentelemetry-proto` | 1.45.2 | `License-Expression: Apache-2.0` | grpc / proto-common 依赖 |
| `googleapis-common-protos` | 1.76.0 | `License-Expression: Apache-2.0` | grpc 依赖 |
| `grpcio` | 1.85.3 | `License-Expression: Apache-2.0` | grpc 依赖 |
| `protobuf` | 7.36.2 | `License: 3-Clause BSD License`（散文） | **具名归一 → `BSD-3-Clause`** |
| `typing-extensions` | 既有白名单 | `PSF-2.0` | api / sdk / grpc 依赖 |

**闭包断言**：无 `certifi` / `requests` / `charset-normalizer` / `idna` / `urllib3` /
`langchain*` / `langsmith` / `langgraph*` / `deepagents` / provider 包。

> **版本口径**：上表是 **as-of 证据**，不是硬钉版本；`pyproject` 用 `>=1.20`。
> 实现 / CI MUST 记录实际安装版本；若 `protobuf` 元数据从散文改为
> `License-Expression: BSD-3-Clause`，可移除归一通道（更简），但 MUST 先实测。

---

## 3. G3 / G21 白名单

### 3.1 G3 `CONSTITUTION_DEPENDENCY_WHITELIST`

**只增** 7 名（12 → 19）：

```
opentelemetry-exporter-otlp-proto-grpc
opentelemetry-exporter-otlp-proto-common
opentelemetry-exporter-otlp-common
opentelemetry-proto
googleapis-common-protos
grpcio
protobuf
```

既有 12 名逐字保留：`annotated-types` · `greenlet` · `opentelemetry-api` ·
`opentelemetry-sdk` · `opentelemetry-semantic-conventions` · `ormsgpack` · `playwright` ·
`pydantic` · `pydantic-core` · `pyee` · `typing-extensions` · `typing-inspection`。

### 3.2 `extras-v2.toml`

在 `[project.optional-dependencies]` 增加 `otlp`；在 `closed_closure` 增加上述 7 名 +
既有 12 名。**MUST NOT** 删除既有条目。

> **注意**：`extras-v2.toml` 仍是 G21 / G23 的**预验证取证清单**；其中 `otlp` 是
> **v1.0 的具名例外**（宪法 v1.17.0），不是「第五个 v2.0 extra」。文件注释 MUST
> 写明这一点，避免把 `[otlp]` 误当成 v2.0 才可用的 extra。

### 3.3 G21 黑名单

`[otlp]` 闭包 MUST NOT 含 `langsmith` / `langchain*` / `langgraph*` / `deepagents` /
provider 包。基础安装闭包仍为空集。

---

## 4. G23 许可证门禁

### 4.1 既有规则（不变）

- 白名单 = {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}，**逐叶子精确 id**。
- 禁用：Elastic-2.0 / AGPL / SSPL / BUSL / GPL-2 / GPL-3 / MPL-2.0 / LGPL。
- 取不到证据 ⇒ 失败；**MUST NOT** skip。
- **MUST NOT** 引入通用等价标识符对照表 / 家族判定 / 豁免入口。

### 4.2 唯一新增具名归一（本 feature）

```python
# harness/scripts/gates/_gatekit.py
SPDX_PROSE_NORMALIZATION = {
    "protobuf": {"3-Clause BSD License": "BSD-3-Clause"},
}
```

- **仅** `protobuf`；**仅** 精确字符串 `3-Clause BSD License`。
- 依据：`protobuf 7.36.2` 的 `dist-info/licenses/LICENSE` 是标准 BSD-3-Clause。
- **不是**通用对照表；**不放宽**白名单；**不**接受其它散文标识。
- 若 `License-Expression: BSD-3-Clause` 可用 ⇒ 优先直接使用，归一不触发。

**Governance**：这是对 B3F1 裁定 18「MUST NOT 引入等价标识符对照表」的**唯一具名例外**；
MUST 更新 `architecture-gates.md` / `gate_G23_licenses.py` docstring，并经发起者书面追认。
未追认 ⇒ **STOP**；不得改走自研编码 / 放宽白名单。

---

## 5. G26 网络静态扫描

### 5.1 网络客户端清单（更严）

将 `grpc` 加入 `_gatekit.NETWORK_CLIENTS` 扫描清单；`_otlp_transport.py` 是唯一合法
使用方。

### 5.2 具名例外（只增）

```python
G26_EXCEPTED_MODULES = (
    "freegraph.observability._otlp_transport",
)
```

- 扫描域 `src/freegraph/**` **不变**；MUST NOT 放宽扫描域。
- 默认路径（未构造 `OtlpExporter`）仍零出站。
- 例外只覆盖**用户显式启用**的 OTLP 传输模块。

---

## 6. B19F1 import / egress 门禁变更

### 6.1 现状

- `tests/contracts/test_b19f1_gates.py` 的 `forbidden_roots` 含 `opentelemetry`；
- `tests/contracts/test_architecture.py::test_l5_observability_imports_only_stdlib_and_l1`
  只允许标准库 + L1；
- `test_b18f1_modules_have_no_forbidden_third_party_imports` 扫描 `runtime` / `observability`；
- `test_b18f1_modules_have_no_env_or_egress` 扫描 env / egress。

### 6.2 变更（具名例外 + 只增）

| 门禁 | 变更 |
|---|---|
| `test_b19f1_gates::test_new_modules_have_no_forbidden_imports_or_env_reads` | 只允许 `_otlp_mapping.py` / `_otlp_transport.py` / `_otlp_exporter.py` import `opentelemetry` / `grpc`；其它 L5 模块禁令不变；仍断言无 `environ` / `getenv` |
| `test_b19f1_gates::test_no_network_client_is_used_by_new_modules` | 只允许 `_otlp_transport.py` 使用 `grpc`；其它模块仍禁 `socket` / `requests` / `httpx` / `urllib` |
| `test_architecture::test_l5_observability_imports_only_stdlib_and_l1` | 具名例外：3 个 OTLP 模块允许 `opentelemetry` / `grpc`；仍禁 L2/L3/L4 |
| `test_architecture::test_b18f1_modules_have_no_forbidden_third_party_imports` | 同上；`langchain*` / `langsmith` / `langgraph*` 仍零 |
| `test_architecture::test_b18f1_modules_have_no_env_or_egress` | 具名例外只给 `_otlp_transport.py`；默认路径仍零出站 |
| `test_b19f1_lazy` | 新增 `OtlpExporter` 在 `observability.__all__`；子进程断言 `import observability` 后 `opentelemetry` / `grpc` 不在 `sys.modules` |

**判据零放宽**：例外是**具名的、最小范围的**；其它模块的禁令与默认路径的零出站断言
**一字不改**。

---

## 7. 宪法 v1.17.0 具名例外

| 项 | 内容 |
|---|---|
| 被破冻结面 | v1.0 的 `pyproject.toml` MUST NOT 含 `[project.optional-dependencies]` |
| 例外 | **仅** `[otlp]` 进入 v1.0 发行元数据；其它四个 extra 仍归 v2.0 |
| 基础安装 | `dependencies = []` **不变**；不装 `[otlp]` 时零第三方依赖 |
| 宪法修订 | **v1.17.0（2026-11-24 · MINOR）**：唯一具名例外；条件见宪法正文 |
| 追认 | 发起者 2026-11-24 选择 A（允许窄例外）；正式文字 + 确认人 + 日期落 `harness/verification/B21F1/manual-verification.md` |

---

## 8. CI 安装范围

`.github/workflows/ci.yml` 第 5.5 步（extras 预验证；含 v1.0 `[otlp]` 具名例外）MUST 增加：

```text
opentelemetry-exporter-otlp-proto-grpc>=1.20
```

或直接安装 `.[otlp]`。**全部 7 个作业**都必须安装，理由：

- G21 的闭包递归需要 `[otlp]` 的传递依赖已安装；
- G23 的许可证证据需要 `protobuf` / `grpcio` 等 dist-info 可见；
- 否则门禁要么红、要么退化为空门禁（违宪）。

**测试标记**：

- 桩导出器 / 映射 / 契约测试：全平台（`[otlp]` 已装）；
- 最小 gRPC 接收端：`@pytest.mark.linux_only` + `@pytest.mark.full_install`；
- 默认关闭 / 零 env / 零出站：子进程，全平台。

**pyproject markers**：`full_install` 描述由「四个 extras」改为「全部 extras（含 `otlp`）」；
非 Linux 作业的 `-m "not linux_only and not full_install"` 不变（gRPC 接收端只在 Linux 跑）。

---

## 9. `THIRD_PARTY_NOTICES`

新增 `[otlp]` 条目（与既有 `[otel]` 分开）：

```
[otlp]（OTLP gRPC 导出 · 默认关闭）:
opentelemetry-api (Apache-2.0)
opentelemetry-sdk (Apache-2.0)
opentelemetry-semantic-conventions (Apache-2.0)
opentelemetry-exporter-otlp-proto-grpc (Apache-2.0)
opentelemetry-exporter-otlp-proto-common (Apache-2.0)
opentelemetry-exporter-otlp-common (Apache-2.0)
opentelemetry-proto (Apache-2.0)
googleapis-common-protos (Apache-2.0)
grpcio (Apache-2.0)
protobuf (BSD-3-Clause; metadata prose "3-Clause BSD License" normalized)
typing-extensions (PSF-2.0)
```

**MUST NOT** 登记 `opentelemetry-exporter-otlp` 元包 / HTTP exporter / `requests` /
`certifi`；HTTP exporter 是用户在示例侧自装的依赖。

---

## 10. 门禁验收矩阵

| 门禁 | 期望 | 证据 |
|---|---|---|
| G3 基础安装闭包 | 空集 | `test_architecture.py` |
| G3 extras 闭包 | ⊆ 19 名白名单 | `test_architecture.py` |
| G21 依赖黑名单 | 无 `langsmith` / `langchain*` / `langgraph*` / `deepagents` | `gate_G21_dependencies.py` |
| G23 许可证 | 全白名单；`protobuf` 归一；无 MPL | `gate_G23_licenses.py` |
| G26 网络静态 | 默认路径零出站；`_otlp_transport.py` 具名例外 | `gate_G26_network_static.py` |
| B19F1 import / egress | 3 个 OTLP 模块具名例外；其它不变 | `test_b19f1_gates.py` / `test_architecture.py` |
| L5 惰性 | `import freegraph` 不加载 L5；`import observability` 不加载 OTel / grpc | `test_b19f1_lazy.py` |
| 公开面 | `observability.__all__` 只增 `OtlpExporter` | `test_api_snapshot.py` |
| 发行元数据 | `[otlp]` 存在；基础 `dependencies=[]` | `pyproject.toml` / 依赖测试 |

---

## 11. 不变量

1. 基础安装闭包 **仍为空集**。
2. `[otlp]` 闭包 **逐包白名单**；无 `certifi` / MPL。
3. `protobuf` 归一 **仅此一包 / 仅此一字符串**。
4. 默认路径 **零出站 / 零 env / 零 OTel import**。
5. `import freegraph` / `import freegraph.observability` **不加载 OTel / grpc**。
6. 门禁例外 **具名、最小、可审计**；MUST NOT 出现通用豁免入口。
7. v1.17.0 具名例外 **仅 `[otlp]`**；其它四个 extra 仍归 v2.0。
