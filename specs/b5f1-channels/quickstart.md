# Quickstart: B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

**Feature**: `B5F1` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**契约权威**: [contracts/channel-contract.md](./contracts/channel-contract.md) ·
**上游对照**: [contracts/upstream-parity.md](./contracts/upstream-parity.md)

> **本手册是「怎么验证 B5F1 交付到位了」的**可照抄**手册** —— 每条命令都可直接复制执行，
> 每条命令后都写了**期望输出**（形态，而非逐字）。
> ⚠️ **编号约定**：本手册的验收闸口用 **`V1`–`V9`**（**不与**「验收判据 **A1**–**A3**」撞名 ——
> 见 spec 追溯表的「编号多义提示」）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（实测 · B3F1 的既有结论）
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --group dev

# ③ 发行形态（可编辑安装）
uv pip install -e .

# ④ 打印本手册用的解释器路径（确认是 venv 内的）
python3 -c "import sys; print(sys.executable); print(sys.version)"
```

**期望**：第 ④ 步打印的路径位于 `.venv/` 内；版本为 **CPython ≥ 3.11**。

### 0.2 本 feature **不需要** `langgraph`（沿用 B4F1 澄清 Q5）

```bash
# 仓库的依赖声明里 MUST NOT 出现 langgraph（运行时 / 发行元数据 / 开发期依赖组三处）
python3 - <<'PY'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
proj, groups = data.get("project", {}), data.get("dependency-groups", {})
names = list(proj.get("dependencies", [])) + list(proj.get("optional-dependencies", {})) \
        + [d for v in groups.values() for d in v]
print("声明处的 langgraph 次数 =", sum("langgraph" in str(n) for n in names))
PY
```

**期望**：`声明处的 langgraph 次数 = 0`（本机是否装了 `langgraph` **不影响**本 feature 的任何判据）。

---

## 1. 覆盖语义 —— 无归约器的 key 被覆盖（P1 · **验收判据 A2** · SC-001）

```bash
python3 - <<'PY'
from freegraph.runtime import LastValue
ch = LastValue("llm_calls", int)
print("初始有值？", ch.is_available())          # False（覆盖型初始「无值」）
ch.update([1]); print("写 1 后 =", ch.get())     # 1
ch.update([2]); print("再写 2 后 =", ch.get())   # 2 ← 覆盖，不是累加
print("归约器 =", ch.reducer)                   # None（覆盖型不持有归约器）
PY
```

**期望**：`初始有值？ False` → `写 1 后 = 1` → `再写 2 后 = 2` → `归约器 = None`。

## 2. 归约语义 —— 归约器 `operator(current, new)`（P2 · **验收判据 A1** · SC-002 / SC-021）

```bash
python3 - <<'PY'
import operator
from freegraph.runtime import BinaryOperatorAggregate
ch = BinaryOperatorAggregate("messages", list, operator.add)
print("初始有值？", ch.is_available(), "初值 =", ch.get())   # True []（空值）
ch.update([["m1"]]); ch.update([["m2"]])
print("累积结果 =", ch.get())                               # ['m1', 'm2']
# 折叠基准：从**初始空值**起逐次折叠（SC-021）
base = list(); base = operator.add(base, ["m1"]); base = operator.add(base, ["m2"])
print("与空值起折一致？", ch.get() == base)                  # True
print("归约器是 operator.add 本身？", ch.reducer is operator.add)  # True（身份判定）
PY
```

**期望**：初值 `[]` · 累积 `['m1', 'm2']` · 与空值起折一致 `True` · 归约器身份 `True`。

## 3. 路由通道清空 —— 每 super-step 清空（P3 · **验收判据 A3** · SC-003 / SC-023）

```bash
python3 - <<'PY'
from freegraph.runtime import EphemeralValue
ch = EphemeralValue("route", str)
ch.update(["tool_node"])
print("清空前 =", ch.get())
ch.clear()
print("清空后有值？", ch.is_available())        # False
try:
    ch.get()
except Exception as e:
    print("清空后读取抛出 =", type(e).__name__)  # EmptyChannelError（不是 None）
ch.update(["other"]); print("清空后再写 =", ch.get())   # other（无残余状态）
PY
```

**期望**：`清空前 = tool_node` → `清空后有值？ False` → 读取抛 `EmptyChannelError` → `清空后再写 = other`。

## 4. 一步内多值冲突 ⇒ 显式失败（SC-006 / SC-025）

```bash
python3 - <<'PY'
from freegraph.runtime import LastValue, InvalidChannelUpdateError
ch = LastValue("k", int)
try:
    ch.update([1, 2])
except InvalidChannelUpdateError as e:
    print("抛出 =", type(e).__name__)
    print("结构化字段：key =", e.key, "· received =", e.received_count, "· expected =", e.expected_count)
    print("仍无值？", not ch.is_available())     # True（**先检测后写入** ⇒ 值不变）
PY
```

**期望**：抛 `InvalidChannelUpdateError`；`key = k` · `received = 2` · `expected = 1`；`仍无值？ True`。

## 5. 映射入口 —— schema → 通道（FR-012 · SC-008 / SC-019）

```bash
python3 - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema, build_channel, build_channels
class S(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int
spec = parse_state_schema(S)
chs = build_channels(spec)
print("通道类型：", {k: type(v).__name__ for k, v in chs.items()})
print("保序？", list(chs) == list(spec.keys))
print("归约器是同一引用？", chs["messages"].reducer is operator.add)
ch = build_channel(spec.channels["llm_calls"])
print("单入口类型：", type(ch).__name__)
PY
```

**期望**：`{'messages': 'BinaryOperatorAggregate', 'llm_calls': 'LastValue'}` · 保序 `True` ·
归约器身份 `True` · 单入口 `LastValue`。

## 6. 零副作用 —— 导入无副作用 / 零环境变量 / 零出站（SC-005 · I-19）

```bash
python3 - <<'PY'
import sys
before = set(sys.modules)
import freegraph.runtime as rt
delta = sorted(m for m in set(sys.modules) - before
                if m.split(".")[0] not in sys.stdlib_module_names
                and not m.startswith("freegraph"))
print("非标准库增量 =", delta)          # []（MUST 为空）
print("导出符号 =", rt.__all__)
PY
```

**期望**：`非标准库增量 = []`；导出符号共 **12** 个（`Channel` / `LastValue` /
`BinaryOperatorAggregate` / `EphemeralValue` / `build_channel` / `build_channels` /
`EmptyChannelError` / `InvalidChannelUpdateError` + B4F1 的 4 个）。

> 📌 **口径说明**（2026-11-09 · 实现轮的演示手段订正 · **判据未变**）：
> 「非标准库」的判定 MUST 用**顶层包名**（`m.split(".")[0]`）⇒ 与既有夹具
> `tests/runtime/conftest.py` 的 `non_stdlib_delta` **逐字同构**。
> ⚠️ 用**全名精确匹配**会把标准库的**子模块**（`collections.abc` ·
> `typing.io` · `importlib._bootstrap` 等）误判为「非标准库」⇒ **演示手段**
> 与**判据**脱节（判据本身一直正确 —— CI 断言版用的是夹具口径）。

> ⚠️ **CI 断言版**（含环境变量 / 出站计数）由 pytest 的 `run_in_subprocess` 夹具执行 ——
> 见 §8 的 `pytest tests/runtime/test_channel_purity.py`。

## 7. 规模口径 —— 单通道操作不随 key 数增长（SC-022 · I-2）

```bash
python3 - <<'PY'
import gc
from typing import TypedDict
from freegraph.runtime import parse_state_schema, build_channels, Channel

def make(n):
    return TypedDict("S", {f"k{i}": int for i in range(n)})

refs = []
for n in (1, 1000):
    spec = parse_state_schema(make(n))
    ch = build_channels(spec)["k0"]
    refs.append(len(gc.get_referents(ch)))
    # ① 主判据 = 引用类型白名单（直接引用中不得出现 dict / SchemaSpec / 其它 Channel）
    bad = [type(r).__name__ for r in gc.get_referents(ch)
           if isinstance(r, (dict, Channel)) or type(r).__name__ == "SchemaSpec"]
    print(f"N={n:5d} 直接引用数={refs[-1]}  白名单违例={bad}")
print("⇒ 计数相等？", refs[0] == refs[1])
PY
```

**期望**：① **白名单违例 == 0**（每个 N 下都是空列表）⇒ 通道**结构上**不牵住其它通道 / 状态表；
② 两个计数**相等**（⚠️ **具体数值与实现相关** —— 槽位一改即变 ⇒ **判据是「相等」**，不是某个数字）。
> ⚠️ **计数相等**只是**辅助**判据（spec SC-022 ①③ · 裁定 17 ③）—— 实测「持有整张状态表」的违规实现
> 计数在 N=1 与 N=1000 时**同为 6** ⇒ **计数相等不蕴含「未持有状态表」** ⇒ **白名单才是主判据**。

## 8. 全量测试 + 覆盖率取证 + 独立验收脚本

```bash
# ① 全量测试（含 B4F1 的既有测试 ⇒ 本 feature MUST NOT 弄红它们）
pytest -q

# ② 本 feature 的测试单独跑
pytest -q tests/runtime/test_channel_semantics.py tests/runtime/test_channel_errors.py \
          tests/runtime/test_channel_mapping.py tests/runtime/test_channel_purity.py

# ③ 覆盖率取证（**开发期临时装** · MUST NOT 写进仓库依赖声明 · research D-13）
python3 -m pip install coverage            # ⚠️ 仅本机 · 不写进 pyproject.toml
python3 -m coverage run --branch -m pytest -q tests/runtime   # ⚠️ 必须 --branch（见下）
python3 -m coverage json -o /tmp/b5f1-cov.json
python3 -m coverage report --include="src/freegraph/runtime/*" --show-missing
#    ⇒ **三个数字都要记**（口径见 spec FR-019 ② / SC-015 · 澄清轮 Q14 · 裁定 17 ⑤）：
#      ① **本 feature 新增/修改的代码** —— channel.py / mapping.py 的 **行 100% / 分支 100%**（**阻断判据**）；
#         errors.py / __init__.py 只要求其**新增部分**被覆盖（**差分口径** · 见下）
#      ② **整包** src/freegraph/runtime/ 的覆盖率 —— **记录但 MUST NOT 阻断**
#         （B4F1 的既有模块从未设过覆盖率判据、无 100% 基线 ⇒ 本 feature 不承担其历史债）
#      ③ **差分口径** —— errors.py / __init__.py 的「新增部分」判定：
python3 - <<'PY'
import json, re, subprocess
cov = json.load(open("/tmp/b5f1-cov.json"))
for path in ("src/freegraph/runtime/errors.py", "src/freegraph/runtime/__init__.py"):
    diff = subprocess.run(["git", "diff", "-U0", "HEAD", "--", path],
                          capture_output=True, text=True).stdout
    added = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start = int(m.group(1)); cnt = int(m.group(2) or 1)
        added.update(range(start, start + cnt))
    f = cov["files"][path]
    miss_lines = added & set(f.get("missing_lines", []))
    miss_br = [b for b in f.get("missing_branches", []) if b[0] in added]
    print(f"{path}: 新增行={len(added)} 未覆盖新增行={sorted(miss_lines)} 未覆盖新增分支={miss_br}")
    # ⇒ 两个列表都必须为空
PY
#    ⇒ 把这段输出**原样粘贴**进 manual-verification.md 的第 3 节
#
#    ⚠️ **三条取证纪律**（裁定 17 ⑤ · research D-17 实测）：
#      ① 分支覆盖 **必须** 用 --branch（否则 report **不输出 Branch 列** ⇒ 分支覆盖无从判定）
#      ② 文件级 report **无法**区分「既有行」与「新增行」⇒ 不能单独作「新增部分」的判据
#      ③ 「新增部分」**必须**走上面的差分口径

# ④ 独立验收脚本（一条命令跑完全部判据 · 零第三方依赖）
python3 harness/verification/B5F1/acceptance.py
python3 harness/verification/B5F1/acceptance.py --record /tmp/b5f1-record.md   # 五段式片段
```

**期望**：① 全绿；② 全绿；③ 行/分支 **100%**；④ 退出码 **0**（PASS）。

## 9. 冻结面审计（SC-011 / SC-012 / SC-023）

```bash
# ① 公开面零变更（契约层 18 个 / 门面 7 个）
python3 - <<'PY'
import freegraph.contracts as c, freegraph.graph as g
print("契约层符号数 =", len(c.__all__), "· 门面符号数 =", len(g.__all__))
PY

# ② 兼容矩阵零新增行 + 层注册表零改动 + 门禁编号仍为 30
git diff --stat -- README.md specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md
awk '/^## 0\./,/^## 1\./' specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md \
  | grep -c '^| \*\*G'   # ⇒ 30（**只数 §0「门禁总览」表** —— 全文另有 §2 的逐条引用）

# ③ 既有 C4 / C8 挂载点 MUST NOT 被改成 landed（spec 追溯表 · 登记项 R-1）
grep -n "not-landed" tests/contracts/test_contract_regressions.py
```

**期望**：① `18` / `7`；② `git diff --stat` **无输出**、门禁编号计数 **30**（⚠️ 门禁总表在 `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` 的 §0「门禁总览」—— **不在** `_gatekit.py` 里）；③ 仍为 `status=not-landed`。

---

## 10. 人工验证记录（SC-013）与验收闸口

### 10.1 记录落点与五段式

落 **`harness/verification/B5F1/manual-verification.md`**，五段式（宪法原则 V）：

| # | 段 | 内容 |
|---|---|---|
| 1 | **环境** | Python 版本 / 平台 / 包版本 / 依赖闭包实测 |
| 2 | **步骤** | 照本手册 §1–§9 的**可复制**命令 |
| 3 | **实际输出** | 粘贴**真实**输出（§8 ③ 的覆盖率输出 MUST 在此）—— **MUST NOT** 伪造 |
| 4 | **结论** | 逐条对照 **A1–A3** + 内部 SC；**不适用**的子项**显式记一句** |
| 5 | **遗留问题** | 已知限制与其归属 feature（如 **DR-1** `__eq__` / **DR-2** 类型文本） |

并 MUST 含**来源覆盖表**（宪法原则 VIII）：每条判据标注来源
（上游 `路径:行号` + 核实版本 `langgraph 1.2.11` / 澄清条号 / 宪法条款号）。

### 10.2 验收闸口（`V1`–`V9`）

| 闸口 | 内容 | 对应判据 / SC |
|---|---|---|
| **V1** | 覆盖语义：`LastValue` 连续两次写入 ⇒ 读到**末值** | **验收判据 A2** · SC-001 |
| **V2** | 归约语义：`BinOp` 写入序列 == **从空值起**的逐次归约 | **验收判据 A1** · SC-002 / SC-021 |
| **V3** | 路由清空：`EphemeralValue.clear()` ⇒ **无值**（抛错，不返回 `None`） | **验收判据 A3** · SC-003 |
| **V4** | 冲突显式失败：一步内多值 ⇒ `InvalidChannelUpdateError` + **值不变** | SC-006 · SC-025 |
| **V5** | 可判定性：「无值」与「值为 `None`」严格可分；清空后**一律**无值 | SC-004 · SC-023 |
| **V6** | 映射正确：`build_channel(s)` 的类型 / 保序 / 归约器**身份** | SC-008 · SC-019 |
| **V7** | 纯净性与规模：属性集 ⊆ 4 项；引用数与 key 数**无关**；浅引用 | SC-009 · SC-022 · SC-025 |
| **V8** | 零副作用：导入无副作用 / 零环境变量 / 零出站；依赖三处零新增 | SC-005 · SC-012 |
| **V9** | 交付面：覆盖率 **100%**（行 + 分支）+ 独立验收脚本 **PASS** + 人工记录五段式 | SC-015 · SC-027 · SC-013 |

> **⚠️ 未闭合项须显式登记**（原则 V）：「门禁 3 / 4 / 5 的 C4 回归 · C8 回归 · fake 模型轮 ·
> 真实模型轮」在本 feature **物理不可达成**（无图可跑）⇒ MUST 记入 **登记项 R-1** 并请发起者追认
> （承接方：**B5F2** / **B8F1** / **B7F2** / **B7F3** / **B25F1**）。

---

## 11. 常见问题

| 症状 | 原因 | 处理 |
|---|---|---|
| `ImportError: cannot import name 'Channel'` | 装的是**旧版本**发行包 | 重新 `uv pip install -e .`（§0.1 ③） |
| 覆盖率报告里 `channel.py` 分支 < 100% | 缺「不可实例化类型」/「抽象容器映射」/「归约失败」等分支用例 | 对照 spec FR-006 ①②③ · FR-007 ② · FR-008 补用例 |
| `sys.modules` 增量不为空 | 测试**同进程**断言（pytest 已 import 大量模块） | MUST 在**子进程**里断言（复用 `tests/runtime/conftest.py` 的 `run_in_subprocess`） |
| 验收脚本报「环境未就绪」（退出码 2） | 当前环境**未安装** freegraph 且脚本跑了 `--require-installed` | 去掉该参数（两态运行会自动测源码树）· 或先 `uv pip install -e .` |
