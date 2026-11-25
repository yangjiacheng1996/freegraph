# Quickstart: B25F1 验收手册

**Feature**: B25F1 · **Date**: 2026-11-25 · **Spec**: [spec.md](./spec.md)

> 本手册只列**可执行验证**；实现细节见 [plan.md](./plan.md) 与
> [contracts/](./contracts/)。所有命令在仓库根执行。

---

## 0. 前置

- Linux / macOS / Windows · Python ≥ 3.11
- `uv`（既有 CI 已钉版本）
- 安装（**测试侧依赖不进发行包**）：

```bash
uv venv --python 3.11
uv pip install --python .venv --group dev
uv pip install --python .venv --group differential
uv pip install --python .venv --group acceptance
uv pip install --python .venv -e .
# 真实轮若使用 OTLP 探针（endpoint= 或 exporter=），再装 [otlp]
uv pip install --python .venv -e ".[otlp]"
```

> `acceptance` 组 = `langchain` + `IPython`（固定脚本自身依赖）。
> 没有该组时，fake 轮测试 `skip`（非失败）；CI 的 Linux 全量档会安装。
> `[otlp]` 只在真实轮的 OTLP 探针需要；不影响基础安装的零依赖闭包。

---

## 1. fake 轮（A1）

```bash
.venv/bin/python harness/verification/B25F1/fake_round.py
echo $?
```

**期望**：

- 退出码 `0`；
- 输出末行 `B25F1 fake round: PASS`；
- 断言点：`messages == 4`、`llm_calls == 2`、工具结果 `== 7`（`ToolMessage.content` 归一为 int）、状态含两键；
- `draw_mermaid_png()` 返回合法 PNG 字节；框架出站 `0`；用户出站逐条记录；
- `target.py` 零改动。

**外部注入等价轮**（同一脚本的 `--subprocess` 模式）：

```bash
.venv/bin/python harness/verification/B25F1/fake_round.py --subprocess
```

**期望**：子进程通过临时 `sitecustomize.py` 注入，退出码 `0`；证明「不改 `target.py` 也能注入」。

---

## 2. 固定脚本防御（A5）

```bash
.venv/bin/python -m pytest tests/runtime/test_b25f1_target_guard.py -q
```

**期望**：

- `test_target_py_matches_recorded_sha256` PASS；
- `test_target_py_matches_baseline_ref` PASS；若基线 ref 不可用 ⇒ **skip 且理由明确**
  （SHA-256 仍须 PASS）。

**手工核对**：

```bash
sha256sum harness/demo/target.py
cat tests/runtime/data/b25f1_target_py.sha256
git diff origin/main -- harness/demo/target.py
```

**期望**：哈希一致；`git diff` 为空。

---

## 3. 四组（含 diagnostics）（A4）

```bash
.venv/bin/python harness/demo/acceptance.py
echo $?
```

**期望**：

- `graph_core.py` / `agent_loop.py` / `visualization.py` / `diagnostics.py` 全部退出码 `0`；
- `harness/demo/acceptance.py` 自身检查（前置自检 / 最小图 / 零出站）PASS；
- 末行总体退出码 `0`。

**只跑 diagnostics**：

```bash
.venv/bin/python harness/demo/diagnostics.py
```

**期望**：`diagnostics: PASS`；覆盖 trace（JSONL / SQLite + `query()`）/ checkpoint
（`MemorySaver` / `SqliteSaver` + 历史）/ 时间旅行（重放 / 分叉 / 中断组合）。

---

## 4. B25F1 一键验收（CI 用）

```bash
.venv/bin/python harness/verification/B25F1/acceptance.py --skip-real
echo $?
```

**期望**：

- 退出码 `0`；
- 末行 `B25F1 acceptance: PASS`；
- 覆盖 `DEP` / `A1` / `A3` / `A4` / `A5`；
- 环境未就绪（缺依赖）⇒ 退出码 `2`（不是 `1`）。

**生成记录草稿**：

```bash
.venv/bin/python harness/verification/B25F1/acceptance.py --skip-real \
  --record /tmp/opencode/b25f1-acceptance-draft.md
```

> 生成的草稿再**合并**进 `harness/verification/B25F1/manual-verification.md`；
> **MUST NOT** 直接覆盖已含真实轮证据的记录。`--skip-real` 生成的记录中，A2 为
> 「待人工轮填写」；**不得**据此宣布完成。

---

## 5. 真实模型轮（A2 · 人工）

### 5.1 环境

```bash
# 清空 LangSmith 环境变量（三轮验收都必须）
unset LANGSMITH_API_KEY LANGSMITH_TRACING LANGSMITH_ENDPOINT LANGSMITH_PROJECT
env | grep '^LANGSMITH_' || echo "LANGSMITH_* = 0"
```

接入方式（二选一，记录实际路径）：

- **官方直连**（优先）：配置 provider 官方 SDK 的凭据（如 `ANTHROPIC_API_KEY`）；
- **兼容网关**（受限时）：配置网关 `base_url` + key；`real_round.py` 会**外部包装**
  `init_chat_model` 仅做接线（不改 `target.py`）；记录写明「网关」与原因。

### 5.2 运行

```bash
.venv/bin/python harness/verification/B25F1/real_round.py --record \
  /tmp/opencode/b25f1-real-round-draft.md
```

> 真实轮草稿再**合并**进 `harness/verification/B25F1/manual-verification.md`；
> **MUST NOT** 直接覆盖已有人工记录。

**两段式**：

1. **固定脚本段**：原样跑 `target.py`；记录最终消息 / 工具结果 / PNG 字节 / 框架出站 0 /
   用户出站逐条；
2. **专用探针段**：
   - `FileTraceStore(directory=tmp)` → JSONL 证据（**独立运行 1**）；
   - `SqliteTraceStore(database=tmp)` → `query()` 四类过滤 / 组合 / 空过滤器（**独立运行 2**）；
     两次都使用 `RunConfig(thread_id="b25f1-real")` 并捕获 `run_id` / 起止时间；
   - `OtlpExporter(exporter=RecordingSpanExporter())`（默认；`RecordingSpanExporter` 在
     `real_round.py` 内定义，记录到内存、无网络）或 `OtlpExporter(endpoint=local_grpc)`
     （可选，本地接收端）→ span 证据；
   - `SqliteSaver.from_conn_string(tmp)` → `get_tuple` / `get_state` / `get_state_history` /
     `stream(checkpoints)`；
   - `update_state` + `invoke(None, snapshot.config)` → 重放 / 分叉 / 原历史不变 / 中断组合。

**期望**：实际输出非空；框架出站 `0`；用户出站逐条；所有承接证据写入记录。

> 凭据 / 网络受限 ⇒ 记录**环境偏离**（已完成 / 未完成 / 原因）；**MUST NOT** 写「未验证」。
> 真实轮完全无法执行 ⇒ **不得宣布 v1.0 收口**（A2 硬判据）。

---

## 6. 断网等价性（FR-005）

### 6.1 进程内层（必做）

```bash
.venv/bin/python -m pytest tests/runtime/test_b25f1_offline_equivalence.py -q
```

**期望**：PASS；fake 轮 + diagnostics 核心用例在 socket 禁用时全绿。

### 6.2 OS 级（Linux · 条件增强）

```bash
sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 2>/dev/null || true
unshare --net --map-root-user .venv/bin/python harness/scripts/gates/gate_G28_offline_equiv.py
echo $?
```

**期望**：`0`；不具备 `unshare` ⇒ 记录环境偏离（不判失败）。

---

## 7. 依赖断言 + 反向断言（DEP）

```bash
# 发行元数据：基础依赖为空；唯一 extra = otlp
.venv/bin/python - <<'PY'
import importlib.metadata as m
meta = m.metadata("freegraph")
print([r for r in meta.get_all("Requires-Dist") or []])
print(meta.get_all("Provides-Extra"))
PY

# 反向断言：运行时 sys.modules 无 langchain / langchain_core
.venv/bin/python - <<'PY'
import sys
import freegraph
bad = [n for n in sys.modules if n == "langchain" or n.startswith("langchain.") or n == "langchain_core" or n.startswith("langchain_core.")]
print("langchain modules:", bad)
assert not bad
PY
```

**期望**：基础 `Requires-Dist` 为空（或只有 `typing-extensions` 之外的**无**）；
`Provides-Extra` 只有 `otlp`；反向断言列表为空。

**注意**：在安装了 `acceptance` 组的同一 venv 中，`sys.modules` 反向断言必须在**未导入
`langchain`** 的干净进程里执行；`freegraph` 自身不得拉起 `langchain`。

---

## 8. 文档核对

```bash
# README：绝对 COMPAT 链接、无完整矩阵
grep -n "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md" README.md
grep -c '^| `' README.md   # 应远小于完整矩阵行数（能力表不是逐符号矩阵）

# 迁移说明：三类 + Y-01
grep -n "同名直接可用\|同名但行为有差异\|需改写\|Y-01\|Command.goto" harness/proposals/更名与迁移说明.md
```

**期望**：README 有绝对链接；迁移说明含三类与 Y-01。

---

## 9. CI 接线

`.github/workflows/ci.yml` MUST 包含：

1. `actions/checkout@v7` 的 `fetch-depth: 0`；
2. Linux 全量档安装 `--group acceptance`（在「Run test suite」之前）；
3. 一个 B25F1 验收步：

```bash
uv run --no-project --python .venv python harness/verification/B25F1/acceptance.py --skip-real
```

**期望**：退出码 `0`；job 名不变（分支保护不受影响）。

---

## 10. 完成判定（人工）

- [ ] A1 fake 轮 PASS（四条断言点）
- [ ] A2 真实轮 PASS（两段式 + 实际输出）
- [ ] A3 框架出站 = 0（用户出站逐条记录）
- [ ] A4 四组（含 diagnostics）全绿
- [ ] A5 双重基线 PASS
- [ ] SC-001…SC-006 全部满足
- [ ] 人工记录五要素 + 三附件
- [ ] 发布前清单已纳入 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
  `harness/verification/B14F1/acceptance.py`（只引用、不回改）
- [ ] 迁移说明 + README 收口
- [ ] **真实轮未完成 ⇒ 不得宣布 v1.0 收口**
