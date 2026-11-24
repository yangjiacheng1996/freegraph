# Quickstart: B21F1 · OTLP 导出插件 + 后端对接

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本文件是**端到端验证指南**，不是实现代码。命令以仓库根为工作目录；Windows 请把
> `source .venv/bin/activate` 换成 `.venv\Scripts\activate`，路径分隔符按平台调整。

---

## 1. 前置条件

| 项 | 要求 |
|---|---|
| Python | ≥ 3.11 |
| freegraph | 本仓库可编辑安装 |
| `[otlp]` | `pip install -e ".[otlp]"` |
| HTTP 后端示例 | **用户侧**再装 `opentelemetry-exporter-otlp-proto-http>=1.20`（不进 freegraph 闭包） |
| 真实后端 | 可选：Phoenix / OpenLIT / Langfuse；至少一个用于人工冒烟 |
| 网络 | 基础路径零出站；只有显式构造 `OtlpExporter` 且传入端点时才出站 |

---

## 2. 安装与基线

```bash
# 1) 虚拟环境 + 基础安装（零第三方依赖）
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2) 开发 / 测试依赖
pip install -e ".[otlp]" pytest packaging

# 3) 基线（应全绿；B21F1 尚未实现时不含本 feature 新测试）
python -m pytest tests/ -q --tb=no
```

**预期**：基础安装后 `pip show freegraph` 的 `Requires` 为空；`import freegraph` 不加载
`opentelemetry`。

---

## 3. A1 · 可选 extra + 不自研 OTLP 编码

### 3.1 依赖声明核对

```bash
python - <<'PY'
import tomllib, pathlib
p = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
print(p.get("project", {}).get("dependencies", []))
print(p.get("project", {}).get("optional-dependencies", {}).get("otlp"))
PY
```

**预期**：

- `dependencies == []`
- `otlp` 恰为 `opentelemetry-api` / `opentelemetry-sdk` /
  `opentelemetry-exporter-otlp-proto-grpc`（版本下限 `>=1.20`）

### 3.2 许可证 / 闭包

```bash
python harness/scripts/gates/gate_G21_dependencies.py \
  --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
python harness/scripts/gates/gate_G23_licenses.py \
  --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
```

**预期**：G21 无黑名单；G23 全白名单；`protobuf` 经**仅此一包**的归一为
`BSD-3-Clause`；无 `certifi` / MPL-2.0。

### 3.3 无自研编码

```bash
python -m pytest tests/contracts/test_b21f1_gates.py -q
```

**预期**：AST / 静态扫描无 protobuf encoder / OTLP wire format；只有官方
`encode_spans` + `TraceServiceStub`。

---

## 4. A4 · 默认关闭 / 零出站（先做，避免误出站）

```bash
python -m pytest tests/observability/test_b21f1_default_off.py -q
```

**预期**：

- 基础安装 / 未传 `tracer`：`opentelemetry` / `grpc` 不在 `sys.modules`；
- 框架出站 == 0；
- 设置 `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_*` / `LANGSMITH_*` 不改变行为。

手动子进程核验：

```bash
python - <<'PY'
import subprocess, sys
code = """
import sys
import freegraph
assert not any(m.startswith('freegraph.') for m in sys.modules)
import freegraph.observability as obs
assert 'OtlpExporter' in obs.__all__
assert not any(m == 'opentelemetry' or m.startswith('opentelemetry.')
               for m in sys.modules), 'OTel imported at observability import'
assert 'grpc' not in sys.modules, 'grpc imported at observability import'
print('ok')
"""
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
print(r.stdout, r.stderr)
raise SystemExit(r.returncode)
PY
```

**预期**：`ok`；`OtlpExporter` 在 `observability.__all__`；无 OTel / grpc 加载。

---

## 5. A5 · 显式端点导出（桩接收端 / 最小 gRPC 接收端）

### 5.1 桩导出器（全平台，快速）

```bash
python -m pytest tests/observability/test_b21f1_mapping.py \
  tests/observability/test_b21f1_export.py -q
```

**预期**：

- 节点 / 模型 / 工具 span 的 name / ids / times / attributes / status / kind 正确；
- 同一 `run_id` 共享 `trace_id`；`thread_id` → `gen_ai.conversation.id`；
- `export_errors` / `last_error` / `on_error` / WARNING 四路可感知；
- 端点不可达时图成功完成。

### 5.2 最小 gRPC 接收端（Linux 全量 / 真实 wire）

```bash
python -m pytest tests/observability/test_b21f1_transport.py -q
```

**预期**：

- 本地 gRPC 接收端收到 `ExportTraceServiceRequest`；
- span 数 == 图产生的完整 span 数；
- name / 时间 / attributes / parent / trace_id 可校验；
- 图最终状态与不导出时逐字相等。

### 5.3 手动运行（最小示例）

```bash
python - <<'PY'
from typing import TypedDict
from freegraph.graph import END, START, StateGraph
from freegraph.observability import OtlpExporter

class S(TypedDict, total=False):
    x: int

exporter = OtlpExporter(endpoint="127.0.0.1:4317", insecure=True)
b = StateGraph(S)
b.add_node("a", lambda state: {"x": 1})
b.add_node("b", lambda state: {"x": state["x"] + 1})
b.add_edge(START, "a")
b.add_edge("a", "b")
b.add_edge("b", END)
app = b.compile(tracer=exporter)
print(app.invoke({"x": 0}))
print("export_errors =", exporter.export_errors)
print("last_error =", exporter.last_error)
PY
```

**预期**：图返回 `{"x": 2}`；若本地无接收端，`export_errors > 0`、`last_error` 非空，
但图**仍然成功**。

---

## 6. A5 / SC-003 · 失败不阻断

```bash
python -m pytest tests/observability/test_b21f1_export.py -q -k "failure or unreachable or on_error or base_exception"
```

**预期**：

- 端点不可达 / `exporter.export` 抛 `Exception` / `on_error` 抛 `Exception` ⇒ 图成功；
- `KeyboardInterrupt` / `SystemExit` ⇒ 不被吞；
- `export_errors` 增加；`last_error` 记录；WARNING 出现；
- **不重试**同一 span。

---

## 7. A2 / A3 · 三个后端示例

### 7.1 语法 / `--help`

```bash
python harness/examples/B21F1/phoenix.py --help
python harness/examples/B21F1/openlit.py --help
python harness/examples/B21F1/langfuse.py --help
```

**预期**：三个脚本都成功打印帮助；无默认端点；端点 / 认证从 CLI 读取。
`--help` **不需要**预先安装用户侧 HTTP exporter；`openlit.py` / `langfuse.py` 只在真正
执行导出时才惰性导入它（缺包时打印安装提示并以非零退出码结束）。

### 7.2 Phoenix（gRPC · 真实后端）

```bash
# 启动 Phoenix（按其文档；默认 gRPC 4317）
python harness/examples/B21F1/phoenix.py --endpoint 127.0.0.1:4317
```

**预期**：Phoenix UI 可查到本次运行的节点 / 模型 / 工具 span；`export_errors == 0`。

### 7.3 OpenLIT（HTTP · 用户自装 HTTP exporter）

```bash
pip install "opentelemetry-exporter-otlp-proto-http>=1.20"
python harness/examples/B21F1/openlit.py --endpoint http://127.0.0.1:4318/v1/traces
```

**预期**：OpenLIT 可查到 trace；README 已标注旧路径 `openlit.io/docs` 404、现行
`https://docs.openlit.io/latest/overview`、as-of 日期。

### 7.4 Langfuse（HTTP + Basic auth）

```bash
pip install "opentelemetry-exporter-otlp-proto-http>=1.20"
python harness/examples/B21F1/langfuse.py \
  --endpoint http://localhost:3000/api/public/otel/v1/traces \
  --public-key "$LANGFUSE_PUBLIC_KEY" \
  --secret-key "$LANGFUSE_SECRET_KEY"
```

**预期**：Langfuse 可查到 trace；`$LANGFUSE_*` 是 shell 展开后作为 CLI 参数传入，
**不是** freegraph 读 env。

### 7.5 验收口径

- 三个示例文件存在；三个 `--help` 成功；
- **至少一个**真实后端冒烟（优先 Phoenix / OpenLIT）；
- 其余示例用桩接收端 / 最小接收端，记录捕获的 span 数 / 字段；
- README 含「能力分工 / 重叠」表、来源 + as-of、旧路径 404、HTTP exporter 用户侧依赖；
- **无默认推荐后端**措辞。

---

## 8. 差分 / 门禁 / 人工记录

```bash
# 差分（上游缺席即 skip）
python -m pytest tests/differential/test_b21f1_otlp_parity.py -q

# 契约 / 门禁
python -m pytest tests/contracts/test_b21f1_contracts.py \
  tests/contracts/test_b21f1_gates.py -q

# 全量回归
python -m pytest tests/ -q --tb=no
```

**人工记录**：`harness/verification/B21F1/manual-verification.md` MUST 含：

- 验证环境（Python / OS / OTel 版本 / 后端版本）；
- fake / 本地轮 + 桩接收端 / 最小 gRPC 接收端实测输出；
- 至少一个真实后端冒烟输出；
- 零出站 / 零 OTel import 证据；
- 端点不可达时图成功证据；
- 三示例运行记录；
- 许可证归一（`protobuf`）证据；
- 治理追认文字（G3 / G23 / G26 / B19F1 import 例外 / v1.17.0 具名例外）；
- **质量门禁 5 偏离声明 + 发起者追认**；
- 结论 / 遗留问题。

---

## 9. 已知问题 / 排障

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `ImportError: ... freegraph[otlp]` | 未装 extra | `pip install -e ".[otlp]"` |
| `ValueError: endpoint must be host:port` | 传了 `http://...` | 去掉 scheme，用 `127.0.0.1:4317` + `insecure=True` |
| 本地 Phoenix 连不上 | 默认 TLS | 本地示例必须 `insecure=True` |
| OpenLIT / Langfuse 示例 `ImportError` | 未装 HTTP exporter | `pip install "opentelemetry-exporter-otlp-proto-http>=1.20"` |
| 真实后端不可得 | Docker / 网络 / 版本 | 用桩接收端；manual-verification 写明原因、替代证据、待补验证项 |
| G23 报 `protobuf` 散文标识 | 归一未生效 | 确认 `_gatekit` 的仅 `protobuf` 归一；不得放宽白名单 |
| `import freegraph.observability` 加载了 OTel | 顶层 import 了 OTel | 只在 `OtlpExporter.__init__` / `on_span_end` 惰性 import |

---

## 10. 完成判据

- [ ] A1：`[otlp]` 依赖 / 闭包 / 许可证正确；无自研编码。
- [ ] A2：三示例存在 + `--help` + 至少一个真实后端冒烟 + 其余桩记录。
- [ ] A3：分工表 + 来源 / as-of + 旧路径 404 + 风险说明。
- [ ] A4：未传端点 / 未装 extra ⇒ 零出站 / 零 OTel import / 零 env 读取。
- [ ] A5：显式端点 ⇒ 最小 gRPC 接收端收到完整 span；图结果不变。
- [ ] SC-003：端点不可达 ⇒ 图成功；四路诊断可感知。
- [ ] 门禁：G3 / G21 / G23 / G26 / B19F1 import 例外 / `__all__` 全绿。
- [ ] 人工记录 + 治理追认 + 质量门禁 5 偏离声明。
