# B21F1 · OTLP 导出插件（可选 extra）+ 后端对接文档 —— 人工验证记录

> **状态**：已完成。T050 / T052 已执行并获发起者书面追认（2026-11-24）；T054 文档守卫已通过。

## 1. 验证环境

- Python：**3.11.16**（`/home/ctyun/workspace/github/freegraph/.venv`）。
- 平台：Linux x86_64。
- `[otlp]` 实测闭包（`uv pip install -e ".[otlp]"`）：`opentelemetry-api 1.45.2` ·
  `opentelemetry-sdk 1.45.2` · `opentelemetry-semantic-conventions 0.66b2` ·
  `opentelemetry-exporter-otlp-proto-grpc 1.45.2` ·
  `opentelemetry-exporter-otlp-proto-common 1.45.2` ·
  `opentelemetry-exporter-otlp-common 0.66b2` · `opentelemetry-proto 1.45.2` ·
  `googleapis-common-protos 1.76.0` · `grpcio 1.85.3` · `protobuf 7.36.2` ·
  `typing-extensions`（既有白名单）。
- 基础安装：`dependencies = []`；`[otlp]` 默认不安装。

### 1.1 基线

- 实施前基线（plan 记录 · 2355 collected）：**`2345 passed, 10 skipped`**。
- `git diff --exit-code -- harness/demo/target.py src/freegraph/contracts/trace.py src/freegraph/contracts/protocols.py`
  ⇒ **无输出（退出码 0）**，冻结契约零改动。
- 实施后全量回归（T049）：**`2426 passed, 10 skipped`**（见 §3.5）。

## 2. 验证步骤

1. `uv pip install --python .venv -e ".[otlp]"`。
2. `python -m pytest tests/observability/test_b21f1_*.py tests/contracts/test_b21f1_*.py tests/differential/test_b21f1_otlp_parity.py -q`。
3. `python harness/verification/B21F1/acceptance.py`。
4. `python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`。
5. 三示例 `python harness/examples/B21F1/<name>.py --help`（不要求安装 HTTP exporter）。
6. `python -m pytest -q --tb=no`（全量回归）。

## 3. 实际输出

### 3.1 显式端点 / 桩 / 最小 gRPC（acceptance.py）

```text
[PASS] A1 基础依赖为空
[PASS] A1 [otlp] 仅 gRPC 协议实现 + OTel SDK
[PASS] A1 无 certifi / HTTP exporter
[PASS] A1 无自研 protobuf / wire 编码 / OTLPSpanExporter 门面
[PASS] A2 示例存在：phoenix.py
[PASS] A2 示例存在：openlit.py
[PASS] A2 示例存在：langfuse.py
[PASS] A2 示例存在：README.md
[PASS] A2 --help 成功：phoenix.py
[PASS] A2 --help 成功：openlit.py
[PASS] A2 --help 成功：langfuse.py
[PASS] A3 文档标记：OpenLIT 旧路径 404
[PASS] A3 文档标记：https://docs.openlit.io/latest/overview
[PASS] A3 文档标记：as-of
[PASS] A3 文档标记：能力分工 / 重叠
[PASS] A3 文档标记：无默认推荐
[PASS] A3 文档标记：HTTP exporter 是**用户侧依赖**
[PASS] A3 文档标记：只连不嵌
[PASS] A4 默认关闭 / 零 OTel import / 忽略 env
[PASS] A4 默认路径框架出站 == 0
[PASS] A5 桩 exporter：图结果不变
[PASS] A5 桩 exporter：2 个完整 span
[PASS] A5 最小 gRPC：图结果不变
[PASS] A5 最小 gRPC：每 span 一次 Export
[PASS] A5 最小 gRPC：trace_id 非空
checks = 25, failures = 0
B21F1 acceptance: PASS
```

### 3.2 许可证归一 / G23

```text
[G23] 被检查的包数 = 19（并集口径：闭包包集 ∪ 取证作用域根下扫到的 dist-info）
[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）
```

`protobuf 7.36.2` 的元数据为散文 `License: 3-Clause BSD License`；G23 经**仅此一包 /**
仅此一字符串**的具名归一为 `BSD-3-Clause`（依据其 LICENSE 文件），未放宽白名单。

### 3.3 三个后端示例

- 三个 `--help` 在**未安装**用户侧 HTTP exporter 的环境下均退出 0。
- `openlit.py` / `langfuse.py` 在缺少 HTTP exporter 时打印
  `pip install "opentelemetry-exporter-otlp-proto-http>=1.20"` 并以退出码 2 结束。
- **真实后端冒烟**：本机无 Phoenix / OpenLIT / Langfuse 运行环境 ⇒ 按 SC-015
  用**最小 gRPC 接收端 + 桩接收端**替代；未声称「已接真实后端」。

### 3.4 默认关闭 / 零出站 / 失败隔离

- 默认关闭 / 零 OTel import / 忽略 `OTEL_*` / `LANGSMITH_*`：§3.1 A4 全 PASS。
- 失败隔离：`tests/observability/test_b21f1_failure.py` **10 passed**
  （不可达端点、用户 exporter 异常、`FAILURE`、`on_error` 异常、`BaseException` 不吞、
  不重试、并发、`last_error` 不清空）。
- 最小 gRPC 接收端：`tests/observability/test_b21f1_transport.py` **1 passed**
  （每 span 一次 `Export`，name / trace_id / parent / `gen_ai.*` 属性可校验）。

### 3.5 全量回归 / 门禁

```text
2426 passed, 10 skipped
```

- `pytest tests/contracts/test_architecture.py tests/gates -q`：**185 passed**。
- G21 / G23：`--project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml` ⇒ **PASS**（被检查包数 = 19）。
- G24 / G25 / G26 / G27：**PASS**（G26 例外名单 = `['freegraph.observability._otlp_transport']`；
  G27「框架出站 = 0 · 用户出站 = 2（记录在案，不判失败）」）。
- `harness/demo/target.py` 与冻结契约文件 diff 为空（§1.1）。
- T041：`spec.md` §6 的 G23 `protobuf` 具名归一与 B19F1 import 例外两行**已存在**，无漂移。
- **GitHub Actions CI**：**7/7 作业全绿**（run `45365129113` · `head_sha = 45b50b6` ·
  ubuntu 3.11/3.14 + ubuntu-arm64 3.11 + macOS 3.11/3.14 + Windows 3.11/3.14；
  Linux 档的 G22 / G27 / G28 均真跑通过；G28 已登记 2 条 B21F1 回环 gRPC 排除项）。

## 4. 结论

- **A1** 可选 `[otlp]` + 不自研 OTLP 编码：PASS（依赖声明 / AST 扫描 / G23）。
- **A2** 三个后端最小对接示例：PASS（三文件 + `--help` + README 分工表）。
- **A3** 已知失效风险说明：PASS（旧路径 404、现行 URL、as-of、HTTP 用户侧依赖、只连不嵌）。
- **A4** 默认关闭，仅显式传入时生效：PASS（零 OTel import / 零框架出站 / 忽略 env）。
- **A5** 可导出到任一 OTel 后端：PASS（桩 + 最小 gRPC；真实后端按 SC-015 记录替代证据）。
- **SC-001…SC-015**：见 tasks.md 追溯表与上述证据；`TraceRecord` / `context` /
  `checkpoint_id` / `node` 不导出；不消费 B20F2 `query()`。

### 4.1 最终审计（T055）

- FR-001…FR-041 / SC-001…SC-015：逐条映射到 tasks.md 的追溯表与上述测试 / 验收证据；
  无零覆盖项。
- plan 红名单 B-1…B-17：已逐条核对（白名单 12→19、`SIGNED_SOURCE_FILES` +3、
  L5 / B19F1 import 例外、G26 例外、G23 归一、`__all__` 只增、CI 安装 `[otlp]`、
  全量计数只增）。B-16 文档守卫在记录写就后加入。
- P-01…P-07 ↔ X-1…X-5：三态标注一致（SAME / STRICTER / DIFF 与 spec §Upstream Parity 一致）。
- 无未登记澄清标记 / 无占位符 / 无越界实现（未做 async / UI / Agent Server /
  自托管后端 / `DateTime` / `TraceRecord` 导出 / `query()` 消费 / `resource_attributes`）。
- G23 / G26 / B19F1 例外均为**具名且最小范围**；其余模块禁令不变。

### 4.2 治理追认

- 宪法 v1.17.0 `[otlp]` 具名例外：已正式修订；**已由发起者于 2026-11-24 书面追认**（确认人：发起者本人）。
- G3 白名单 12 → 19；G23 `protobuf` 归一；G26 / B19F1 import 例外：
  均已登记；**已由发起者于 2026-11-24 书面追认**（确认人：发起者本人）。
- **质量门禁 5 偏离**：已登记；真实模型轮由 **B25F1（M4 双跑验收）** 承接，
  承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B21F1）」。
- **追认已完成，可合入**；本条记录由发起者于 2026-11-24 在本会话中确认并授权写入。

## 5. 遗留问题

- **真实后端冒烟**：本机环境不可得 ⇒ 已用最小 gRPC 接收端 / 桩接收端替代；待补验证项 =
  Phoenix / OpenLIT / Langfuse 各一次真实导出。
- **真实模型轮**：偏离到 **B25F1**（质量门禁 5 承接）。
- v1 不提供 async / 后台线程 / batching 导出；不提供 `close()` / 上下文管理器。
- v1 不导出 `TraceRecord` / `context` / `checkpoint_id` / `node`。
- v1 不提供 `resource_attributes` 参数（固定 `service.name="freegraph"`）。
