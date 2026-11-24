# Quickstart: B24F1 验收手册

**Feature**: B24F1 · **Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md)

> 本手册只列**可执行验证**；实现细节见 [plan.md](./plan.md) 与
> [contracts/](./contracts/)。所有命令在仓库根执行。

---

## 0. 前置

- Linux / macOS / Windows · Python ≥ 3.11
- `uv`（既有 CI 已钉版本）
- 已装 dev 组（`pytest` / `packaging`，供测试与 G23 等开发门禁使用；**纯度脚本本身不依赖 `packaging`**）；真实差分需 `differential` 组（可选）

```bash
uv venv --python 3.11
uv pip install --python .venv --group dev
uv pip install --python .venv -e .
```

---

## 1. 发行包就绪（SC-001 / SC-005 / SC-006）

### 1.1 构建

```bash
rm -rf dist
uv build
ls dist/
```

**期望**：产出 `freegraph-0.0.x-py3-none-any.whl` 与 `freegraph-0.0.x.tar.gz`。

### 1.2 基础安装（隔离环境）

```bash
python3 -m venv /tmp/fg-base
/tmp/fg-base/bin/python -m pip install --no-index --find-links dist freegraph
/tmp/fg-base/bin/python -c "import freegraph; print(freegraph.__version__)"
/tmp/fg-base/bin/python -m pip freeze
```

**期望**：

- `import freegraph` 成功；
- `pip freeze` 只有 `freegraph`（及 `pip` 自身）；无第三方运行时依赖。

### 1.3 `[otlp]` 安装

```bash
python3 -m venv /tmp/fg-otlp
/tmp/fg-otlp/bin/python -m pip install --no-index --find-links dist "freegraph[otlp]"
/tmp/fg-otlp/bin/python -m pip freeze
```

**期望**：

- 安装成功；
- 列表**没有** `certifi` / `requests` / `opentelemetry-exporter-otlp`（元包）/ HTTP exporter。

> 若本机无 `[otlp]` 依赖的离线 wheel，可联网安装，或使用具备网络 / uv-PIP 缓存的 CI Linux 作业取证；
> **不得假设 CI `.venv` 已装的 extras 会被新建隔离 venv 继承**。记录实际命令、环境、`[otlp]`
> 依赖来源与（若引用 CI）作业名 / 运行标识。

---

## 2. 纯度门禁（SC-002 / SC-003）

### 2.1 正向

```bash
python3 harness/scripts/check_dist_purity.py dist/
echo $?
```

**期望**：每个产物打印「仅含包代码与必要元数据」，退出码 `0`。

### 2.2 负向（合成产物，不污染真实 `dist/`）

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/dist"
cp dist/*.whl "$tmp/dist/"
cp dist/*.tar.gz "$tmp/dist/"
# 人为把一个仓库文件塞进 sdist（示例：重新打包）
python3 - "$tmp/dist" <<'PY'
import sys, tarfile, io, pathlib
dist = pathlib.Path(sys.argv[1])
sdist = next(dist.glob("*.tar.gz"))
import shutil
tmp = dist / "poisoned.tar.gz"
with tarfile.open(sdist) as src, tarfile.open(tmp, "w:gz") as dst:
    for m in src.getmembers():
        dst.addfile(m, src.extractfile(m))
    data = b"# harness report\n"
    info = tarfile.TarInfo("freegraph-0.0.x/harness/report.md")
    info.size = len(data)
    dst.addfile(info, io.BytesIO(data))
print(tmp)
PY
python3 harness/scripts/check_dist_purity.py "$tmp/dist"
echo $?
```

**期望**：退出码 `1`，输出指名 `harness/report.md` 并含「拒绝发布」。

### 2.3 额外产物类型（负向）

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/dist"
cp dist/*.whl "$tmp/dist/"
cp dist/*.tar.gz "$tmp/dist/"
printf 'poison' > "$tmp/dist/evil.zip"
python3 harness/scripts/check_dist_purity.py "$tmp/dist"
echo $?
```

**期望**：退出码 `1`（`dist/` 内**归档类**非 `.whl` / `.tar.gz` 文件不得被静默忽略）。

> `uv build` 会在 `dist/` 生成 `.gitignore`；真实 `dist/` 上运行时应仍为 `0`——该标记不是额外产物。

**补充（wheel 根级非法前缀）**：在临时 wheel 的**根级**注入 `freegraph-evil.txt`
⇒ 退出码 `1`；wheel 根级只允许 `freegraph/` 与 `freegraph-*.dist-info/`，
`freegraph-` 前缀本身不构成合法豁免（T045）。

### 2.3b sdist 含 `.gitignore`（负向）

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/dist"
cp dist/*.whl "$tmp/dist/"
cp dist/*.tar.gz "$tmp/dist/"
python3 - "$tmp/dist" <<'PY'
import sys, tarfile, io, pathlib
dist = pathlib.Path(sys.argv[1])
sdist = next(dist.glob("*.tar.gz"))
tmp = dist / "with-gitignore.tar.gz"
with tarfile.open(sdist) as src, tarfile.open(tmp, "w:gz") as dst:
    for m in src.getmembers():
        dst.addfile(m, src.extractfile(m))
    data = b"dist/\n"
    info = tarfile.TarInfo("freegraph-0.0.x/.gitignore")
    info.size = len(data)
    dst.addfile(info, io.BytesIO(data))
print(tmp)
PY
python3 harness/scripts/check_dist_purity.py "$tmp/dist"
echo $?
```

**期望**：退出码 `1`（`.gitignore` 不属于 Release Gate 的必要元数据）。

### 2.4 空目录

```bash
empty=$(mktemp -d)
python3 harness/scripts/check_dist_purity.py "$empty"
echo $?
```

**期望**：退出码 `2`。

### 2.5 发布流水线顺序

```bash
python3 - <<'PY'
import pathlib, re
text = pathlib.Path(".github/workflows/publish.yml").read_text(encoding="utf-8")
build = text.index("name: Build")
purity = text.index("Verify artifact purity")
publish = text.index("Publish to PyPI")
assert build < purity < publish, (build, purity, publish)
assert "check_dist_purity.py" in text[purity:publish]
print("order OK")
PY
```

**期望**：`order OK`。

---

## 3. 兼容矩阵与归属（SC-004）

### 3.1 `COMPAT.md` 结构

```bash
python3 - <<'PY'
import pathlib
text = pathlib.Path("COMPAT.md").read_text(encoding="utf-8")
for heading in [
    "## API 兼容矩阵",
    "## 18 项覆盖表",
    "## 下游承接行",
    "## 证据与来源",
    "## 维护规则",
]:
    assert heading in text, heading
assert "不构成 affiliation" in text
# affiliation 必须在机读段内（G8 / G29 的段内断言）
machine = text.split("## API 兼容矩阵", 1)[1].split("\n## ", 1)[0]
assert "不构成 affiliation" in machine, "affiliation 不在机读段内"
print("sections OK")
PY
```

### 3.2 18 项

```bash
python3 - <<'PY'
import re, pathlib
text = pathlib.Path("COMPAT.md").read_text(encoding="utf-8")
section = re.search(r"^## 18 项覆盖表\s*$(.*?)(?=^## |\Z)", text, re.S | re.M).group(1)
rows = [l for l in section.splitlines() if re.match(r"^\|\s*\d+\s*\|", l)]
assert len(rows) == 18, len(rows)
assert [int(re.match(r"^\|\s*(\d+)", r).group(1)) for r in rows] == list(range(1, 19))
print("18 items OK")
PY
```

### 3.3 下游承接行

```bash
python3 - <<'PY'
import pathlib
text = pathlib.Path("COMPAT.md").read_text(encoding="utf-8")
for needle in [
    "多源汇合边", "MemorySaver", "InMemorySaver", "CheckpointTuple",
    "SqliteSaver", "get_state", "get_state_history", "update_state",
    "时间旅行", "OtlpExporter",
]:
    assert needle in text, needle
# 下游档位（按 B15F1 证据钉死）
downstream = text.split("## 下游承接行", 1)[1].split("\n## ", 1)[0]
for sym, degree in [
    ("SqliteSaver", "部分等价"),
    ("get_state", "部分等价"),
    ("get_state_history", "行为等价"),
    ("update_state", "部分等价"),
]:
    row = next(l for l in downstream.splitlines() if sym in l and l.strip().startswith("|"))
    assert degree in row, (sym, degree, row)
print("downstream rows OK")
PY
```

### 3.4 `Command` = 部分等价

```bash
python3 - <<'PY'
import pathlib
text = pathlib.Path("COMPAT.md").read_text(encoding="utf-8")
row = next(l for l in text.splitlines() if l.strip().startswith("| `Command` |"))
cells = [c.strip() for c in row.strip().split("|")[1:-1]]
assert cells[2] == "部分等价", cells
diff = cells[3]
assert "Y-01" in diff and "DIFF" in diff, diff
assert "X-06" in diff and "STRICTER" in diff, diff
assert "X-2" in diff and "X-3" in diff, diff
print("Command OK")
PY
```

### 3.4b H-2/H-3/H-4 / FR-018 / Store 关键措辞

```bash
python3 - <<'PY'
import pathlib
text = pathlib.Path("COMPAT.md").read_text(encoding="utf-8")
rows = {}
for line in text.splitlines():
    if line.strip().startswith("| `"):
        cells = [c.strip() for c in line.strip().split("|")[1:-1]]
        if cells:
            rows[cells[0].strip("`")] = cells
need = {
    "NodeFunc": ["命令列表", "Send", "list[Send]", "tuple[Send, ...]", "无上游同名协议"],
    "Send": ["fan-out", "运行期语义已落地", "不可变"],
    "StateGraph": ["interrupt_before", "interrupt_after", "recursion_limit"],
    "Graph": ["占位 PNG", "[png]"],
    "CompiledGraph": ["Y-02", "None", "StateSnapshot", "v1 能力边界"],
}
for sym, needles in need.items():
    assert sym in rows, sym
    joined = " | ".join(rows[sym])
    for n in needles:
        assert n in joined, (sym, n)
assert rows["NodeFunc"][2] == "不支持", rows["NodeFunc"]

# Store 的澄清在「证据与来源」，不得改动机读行
evidence = text.split("## 证据与来源", 1)[1].split("\n## ", 1)[0]
assert "Store" in evidence and "协议等价" in evidence and "v1 无实现" in evidence
print("H-2/H-3/H-4/FR-018/Store OK")
PY
```

### 3.4c 最小差分组（宪法原则 XI）

```bash
# 上游缺席时该组应 skip（不是失败）；本 feature 不改运行时
uv pip install --python .venv --group differential   # 可选：装上 langgraph 才能真跑
uv run --no-project --python .venv python -m pytest \
  tests/differential/test_b24f1_matrix_parity.py -q
```

**期望**：上游可用时 `B24F1-D-01…D-03` 通过（判词 DIFF）；上游缺席时标记 skip。
该组只断言 `COMPAT.md` 的 Y-01 / Y-02 / Y-03 既有差异，**不要求对齐运行时**。

### 3.5 README 指针与能力表

```bash
python3 - <<'PY'
import pathlib, re
readme = pathlib.Path("README.md").read_text(encoding="utf-8")
assert "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md" in readme
assert "## 能力 → freegraph 处置" in readme
assert "独立实现、非 LangChain Inc. 产品" in readme
assert "零第三方运行时依赖" in readme
assert "内核尚未实现" not in readme
assert "没有任何图运行时能力" not in readme
assert "请勿用于生产" not in readme
assert "请勿当作可用替代品" not in readme
assert "不要把它当作" not in readme
assert "31 个 feature" not in readme, "旧计数：应为 32 个 feature"
assert "93 人日" not in readme, "旧计数：应为 96 人日"
assert "契约层 20 个" not in readme, "旧计数：应为契约层 22 个（manifest 驱动）"
assert "契约层 18" not in readme, "旧计数：应为契约层 22 个（manifest 驱动）"
assert "契约层 21" not in readme, "旧计数：应为契约层 22 个（manifest 驱动）"
assert "门面 7" not in readme, "旧计数：应为门面 8 个（manifest 驱动）"
# 中文为主（FR-006 结构化判定）：除显式 English 段外，## 标题必须含中文
headings = re.findall(r"(?m)^##\s+(.+)$", readme)
english_headings = [h for h in headings if "English" in h]
assert english_headings, "缺少显式 ## English / ## English Summary 段"
for h in headings:
    if h in english_headings:
        continue
    assert re.search(r"[\u4e00-\u9fff]", h), f"非英文段标题应为中文：{h!r}"
for zh in ("独立实现声明", "零账号", "零出站", "零第三方运行时依赖"):
    assert zh in readme, zh
for backend in ("OpenLIT", "Langfuse", "Phoenix"):
    assert backend in readme, backend
assert "无默认推荐" in readme

# 能力处置表：5 列 + 8 行 + as-of
cap = re.search(r"^## 能力 → freegraph 处置\s*$(.*?)(?=^## |\Z)", readme, re.S | re.M).group(1)
header = [c.strip() for c in next(
    l for l in cap.splitlines() if l.strip().startswith("|") and "能力" in l
).strip().split("|")[1:-1]]
assert header == [
    "能力", "Developer $0", "Plus $39/seat/月", "Enterprise", "freegraph v1"
], header
cap_rows = [l for l in cap.splitlines() if l.strip().startswith("|") and not re.match(r"^\|[\s\-|:]+\|$", l.strip())]
cap_rows = [l for l in cap_rows if not ("能力" in l and "Developer" in l)]
assert len(cap_rows) == 8, len(cap_rows)
assert "2026-11-01" in cap or "as-of 2026-11-01" in cap

# README 的兼容矩阵章节不得含完整符号矩阵
section = re.search(r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", readme, re.S | re.M).group(1)
rows = [l for l in section.splitlines() if re.match(r"^\|\s*`[A-Za-z_]", l)]
assert rows == [], rows
print("README OK")
PY
```

### 3.6 归属清单

```bash
python3 - <<'PY'
import pathlib
text = pathlib.Path("THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
for needle in [
    "langgraph-checkpoint-sqlite", "MIT", "LangChain, Inc.",
    "opentelemetry-api", "opentelemetry-exporter-otlp-proto-grpc",
    "protobuf", "BSD-3-Clause", "不构成 affiliation", "COMPAT.md",
]:
    assert needle in text, needle
print("notices OK")
PY
```

---

## 4. 门禁迁移（G8 / G19 / G29）

```bash
uv run --no-project --python .venv python -m pytest \
  tests/contracts/test_architecture.py \
  tests/facade/test_facade_gates.py \
  tests/runtime/test_parse_contract.py \
  tests/contracts/test_b24f1_compat.py \
  tests/contracts/test_b24f1_docs.py \
  tests/contracts/test_b24f1_notices.py \
  tests/contracts/test_b24f1_packaging.py \
  tests/contracts/test_b24f1_otlp_meta.py \
  tests/contracts/test_b24f1_purity.py \
  tests/contracts/test_b24f1_purity_negative.py \
  tests/contracts/test_b24f1_publish_order.py \
  -ra

uv run --no-project --python .venv python \
  harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
```

**期望**：全部通过；G29 输出「**COMPAT.md 已覆盖契约 ∪ 门面 + Command = 部分等价 + README 仅指针**」
（或等价措辞），退出码 `0`。

> 迁移后 G8 / G19 / G29 与 `test_parse_contract.py` 的取行源均为 `COMPAT.md`；
> README 的 `## API 兼容矩阵` 章节只作指针。若 README 仍有完整矩阵，
> `test_b24f1_docs.py` 或 G29 应失败。

---

## 5. 全量质量门禁（可选但推荐）

```bash
uv run --no-project --python .venv python -m pytest tests/ -ra
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
uv run --no-project --python .venv python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
uv run --no-project --python .venv python harness/scripts/gates/gate_G26_network_static.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G30_attribution.py

# Linux only（隔离环境 / 零出站 / 断网等价）：
uv run --no-project --python .venv python harness/scripts/gates/gate_G22_isolated_env.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G27_zero_egress.py
unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py
```

**期望**：全绿；`src/freegraph/` 与 `harness/demo/target.py` 无 diff。
**非 Linux**：G22 / G27 / G28 标记为「环境未就绪」，由 CI 的 Linux 全量作业覆盖。

---

## 6. 人工验收

```bash
uv run --no-project --python .venv python harness/verification/B24F1/acceptance.py
```

按提示记录：

- 隔离安装的 `pip freeze` 实际输出；
- 纯度正向 / 负向的退出码与关键输出；**额外产物类型（`evil.zip`）负向退出码**；
- `[otlp]` 安装后的 `pip freeze`（确认无 `certifi` 等）；
- `COMPAT.md` 18 项 / 下游行 / `Command` 的核对结果（`goto` 缺省 = DIFF / Y-01；失败信号 = STRICTER / X-06；X-2 / X-3 异常类型差异）；
- **G8 / G19 / G29 取行源迁移 + `Command` 例外的发起者追认文字**（2026-11-24 · 选项 A）；
- **质量门禁 5 偏离（真实模型轮 → B25F1）+ 发起者追认 + B25F1 承接条款**；
- **B15F1 / B16F1 的人工验收证据（或链接）**；
- **Y-01（`Command.goto` 缺省 `()` vs `None`）**：既有 DIFF，**具名承接 B25F1（M4）**，运行时对齐归 v2；
  **Y-02（`get_state` 无快照 `None` vs 上游空 `StateSnapshot`）** 与 **Y-03（`Send` 不可变 vs 上游可变）**：
  既有 DIFF，只登记、运行时对齐归 v2；其他遗留问题与环境偏离。

→ 写入 `harness/verification/B24F1/manual-verification.md`（**实际输出**，不得只写「符合预期」）。

记录写就后运行**自动文档守卫**（宪法 v1.13.0）：

```bash
uv run --no-project --python .venv python -m pytest tests/runtime/test_b24f1_manual_record_guard.py -ra
```
