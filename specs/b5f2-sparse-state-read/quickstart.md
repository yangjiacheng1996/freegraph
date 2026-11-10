# Quickstart: B5F2 · 稀疏状态读取（C4 独立回归测试）+ 差分测试夹具

**Feature**: `B5F2` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**契约权威**: [contracts/read-contract.md](./contracts/read-contract.md) ·
[contracts/differential-fixture.md](./contracts/differential-fixture.md) ·
**上游对照**: [contracts/upstream-parity.md](./contracts/upstream-parity.md)

> **本手册是「怎么验证 B5F2 交付到位了」的**可照抄**手册** —— 每条命令都可直接复制执行，
> 每条命令后都写了**期望输出**（形态，而非逐字）。
> ⚠️ **编号约定**：本手册的验收闸口用 **`V1`–`V12`**（**不与**「验收判据 **A1**–**A5**」撞名）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（实测 · B3F1 的既有结论）
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --group dev

# ③ 本 feature 包（editable）
uv pip install -e .

# ④（**可选**）差分依赖组 —— 只有跑**差分夹具**才需要；缺席时夹具**自动 skip**
uv pip install --group differential
```

> ⚠️ **`langgraph` 只在第 ④ 步出现** ⇒ 基础安装与**基础 CI** 环境**零上游**（spec FR-018 / 裁定 5）。

### 0.2 两处「**上游不在场**」的正常情形

| 情形 | 现象 | 处置 |
|---|---|---|
| **隔离 / 未装 `differential` 组**的环境（**G22 的隔离 venv** / 开发者未装该组的 venv） | 差分夹具的用例被 **skip** | **正常**（FR-019 / 裁定 11）⇒ MUST NOT 判失败 |
| **CI 主测试作业**（**有** `differential` 组 · **步骤 5.6**） | 差分夹具**真实执行** | **必须**（SC-014）⇒ 避免「永远 skip ⇒ 假绿」 |

> ⚠️ **口径订正（2026-11-09 · clarify 第四轮 · 裁定 31）**：原表首行写「**基础 CI（无 `differential` 组）**」
> ⇒ **步骤 5.6 落地后已不成立**（CI 主测试环境的 venv **已含上游**）⇒ 改为「**隔离 / 未装该组**的环境」。
> ⚠️ **「哪些作业装该组」** = `ci-matrix` §2 步骤 5.6 行：**至少 1 个作业 MUST 执行**（实测通过的那档）·
> 其余作业 **MAY** 执行 ⇒ 装不上的档（3.14 / Windows / arm64）该组**不装** ⇒ 该档差分用例 **skip**
> （**非失败**）· MUST NOT 静默不跑（裁定 30 · 任务 **T035**）。

---

## 1. C4 · 稀疏状态读（**验收判据 A1 / A2** · SC-001 / SC-002）

```bash
# 只跑 C4 独立回归测试
pytest -q tests/runtime/test_read_c4_sparse_state.py
```

**期望**：**通过**（1 个用例）。该用例的断言**逐字**为：

```python
assert "llm_calls" not in node_input                    # A1（否定式）
assert node_input.get("llm_calls", 0) == 0              # A2（default 而非 None）
```

> ⚠️ **判定力度**：断言必须是**否定式**的 —— 若写成「节点入参包含所有 schema key」，
> 则**等于没有防线**（spec §10 的原话）。

**手工复核（不依赖测试）**：

```bash
python3 - <<'PY'
from freegraph.runtime import parse_state_schema, build_channels, read_channels
from typing import TypedDict
import operator
from typing import Annotated

class S(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

chs = build_channels(parse_state_schema(S))
chs["messages"].update([["hi"]])          # 只写 messages ⇒ llm_calls 仍「无值」
r = read_channels(chs)                     # 缺省 skip_empty=True
print(type(r) is dict, sorted(r), r.get("llm_calls", 0))
PY
```

**期望输出**：`True ['messages'] 0`
⇒ 「`llm_calls` 缺席」+「`.get(..., 0)` 返回 `0` 而非 `None`」+「结果是普通 `dict`」三条同时成立。

---

## 2. 挂载点接线（SC-015 / SC-025）

```bash
# 门禁 G29 会读这个标记；「status=landed」即「C4 已落地」
grep -n "GATE-MOUNT" tests/contracts/test_contract_regressions.py
```

**期望**：

```
28:# GATE-MOUNT: C4 · status=landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
29:# GATE-MOUNT: C8 · status=not-landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读
```

⇒ **C4 = `landed`**（本 feature）· **C8 = `not-landed`**（仍属 **B8F1** ⇒ MUST NOT 改动）。

```bash
# G2 门禁必须保持绿（tests/contracts/** 禁止 import freegraph.*）
pytest -q tests/contracts/test_architecture.py -k "internal_import"
```

**期望**：**通过** ⇒ 挂载点文件**没有** import `freegraph.runtime`（元测试只做路径扫描）。

---

## 3. 读取层的行为闸口（SC-003 / SC-004 / SC-027）

```bash
pytest -q tests/runtime/test_read_semantics.py
```

**期望**：**通过**。覆盖的判定（逐条）：

| 判定 | 期望 |
|---|---|
| `type(result) is dict` | 恒真 |
| key 集合 == 「`is_available()` 为真」的通道集合 | 恒相等 |
| 「值为 `None`」的通道 | **出现**在结果里（值为 `None`） |
| `skip_empty=False` 撞上无值通道 | 抛 `EmptyChannelError` |
| 省略 `skip_empty` == 显式 `skip_empty=True` | 结果**逐字相等** |
| 结果里的值与通道当前值 | **同一对象**（`is`） |

---

## 4. fresh 读（SC-005 · C8 的读取原语）

```bash
pytest -q tests/runtime/test_read_fresh.py
```

**期望**：**通过**。逐条判定：

| 判定 | 期望 |
|---|---|
| `fresh=True` 的视图 | **含**本次写入 |
| 读取**前后**通道的**绑定与可用性判定**（`is_available()` 的**结果** + `get()` 的**取值**） | **不变**（零污染 · 作用域见 FR-009 · 裁定 29） |
| **已知面**：**就地修改型**归约器改写了**值对象** | 会被改写（**与上游同构**）⇒ **不计入**上面的零污染判据 · **不修** · 已在用例中写明 |
| 归约型通道的 fresh 视图 | == 归约后的结果 |
| `fresh=False` 的视图 | == 通道当前值（**不含**本次写入） |
| 待写入的未知 key | 抛 `InvalidChannelUpdateError`（`key` 指向那个 key） |
| `read_channels(channels)` vs `local_read(channels, {}, fresh=False)` | 结果**逐字相等**（**SC-033** · `read-contract.md` **I-11**） |

---

## 5. 差分夹具（**验收判据 A3 / A4** · SC-006 / SC-007 / **SC-032** / SC-013）

```bash
# 需先装 differential 组（§0.1 第 ④ 步）
pytest -q tests/differential/ -v
```

**期望**：**通过**（**不是 skip**）。逐条判定：

| 投影 | 期望 |
|---|---|
| **节点入参** | 两侧的 key 集合与逐 key 值**相等**（含「空 key 缺席」） |
| **输出状态** | 两侧的 key 集合与逐 key 值**相等** |
| **事件序列** | 归一化后的 `(步序, 节点名, 写入)` 三元组**逐项相等**（**空更新 ⇒ 写入为 `None`**） |

> ⚠️ **无 `langgraph` 时** ⇒ 用例被 **skip**（**不是失败**）：

```bash
# 在没有 differential 组的环境里
pytest -q tests/differential/ -v
# ⇒ skipped（不是 failed）
```

---

## 6. 依赖红线（**验收判据 A5** · SC-008 / SC-010）

```bash
# 发行元数据 MUST 整体为空
python3 -c "import importlib.metadata as m; print(m.requires('freegraph') or [])"
```

**期望输出**：`[]` ⇒ `langgraph` / `langchain*` / `langsmith` **均不在** `Requires-Dist`。

```bash
# 内核路径 MUST NOT import 上游
grep -rn "import langgraph\|import langchain\|from langgraph\|from langchain" src/freegraph/ || echo "OK：无上游导入"
```

**期望**：`OK：无上游导入`。

```bash
# 既有依赖判据已按 R-3 拆分取样范围（SC-031 的五条断言）
pytest -q tests/runtime/test_parse_contract.py -k "dependency or workflow"
```

**期望**：**通过** ⇒ ① `[project].dependencies` 中零上游；② `[dependency-groups]` 中含上游的组
**恰好 1 个**且为 `differential`；③ `Requires-Dist` **整体为空**；④ `ci.yml` 中 `langgraph` 的安装
**只**经 `--group differential`；⑤ **拆分前**的其余断言**一条未放宽**（发行面断言**逐字保留**）。

---

## 7. 全量测试 + 门禁（CI 的等价物）

```bash
pytest -q tests/ -ra
```

**期望**：**全绿**（含 `tests/contracts/` · `tests/facade/` · `tests/gates/` 三层门禁）。

```bash
# 既有门禁逐条（编号总数 MUST 仍为 30）
python harness/scripts/gates/gate_G21_dependencies.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
python harness/scripts/gates/gate_G23_licenses.py --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
python harness/scripts/gates/gate_G24_config_layer.py
python harness/scripts/gates/gate_G25_import_graph.py
python harness/scripts/gates/gate_G26_network_static.py
python harness/scripts/gates/gate_G27_zero_egress.py
python harness/scripts/gates/gate_G29_contract_carrier.py
python harness/scripts/gates/gate_G30_attribution.py
```

**期望**：**全部**退出码 0；G29 的输出含「挂载点 C4：**已落地**」。
（**G2 / G3** 随 `pytest tests/` 全绿隐含；**G22**（隔离 venv）与 **G28**（断网）由 CI 的 **Linux** 作业承担
⇒ 见 §7 的断网实测说明。）

```bash
# ⚠️ 步骤 5.6（装 differential 组）MUST 位于步骤 6（全量测试套件）之前 —— 否则差分用例永远 skip
python3 - <<'PY'
import pathlib, sys
t = pathlib.Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
i56 = t.find("--group differential")
i6 = t.find("-m pytest tests/")
if i56 == -1:
    sys.exit("FAIL：未找到步骤 5.6（--group differential）⇒ 差分夹具永远 skip")
if i6 == -1:
    sys.exit("FAIL：未找到步骤 6（全量测试套件）")
print(f"OK：5.6 位置 {i56} < 步骤 6 位置 {i6}") if i56 < i6 else sys.exit(
    f"FAIL：5.6 位置 {i56} ≥ 步骤 6 位置 {i6} ⇒ 差分永远 skip")
PY
```

**期望**：`OK：5.6 位置 … < 步骤 6 位置 …` ⇒ 否则 **FAIL**（裁定 30 · FR-025 · **V10** 的一部分）。

---

## 8. 覆盖率取证（SC-018）

```bash
# ⚠️ 覆盖率工具**不进**依赖声明（v1.0 依赖面为零）⇒ 开发期临时安装
python3 -m coverage run --branch -m pytest -q tests/runtime tests/differential
python3 -m coverage report --include="src/freegraph/runtime/read.py"
```

**期望**：`src/freegraph/runtime/read.py` 的**行 / 分支覆盖率 == 100%**；
**整包**覆盖率**记录但不阻断**（B5F1 无基线）。

---

## 9. 冻结面审计（SC-011 / SC-012 / SC-029）

```bash
python3 - <<'PY'
import freegraph.contracts as c, freegraph.graph as g, freegraph.runtime as r
print("契约层符号数 =", len(c.__all__), "（MUST == 18）")
print("门面符号数   =", len(g.__all__), "（MUST == 7）")
print("runtime 符号数 =", len(r.__all__), "（MUST == 14 · 含 read_channels / local_read）")
print("读取入口在 runtime 上 =",
      all(hasattr(r, n) for n in ("read_channels", "local_read")))
PY
```

**期望**：`18` / `7` / `14` / `True` ⇒ 既有冻结面**零变更**，L2 导出面 12 → **14**。

---

## 10. 跨 feature 接线复核（宪法 **v1.8.0**「跨 feature 承接的接线通则」）

```bash
grep -n "承接条款（B5F2 → B7F1" harness/features/B7F1_任务准备与super-step循环.md
grep -n "夹具接口口径（B5F2 → B8F1" harness/features/B8F1_条件边路由与fresh读.md
grep -n "承接条款（B5F2 → B25F1" harness/features/B25F1_双跑验收与迁移说明.md
grep -n "承接条款（B5F2 → B4F1" harness/features/B4F1_schema解析与归约器提取.md
# ⚠️ **内容级校验**（B4F1 处 · 2026-11-09 clarify 第四轮）：标题命中**不足以**判通过 ⇒ 须校验措辞与裁定 27 一致
grep -c "取样范围拆分" harness/features/B4F1_schema解析与归约器提取.md
! grep -q "判据收窄" harness/features/B4F1_schema解析与归约器提取.md
```

**期望**：**四处各命中一行** ⇒ B7F1 / B8F1 / B25F1 / B4F1 的提示词初稿**含**承接条款
⇒ 下一棒**看得见**这几条义务（**不越界实现** · 只接线）。
⚠️ **B4F1 的附加判定**：`取样范围拆分` 的命中数 ≥ **1** **且** `判据收窄` 的命中数 == **0**
⇒ 措辞与 **裁定 27**（拆分取样范围 · 发行面断言逐字保留 · 取样范围 bug 修复 · 无需宪法修订）一致。

---

## 11. 人工验证记录与验收闸口（SC-017 / SC-019 / SC-029）

### 11.1 记录落点与五段式

- **路径**：`harness/verification/B5F2/manual-verification.md`
- **五段式**：① 验证环境 · ② 逐条判据的实测输出 · ③ 与上游的逐条对照 · ④ 未实跑项（**MUST NOT** 伪造输出）· ⑤ 来源覆盖表
- **证据门禁**：差分夹具的判定**MUST 记录比对的具体字段**（MUST NOT 只写「一致」· SC-019）

### 11.2 验收闸口（`V1`–`V12`）

| 闸口 | 内容 | 判定方式 |
|---|---|---|
| **V1** | C4 独立回归测试**通过**（A1 / A2 两条断言） | §1 |
| **V2** | 挂载点 C4 = `landed` · C8 = `not-landed` | §2 |
| **V3** | G2 门禁**绿**（`tests/contracts/**` 无 `freegraph.*` 导入） | §2 |
| **V4** | 稀疏读的三条判定（普通 `dict` / key 集合 / `None` 值） | §3 |
| **V5** | `skip_empty` 两分支（缺省稀疏 / 抛错） | §3 |
| **V6** | fresh 读的五条判定（含**零污染**）**＋ 两个稀疏入口的结果逐字相等**（SC-033 · `I-11`） | §4 |
| **V7** | 差分夹具的**三项投影**一致（A3 / A4）—— 含**节点入参投影**（**SC-032**） | §5 |
| **V8** | `langgraph` 缺席 ⇒ **skip 而非 fail** | §5 |
| **V9** | 发行元数据**零依赖包**（A5） | §6 |
| **V10** | 全量测试 + 既有门禁**全绿** · 门禁编号仍为 **30** · **步骤 5.6 位于步骤 6 之前** | §7 |
| **V11** | 读取层覆盖率 == **100%** | §8 |
| **V12** | 冻结面**零变更** + 跨 feature 接线**在位**（B7F1 / B8F1 / B25F1 / B4F1） | §9 / §10 |

---

## 12. 常见问题

| 症状 | 原因 | 处置 |
|---|---|---|
| 差分夹具全部 **skipped** | 环境**无** `differential` 组 | 装该组；**MUST NOT** 把 skip 当成「已验证」（SC-014） |
| 差分夹具报「不等价」 | 事件序列的**空更新**投影错了（应投影为 `None`） | 见 `contracts/differential-fixture.md` §3.3 |
| 差分夹具报「不等价」 | 节点返回了 schema 之外的 key | 两侧**行为不同**（上游静默丢弃）⇒ 前置校验拦截（`DR-2`） |
| C4 用例红了 | 读取层把**无值**通道也放进了结果 | 检查 `is_available()` 判定（spec FR-003） |
| `EmptyChannelError` 在 `skip_empty=False` 时**没**抛 | 实现用了「以 `None` 填充」 | **MUST** 抛错（spec 裁定 3）⇒ 见 `upstream-parity.md` P-04 |
