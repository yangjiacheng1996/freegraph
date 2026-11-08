# Quickstart: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) |
**契约**: [contracts/schema-parse-contract.md](./contracts/schema-parse-contract.md) ·
[contracts/binary-criterion.md](./contracts/binary-criterion.md)

> 本手册是**实现完成后的可照抄验证指南**：每节给出**命令** + **期望输出** + **对应判据**。
> ⚠️ 第 1 节起的命令依赖 `freegraph.runtime`（**实现后**才存在）⇒ 实现前跑会得到
> `ModuleNotFoundError: No module named 'freegraph.runtime'`（这是**预期**的，不是缺陷）。
> 第 0 节与第 8.1 节的命令**现在就能跑**（零依赖）。

---

## 0. 前置条件

### 0.1 环境准备（**一次性 · 四条命令** · 跨平台）

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在无活动虚拟环境时报
#    "error: No virtual environment found" 并以退出码 2 失败（实测 · B3F1 的既有结论）
uv venv --python .venv

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --python .venv --group dev

# ③ 发行形态（可编辑安装）
uv pip install --python .venv -e .

# ④ 打印本手册用的解释器路径（确认是 venv 内的）
uv run --no-project --python .venv python -c "import sys; print(sys.executable)"
```

> **跨平台写法**（B3F1 的既有纪律）：一律用 **venv 目录** `.venv` + `uv run --no-project`；
> **MUST NOT** 出现平台专属的解释器路径（Windows 上是 `.venv\Scripts\python.exe`）。

### 0.2 本 feature **不需要** `langgraph`（澄清 Q5）

```bash
# 期望：freegraph 的依赖声明里没有 langgraph；本机是否装了它不影响本 feature 的任何判据
uv run --no-project --python .venv python -c "
import importlib.metadata as md
print('Requires-Dist:', md.requires('freegraph'))
"
```

**期望输出**：`Requires-Dist: None`（v1.0 的发行元数据**零依赖包名** · 宪法 v1.7.0）。

> **📌 为什么要写这一节**：A2（「二元性判据与 LangGraph 一致」）由
> [contracts/binary-criterion.md](./contracts/binary-criterion.md) 的**判定表**承载（上游行为的固化快照）；
> **CI 不装** `langgraph` ⇒ 上游升级**不会**让本 feature 的 CI 变红。
> 实时对照留给 **B5F2 / B8F1** 的差分夹具。

---

## 1. 解析主路径 —— 归约器识别与身份判定（P1 · **验收判据 A1**）

```bash
uv run --no-project --python .venv python -c "
import operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

class MessagesState(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

spec = parse_state_schema(MessagesState)
msgs = spec.channels['messages']

print('归约器是 operator.add 本身 :', msgs.reducer is operator.add)
print('has_reducer                :', msgs.has_reducer)
print('semantics                  :', msgs.semantics)
print('value_type（基类型，无 Annotated 包装）:', msgs.value_type)
print('keys（保序）               :', spec.keys)
print('规格条数 == key 数          :', len(spec.channels) == len(spec.keys) == 2)
"
```

**期望输出**

```text
归约器是 operator.add 本身 : True
has_reducer                : True
semantics                  : reduce
value_type（基类型，无 Annotated 包装）: <class 'list'>
keys（保序）               : ('messages', 'llm_calls')
规格条数 == key 数          : True
```

**判据**：SC-001（身份判定 · 四项全中）· SC-008（条数 == key 数）· FR-012（按引用持有）。

### 1.2 验收基准同构形态（`typing_extensions.TypedDict` · SC-018）

> 验收基准 `harness/demo/target.py:59-61` 的 schema 用的是 **`typing_extensions.TypedDict`**
> ⇒ `typing.is_typeddict` 对它返回 **`False`** ⇒ freegraph MUST 走**鸭子判定**（裁定 3）。
> ⚠️ 该形态由**测试代码**构造；freegraph 侧**不 import** `typing_extensions`（FR-001 ②）。

```bash
uv run --no-project --python .venv python -c "
import operator
from typing import Annotated
from typing_extensions import TypedDict
from freegraph.runtime import parse_state_schema

class AnyMessage:  # 零依赖替身（真实形态是 langchain.messages.AnyMessage）
    pass

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

spec = parse_state_schema(MessagesState)
msgs = spec.channels['messages']
calls = spec.channels['llm_calls']

print('解析成功（非「非 TypedDict」）:', True)
print('messages.reducer is operator.add:', msgs.reducer is operator.add)
print('messages.has_reducer           :', msgs.has_reducer)
print('messages.semantics             :', msgs.semantics)
print('llm_calls.semantics            :', calls.semantics)
" 2>&1 | tail -20
```

**期望输出**：`解析成功（非「非 TypedDict」）: True` · `messages.reducer is operator.add: True` ·
`messages.has_reducer: True` · `messages.semantics: reduce` · `llm_calls.semantics: overwrite`。

**判据**：SC-018（`typing_extensions.TypedDict` 的**接受率 == 100%** · 裁定 3 · FR-001 ①）·
FR-001 ②（内核 **MUST NOT** import `typing_extensions`）。

> ⚠️ 若环境**未装** `typing_extensions` ⇒ 该例**跳过**（测试侧用 `pytest.importorskip` 兜底）；
> **MUST NOT** 因此把 `typing_extensions` 写进 `pyproject.toml`（FR-016 ② · FR-019）。

---

## 2. 默认覆盖语义 —— 无归约器的 key（P2 · **验收判据 A3**）

```bash
uv run --no-project --python .venv python -c "
from typing import TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict):
    llm_calls: int

spec = parse_state_schema(S)
c = spec.channels['llm_calls']
print('reducer（无归约器 → 空）:', c.reducer)
print('has_reducer             :', c.has_reducer)
print('semantics（默认覆盖）   :', c.semantics)
"
```

**期望输出**：`reducer: None` · `has_reducer: False` · `semantics: overwrite`。
**判据**：SC-002（C3 标记）· FR-006 ①（**只标记**，覆盖的执行在 **B5F1**）。

---

## 3. 别的 `Annotated` 用法不被误判（P3）

```bash
uv run --no-project --python .venv python -c "
import operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict):
    note: Annotated[int, '说明文字']                      # 末位非 callable
    hist: Annotated[list, '描述', operator.add]           # 多条目 · 只认末位

spec = parse_state_schema(S)
print('note.semantics        :', spec.channels['note'].semantics)
print('note.reducer          :', spec.channels['note'].reducer)
print('hist.reducer is add   :', spec.channels['hist'].reducer is operator.add)
"
```

**期望输出**：`note.semantics: overwrite` · `note.reducer: None` · `hist.reducer is add: True`。
**判据**：SC-003（末位非 callable ⇒ 无归约器，**且解析成功**）· FR-005（只认末位）。

---

## 4. 非法 schema —— 快速失败 + 结构化错误（P4 · SC-006 / SC-017）

```bash
uv run --no-project --python .venv python -c "
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema, InvalidSchemaError
from freegraph.contracts import FreegraphError

class Bad(TypedDict):
    bad: Annotated[int, lambda a, b, c: None]     # 3 个位置参数 → 非二元

try:
    parse_state_schema(Bad)
except InvalidSchemaError as e:          # 读结构化字段：import 具体子类（裁定 14）
    print('捕获类型            :', type(e).__name__)
    print('key（结构化字段）  :', e.key)
    print('reason（结构化字段）:', e.reason)
    print('是 ValueError 吗    :', isinstance(e, ValueError))
except FreegraphError as e:             # 捕获：基类即可（不需要 import 具体子类）
    print('基类捕获            :', type(e).__name__)
"
```

**期望输出**（结构化字段**不需要**解析消息）：

```text
捕获类型            : InvalidSchemaError
key（结构化字段）  : bad
reason（结构化字段）: reducer_not_binary
是 ValueError 吗    : True
```

> **📌 两条路径（裁定 14 · FR-007 ⑤⑥）**：**捕获**用基类 `FreegraphError` 即可
> （`except ValueError` 同样有效）；**读 `key` / `reason`** 时从 `freegraph.runtime`
> import 具体子类 —— 门面 7 符号面与契约层 18 符号面**均不变**（L2 子包路径）。

**判据**：SC-006（拒绝率 100% · 消息点名 key · 快速失败只报第一个）· SC-017（字段齐备率 100% ·
原因码 ∈ 封闭集合）· FR-007 ④⑥ · FR-004（计数口径）。

**其余两类原因码的取样**：

```bash
uv run --no-project --python .venv python -c "
from freegraph.runtime import parse_state_schema
from freegraph.contracts import FreegraphError
for bad in ({'a': 1}, {'a': int}):
    try:
        parse_state_schema(bad)
    except FreegraphError as e:
        print(type(e).__name__, '| key =', e.key, '| reason =', e.reason)
"
```

**期望输出**：`InvalidSchemaError | key = None | reason = not_a_typed_dict`（两行相同）。

---

## 5. 二元性判据表逐条比对（A2 · SC-004）

```bash
# 全量测试（含判定表逐条比对）
uv run --no-project --python .venv python -m pytest tests/runtime/ -ra

# 只跑判据表那一个文件
uv run --no-project --python .venv python -m pytest tests/runtime/test_binary_criterion.py -v
```

**期望**：全部用例通过；判定表**缺失条数 == 0**（`contracts/binary-criterion.md` §2 的 16 行 +
§3 的 2 行**逐条**被比对，每条都带上游 `路径:行号`）。
**判据**：SC-004（一致率 == 100% · 无来源项数 == 0）· FR-016 ①-a·①-b。

> **📌 判定表是判据的**唯一权威**（`<!-- authority: yes -->`）：测试**解析该 Markdown 表格**取样
> ⇒ 判据与用例**天然分离**（改判据必然改测试同提交可见）。

---

## 6. 纯数据 —— 不可变 / 可比较 / 投影无地址（SC-005）

```bash
uv run --no-project --python .venv python -c "
import dataclasses, json, operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict):
    messages: Annotated[list, operator.add]
    n: int

a = parse_state_schema(S)
b = parse_state_schema(S)

print('两次解析相等          :', a == b)
proj = a.to_dict()
print('投影可 JSON 序列化    :', bool(json.dumps(proj)))
print('投影含内存地址        :', '0x' in json.dumps(proj))
try:
    a.channels['x'] = None
except TypeError as e:
    print('channels 只读         :', type(e).__name__)
try:
    dataclasses.replace(a.channels['n'], key='zzz')
except Exception as e:
    print('字段不可改            :', type(e).__name__)
"
```

**期望输出**：`两次解析相等: True` · `投影可 JSON 序列化: True` · `投影含内存地址: False` ·
`channels 只读: TypeError` · `字段不可改: FrozenInstanceError`。
**判据**：SC-005（可比较 + 可序列化 + 无地址）· FR-010 · FR-011（research D-01 / D-02 / D-05 / D-06）。

---

## 7. 必填性 —— 只记录不执行（SC-016）

```bash
uv run --no-project --python .venv python -c "
from typing import NotRequired, TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict, total=False):
    a: int
    b: str

class T(TypedDict):
    c: int
    d: NotRequired[str]

for cls in (S, T):
    spec = parse_state_schema(cls)
    print(cls.__name__, {k: spec.channels[k].required for k in spec.keys})
"
```

**期望输出**：`S {'a': False, 'b': False}` · `T {'c': True, 'd': False}`。
**判据**：SC-016（标记正确率 == 100% · **本 feature 不执行任何必填性校验** · 校验归 **B7F3**）· FR-021。

---

## 8. 依赖与 I/O 纪律

### 8.1 零第三方依赖 / 顶层包惰性 / 零 import 副作用（**现在就能跑**）

```bash
uv run --no-project --python .venv python -c "
import sys
import freegraph
print('顶层包已加载的子模块:', [m for m in sys.modules if m.startswith('freegraph.')])
"
```

**期望输出**：`[]` ⇒ **顶层包惰性**成立（G1 / L-1：L2 的 `freegraph.runtime` **不被**顶层包 import）。

### 8.2 解析的零副作用（零环境变量 / 零出站 / 不调用归约器 · SC-007 / SC-009）

```bash
uv run --no-project --python .venv python -c "
import os, sys
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

calls = []
def reducer(a, b):            # 用户归约器：解析期 MUST NOT 被调用
    calls.append(1)
    return a

class S(TypedDict):
    messages: Annotated[list, reducer]

before = set(sys.modules)
spec = parse_state_schema(S)
new = {m for m in set(sys.modules) - before if not m.startswith('freegraph')}
non_std = sorted(m for m in new if m.split('.')[0] not in set(sys.stdlib_module_names))
print('新增的非标准库模块:', non_std)
print('归约器被调用次数    :', len(calls))
print('reducer 是同一对象  :', spec.channels['messages'].reducer is reducer)
```

**期望输出**：新增的非标准库模块 **[]**（仅标准库 `typing` / `inspect` 等）；
归约器被调用次数 **0**；`reducer 是同一对象: True`。
**判据**：SC-007 · SC-009（引用保持率 == 100% · 调用次数 == 0）· FR-013（纯函数）。

> **📌 环境变量读取次数 == 0 与出站连接次数 == 0** 的断言在**子进程**里做
> （测试进程自身已导入 pytest，同进程不可用）⇒ 落 `tests/runtime/conftest.py` 的夹具
> （沿用 B3F1 的形态）。

---

## 9. 层纪律与署名头（SC-012）

```bash
# 层归属：src/freegraph/runtime/ 已在层注册表登记为 L2（层注册表零改动）
grep -n "runtime/" specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md

# 既有门禁 G25（导入图单向）· G30（全仓署名头）自动覆盖新模块 —— 门禁编号总数仍为 30
uv run --no-project --python .venv python -m pytest tests/gates/test_gates.py -ra -k "G25 or G30"
```

**期望**：层注册表命中 `src/freegraph/runtime/` = **L2**；既有门禁**全绿**（无新增门禁编号）。

---

## 10. 人工验证记录（SC-013）与验收闸口

```bash
ls harness/verification/B4F1/manual-verification.md
grep -n "^## \|^### " harness/verification/B4F1/manual-verification.md
```

**期望**：文件存在，且五段式小节齐全（**环境 / 步骤 / 实际输出 / 结论 / 遗留问题**）
+ **来源覆盖表**一节（每条判据 → 来源 `路径:行号` / Q8 条号 / 宪法条款号）。

**闸口（合入前）** —— 编号用 **V1–V9**（Verification gates）⇒ 与「验收判据 **A1–A3**」
（spec / 引文 §6）/「执行闸口 **A1–A5**」（`tasks.md`）/ 宪法**门禁 G1–G30**
**四套编号互不撞名** ⇒ 引用时 MUST 带限定语（「quickstart 闸口 V1」）：

| # | 闸口 | 判据 |
|---|---|---|
| V1 | `Annotated[list, operator.add]` 被识别为二元归约器（**身份**判定） | 第 1 节 · SC-001 |
| V2 | 二元性判据与 LangGraph 一致 | 第 5 节 + 判定表 · SC-004 |
| V3 | 无归约器 key 走覆盖语义 | 第 2 节 · SC-002 |
| V4 | 非法 schema **快速失败** + 结构化错误 | 第 4 节 · SC-006 / SC-017 |
| V5 | 纯数据（不可变 / 可比较 / 投影无地址） | 第 6 节 · SC-005 |
| V6 | 必填性只记录不执行 | 第 7 节 · SC-016 |
| V7 | 依赖与 I/O 纪律 | 第 8 节 · SC-007 / SC-011 |
| V8 | 层纪律与署名头 | 第 9 节 · SC-012 |
| V9 | **发起者追认**（plan 登记项 R-1：宪法门禁 3/4/5 的偏离登记） | 人工验证记录第 4 节 · **阻断合入** |
