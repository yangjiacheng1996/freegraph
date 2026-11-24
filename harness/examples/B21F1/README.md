# B21F1 · 后端最小对接示例（OpenLIT / Langfuse / Phoenix）

> 三个示例**并列、无默认推荐后端**；用户按自己的 OTel 栈选择。
> 本目录是**开发辅助材料**，不进 freegraph 发行包。

## 1. 前置安装

```bash
# freegraph 的合规 extra（只含 gRPC 协议实现 + OTel SDK）
pip install "freegraph[otlp]"

# OpenLIT / Langfuse 是 OTLP/HTTP 后端：HTTP exporter 是**用户侧依赖**，
# 不进 freegraph 的 [otlp] 闭包（其闭包含 certifi（MPL-2.0））。
pip install "opentelemetry-exporter-otlp-proto-http>=1.20"
```

三个脚本的 `--help` **不需要**安装用户侧 HTTP exporter；OpenLIT / Langfuse
只在真正执行导出时才惰性导入它（缺包时打印安装提示并以非零退出码结束）。

## 2. 三个后端

### Phoenix（gRPC · `endpoint=` · 本地明文）

- 来源：`https://arize.com/docs/phoenix` · **as-of 2026-11-24**。
- 协议 / 端口：gRPC OTLP · 默认 `4317`。
- 命令：

```bash
python harness/examples/B21F1/phoenix.py --endpoint 127.0.0.1:4317
```

- 许可：**Elastic-2.0 ⇒ 只连不嵌**；免费不把 Phoenix 的代码 / 包 / 镜像放进 freegraph。
- 本地明文 MUST 显式 `insecure=True`（示例已内置）。

### OpenLIT（OTLP/HTTP · `exporter=`）

- 来源：`https://docs.openlit.io/latest/overview` + `https://github.com/openlit/openlit`
  · **as-of 2026-11-24**。
- **OpenLIT 旧路径 404**：`https://openlit.io/docs`（旧路径）；仓库 README 可作回退。
- 协议 / 端口：OTLP/HTTP · 默认 `4318`。
- 命令：

```bash
python harness/examples/B21F1/openlit.py --endpoint http://127.0.0.1:4318/v1/traces
```

### Langfuse（OTLP/HTTP + Basic auth · `exporter=`）

- 来源：`https://langfuse.com/docs` + `https://langfuse.com/self-hosting` ·
  **as-of 2026-11-24**。
- 协议 / 端口：OTLP/HTTP · 自托管默认 `3000`（以官方文档为准）。
- 认证：`Authorization: Basic base64(public_key:secret_key)`。
- 命令（`$LANGFUSE_*` 是 **shell 展开后作为 CLI 参数**传入，不是 freegraph 读 env）：

```bash
python harness/examples/B21F1/langfuse.py \
  --endpoint http://localhost:3000/api/public/otel/v1/traces \
  --public-key "$LANGFUSE_PUBLIC_KEY" \
  --secret-key "$LANGFUSE_SECRET_KEY"
```

## 3. 能力分工 / 重叠说明

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

**结论**：重叠是**分层互补**，不是替代关系。freegraph 负责**本地运行时诊断 /
图交互 / 状态回溯**；外部后端负责**团队协作 / trace 分析 / 评测 / Prompt 管理**。
外部后端的 agent graph 是**从 trace 只读还原**，不能改 prompt、不能跑图、不能
time-travel。**三个示例并列，无默认推荐后端**；不使用「官方推荐 / 默认后端」措辞。

## 4. 已知失效风险

| # | 风险 | 处置 |
|---|---|---|
| X-1 | **OpenLIT 旧路径 404** | 用现行 `https://docs.openlit.io/latest/overview`；仓库 README 回退；标注 as-of |
| X-2 | OTel 后端 API / 版本变更 | 示例可能失效；标注 as-of；不承诺长期兼容 |
| X-3 | HTTP exporter 是用户侧依赖 | 需用户自装；其 `certifi`/MPL-2.0 不进 freegraph 闭包 |
| X-4 | 真实后端环境不可得 | 至少一个真实后端冒烟；其余用桩 / 最小接收端；manual-verification 写明原因与替代证据 |
| X-5 | Phoenix = Elastic-2.0 | **只连不嵌**；绝不把 Phoenix 代码 / 包 / 镜像放进 freegraph 发行包 |
| X-6 | 端点 / 认证路径变更 | 端点从 CLI 读；README 给出现行路径与 as-of；用户按自己的部署调整 |

## 5. 三个示例的共同约束

- 三个示例导出**同一份标准 OTLP 数据**；不为不同后端写不同映射 / 字段分支。
- 每个脚本从 **CLI** 读端点 / 认证；**不读环境变量**、不内置默认端点。
- 不 import `langchain` / `langchain-core` / `langsmith` / `langgraph*`。
- 不内嵌 Phoenix / Langfuse / OpenLIT 的代码或包。
