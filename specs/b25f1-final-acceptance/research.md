# Research: B25F1 · 双跑验收 + 迁移说明 + README 收口

**Date**: 2026-11-25 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **取证口径**：本文件对**仓库现状 / 验收入口 / 门禁实现 / 测试夹具**的断言来自本地源码
> （`harness/` · `tests/` · `pyproject.toml` · `.github/workflows/`，as-of 2026-11-25）；
> 对**上游行为**的断言沿用 `langgraph==1.2.11` 的既有实测基线。本 feature **不新增运行时行为**。
> **无未决澄清。**

---

## D-01 · fake 注入机制：同进程猴补 + 子进程 `sitecustomize`

**Decision**：

1. **主路径（CI A1）**：在**同进程**里先猴补 `langchain.chat_models.init_chat_model`，再用
   `runpy.run_path("harness/demo/target.py", run_name="__main__")` 执行固定脚本；
2. **等价路径**：生成临时目录中的 `sitecustomize.py`（导入 `fake_model.install()`），
   以 `PYTHONPATH=<tmp>` + `python harness/demo/target.py` 起**子进程**执行；
3. 两条路径都**不修改** `target.py`，且注入代码只存在于 `harness/verification/B25F1/` 与 `tests/`。

**证据（关键）**：

| 事实 | 证据 |
|---|---|
| 固定脚本在**导入期**解析 `init_chat_model` | `harness/demo/target.py:23`（`from langchain.chat_models import init_chat_model`） |
| 紧接着立即调用（无延迟） | `harness/demo/target.py:26-29`（`model = init_chat_model("claude-sonnet-4-6", temperature=0)`） |
| 工具绑定 | `harness/demo/target.py:69`（`model_with_tools = model.bind_tools(tools)`） |
| 固定脚本自带 IPython | `harness/demo/target.py:161`（`from IPython.display import Image, display`） |
| 现有验收脚本已有「导入前注入」经验 | `harness/demo/acceptance.py` 的 `EgressProbe` 在运行前安装；`acceptance.py:...` 的 `run_suite` 用子进程 |
| 现有 runtime conftest 已有子进程执行器 | `tests/runtime/conftest.py` 的 `run_in_subprocess`（子进程内 `sys.modules` / env / egress 计数） |

**Rationale**：同进程路径最容易捕获 `display(Image(...))` 的 PNG 字节与 socket 出站；
子进程路径证明「外部注入」可行，避免把「只能 import 后改对象」当成唯一答案。
⇒ 两条路径共同构成 FR-001 的「外部机制替换」证据。

**Alternatives considered**：
- **只改 `target.model` / `target.model_with_tools`** —— 可行但依赖 import 后替换，且无法证明
  导入期注入；Spec 的 Clarifications 已把它列为**备选**，不作主路径。
- **只做子进程 + sitecustomize** —— 更接近 CI 独立进程，但同进程的 PNG / 出站观测更难做，
  且调试成本高；故保留同进程为主、子进程为等价验证。

---

## D-02 · 固定断言点：`messages == 4`（不是 3）

**Decision**：A1 的固定断言点为：

- `messages` 长度 == **4**（Human → AI(tool_call) → ToolMessage → AI 最终答案）；
- `llm_calls == 2`；
- 工具结果 == **7**（按整数归一比较：`ToolMessage.content` 实测为 `"7"`，断言用
  `int(content) == 7` / `content in (7, "7")`，**不得**因字符串类型误判失败）；
- `invoke()` 返回完整状态（含 `messages` / `llm_calls` 两键）。

**证据**：

| 事实 | 证据 |
|---|---|
| `MessagesState.messages` 用 `operator.add` 累积 | `harness/demo/target.py:78-80` |
| 初始消息是 HumanMessage | `harness/demo/target.py:166-168`（`messages = [HumanMessage(content="Add 3 and 4.")]`） |
| `SystemMessage` 只在 `llm_call` 的模型入参里拼接 | `harness/demo/target.py:86-101`（`[SystemMessage(...)] + state["messages"]`） |
| 第 1 轮返回 AI(tool_call)、第 2 轮返回最终 AI | 固定输出序列（fake） |
| 工具节点返回 ToolMessage | `harness/demo/target.py:109-117` |
| `ToolMessage` 会把 `content=7` 归一为 `"7"` | 实测 `langchain_core`：`ToolMessage(content=7, tool_call_id="call_1").content == "7"`（2026-11-25） |

**Rationale**：System 只进模型输入、不进 state；最终状态必然包含 Human、AI(tool_call)、
ToolMessage、AI(final) 四条。简报 / **立项书 §4.2 S4 / §9.2** 的「3（System + AI + Tool）」
是**三点投影**，不是长度。⇒ 按宪法原则 XI「上游优先」照抄上游同款 Quickstart 实际行为，
**不向错误数字对齐**。**立项书已事实性更正为 4**（2026-11-25 发起者确认）。

**Alternatives considered**：
- **断言 3** —— 会让 fake 轮无法反映真实的工具循环状态（缺 Human 或 AI final），且与上游实测冲突。
- **只断言 `len(messages) >= 3`** —— 太弱，无法抓住「最终答案缺失」或「工具消息缺失」。

---

## D-03 · 零出站归因：复用 G27 的「第一个非标准库帧」

**Decision**：B25F1 的零出站监测**复用** `harness/scripts/gates/_gatekit.py` 的
`record_egress` / 归因逻辑（G27 的「第一个非标准库帧」规则）；`harness/demo/acceptance.py`
的内联 `EgressProbe` **对齐同一规则**（仍只 import 标准库），不改变「只观测不阻断」。

**证据**：

| 事实 | 证据 |
|---|---|
| G27 的观察面 = 测试套件执行期 + 内核运行时 | `harness/scripts/gates/gate_G27_zero_egress.py` 的 `OBSERVATION_SCOPE` |
| G27 的归因规则 = 第一个非标准库帧 | `gate_G27_zero_egress.py` 模块 docstring「裁定 19 · research D-11」 |
| G27 的共享实现 | `harness/scripts/gates/_gatekit.py`（`record_egress` / `EgressRecord`） |
| demo 现有内联实现 | `harness/demo/acceptance.py` 的 `EgressProbe._classify`（当前「栈含 freegraph」） |
| 用户出站不判失败的既有口径 | `harness/demo/acceptance.py:case_zero_egress`（`len(probe.user)` 只打印） |

**Rationale**：`target.py` 的 `tool_node` / `llm_call` 都会被框架调用；若用户节点内部再发起连接，
「栈含 freegraph」会把**用户出站**误判为**框架出站**。`_gatekit` 的「第一个非标准库帧」能正确
归因，且 G27 已是宪法锁定的口径。⇒ B25F1 新探针直接复用；demo 内联实现同步规则，保持
「单文件 + 标准库」约束。

**Alternatives considered**：
- **另写一套归因** —— 与 G27 漂移，违反「同一判定不双写」；已有 G27 权威实现。
- **demo 直接 import `_gatekit`** —— 会让 `harness/demo/` 的「只 import freegraph + 标准库」字面约束
  失效；故内联对齐规则，不 import。

---

## D-04 · `target.py` 双重基线：SHA-256 + 基线 ref diff

**Decision**：

- **内容真值**：`tests/runtime/data/b25f1_target_py.sha256`，内容为 `<sha256>  target.py`；
  测试读取并以 `hashlib.sha256` 比对；
- **历史真值**：`git diff --exit-code <baseline_ref> -- harness/demo/target.py`；
  `baseline_ref` 默认 `origin/main`，可由 `B25F1_BASELINE_REF` 覆盖；
- **不可用时**：`git` 缺失 / 基线 ref 不可达 ⇒ pytest `skip`（理由明确）或 acceptance 记录
  **环境偏离**；**SHA-256 断言仍然执行**，MUST NOT 静默通过；
- CI：`actions/checkout@v7` 加 `with: fetch-depth: 0`，保证 `origin/main` 可用。

**证据**：

| 事实 | 证据 |
|---|---|
| 现有 CI 的 checkout 未设 fetch-depth | `.github/workflows/ci.yml` 的 `actions/checkout@v7` 步骤（无 `with:`） |
| 固定脚本当前内容 | `harness/demo/target.py`（170 行；SHA 由实现期生成） |
| `git diff HEAD` 的缺陷 | 只能发现工作区未提交改动；已提交篡改需与基线 ref 比较 |

**Rationale**：SHA-256 离线可判、跨分支稳定；基线 ref diff 能发现「提交级篡改」。
两者互补，直接兑现 spec FR-011 / A5。

**Alternatives considered**：
- **只记录 SHA-256** —— 可行，但无法证明「与历史基线一致」；spec 明确要求双重基线。
- **只比 `origin/main`** —— 浅克隆 / 本地无远端时不可用；且无法在离线环境判定。

---

## D-05 · B5F2 模型工厂：新增入口，不放宽旧入口

**Decision**：在 `tests/differential/spec_builder.py` **新增**：

```python
def build_model_graph_spec(
    *,
    name: str,
    schema: Mapping[str, tuple[Any, Callable[..., Any] | None]],
    nodes: Sequence[tuple[str, Callable[[dict], dict]]],
    initial_input: Mapping[str, Any],
    model_factory: Any,
    conditional_edges: Sequence[Any] = (),
) -> GraphSpec: ...
```

- 该入口**显式要求** `model_factory`（非空），用于**模型形状**的图规格；
- 既有 `build_graph_spec(...)` **保持**：`model_factory` 恒空；非空 ⇒ `GraphSpecError`；
- 差分夹具的 B5F2 纯本地测试（`test_a_non_empty_model_factory_is_an_explicit_failure`）**保持不变**；
- B25F1 的 `_b25f1_model_factory.py` 提供 `FakeModelFactory` / `make_fake_model`，供模型形状规格使用。

**证据**：

| 事实 | 证据 |
|---|---|
| B5F2 的纯本地拒绝逻辑 | `tests/differential/spec_builder.py:128-131`（`model_factory` 非空 ⇒ `GraphSpecError`） |
| B5F2 的显式失败测试 | `tests/differential/test_differential.py:111-119` |
| B5F2 的承接口径 | `specs/b5f2-sparse-state-read/spec.md` FR-036 / 裁定 26 |
| 本 feature 的承接条款 | spec H-10（FR-001 / FR-018 / SC-006） |

**Rationale**：B5F2 的契约是「纯本地规格的 `model_factory` **恒空**」；B25F1 需要「模型形状规格」。
用**新入口**区分两种规格形状，既满足 B25F1，又不回改 B5F2 的判据（宪法「只接线 · 不放宽」）。

**Alternatives considered**：
- **放宽 `validate_graph_spec`** —— 直接破坏 B5F2 的纯本地契约，既有测试必红。
- **在 B5F2 的测试里特判 B25F1** —— 把跨 feature 逻辑塞进上游测试，难维护且违反「只接线」。

---

## D-06 · `diagnostics.py`：三组用例与 API 形态

**Decision**：新增 `harness/demo/diagnostics.py`（`freegraph` + 标准库），三组用例：

1. **trace**
   - `FileTraceStore(directory=tmp)` + `compile(tracer=store)` → 运行最小图；
   - 断言 `trace-<run_id>.jsonl` 存在；含 `kind="span"` 与 `kind="trace_record"` 行；
   - `SqliteTraceStore(database=tmp)` + 同图 → `query()` 四类过滤（`run_id` / `thread_id` /
     `node` / 时间窗）+ 组合 + 空过滤器，结果条数与 `json.dumps` 可序列化。
2. **checkpoint**
   - `MemorySaver()` / `SqliteSaver.from_conn_string(tmp)`；
   - `get_tuple` / `get_state` / `get_state_history` / `stream(stream_mode="checkpoints")`；
   - 断言持久化往返、历史数量 / 倒序、`tasks` / `interrupts` 形状。
3. **时间旅行**
   - 从历史快照 `invoke(None, snapshot.config)` 重放；
   - `update_state(config, values, as_node=...)` 覆盖 / 归约；
   - 分叉后原历史不变；
   - 中断组合（`interrupt` / `resume` + 历史）。

**证据**：

| 事实 | 证据 |
|---|---|
| 验收脚本的补齐约定 | `harness/demo/README.md:107-126`（诊断脚本待 M3 形态锁定后补齐） |
| `compile(tracer=...)` | `specs/b19f1-tracesink-current-span/spec.md` §「注入点形态裁定」 |
| `FileTraceStore(directory=...)` | `specs/b20f1-local-trace-jsonl/spec.md` §「形态锁定裁定」 |
| `SqliteTraceStore(database=...)` + `query()` | `specs/b20f2-trace-query-sqlite/spec.md` §「形态锁定裁定」 |
| `MemorySaver` 模块路径 | `specs/b14f1-checkpointer-memory-saver/spec.md` |
| `update_state` 签名 | `specs/b16f1-update-state-time-travel/spec.md` 裁定 1 |
| `SqliteSaver.from_conn_string` | `specs/b15f1-sqlite-saver-state-history/spec.md` 裁定 2 |
| `OtlpExporter` 注入形态 | `specs/b21f1-otlp-export/spec.md`（本文件的 diagnostics 不强制 OTLP；OTLP 归真实轮） |

**Rationale**：这些形态已在 M3 各 feature 锁定；现在补齐脚本不再「赌接口」。
`diagnostics.py` 只做**本地可诊断**子集，不引入第三方依赖，符合 demo 脚本约束。

**Alternatives considered**：
- **把 OTLP 也放进 diagnostics** —— OTLP 需要额外依赖 / 接收端，且真实轮已覆盖；放进 demo 会破坏
  「demo 只依赖 freegraph + 标准库」的约束。
- **只写 trace，不写 checkpoint / 时间旅行** —— 无法覆盖 M3 的三类可诊断性。

---

## D-07 · 真实轮两段式：固定脚本段 + 专用探针段

**Decision**：

- **段 1（固定脚本）**：`target.py` **原样**执行（真实模型）；记录实际输出、PNG 字节、
  框架出站 = 0、用户出站逐条；
- **段 2（专用探针）**：`real_round.py` 用同一 agent 循环形状 + **真实模型**搭图，编译时注入：
  - `FileTraceStore(directory=...)` → JSONL 证据（**独立运行 1**）；
  - `SqliteTraceStore(database=...)` → 同一 `query()` 语义证据（**独立运行 2**）；
    两次都使用 `RunConfig(thread_id="b25f1-real")` 并捕获 `run_id` / 起止时间，以覆盖四类过滤；
  - `OtlpExporter(exporter=RecordingSpanExporter())`（默认，记录型 exporter，无网络；类定义在
    `real_round.py`）或 `OtlpExporter(endpoint=local_grpc)`（可选，本地接收端）→ span 证据；
  - `SqliteSaver.from_conn_string(path)` + `RunConfig(thread_id=...)` → `get_tuple` / `get_state` /
    `get_state_history` / `stream(checkpoints)`；
  - `update_state` + `invoke(None, config)` → 重放 / 分叉 / 原历史不变 / 中断组合。
- **不修改 `target.py`**；**不猴补** `compile` / `invoke` 把组件塞进段 1。

**证据**：

| 事实 | 证据 |
|---|---|
| 固定脚本的编译点 | `harness/demo/target.py:158`（`agent = agent_builder.compile()`） |
| 固定脚本的调用点 | `harness/demo/target.py:168`（`messages = agent.invoke({"messages": messages})`） |
| B20F1 / B20F2 的一键验收已有本地 trace 证据 | `harness/verification/B20F1/acceptance.py` · `harness/verification/B20F2/acceptance.py` |
| B21F1 的 OTLP 验收已有 `exporter=` / 桩接收端模式 | `harness/verification/B21F1/acceptance.py` |
| B15F1 / B16F1 的 checkpoint / 时间旅行验收 | `harness/verification/B15F1/acceptance.py` · `harness/verification/B16F1/acceptance.py` |
| 真实模型轮的承接条款 | spec H-2…H-9（FR-012…FR-017） |

**Rationale**：固定脚本必须原样；观测 / 持久化需要额外图实例。两段式既保持固定脚本的
「只读基准」证据，又能把 B15/B16/B20/B21 的组件证据做全，且真实调用次数可控。

**Alternatives considered**：
- **全塞进固定脚本**（猴补 `compile` / `invoke`）—— 与「原样跑」冲突；spec 明确禁止。
- **每组件独立真实调用** —— 成本高、证据碎片化；两段式已能覆盖全部承接条款。

---

## D-08 · 断网等价性：进程内 + OS 级

**Decision**：

- **进程内层（必做）**：`test_b25f1_offline_equivalence.py` 在进程内把
  `socket.socket.connect` / `socket.create_connection` 替换为**抛异常**，运行：
  - fake 轮（`fake_round.run_fake_round()`）；
  - `diagnostics` 的核心函数（trace / checkpoint / 时间旅行）；
  - 最小 freegraph 图；
  ⇒ 断言全部通过（不需要网络）。
- **OS 级（条件增强）**：复用既有 **G28**（CI 在 `unshare --net --map-root-user` 下跑全量
  `tests/`）；B25F1 不新增门禁编号、不另起脚本。
- **真实轮**是 `harness/verification/B25F1/real_round.py` 人工脚本，**不进 `tests/`**
  ⇒ 不触发 G28 的断网假红，也不需要新增排除项。

**证据**：

| 事实 | 证据 |
|---|---|
| 既有 G28 已用网络命名空间跑全量测试 | `harness/scripts/gates/gate_G28_offline_equiv.py` + `.github/workflows/ci.yml` 的 G28 步 |
| G28 的排除清单是单文件权威 | `tests/gates/data/offline_exclusions.txt` |
| G27 已有零出站动态断言 | `harness/scripts/gates/gate_G27_zero_egress.py` |
| spec 的断网口径 | FR-005（进程内必做 + OS 级条件增强） |

**Rationale**：进程内层可移植、无特权；OS 级已有 CI 载体，不必重复造。
真实轮移出 `tests/` 避免 G28 / G27 与人工网络调用冲突。

**Alternatives considered**：
- **只做 OS 级** —— Windows / macOS 无法跑，且需要特权。
- **把真实轮放进 `tests/` 再加排除项** —— 可行但会把人工轮变成测试套件的常驻成员，
  且容易在 CI 无凭据时产生 skip / 环境噪声。

---

## D-09 · CI 依赖组：新增 `acceptance`

**Decision**：在 `pyproject.toml` 新增 PEP 735 依赖组：

```toml
acceptance = [
  "langchain>=1.0,<2",
  "IPython>=8",
]
```

- **不是 extra** ⇒ 不进 `Requires-Dist`；基础安装闭包仍为空。
- CI 在 **Linux 全量档**（`ubuntu-24.04` 的 3.11 / 3.14）安装：
  `uv pip install --python .venv --group acceptance`（在「Run test suite」之前）。
- 其余档（macOS / Windows / arm64）不装 ⇒ B25F1 的 fake 测试用 `pytest.importorskip("langchain")`
  / `pytest.importorskip("IPython")` ⇒ **skip（非失败）**。
- 差分组已含 `langgraph==1.2.11`；`acceptance` 组不重复声明（若需要，CI 同档已装）。

**证据**：

| 事实 | 证据 |
|---|---|
| `target.py` 自身依赖 `langchain.*` / `IPython` | `harness/demo/target.py:22-23` · `:161` |
| 既有 `differential` 组的安装模式 | `pyproject.toml` 的 `[dependency-groups] differential` + `ci.yml` 步骤 5.6 |
| G21 / G23 只扫描发行依赖 | `harness/scripts/gates/gate_G21_dependencies.py`（`Requires-Dist`）；G23 同 |
| B5F2 的「未装 differential 组 ⇒ skip」先例 | `tests/differential/conftest.py` |

**Rationale**：测试侧依赖不进发行包，符合零依赖承诺；Linux 全量档保证 fake 轮真实执行，
其余档 skip 与非失败符合既有差分纪律。

**Alternatives considered**：
- **把 `langchain` 加入运行时 `dependencies`** —— 直接违反宪法原则 I / II / IX。
- **把 `langchain` 加入 `differential` 组** —— 语义混淆；`differential` 是「上游比对」，
  `acceptance` 是「固定脚本验收」，分开更清晰。

---

## D-10 · 一键验收与人工记录

**Decision**：

- `harness/verification/B25F1/acceptance.py`：
  - 默认：A1（fake 轮）/ A3（零出站）/ A4（四组，含 diagnostics）/ A5（双重基线）；
  - `--real`：额外跑 A2（真实轮两段式）；
  - `--skip-real`：显式跳过 A2（CI 用）；
  - `--record <path>`：生成《人工验收记录》草稿（五要素 + 三附件占位 / 实测输出）；
  - 退出码 `0 = PASS` / `1 = 断言失败` / `2 = 环境未就绪`；
  - 最后一行 MUST 打印 `B25F1 acceptance: PASS|FAIL`。
- `tests/runtime/test_b25f1_acceptance.py`：跑 `--skip-real`；`rc == 2` ⇒ `pytest.skip`（环境未就绪）。
- `tests/runtime/test_b25f1_manual_record_guard.py`：断言记录存在、五段式、正文非空、
  三附件齐备、含 B15/B16/B20/B21/B23/B24 的非空实测证据、含 **Y-01**、遗留问题非空。
- 记录中的「真实轮」MUST 引用 `real_round.py` 的实际输出；MUST NOT 用「符合预期」替代。

**证据**：

| 事实 | 证据 |
|---|---|
| 既有 acceptance 脚本的退出码 / 末行约定 | `harness/verification/B21F1/acceptance.py` 模块 docstring |
| 既有记录守卫模式 | `tests/runtime/test_b24f1_manual_record_guard.py`（B24F1） |
| demo 记录的五个段落 | `harness/demo/acceptance.py:build_record`（环境 / 步骤 / 实际输出 / 结论 / 遗留问题） |
| 真实轮承接 | spec FR-008 / FR-012 / SC-004 |

**Rationale**：CI 不能依赖真实模型凭据，因此 A2 必须可显式跳过；但人工记录守卫保证
**宣布完成前** A2 已真实执行。这既满足「双跑都要过」，又不把凭据塞进 CI。
**守卫顺序（宪法 v1.13.0）**：记录未收口 / 仅有环境偏离时 T019 守卫 `skip`（不判失败，避免永久红 CI）；
**T052 的严格模式仅在发布 / 人工门禁执行**（T051 记录收口后）。T034 / T048 的 G28 / 全量 pytest
可在 skip 状态先跑，最终发布判定以 T052 为准。

**Alternatives considered**：
- **CI 直接跑真实模型** —— 需要凭据 / 网络 / 成本；且违反「人工验收」原则 V 的分工。
- **不设记录守卫** —— 容易把「自动验收通过」冒充人工验收。

---

## D-11 · 文档：迁移说明三类 + README 唯一权威指针

**Decision**：

- `harness/proposals/更名与迁移说明.md` 新增 **v1 迁移章节**：
  - **同名直接可用**：`StateGraph` / `START` / `END` / `add_node` / `add_edge` /
    `add_conditional_edges` / `compile` / `invoke`；
  - **同名但行为有差异**：`get_graph(...).draw_mermaid_png()`（v1 占位 PNG）、
    `Command.goto` 缺省值 **Y-01**（上游 `()` vs freegraph `None`）、
    `get_state` 无快照（上游空 `StateSnapshot` vs freegraph `None`，Y-02）、
    `Send` 不可变（Y-03）；
  - **需改写**：`init_chat_model` / `@tool` / `ToolMessage` 等属 `langchain` 层，
    freegraph 只原样承载（不是替代 `langchain`）；
  - 逐符号细节统一指向 `COMPAT.md`（**不复制矩阵**）。
- `README.md` 最终收口：
  - 快速上手（安装、最小图、`[otlp]`、fake / 真实轮入口）；
  - 三条对外承诺；能力处置表；独立实现声明；
  - **绝对链接** `https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`；
  - **不复制**完整兼容矩阵。
- `harness/demo/README.md`：标记 diagnostics 已交付；补双跑与 `harness/demo/acceptance.py` 新组说明。

**证据**：

| 事实 | 证据 |
|---|---|
| B24F1 已把矩阵迁到 `COMPAT.md` | `COMPAT.md`（2026-11-24）· `specs/b24f1-packaging-compat-matrix/spec.md` Clarifications |
| Y-01 / Y-02 / Y-03 | `COMPAT.md` 的 `Command` / `get_state` / `Send` 行 |
| README 现有状态说明 | `README.md:1-40`（B24F1 已修正） |
| 迁移说明现有章节 | `harness/proposals/更名与迁移说明.md` §1–§6 |
| demo README 的补齐约定 | `harness/demo/README.md:107-126` |

**Rationale**：`COMPAT.md` 是唯一权威；README / 迁移说明只做摘要与链接，避免第二份矩阵漂移。
**diagnostics 口径**：`diagnostics.py` 是 M3 可诊断性的**额外验收脚本**；立项书 / README 的
「四组」定义 = `graph_core` / `agent_loop` / `visualization` / `diagnostics`（diagnostics 为第四组）；`harness/demo/acceptance.py` 是编排器；此后统一使用本定义。

**Alternatives considered**：
- **在 README 重新放完整矩阵** —— 直接违反 B24F1 的结构与宪法原则 XII。
- **迁移说明另建新文件** —— 用户要求落在既有 `更名与迁移说明.md`；且该文件已是迁移主入口。

---

## D-12 · 证据纪律：实测输出非空、环境偏离可追溯

**Decision**：

- 所有实测证据 MUST 是**可复核的具体值**：
  - fake 轮：`messages` 长度 / `llm_calls` / 工具结果 / 最终消息 / PNG 字节数 / 框架出站计数；
  - 真实轮：模型标识 / 端点 / 接入路径 / 最终消息 / 工具结果 / 用户出站逐条 / 框架出站 0；
  - trace：文件数 / `kind="span"` 行 / `kind="trace_record"` 行 / `query()` 条数 + `json.dumps`；
  - OTLP：span 数 / `name` / `trace_id` / `parent` / `gen_ai.*`；
  - checkpoint：`get_tuple` / `get_state` / 历史数量 / 倒序 / `tasks` / `interrupts` / 事件数；
- **MUST NOT** 用「符合预期」「正常」「未验证」替代实测；
- 环境受限时 MUST 写「环境偏离」：已完成 / 未完成范围、原因、仍可判定的部分；
- 遗留问题逐条列出，带来源。

**证据**：

| 事实 | 证据 |
|---|---|
| 宪法原则 V（人工验收是最终标准） | `.specify/memory/constitution.md` 原则 V |
| 宪法原则 VIII（证据与术语纪律） | 同上 |
| B20F1 / B20F2 / B21F1 / B24F1 的记录先例 | `harness/verification/B20F1/manual-verification.md` 等 |
| spec 的证据门禁 | FR-008 / FR-012 / SC-004 |

**Rationale**：本 feature 的判定是「双跑通过 + 框架零出站」，没有具体输出就无法复核；
环境偏离是允许的，但必须可追溯，避免「未验证」混过。

**Alternatives considered**：
- **只写结论、不写输出** —— 违反证据门禁，且无法区分「真实跑过」与「声称跑过」。

---

## 研究结论汇总

| # | 决策 | 影响 |
|---|---|---|
| D-01 | 同进程猴补 + 子进程 `sitecustomize` | FR-001 / A1 |
| D-02 | `messages == 4` | FR-003 / A1 |
| D-03 | 复用 G27 `_gatekit` 归因 | FR-004 / A3 |
| D-04 | SHA-256 + 基线 ref diff | FR-011 / A5 |
| D-05 | 新增 `build_model_graph_spec` | FR-018 / SC-006 |
| D-06 | diagnostics 三组 | FR-006 / SC-003 |
| D-07 | 真实轮两段式 | FR-012…FR-017 / A2 |
| D-08 | 进程内 + OS 级断网 | FR-005 |
| D-09 | 新增 `acceptance` 依赖组 | FR-001 / CI |
| D-10 | 一键验收 + 记录守卫 | FR-007 / FR-008 |
| D-11 | 迁移说明 + README | FR-009 / FR-010 |
| D-12 | 实测证据 + 环境偏离 | FR-008 / FR-012 / SC-004 |

**无未决澄清。**
