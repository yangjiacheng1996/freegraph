# B25F1 · 人工验收记录

> 记录日期：2026-11-25；**人工验收签字：2026-11-26（通过）**。
> 本地自动化重跑真实模型轮时本机未配置凭据，曾登记**环境偏离**（历史记录保留在 §3.9）；
> 发起者随后以真实 provider 完成人工验收，A2 通过。**v1.0 收口条件已满足。**

## 1. 验证环境

| 项 | 内容 | 来源 |
|---|---|---|
| 操作系统 | Linux 6.8.0-139-generic (x86_64) | `platform.system()` / `platform.release()` |
| Python | 3.11.16 | `.venv/bin/python --version` |
| freegraph | 0.0.3 | `importlib.metadata.version("freegraph")` |
| `langchain` | 1.4.5 | `importlib.metadata.version("langchain")` |
| `langchain-core` | 1.8.4 | `importlib.metadata.version("langchain-core")` |
| `langgraph`（仅差分/上游） | 1.2.11 | `importlib.metadata.version("langgraph")` |
| `IPython` | 9.19.1 | `importlib.metadata.version("IPython")` |
| `LANGSMITH_*` 清理方式 | 本进程与所有子进程逐项剔除；计数 == 0 | `harness/demo/acceptance.py::collect_env` / `run_suite` |
| 真实模型接入路径 | **官方直连**（DeepSeek / MiniMax OpenAI-compatible 端点）；**兼容网关**未使用 | `harness/verification/B25F1/verify_deepseek.py` / `verify_minimax.py` · 发起者人工验收 |

## 2. 验证步骤

- [x] fake 轮（A1）：`harness/verification/B25F1/fake_round.py`（默认 + `--subprocess`）
- [x] 真实模型轮段 1（A2）：原样执行 `harness/demo/target.py` —— **发起者人工验收通过（2026-11-26）**
- [x] 真实模型轮段 2（A2）：`harness/verification/B25F1/real_round.py` —— **发起者人工验收通过（2026-11-26）**
- [x] 四组（含 diagnostics）：`harness/demo/acceptance.py`
- [x] 双重基线（A5）：SHA-256 + 基线 ref diff
- [x] 断网等价性：进程内层（OS 级 G28 见后文命令）
- [x] 依赖断言 + 反向断言（DEP）
- [x] 发布前人工验收清单：引用 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
      `harness/verification/B14F1/acceptance.py`（只引用、不回改）

## 3. 实际输出

### 3.1 fake 轮（A1 · 同进程）

```text
[fake] 模型调用次数 = 2
[fake] messages 长度 = 4
[fake] llm_calls = 2
[fake] PNG 字节数 = 173
[fake] 框架出站 = 0
[fake] 用户出站 = 0（记录在案，不判失败）
B25F1 fake round: PASS
```

### 3.2 fake 轮（A1 · `--subprocess` 外部注入）

```text
[subprocess] messages 长度 = 4
[subprocess] llm_calls = 2
[subprocess] PNG 字节数 = 173
[subprocess] 框架出站 = 0
[subprocess] 用户出站 = 0（记录在案，不判失败）
B25F1 fake round: PASS
```

### 3.3 US1 测试（固定断言点 / 双重基线 / 差分 / 模型工厂）

```text
$ .venv/bin/python -m pytest tests/runtime/test_b25f1_target_fake.py \
    tests/runtime/test_b25f1_target_guard.py \
    tests/differential/test_b25f1_final_acceptance.py \
    tests/differential/test_b25f1_model_factory.py -q
.........                                                                [100%]
9 passed in 2.05s
```

### 3.4 四组（含 diagnostics）· A4

```text
$ .venv/bin/python harness/demo/acceptance.py
graph_core.py 退出码 0
agent_loop.py 退出码 0
visualization.py 退出码 0
diagnostics.py 退出码 0（硬断言 32 条 · 失败 0）
target fake 旁路步骤 退出码 0（旁路 · 不计入四组）
自身检查 13 条 · 失败 0
总体 0
```

### 3.5 B23F1 PNG 实测

```text
$ .venv/bin/python harness/verification/B23F1/acceptance.py
B23F1 acceptance: PASS
```

补充：fake 轮捕获到的 `draw_mermaid_png()` 字节数为 **173**，PNG 签名 / IHDR 校验通过
（`harness/verification/B25F1/fake_round.py` 内 `_png_ok`）。框架出站 = 0。

### 3.6 B24F1 发行产物 + `COMPAT.md` 声明

```text
$ .venv/bin/python harness/verification/B24F1/acceptance.py
B24F1 acceptance: PASS (68 checks)
```

实测项包含：基础依赖为空、唯一 extra `[otlp]`、`COMPAT.md` 27 行机读段 / 18 项覆盖表、
`Command` = 部分等价、`Y-01` / `Y-02` / `Y-03` 均在 `COMPAT.md` 中保留。

### 3.7 跨 feature 复验引用（不是替代）

| Feature | 命令 | 实际结果 |
|---|---|---|
| B14F1 | `harness/verification/B14F1/acceptance.py` | `共 48 条断言 · 失败 0 条` · `B14F1 acceptance: PASS` |
| B15F1 | `harness/verification/B15F1/acceptance.py` | `共 62 条断言 · 失败 0 条` · `B15F1 acceptance: PASS` |
| B16F1 | `harness/verification/B16F1/acceptance.py` | `共 77 条断言 · 失败 0 条` · `B16F1 acceptance: PASS` |
| B20F1 | `harness/verification/B20F1/acceptance.py` | `B20F1 acceptance: PASS（23 项检查）` |
| B20F2 | `harness/verification/B20F2/acceptance.py` | `B20F2 acceptance: PASS（35 项检查）` |
| B21F1 | `harness/verification/B21F1/acceptance.py` | `checks = 25, failures = 0` · `B21F1 acceptance: PASS` |

B14F1 记录引用：`harness/verification/B14F1/manual-verification.md`；一键验收：
`harness/verification/B14F1/acceptance.py`。**MUST NOT 回改** B14F1 记录。

### 3.8 零出站 + 断网等价性

```text
$ .venv/bin/python -m pytest tests/runtime/test_b25f1_zero_egress.py \
    tests/runtime/test_b25f1_offline_equivalence.py -q
...                                                                      [100%]
3 passed in 2.14s
```

- 进程内层（必做）：`fake_round.py` + `graph_core.py` + `agent_loop.py` +
  `visualization.py` + `diagnostics.py` 在禁用 socket 后全部退出码 0。
- 用户出站测试**不触网**（进入 `record_egress` 前把底层 connect 替换为 no-op）⇒
  G28 无需新增排除项。
- OS 级 G28（条件增强）：

```text
$ unshare --net --map-root-user true
unshare: 写失败：/proc/self/uid_map: 不允许的操作
```

⇒ 本机无创建非特权网络命名空间的权限；**环境偏离**（OS 级未执行，不判失败；已有进程内层证据）。
进程内层已完成，不替代 OS 级。

### 3.9 真实模型轮（A2）· 自动重跑环境偏离（历史）

```text
$ .venv/bin/python harness/verification/B25F1/real_round.py --record /tmp/opencode/b25f1-real-round-draft.md
[environment_deviation]
{
  "deviation": "真实模型凭据未配置：未检测到 ANTHROPIC_API_KEY / OPENAI_API_KEY / B25F1_BASE_URL；已完成：fake 轮 / 四组 / 诊断；未完成：真实模型轮 段 1 + 段 2。"
}
B25F1 real round: ENV
```

**已完成**：fake 轮、四组（含 diagnostics）、双重基线、依赖/反向断言、B14F1–B24F1 跨 feature 复验。
**历史说明**：本节仅记录本地自动化重跑时的环境偏离（本机未配置凭据）；
**不代表最终验收结论**。发起者随后以真实 provider 完成人工验收，见 §3.14。

### 3.10 迁移说明 + README 收口（SC-005）

```text
$ .venv/bin/python -m pytest tests/runtime/test_b25f1_docs_guard.py \
    tests/contracts/test_b24f1_docs.py -q
...........                                                              [100%]
11 passed in 0.11s

$ .venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py
[G29] PASS —— 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）

$ .venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
[G29] COMPAT.md：覆盖契约 ∪ 门面清单 + Command = 部分等价 + README 仅指针（严格判定通过）
```

- 迁移说明：三类（同名直接可用 / 同名但行为有差异 / 需要改写）+ **Y-01** + `COMPAT.md` 指针。
- README：快速上手 + 三条承诺 + 能力处置表 + 独立实现声明 + `COMPAT.md` **绝对链接**；
  无第二份完整逐符号矩阵。

### 3.11 一键验收（`acceptance.py --skip-real --record`）

```text
$ .venv/bin/python harness/verification/B25F1/acceptance.py --skip-real \
    --record /tmp/opencode/b25f1-acceptance-draft.md
[DEP] PASS — 基础零依赖 + 唯一 extra otlp + 反向断言通过
[A1] PASS — messages==4 / llm_calls==2 / tool==7 / 两键 / PNG / 框架出站 0
[A3] PASS — 框架出站 = 0
[A4] PASS — 四组（含 diagnostics）全绿；target fake 为旁路
[A5] PASS — SHA-256 + 基线 ref diff 双重基线通过
B25F1 acceptance: PASS
```

A5 实际值：

```text
recorded = 2bd47c225645f9ed7e991577d2a118b5eea8d4ab8e3b43b9e0e50539ac202991
actual   = 2bd47c225645f9ed7e991577d2a118b5eea8d4ab8e3b43b9e0e50539ac202991
git diff: empty
```

> 草稿路径：`/tmp/opencode/b25f1-acceptance-draft.md`。本节只合并**未与真实轮冲突**的
> 自动步骤；T026–T028 的真实轮证据未被覆盖（真实轮当前为环境偏离）。

### 3.12 COMPAT.md ↔ 上游 langgraph 对照审计

```text
$ .venv/bin/python -m pytest tests/differential/ -q
140 passed, 3 skipped in 45.25s

$ .venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
[G29] COMPAT.md：覆盖契约 ∪ 门面清单 + Command = 部分等价 + README 仅指针（严格判定通过）
```

- 差分夹具（`langgraph==1.2.11`）覆盖输出状态 / 事件序列 / 节点入参等投影；140 passed。
- `COMPAT.md` 的既有 DIFF：**Y-01**（`Command.goto` 默认 `()` vs `None`）、
  **Y-02**（`get_state` 无快照 `None` vs 上游空 `StateSnapshot`）、
  **Y-03**（`Send` 不可变 vs 上游可变）均按既有登记保留；运行时对齐归 **v2 独立契约修订**。
- 本 feature **未修改 `src/freegraph/**`**（`git diff -- src/freegraph` 为空）；
  上游 1.2.11 的 `Send(..., timeout=)` / `add_node` 新策略关键字属 v1 目标表面之外，
  不改 v1 运行时，避免越出 B25F1「零运行时改动」边界。

### 3.13 真实 provider 连通性（人工验收证据之一）

本地生成的两份**忽略文件**脚本（`harness/verification/B25F1/verify_deepseek.py` /
`verify_minimax.py`，已加入 `.gitignore`，含凭据，**未提交**）用 `target.py` 同款
SystemMessage / 工具循环 / 条件边形状，直接调用 provider 的 OpenAI-compatible 端点：

| Provider | 端点 | 模型 | 实际结果 |
|---|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-v4-flash` | `messages=4` · `llm_calls=2` · `add(3,4)=7` · **PASS** |
| MiniMax | `https://api.minimaxi.com/v1` | `MiniMax-M3` | `messages=4` · `llm_calls=2` · `add(3,4)=7` · **PASS** |

> 该证据证明「真实 provider 能完成 target.py 同款工具循环」。A2 的
> `real_round.py` 两段式由发起者人工执行并确认通过（见 §3.14）。
> 记录中不写入任何密钥。

### 3.14 人工验收签字（A2 · 2026-11-26）

```text
B25F1 real round: PASS（发起者人工验收，2026-11-26）
```

| 项 | 内容 |
|---|---|
| 验收日期 | 2026-11-26 |
| 验收人 | 项目发起者 杨家成 |
| 验收结论 | **通过**（双跑通过；框架零出站；四组全绿；`target.py` 零改动） |
| 真实模型依据 | DeepSeek `deepseek-v4-flash` 与 MiniMax `MiniMax-M3` 的 target.py 同款工具循环均 PASS；`real_round.py` 两段式由发起者人工执行并确认 |
| 接入路径 | **官方直连**（OpenAI-compatible 端点）；未使用**兼容网关** |
| 遗留 | Y-01 / Y-02 / Y-03 按 COMPAT 保留，运行时对齐归 v2 |

> 签字含义：发起者确认 A2 真实模型轮已完成，B25F1 达到 v1.0 收口条件。

## 4. 结论

- **fake 轮 / CI 轮**：PASS（A1）。
- **框架零出站**：PASS（A3；框架出站 = 0，用户出站逐条记录、不判失败、不设白名单）。
- **验收脚本集四组（含 diagnostics）**：PASS（A4）。
- **`target.py` 未修改**：PASS（A5；SHA-256 + 基线 ref diff）。
- **真实模型轮**：**PASS（A2 · 发起者人工验收，2026-11-26）**。
- **v1.0 收口条件已满足**（双跑通过 + 框架零出站 + 四组全绿 + 只读基准）。
- 本地自动化重跑时的真实模型环境偏离（§3.9）保留为历史记录，不改变人工验收结论。

## 5. 遗留问题

1. **Y-01**：`Command.goto` 缺省值上游 `()` vs freegraph `None` = **DIFF**；v1 行为提示保留；
   运行时对齐归 **v2 独立契约修订**（本 feature 不改运行时）。
2. **Y-02 / Y-03**：`get_state` 无快照返回值、`Send` 不可变性为既有 DIFF；按 COMPAT 保留，v2 对齐。
3. OS 级断网 G28 为条件增强；本机 `unshare` 无权限（环境偏离），进程内层已通过。
4. 本地自动化重跑真实模型轮时的凭据缺失环境偏离（§3.9）为历史，不影响人工验收签字。

## 附件 1 · 依赖断言轮输出

```text
Requires-Dist: ["opentelemetry-api>=1.20; extra == 'otlp'",
                "opentelemetry-exporter-otlp-proto-grpc>=1.20; extra == 'otlp'",
                "opentelemetry-sdk>=1.20; extra == 'otlp'"]
version: 0.0.3
dependencies: []
optional: ['otlp']
```

⇒ 基础安装 `Requires-Dist` 为空；唯一 extra = `otlp`。

## 附件 2 · 框架出站 = 0 监测记录

```text
[fake] 框架出站 = 0
[subprocess] 框架出站 = 0
[A3 框架零出站断言] 框架出站数 = 0（freegraph 自身未发起任何连接）
用户出站：0 条（fake 轮无模型网络调用；真实轮待补）
```

## 附件 3 · 反向断言结果

```text
bad_sys_modules: []
```

⇒ `import freegraph` 后 `sys.modules` 中无 `langchain` / `langchain_core` / `langsmith` / `langgraph`。

## 6. 最终门禁报告

| 检查 | 命令 | 实际结果 |
|---|---|---|
| 全量测试 + 零出站（G27） | `.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py` | `2489 passed, 13 skipped` · 框架出站 = 0 · 用户出站 = 3（记录在案，不判失败）· PASS |
| 隔离环境（G22） | `.venv/bin/python harness/scripts/gates/gate_G22_isolated_env.py` | 基础闭包第三方包数 = 0 · 运行期 `sys.modules` 无 langchain 家族 · 框架出站 = 0 · PASS |
| 依赖黑名单（G21） | `gate_G21_dependencies.py --project .../extras-v2.toml` | PASS |
| 许可证白名单（G23） | `gate_G23_licenses.py --project .../extras-v2.toml` | PASS（19 包 · 5 SPDX id） |
| 配置层（G24） | `gate_G24_config_layer.py` | PASS |
| 导入图（G25） | `gate_G25_import_graph.py` | PASS |
| 网络静态（G26） | `gate_G26_network_static.py` | PASS |
| 契约门禁载体（G29） | `gate_G29_contract_carrier.py` / `--check-compat` | PASS / 严格判定通过 |
| 署名头（G30） | `gate_G30_attribution.py` | PASS（覆盖率 100%） |
| 断网等价（G28） | `unshare --net --map-root-user ... gate_G28_offline_equiv.py` | **环境偏离**：本机 `unshare` 无权限（`/proc/self/uid_map: 不允许的操作`）；进程内层已通过 |
| B25F1 一键验收（CI） | `harness/verification/B25F1/acceptance.py --skip-real` | `B25F1 acceptance: PASS`（DEP/A1/A3/A4/A5） |
| 真实模型轮（A2） | 发起者人工验收（`real_round.py` 两段式） | **PASS（2026-11-26）**；本地自动化重跑的环境偏离为历史 |

| T052 严格记录守卫（发布 / 人工门禁） | `B25F1_RECORD_STRICT=1 pytest tests/runtime/test_b25f1_manual_record_guard.py` | **PASS**（人工验收签字后） |

**结论**：A1 / A2 / A3 / A4 / A5 与 CI 门禁全部通过；**v1.0 收口条件已满足**。
本地自动化重跑真实模型轮的凭据缺失环境偏离（§3.9）为历史记录，不改变人工验收结论。
