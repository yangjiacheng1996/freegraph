# Contract: 三个后端最小对接示例

**Feature**: B21F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

> 本契约锁定三个示例的**文件、端点、认证、前置安装、来源 / as-of、分工 / 重叠说明、
> 已知失效风险与验收口径**。三示例 **并列、无默认推荐**；每个示例 MUST 可复制运行。

---

## 1. 文件与入口

| 文件 | 后端 | 接入模式 | 前置 |
|---|---|---|---|
| `harness/examples/B21F1/phoenix.py` | Phoenix | `OtlpExporter(endpoint="127.0.0.1:4317", insecure=True)` | `freegraph[otlp]` |
| `harness/examples/B21F1/openlit.py` | OpenLIT | `OtlpExporter(exporter=OTLPSpanExporter(...))` | `freegraph[otlp]` + 用户自装 `opentelemetry-exporter-otlp-proto-http` |
| `harness/examples/B21F1/langfuse.py` | Langfuse | `OtlpExporter(exporter=OTLPSpanExporter(...))` | `freegraph[otlp]` + 用户自装 `opentelemetry-exporter-otlp-proto-http` |
| `harness/examples/B21F1/README.md` | 三后端说明 | — | — |

**每个脚本**：

- 自包含（可单独复制运行）；只 import 标准库 + `freegraph` + 对应 OTel exporter。
- 从 **CLI 参数**读取端点 / 认证（`argparse`），**不读环境变量**、不内置默认端点。
- 支持 `--help`；**HTTP exporter 只在实际导出路径内惰性导入**（`argparse` 之后）；
  `--help` MUST NOT 触发该导入；缺包时 MUST 打印安装提示并以非零退出码结束。
- 三个示例的 `--help` MUST 在**未安装**用户侧 HTTP exporter 的环境下成功。
- **不 import** `langchain` / `langchain-core` / `langsmith` / `langgraph*`。
- **不内嵌** Phoenix / Langfuse / OpenLIT 的代码或包。

---

## 2. 端点 / 认证 / 来源

### 2.1 Phoenix

| 项 | 值 |
|---|---|
| 协议 | gRPC OTLP |
| 默认端口 | `4317` |
| 示例参数 | `--endpoint 127.0.0.1:4317`（`insecure=True`） |
| 认证 | 本地默认无；远程由用户自行部署 TLS / 网关（示例不提供 mTLS） |
| 来源 | `https://arize.com/docs/phoenix`（Q6 C14） |
| as-of | 2026-11-24 |
| 许可 | Elastic-2.0 ⇒ **只连不嵌** |

### 2.2 OpenLIT

| 项 | 值 |
|---|---|
| 协议 | OTLP/HTTP |
| 默认端口 | `4318`（Q6 C15 / README） |
| 示例参数 | `--endpoint http://127.0.0.1:4318/v1/traces` |
| 认证 | 本地默认无；如启用由用户自行配置 header |
| 来源 | `https://docs.openlit.io/latest/overview`（用户 2026-11-24 核实可访问）+ `https://github.com/openlit/openlit` |
| 旧路径 | `https://openlit.io/docs` **404**（Q6 取证于 2026-11-03）；仓库 README 可作回退 |
| as-of | 2026-11-24 |
| 许可 | Apache-2.0 ⇒ 可外部连接 |

### 2.3 Langfuse

| 项 | 值 |
|---|---|
| 协议 | OTLP/HTTP |
| 默认端口 | `3000`（自托管默认；以官方文档为准） |
| 示例参数 | `--endpoint http://localhost:3000/api/public/otel/v1/traces` · `--public-key ...` · `--secret-key ...` |
| 认证 | Basic auth header：`Authorization: Basic base64(public_key:secret_key)` |
| 来源 | `https://langfuse.com/docs`（2026-11-24 验证可访问）+ `https://langfuse.com/self-hosting` |
| as-of | 2026-11-24 |
| 许可 | MIT 核心 + `ee/` 另行许可 ⇒ 只经 OTLP/API 外部连接，不拷贝代码 |

> **端点路径复核**：Langfuse / OpenLIT 的 OTLP/HTTP 路径以官方文档为准；示例 MUST 在
> README 标注 as-of 日期与「OTel 后端 API 变更可能导致示例失效」。

---

## 3. 前置安装（用户侧）

```bash
# freegraph 的合规 extra（只含 gRPC）
pip install "freegraph[otlp]"

# HTTP 后端示例需要用户额外安装官方 HTTP exporter（不进 freegraph 依赖闭包）
pip install "opentelemetry-exporter-otlp-proto-http>=1.20"
```

**MUST** 在示例 README 写明：HTTP exporter 是**用户侧依赖**；其闭包含 `certifi`
（MPL-2.0），**不进** freegraph 的 `[otlp]`，freegraph 的许可证白名单不受影响。
该包只在**真正执行** OpenLIT / Langfuse 导出时需要；三个示例的 `--help` **不要求**安装它。

---

## 4. 运行命令（示例）

```bash
# Phoenix（本地 gRPC，明文）
python harness/examples/B21F1/phoenix.py --endpoint 127.0.0.1:4317

# OpenLIT（本地 HTTP）
python harness/examples/B21F1/openlit.py --endpoint http://127.0.0.1:4318/v1/traces

# Langfuse（本地 HTTP + Basic auth）
python harness/examples/B21F1/langfuse.py \
  --endpoint http://localhost:3000/api/public/otel/v1/traces \
  --public-key "$LANGFUSE_PUBLIC_KEY" \
  --secret-key "$LANGFUSE_SECRET_KEY"
```

> 示例脚本本身**不读环境变量**；上面的 `$LANGFUSE_*` 是** shell 展开后作为 CLI 参数**
> 传入，不是 freegraph 读 env。README MUST 明确这一点。

**运行内容**：一个两节点图（`a → b`）+ 节点内一次 fake 模型 / 工具调用；产出节点 /
模型 / 工具 span；`compile(tracer=exporter)`；`invoke()`；打印「exported N spans」。
**MUST NOT** 依赖真实模型 / API key。

---

## 5. 能力分工 / 重叠说明（README 必需）

| 能力 | freegraph（本仓库） | OpenLIT | Langfuse | Phoenix |
|---|---|---|---|---|
| 本地图视图 / mermaid | 是 | 只读调用图 | 只读调用图 | 只读调用图 |
| 本地状态快照 / checkpoint 历史 | 是 | 否 | 否 | 否 |
| interrupt / time-travel / 回放 | 是 | 否 | 否 | 否 |
| 交互式图运行时 IDE | 是 | 否 | 否 | 否 |
| 外部 trace 浏览 / 搜索 | 本地 `query()` | 是 | 是 | 是 |
| 成本 / 延迟 / 用量分析 | 否 | 是 | 是 | 是 |
| 评测 / 数据集 / Prompt 管理 | 否（永不做） | 是 | 是 | 是 |
| 部署 | 本地库 | 自托管 | 自托管 | 自托管 |
| 许可证 | MIT | Apache-2.0 | MIT 核心 + ee | Elastic-2.0 |

**结论（MUST 写入 README）**：

- 重叠是**分层互补**：freegraph 负责**运行时诊断 / 图交互 / 状态回溯**，外部后端负责
  **团队协作 / trace 分析 / 评测 / Prompt 管理**。
- 外部后端的 agent graph 是**从 trace 只读还原**，不能改 prompt、不能跑图、不能
  time-travel；不替代 freegraph 的本地运行时诊断。
- **三示例并列，无默认推荐后端**；用户按自己的栈选择。
- **MUST NOT** 使用「官方推荐 / 默认后端」措辞。

---

## 6. 已知失效风险（README 必需）

| # | 风险 | 说明 / 处置 |
|---|---|---|
| X-1 | OpenLIT 旧路径 `openlit.io/docs` 404 | 现行文档 `https://docs.openlit.io/latest/overview`；仓库 README 回退；标注 as-of |
| X-2 | OTel 后端 API / 版本变更 | 示例可能失效；README 标注 as-of；不承诺长期兼容 |
| X-3 | HTTP exporter 是用户侧依赖 | 需用户自装；其 `certifi`/MPL-2.0 不进 freegraph 闭包 |
| X-4 | 真实后端环境不可得 | 至少一个真实后端冒烟；其余桩接收端；manual-verification 写明原因 / 替代证据 / 待补验证项 |
| X-5 | Phoenix = Elastic-2.0 | **只连不嵌**；绝不把 Phoenix 代码 / 包 / 镜像放进 freegraph 发行包 |
| X-6 | 端点 / 认证路径变更 | 示例从 CLI 读端点；README 给出现行路径与 as-of；用户可按自己的部署调整 |

---

## 7. 验收口径

| # | 判据 | 判定方式 |
|---|---|---|
| A2-1 | 三个示例文件存在 | `test_b21f1_examples.py` |
| A2-2 | 每个示例 `--help` 成功（**不要求**已安装用户侧 HTTP exporter） | 子进程 `python <script> --help`；缺 HTTP exporter 时仍退出 0 |
| A2-3 | 三个示例都有可运行记录 | `manual-verification.md` |
| A2-4 | 至少一个真实后端冒烟 | 优先 Phoenix / OpenLIT；记录输出 |
| A2-5 | 其余示例用桩接收端 / 最小接收端 | 记录捕获的 span 数 / 字段 |
| A3-1 | 分工 / 重叠表存在 | README 文本标记断言 |
| A3-2 | 无默认推荐措辞 | README 不含「官方推荐 / 默认后端」 |
| A3-3 | OpenLIT 旧路径 404 + 现行 URL + as-of | README 文本标记断言 |
| A3-4 | 三后端来源 + as-of | README 文本标记断言 |
| A3-5 | HTTP exporter 用户侧依赖说明 | README 文本标记断言 |
| A3-6 | 无 Phoenix / Langfuse / OpenLIT 内嵌 | 依赖 / 源码扫描 |

---

## 8. 不变量

1. 三示例 **并列、无默认推荐**。
2. 每个示例从 **CLI** 读端点 / 认证；**不读 env**、无默认端点。
3. 三个示例导出**同一份标准 OTLP 数据**；不为不同后端写不同映射 / 分支。
4. HTTP exporter 只在用户侧安装；**不进** freegraph 依赖闭包。
5. **不内嵌** Phoenix / Langfuse / OpenLIT；Phoenix 只连不嵌。
6. **不 import** `langchain*` / `langsmith` / `langgraph*`。
7. 真实后端冒烟 **至少一个**；其余可用桩；不可静默降级。
