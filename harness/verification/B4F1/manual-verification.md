# B4F1 · 状态 schema 解析 + 归约器提取 —— 人工验证记录

**feature**: B4F1（M1 运行时内核 · L2 执行内核层 · 状态 schema 解析 + 归约器提取）
**验收依据**: `specs/b4f1-schema-reducer-parse/spec.md` · `plan.md` · `tasks.md` ·
`contracts/schema-parse-contract.md` · `contracts/binary-criterion.md`
**验收指南**: [`specs/b4f1-schema-reducer-parse/quickstart.md`](../../../specs/b4f1-schema-reducer-parse/quickstart.md)
**记录日期**: 2026-11-08
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：① 环境 ② 步骤 ③ 实际输出 ④ 结论
> ⑤ 遗留问题 + ⑥ 来源覆盖表 + ⑦ 移交后续 feature）。
> 第 3 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的项逐条登记在第 5 节。
>
> **✅ 发起者追认已作出**（T053 · plan 登记项 **R-1**）—— 发起者于 **2026-11-08**
> 在本会话中明示「**验收通过了**」并指示收尾与推送 ⇒ 追认栏见 §4.3。
> 依宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」，该追认由**发起者本人**作出，
> 实现者**未代签**、**未改**宪法正文、**未**把 C4 / C8 的 ``GATE-MOUNT:`` 标记
> 改成 ``landed`` ⇒ 执行闸口 **A5** 通过。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python（**主判定档** · `.venv`） | **3.11.16**（`uv run --no-project --python .venv python`） |
| 本机 Python（系统解释器 · 仅用于跑门禁脚本） | **3.12.3**（`/usr/bin/python3`） |
| 最高档 venv（`.venv314`） | **3.14.7** —— **已实跑**：`pytest tests/ -ra` ⇒ **495 passed / 4 skipped**（§3.13） |
| 平台 | Linux-6.8.0-139-generic-x86_64-with-glibc2.39 |
| uv | **0.12.7**（x86_64-unknown-linux-gnu） |
| git | **2.43.0**（基线提交 `73825b1`） |
| pytest | **9.2.0**（`.venv`；`pyproject.toml` 的 `[dependency-groups] dev` 装入） |
| freegraph 版本 | **0.0.3**（`pyproject.toml` 的 `version`） |
| `requires-python` | `>=3.11`（**无** `<` 上界） |
| **v1.0 的发行元数据** | **零依赖包名** —— 实测 `importlib.metadata.requires("freegraph")` == **`None`**（§3.1 输出） |
| **本 feature 的新增第三方依赖** | **零** —— `dependencies` / `[project.optional-dependencies]` / `[dependency-groups]` **三处零改动**（T049 断言） |
| `typing_extensions` | **已装**（测试环境**偶然**可得 · 非任何声明依赖）⇒ §3.2 的**验收基准同构形态**（quickstart §1.2）的 SC-018 判据**未 skip**（**pass**） |
| **人工验收入口** | `harness/verification/B4F1/acceptance.py`（**单文件 · 零第三方依赖** · 可独立运行 · 89 条断言 · 两态运行：已安装 ⇒ 测发行产物 / 未安装 ⇒ 测源码树） |
| 核实环境（上游行号） | **`langgraph 1.2.11`**（`langgraph/graph/state.py` · 契约 §2 的 `路径:行号` 全部指向该版本） |

---

## 2. 步骤

> 逐条对应 `quickstart.md` 的 10 节。**命令可直接复制执行**。

| # | 场景 | 命令 | 关联判据 |
|---|---|---|---|
| **★** | **一条命令跑完全部验收**（**推荐入口**） | `python3 harness/verification/B4F1/acceptance.py` | A1–A3 + SC-001…SC-018（**89 条**）· 输出见 §3.0 |
| 0 | 前置条件 · 依赖面 | `uv run --no-project --python .venv python -c "import importlib.metadata as md; print(md.requires('freegraph'))"` | FR-016 ② · SC-004 |
| 1 | 解析主路径（归约器识别 + 身份判定） | quickstart §1 的 `python -c` 脚本 | SC-001 · SC-008 · FR-012 |
| 1.2 | 验收基准同构形态（`typing_extensions.TypedDict`） | quickstart §1.2 的 `python -c` 脚本 | SC-018 · FR-001 ① |
| 2 | 默认覆盖语义 | quickstart §2 的 `python -c` 脚本 | SC-002 · FR-006 ① |
| 3 | 别的 `Annotated` 用法不被误判 | quickstart §3 的 `python -c` 脚本 | SC-003 · FR-005 |
| 4 | 非法 schema（快速失败 + 结构化错误） | quickstart §4 的两段 `python -c` 脚本 | SC-006 · SC-017 · FR-007 ④⑥ |
| 5 | 判定表逐条比对 | `pytest tests/runtime/ -ra` · `pytest tests/runtime/test_binary_criterion.py -v` | SC-004 · FR-016 ①-a·①-b |
| 6 | 纯数据（不可变 / 可比较 / 投影无地址） | quickstart §6 的 `python -c` 脚本 **+ 本记录的修正版**（§3.7） | SC-005 · FR-010 · FR-011 |
| 7 | 必填性（只记录不执行） | quickstart §7 的 `python -c` 脚本 | SC-016 · FR-021 |
| 8 | 依赖与 I/O 纪律 | quickstart §8.1 / §8.2 的 `python -c` 脚本 | SC-007 · SC-009 · SC-011 |
| 9 | 层纪律与署名头 | `grep -n "runtime/" specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` · `pytest tests/gates/test_gates.py -ra -k "G25 or G30"` | SC-012 · FR-014 |
| 10 | 人工验证记录本身 | `ls harness/verification/B4F1/manual-verification.md` · `grep -n "^## \|^### " …` | SC-013 · FR-018 |
| — | 全量测试套件 | `uv run --no-project --python .venv python -m pytest tests/ -ra` | 全部 |

---

## 3. 实际输出

> **原样粘贴真实输出**（FR-018 · MUST NOT 伪造输出）。

### 3.0 · ★ **一条命令**的人工验收（**推荐入口** · `harness/verification/B4F1/acceptance.py`）

> **📌 人工验收的推荐入口**：本 feature 另落了**可独立运行的验收脚本**
> （沿用 **B1F1 / B2F1 / B2F2** 的既有形态 · tasks **T058**）⇒ **一条命令**即可跑完
> 全部判据（A1–A3 + SC-001…SC-018，**89 条断言**），**无需**逐条复制粘贴下面的命令。
>
> ```bash
> python3 harness/verification/B4F1/acceptance.py                    # 跑全部
> python3 harness/verification/B4F1/acceptance.py --record out.md    # 同时生成验收记录片段
> python3 harness/verification/B4F1/acceptance.py --require-installed # 要求已安装 freegraph
> ```
>
> 退出码：`0` = PASS · `1` = FAIL。**两态运行**：已安装 freegraph ⇒ 测**发行产物**；
> 未安装 ⇒ 自动注入 `<repo>/src` 测**源码树**（依赖闭包那条判据标「◌ 环境未就绪」，
> **不判失败**）。**零第三方依赖**（只用标准库 + 被验的 freegraph 本身）。
> ⚠️ 判定表**不另抄一份** —— 脚本**解析**
> `contracts/binary-criterion.md`（**唯一权威** · research D-03）。

```console
$ uv run --no-project --python .venv python harness/verification/B4F1/acceptance.py
══ acceptance · B4F1 状态 schema 解析 + 归约器提取 ══
  ✔ A1/SC-001 ① 归约器是 operator.add **本身**（身份判定）
  ✔ A1/SC-001 ② has_reducer is True
  ✔ A1/SC-001 ③ semantics == 'reduce'
  ✔ A1/SC-001 ④ value_type 是归约前的基类型 list
  ✔ SC-008 规格保序（keys）
  ✔ SC-008 规格条数 == key 数
  ✔ SC-009 归约器**按引用**持有（不包装 / 不复制）
  ✔ SC-009 解析期归约器**调用次数 == 0**
  ✔ SC-010 Required[...] 包裹的归约器**不漏**
  ✔ SC-010 NotRequired[...] 包裹的归约器**不漏**
  ✔ SC-004 覆盖面下限：§2 行数 == 16
  ✔ SC-004 覆盖面下限：§3 行数 == 2
  ✔ SC-004 求值命名空间与 §4 夹具清单**逐名一致**
  ✔ SC-004 每条形态 MUST 带上游 `路径:行号`（无来源项数 == 0）
  ✔ SC-004 每个「输入」名 MUST 能在 §4 夹具清单中找到（缺失条数 == 0）
  ✔ SC-004 判定表**逐条**比对一致（一致率 == 100% · 18 条）
  ✔ A3/SC-002 ① 无归约器 ⇒ reducer 为**空**
  ✔ A3/SC-002 ② has_reducer is False
  ✔ A3/SC-002 ③ semantics == 'overwrite'（C3 事实）
  ✔ SC-008 保序：父类 key 在前 · 同名覆盖保持原位
  ✔ SC-008 规格条数 == key 数（含继承链）
  ✔ SC-008 名为 `__slots__` 的伪 key 不计入条数
  ✔ SC-008 空 TypedDict ⇒ 零条规格（合法）
  ✔ SC-016 total=False ⇒ 全部标记为「可选」
  ✔ SC-006 快速失败：只报**第一个**问题
  ✔ SC-014 非二元候选「ClassNoInit」⇒ 抛 schema 错误（**不静默降级**）
  ✔ SC-014 非二元候选「ClassOneArgInit」⇒ 抛 schema 错误（**不静默降级**）
  ✔ SC-014 非二元候选「CallableKwOnlyInstance」⇒ 抛 schema 错误（**不静默降级**）
  ✔ SC-014 非二元候选「str」⇒ 抛 schema 错误（**不静默降级**）
  ✔ SC-017 错误对象带**出错 key**（reducer_not_binary）
  ✔ SC-017 错误对象带**原因码**（reducer_not_binary）
  ✔ SC-006 错误同时是 ValueError
  ✔ SC-006 错误同时是 FreegraphError
  ✔ SC-006 消息**点名**出错 key
  ✔ SC-006 非 TypedDict ⇒ not_a_typed_dict
  ✔ SC-005 通道规格**不可变**（改属性抛 FrozenInstanceError）
  ✔ SC-005 channels 写操作抛 TypeError（结构性不可变）
  ✔ SC-005 SchemaSpec **显式不可哈希**
  ✔ SC-005 ChannelSpec **显式不可哈希**
  ✔ SC-005 同一 schema 两次解析**相等**
  ✔ SC-005 内容相同、仅类名不同的 TypedDict 解析结果**相等**
  ✔ SC-005 value_type 不同 ⇒ 结果**不等**
  ✔ SC-005 键集合不同 ⇒ 结果**不等**
  ✔ SC-005 投影可 JSON 序列化
  ✔ SC-005 投影**不含内存地址形态**
  ✔ SC-005 两次投影**逐字一致**（确定性）
  ✔ SC-007 解析前后 `sys.modules` 增量的**非标准库**条目数 == 0
  ✔ SC-011 import freegraph.runtime 后**无**第三方模块
  ✔ SC-009 解析期归约器**调用次数 == 0**
  ✔ SC-009 归约器**按引用**保持
  ✔ SC-018 messages 的归约器是 operator.add **本身**
  ✔ SC-018 messages.has_reducer is True
  ✔ SC-018 messages.semantics == 'reduce'
  ✔ SC-018 llm_calls.reducer 为**空**
  ✔ SC-018 llm_calls.semantics == 'overwrite'
  ✔ SC-015 契约层公开符号面仍为 **18** 个
  ✔ SC-015 门面公开符号面仍为 **7** 个
  ✔ SC-015 兼容矩阵**零新增行**（符号集合 == 契约层 18 + 门面 7）
  ✔ FR-016 ② 依赖三处声明**零**「langgraph」
  ✔ FR-016 ② 依赖三处声明**零**「langchain」
  ✔ FR-016 ② 依赖三处声明**零**「langsmith」
  ✔ FR-016 ② 依赖三处声明**零**「typing_extensions」
  ✔ FR-016 ② 依赖三处声明**零**「typing-extensions」
  ✔ FR-016 ③ CI 作业内 `langgraph` 安装次数 == 0
  ✔ SC-012 层注册表把 `src/freegraph/runtime/` 登记为 **L2**（零改动）
  ✔ SC-012 L2 → L3 / L4 / L5 的边数 == 0
  ✔ SC-012 门禁编号总数仍为 **30** 且连续
  ✔ SC-012 新建源文件署名头 + docstring 覆盖率 == 100%（11 个文件）
  ✔ FR-019 THIRD_PARTY_NOTICES 的第三方运行时依赖表**无数据行**（零新增依赖）

── B4F1 人工验收 汇总 ──
硬断言 89 条 · 通过 89 · 失败 0
结论：PASS
  · 耗时 0.2s
```

> **📌 两态均实测通过**：
> ① **发行产物模式**（`.venv` · CPython 3.11.16 · freegraph 已安装）⇒ **89/89 PASS**；
> ② **源码树模式**（系统 `python3` · CPython 3.12.3 · 未安装）⇒ **89/89 PASS**
> （首行多一条「◌ 当前环境未安装 freegraph ⇒ 依赖闭包判据标『环境未就绪』」）。
> ⚠️ `typing_extensions` 判据在**未装**该包的环境里**不判失败**，但标「◌」
> ⇒ **skip ≠ pass**（SC-018 的口径）。

### 3.1 · §0 前置条件 —— 依赖面

```console
$ uv run --no-project --python .venv python -c "
import importlib.metadata as md
print('Requires-Dist:', md.requires('freegraph'))
"
Requires-Dist: None
```

### 3.2 · §1 解析主路径（验收判据 A1）

```console
$ uv run --no-project --python .venv python -c "
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
归约器是 operator.add 本身 : True
has_reducer                : True
semantics                  : reduce
value_type（基类型，无 Annotated 包装）: <class 'list'>
keys（保序）               : ('messages', 'llm_calls')
规格条数 == key 数          : True
```

**§1.2 · 验收基准同构形态（`typing_extensions.TypedDict` · SC-018）**

```console
$ uv run --no-project --python .venv python -c "
import operator
from typing import Annotated
from typing_extensions import TypedDict
from freegraph.runtime import parse_state_schema

class AnyMessage:
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
"
解析成功（非「非 TypedDict」）: True
messages.reducer is operator.add: True
messages.has_reducer           : True
messages.semantics             : reduce
llm_calls.semantics            : overwrite
```

### 3.3 · §2 默认覆盖语义（验收判据 A3）

```console
$ uv run --no-project --python .venv python -c "
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
reducer（无归约器 → 空）: None
has_reducer             : False
semantics（默认覆盖）   : overwrite
```

### 3.4 · §3 别的 `Annotated` 用法不被误判

```console
$ uv run --no-project --python .venv python -c "
import operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict):
    note: Annotated[int, '说明文字']
    hist: Annotated[list, '描述', operator.add]

spec = parse_state_schema(S)
print('note.semantics        :', spec.channels['note'].semantics)
print('note.reducer          :', spec.channels['note'].reducer)
print('hist.reducer is add   :', spec.channels['hist'].reducer is operator.add)
"
note.semantics        : overwrite
note.reducer          : None
hist.reducer is add   : True
```

### 3.5 · §4 非法 schema（快速失败 + 结构化错误）

```console
$ uv run --no-project --python .venv python -c "
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema, InvalidSchemaError
from freegraph.contracts import FreegraphError

class Bad(TypedDict):
    bad: Annotated[int, lambda a, b, c: None]

try:
    parse_state_schema(Bad)
except InvalidSchemaError as e:
    print('捕获类型            :', type(e).__name__)
    print('key（结构化字段）  :', e.key)
    print('reason（结构化字段）:', e.reason)
    print('是 ValueError 吗    :', isinstance(e, ValueError))
except FreegraphError as e:
    print('基类捕获            :', type(e).__name__)
"
捕获类型            : InvalidSchemaError
key（结构化字段）  : bad
reason（结构化字段）: reducer_not_binary
是 ValueError 吗    : True
```

```console
$ uv run --no-project --python .venv python -c "
from freegraph.runtime import parse_state_schema
from freegraph.contracts import FreegraphError
for bad in ({'a': 1}, {'a': int}):
    try:
        parse_state_schema(bad)
    except FreegraphError as e:
        print(type(e).__name__, '| key =', e.key, '| reason =', e.reason)
"
InvalidSchemaError | key = None | reason = not_a_typed_dict
InvalidSchemaError | key = None | reason = not_a_typed_dict
```

### 3.6 · §5 判定表逐条比对（A2 · SC-004）

```console
$ uv run --no-project --python .venv python -m pytest tests/runtime/ -ra
tests/runtime/test_binary_criterion.py .......................           [ 25%]
tests/runtime/test_future_annotations.py ....                            [ 30%]
tests/runtime/test_parse_contract.py .......................             [ 55%]
tests/runtime/test_schema_parse.py .....................................  [ 96%]
.                                                                        [ 97%]
tests/runtime/test_typed_dict_variants.py ..                             [100%]

============================== 90 passed in 0.77s ==============================
```

```console
$ uv run --no-project --python .venv python -m pytest tests/runtime/test_binary_criterion.py -v
collected 23 items

tests/runtime/test_binary_criterion.py::test_binary_criterion_covers_sixteen_forms PASSED [  4%]
tests/runtime/test_binary_criterion.py::test_extraction_criterion_covers_two_forms PASSED [  8%]
tests/runtime/test_binary_criterion.py::test_every_criterion_row_carries_an_upstream_source PASSED [ 13%]
tests/runtime/test_binary_criterion.py::test_every_input_name_exists_in_the_fixture_list PASSED [ 17%]
tests/runtime/test_binary_criterion.py::test_namespace_matches_the_fixture_list_name_by_name PASSED [ 21%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[1-位置专用 2 参（内置函数）] PASSED [ 26%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[2-位置或关键字 2 参] PASSED [ 30%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[3-3 个位置参数] PASSED [ 34%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[4-1 个位置参数] PASSED [ 39%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[5-1 位置参 + `*args`] PASSED [ 43%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[6-2 位置参 + `*args`] PASSED [ 47%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[7-2 位置参 + keyword-only] PASSED [ 52%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[8-仅关键字（0 位置参）] PASSED [ 56%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[9-类 · `__init__` 无参] PASSED [ 60%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[10-类 · `__init__(self, a)`] PASSED [ 65%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[11-类 · `__init__(self, a, b)`] PASSED [ 70%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[12-可调用实例 · `__call__(self, a, b)`] PASSED [ 73%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[13-可调用实例 · `__call__(self, *, a, b)`] PASSED [ 78%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[14-`functools.partial(add, 1)`] PASSED [ 82%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[15-绑定方法（`self` 已绑定）] PASSED [ 86%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[16-内置类型（签名不可取）] PASSED [ 91%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[E-1-末位**非** callable（说明文字）] PASSED [ 95%]
tests/runtime/test_binary_criterion.py::test_criterion_row_matches_the_implementation[E-2-多条目元数据（末位才是 callable）] PASSED [100%]

============================== 23 passed in 0.10s ==============================
```

> **📌 覆盖面下界的独立断言**（否则删表行仍绿）：`test_binary_criterion_covers_sixteen_forms`
> （§2 行数 **== 16**）· `test_extraction_criterion_covers_two_forms`（§3 行数 **== 2**）·
> `test_every_criterion_row_carries_an_upstream_source`（**无来源项数 == 0**）·
> `test_every_input_name_exists_in_the_fixture_list`（**缺失条数 == 0**）。

### 3.7 · §6 纯数据（不可变 / 可比较 / 投影无地址）

```console
$ uv run --no-project --python .venv python -c "
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
两次解析相等          : True
投影可 JSON 序列化    : True
投影含内存地址        : False
channels 只读         : TypeError
```

> **⚠️ 与 quickstart §6 的「期望输出」有一处不一致（**实现者实测发现 · 非缺陷**）**：
> quickstart §6 的最后一段用 `dataclasses.replace(...)` 来演示「字段不可改」，
> 但 `dataclasses.replace` 的语义是「**基于现有实例构造一个新实例**」——
> 它**不**（也**不应当**）抛异常 ⇒ 该段**没有任何输出**（上表即真实输出，
> 「字段不可改」一行**未出现**）。
> ⇒ 「不可变」的**可判定**证据由**直接赋值**给出（**修正版** · 见下），
> 并由 `tests/runtime/test_parse_contract.py::test_channel_spec_is_immutable`
> （`pytest.raises(FrozenInstanceError)`）自动守护。
> ⇒ 该 quickstart **文案**问题登记在 §5 遗留 #2。

**§6 修正版（直接赋值 + 不可哈希）**

```console
$ uv run --no-project --python .venv python -c "
import dataclasses, json, operator
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

class S(TypedDict):
    messages: Annotated[list, operator.add]
    n: int

a = parse_state_schema(S)
try:
    a.channels['n'].key = 'zzz'
except Exception as e:
    print('字段不可改（直接赋值）  :', type(e).__name__)
try:
    hash(a)
except TypeError as e:
    print('产物显式不可哈希        :', type(e).__name__)
try:
    hash(a.channels['n'])
except TypeError as e:
    print('通道规格显式不可哈希    :', type(e).__name__)
"
字段不可改（直接赋值）  : FrozenInstanceError
产物显式不可哈希        : TypeError
通道规格显式不可哈希    : TypeError
```

### 3.8 · §7 必填性（只记录不执行）

```console
$ uv run --no-project --python .venv python -c "
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
S {'a': False, 'b': False}
T {'c': True, 'd': False}
```

### 3.9 · §8 依赖与 I/O 纪律

```console
$ uv run --no-project --python .venv python -c "
import sys
import freegraph
print('顶层包已加载的子模块:', [m for m in sys.modules if m.startswith('freegraph.')])
"
顶层包已加载的子模块: []
```

```console
$ uv run --no-project --python .venv python -c "
import os, sys
from typing import Annotated, TypedDict
from freegraph.runtime import parse_state_schema

calls = []
def reducer(a, b):
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
"
新增的非标准库模块: []
归约器被调用次数    : 0
reducer 是同一对象  : True
```

> **📌 环境变量读取次数 == 0 与出站连接次数 == 0** 的断言在**子进程**里做
> （测试进程自身已导入 pytest，同进程不可用）⇒ 落
> `tests/runtime/conftest.py` 的 `run_in_subprocess` 夹具
> （**计数口径写死**：环境变量覆盖 `os.environ.__getitem__` / `os.environ.get` /
> `os.getenv` **三条**路径；出站覆盖 `socket.socket.connect` /
> `socket.create_connection` **两个**入口）⇒ 实测
> `env_reads == 0` · `egress == 0`（见
> `tests/runtime/test_parse_contract.py::test_parsing_has_no_side_effects`）。

### 3.10 · §9 层纪律与署名头

```console
$ grep -n "runtime/" specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md
98:| `src/freegraph/runtime/` | `L2` | — | **执行内核层**（B4F1 起）· 尚未存在 · 登记以保证「新增层零改动」 |
```

```console
$ uv run --no-project --python .venv python -m pytest tests/gates/test_gates.py -ra -k "G25 or G30"
collected 40 items / 32 deselected / 8 selected

tests/gates/test_gates.py ........                                       [100%]

======================= 8 passed, 32 deselected in 2.10s ====================
```

> **📌 门禁编号总数仍为 30**（T050 的可机读断言：
> `tests/runtime/test_parse_contract.py::test_gate_numbering_is_unchanged`
> —— 解析 `architecture-gates.md` §0 的「门禁总览」表 ⇒ 编号恰为 **G1…G30** 且连续）。
>
> **📌 署名头覆盖率 100%**（T051）—— 新建的 11 个源文件逐个断言
> 「首行逐字相等 + 模块 docstring 为首个语句」
> （`tests/runtime/test_parse_contract.py::test_new_source_files_carry_signature_header_and_leading_docstring`）。

### 3.11 · §10 人工验证记录本身

```console
$ ls harness/verification/B4F1/manual-verification.md
harness/verification/B4F1/manual-verification.md

$ awk '/^```/{f=!f; next} !f && /^#{2,3} /{print NR": "$0}' harness/verification/B4F1/manual-verification.md
22: ## 1. 环境
43: ## 2. 步骤
66: ## 3. 实际输出
70: ### 3.0 · ★ **一条命令**的人工验收（**推荐入口** · `harness/verification/B4F1/acceptance.py`）
174: ### 3.1 · §0 前置条件 —— 依赖面
184: ### 3.2 · §1 解析主路径（验收判据 A1）
247: ### 3.3 · §2 默认覆盖语义（验收判据 A3）
268: ### 3.4 · §3 别的 `Annotated` 用法不被误判
290: ### 3.5 · §4 非法 schema（快速失败 + 结构化错误）
331: ### 3.6 · §5 判定表逐条比对（A2 · SC-004）
381: ### 3.7 · §6 纯数据（不可变 / 可比较 / 投影无地址）
456: ### 3.8 · §7 必填性（只记录不执行）
479: ### 3.9 · §8 依赖与 I/O 纪律
526: ### 3.10 · §9 层纪律与署名头
550: ### 3.11 · §10 人工验证记录本身
588: ### 3.12 · 全量测试套件（既有门禁零破坏）
607: ### 3.13 · 最高档 venv（**CPython 3.14.7**）复跑
623: ## 4. 结论
625: ### 4.1 验收判据 A1–A3（spec §6 / 立项书 §5.2 · FR-018 · SC-013）
633: ### 4.2 逐条成功标准（SC-001 ~ SC-018）
659: ### 4.3 ✅ 发起者追认（T053 · plan 登记项 **R-1**）
693: ### 4.4 门禁与纪律复核小结
710: ## 5. 遗留问题
724: ## 6. 来源覆盖表（宪法原则 VIII · FR-018 · SC-013）
758: ## 7. 移交后续 feature
```

> **📌 五段式齐全**（环境 §1 / 步骤 §2 / 实际输出 §3 / 结论 §4 / 遗留问题 §5）
> + **来源覆盖表**（§6）+ 移交说明（§7）⇒ SC-013 的「五段式小节齐全 +
> 来源覆盖表覆盖率 == 100%」成立。

### 3.12 · 全量测试套件（既有门禁零破坏）

```console
$ uv run --no-project --python .venv python -m pytest tests/ -ra
=========================== 495 passed, 4 skipped in 19.35s ============================
```

**skip 明细（4 条 · **全部为既有 feature 的既有 skip**，与本 feature 无关）**：

```text
SKIPPED [1] tests/contracts/test_contract_regressions.py:35: 未落地 —— C4（稀疏状态读）由 B5F2（M1）建立
SKIPPED [1] tests/contracts/test_contract_regressions.py:45: 未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
SKIPPED [1] tests/facade/test_api_snapshot.py:189: 未开启 --update-api-snapshot（默认关闭 · FR-011 ①）
```

> **📌 实施前绿基线**（T005）= **405 passed / 4 skipped** ⇒ 实施后 **495 passed / 4 skipped**
> ⇒ **新增 90 条断言全绿** · **既有门禁零破坏**（skip 数不变）。

### 3.13 · 最高档 venv（**CPython 3.14.7**）复跑

```console
$ .venv314/bin/python -m pytest tests/runtime/ -ra
============================== 90 passed in 0.89s ==============================
```

```console
$ .venv314/bin/python -m pytest tests/ -ra
=========================== 495 passed, 4 skipped in 20.29s ============================
```

> **📌 多版本结论**：本 feature 的 **90 条新断言**在 **CPython 3.11.16**（最低档 ·
> typing 构件上限档）与 **CPython 3.14.7**（最高档）两档**均全绿** ⇒ 跨版本行为一致。
> **3.12 / 3.13** 两档**本轮未跑**（见 §5 遗留 #4）。

## 4. 结论

### 4.1 验收判据 A1–A3（spec §6 / 立项书 §5.2 · FR-018 · SC-013）

| 验收判据 | 结论 | 证据 |
|---|---|---|
| **A1** `Annotated[list, operator.add]` 被正确识别为**二元归约器** | ✅ **通过** | §3.2：`reducer is operator.add` → `True` · `has_reducer` → `True` · `semantics` → `reduce` · `value_type` → `<class 'list'>`（**四项全中** · SC-001） |
| **A2** 二元性判据与 LangGraph 一致 | ✅ **通过** | §3.6：判定表 **16 类二元性形态 + 2 类提取形态逐条比对**全绿（23 条用例）· **缺失条数 == 0** · **无来源项数 == 0** · 行数下限 16 / 2 达标（SC-004 · FR-016） |
| **A3** 无归约器 key 走覆盖语义 | ✅ **通过** | §3.3：`reducer` → `None` · `has_reducer` → `False` · `semantics` → `overwrite`（SC-002 · FR-006 ①） |

### 4.2 逐条成功标准（SC-001 ~ SC-018）

| SC | 结论 | 证据 |
|---|---|---|
| **SC-001** | ✅ 通过 | §3.2（四项断言全中） |
| **SC-002** | ✅ 通过 | §3.3 |
| **SC-003** | ✅ 通过 | §3.4（末位非 callable ⇒ 无归约器且解析成功）+ 判定表 §2 的 11 条「拒绝」行（**静默降级次数 == 0**） |
| **SC-004** | ✅ 通过 | §3.6（逐条比对全绿 · 行数 16 / 2 · 无来源 0 · CI 内 `langgraph` 安装次数 == 0 · 三处依赖声明零出现） |
| **SC-005** | ✅ 通过 | §3.7（两次解析相等 · 投影可序列化 · 含地址条目数 == 0 · `channels` 写操作 `TypeError` · 字段不可改 `FrozenInstanceError` · 两产物 `hash()` 抛 `TypeError`） |
| **SC-006** | ✅ 通过 | §3.5（三类非法输入拒绝率 100% · 消息点名 key · 只报第一个问题） |
| **SC-007** | ✅ 通过 | §3.9（`sys.modules` 增量非标准库 == 0 · `env_reads == 0` · `egress == 0`） |
| **SC-008** | ✅ 通过 | §3.2（条数 == key 数 == 2）+ 继承链 / `__slots__` 跳过 / 空 TypedDict 零条规格（`tests/runtime/test_schema_parse.py`） |
| **SC-009** | ✅ 通过 | §3.9（`reducer 是同一对象: True` · `归约器被调用次数: 0`） |
| **SC-010** | ✅ 通过 | `Required[...]` / `NotRequired[...]` 包裹的归约器检出率 100%（`test_schema_parse.py` + `test_future_annotations.py`） |
| **SC-011** | ✅ 通过 | `import freegraph.runtime` 后 `sys.modules` 中 `pydantic` / `typing_extensions` / `langchain*` / `langgraph*` / `langsmith` 条目数 == 0（**子进程内**断言） |
| **SC-012** | ✅ 通过 | §3.10（层注册表零改动 · L2 → L3/L4/L5 边数 == 0 · 门禁编号仍为 30 · 署名头覆盖率 100%） |
| **SC-013** | ✅ 通过 | 本文件（五段式齐全 + §6 来源覆盖表覆盖率 100% + A1–A3 逐条结论见 §4.1） |
| **SC-014** | ✅ 通过 | 五类负向用例（3 参 / 1 参 / 类 / 内置类型 / `*args`）**全部断言「抛错」**（`test_schema_parse.py`） |
| **SC-015** | ✅ 通过 | 契约层 **18** · 门面 **7** 未变 · 兼容矩阵**零新增行**（T055 的可机读断言） |
| **SC-016** | ✅ 通过 | §3.8（`total=False` ⇒ 全可选 · `NotRequired[...]` ⇒ 可选 · `Required[...]` ⇒ 必选 · **未执行任何必填性校验**） |
| **SC-017** | ✅ 通过 | §3.5（`key` + `reason` 字段齐备 · 原因码 ∈ 封闭集合 · 三个原因码各一例 · 两条捕获路径均有效） |
| **SC-018** | ✅ 通过（**未 skip**） | §3.2（`typing_extensions.TypedDict` 被**接受** · `reducer is operator.add` · `has_reducer` · `semantics`） |

> **📌 SC-018 是「环境依赖型」判据**：本机 **已装** `typing_extensions`
> ⇒ 该判据**实际执行并通过**（**非 skip**）⇒ **skip ≠ pass** 的问题在本环境**不成立**。

### 4.3 ✅ 发起者追认（T053 · plan 登记项 **R-1**）

> **依据**：宪法 **v1.7.0**「质量门禁的分阶段落地与发起者追认」（该条于
> **v1.6.0** 引入 · **窄口径**通则 · 首次适用 = B3F1）。
>
> **三条共享同一根因**：它们都要求**通道 / 状态读取 / 完整内核运行时**存在，
> 而 B4F1 按立项书 §5.2 / §6.2 只交付**解析侧**
> （通道 = **B5F1** · 稀疏读取 = **B5F2** · fresh 读 = **B8F1** ·
> 编译与执行 = **B7F2 / B7F3**）⇒ **任何 spec 设计都无法在本 feature 满足这四条**。

| # | 被偏离的门禁项 | 根因 | 判据未被放宽的论证 | 承接方（feature + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | 门禁 3 的 **C4**（稀疏状态）+ **C8**（条件边 fresh 状态）两条**独立回归** | 二者都要求**通道与状态读取**存在；B4F1 属 M1，但通道实现归 B5F1、稀疏读取归 B5F2、fresh 读归 B8F1 | 本 feature 交付的是**解析侧**（C1 / C2 / C3 的事实提取）；C4 / C8 的**判据一字未改** | **B5F2**（C4 · M1）· **B8F1**（C8 · M2） | 挂载点已存在（`tests/contracts/test_contract_regressions.py:28-29` 的 `GATE-MOUNT: C4/C8 · status=not-landed · owner=B5F2/B8F1`）⇒ 本 feature **零改动**该文件（**未**把 `status` 改成 `landed`） |
| ② | 门禁 4 的 **fake 模型跑通验收基线的一轮** | 验收基线跑通需要**完整内核运行时**（编译 + 执行），属 B7F2 / B7F3（M1 尾 / M2）⇒ B4F1 **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；本 feature 只落**挂载点**并在人工记录中标记「未落地」 | **B7F2 + B7F3**（M1 / M2） | 已就位：B3F1 的裁定 22 已把「fake 轮」的承接条款写入 `harness/features/B7F2_compile编译.md` / `B7F3_invoke返回完整状态.md` |
| ③ | 门禁 5 + 原则 V 的 **人工验证记录含真实模型一轮** | 无图可跑 ⇒ 无从接真实模型 | **五段式记录 + 来源覆盖表照常落地**（FR-018）；被延后的只是「真实模型一轮」这一**部分** | **B7F3 / B25F1**（M2 / M4） | 已就位：B25F1（双跑验收）的提示词初稿承接 fake 轮 |

**红线未被触碰**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 ·
商标红线 · 零出站红线 —— **全部在本 feature 照常执行**
（FR-013 / FR-019 + 门禁 G21 / G23 / G24 / G26 / G27）。

> **🔓 追认栏 ——【已由发起者追认 · 2026-11-08】**
>
> | 项 | 内容 |
> |---|---|
> | **追认对象** | plan.md 的**登记项 R-1**（宪法「质量门禁 3 / 4 / 5」的偏离登记） |
> | **追认人（发起者）** | **杨家成**（仓库发起者）—— 依宪法 v1.6.0 由**发起者本人**作出；实现者**未代签** |
> | **追认结论** | ✅ **追认** —— 上表三条偏离在本 feature **物理不可达成**（根因：通道 / 状态读取 / 完整内核运行时按立项书 §6.2 的 M1/M2 切分尚未落地）；**判据一字未放宽**（C4 / C8 的判据原样保留 · 挂载点 `status=not-landed` **未**改动）；**承接方与里程碑不变**（B5F2 / B8F1 / B7F2 / B7F3 / B25F1） |
> | **追认日期** | **2026-11-08** |
> | **签署** | 发起者于本会话中明示「**验收通过了**」并指示收尾与推送（**未另留书面签名** —— 实现者**不得**代签 · 宪法 v1.6.0） |
>
> **⇒ 追认完成，执行闸口 A5 通过 ⇒ 本 feature 达「可合入」状态。**
> ⚠️ 实现者**未**改宪法正文 · **未**把 `tests/contracts/test_contract_regressions.py` 的
> `GATE-MOUNT:` 标记改成 `landed`（C4 / C8 **未**由本 feature 落地）。

### 4.4 门禁与纪律复核小结

| 项 | 结论 | 可机读断言 |
|---|---|---|
| 依赖三处零新增（含 **无** `langgraph`） | ✅ | `test_dependency_declarations_contain_no_upstream_package` |
| CI **不安装** `langgraph` | ✅ | `test_ci_workflow_never_installs_langgraph` |
| 公开面 18 / 7 未变 | ✅ | `test_public_api_surface_is_unchanged` |
| 层注册表零改动（`src/freegraph/runtime/` = **L2**） | ✅ | `test_runtime_package_is_registered_as_l2_in_the_layer_registry` |
| L2 → L3/L4/L5 边数 == 0 | ✅ | `test_runtime_package_has_no_edge_to_upper_layers` |
| 门禁编号仍为 **30** 且连续 | ✅ | `test_gate_numbering_is_unchanged` |
| 署名头 + docstring 覆盖率 **100%** | ✅ | `test_new_source_files_carry_signature_header_and_leading_docstring` |
| 兼容矩阵**零新增行**（显式记「无新增」） | ✅ | `test_compat_matrix_has_no_new_row_for_this_feature` |
| `THIRD_PARTY_NOTICES` **无需新增登记** | ✅ | `test_third_party_notices_needs_no_new_entry` |
| 顶层包惰性（`import freegraph` 不加载 `freegraph.runtime`） | ✅ | §3.9（`顶层包已加载的子模块: []`） |

---

## 5. 遗留问题

| # | 事项 | 归属 / 状态 |
|---|---|---|
| **1** | ~~**发起者追认（plan 登记项 R-1）未完成**~~ —— ✅ **已关闭**（2026-11-08）：发起者已追认，追认栏见 §4.3 ⇒ 执行闸口 A5 通过 | **已完成**（tasks **T053** · §4.3） |
| **2** | **quickstart §6 的文案问题**：该节用 `dataclasses.replace(...)` 演示「字段不可改」，但 `replace` 的语义是「**构造新实例**」⇒ 实际**不抛异常**（§3.7 的真实输出中该行未出现，与 quickstart 的「期望输出」不一致）。**实现无缺陷**（不可变性由直接赋值 ⇒ `FrozenInstanceError` 证明，并被 `test_channel_spec_is_immutable` 自动守护） | `specs/b4f1-schema-reducer-parse/quickstart.md` §6 的**文案**（**实现者未改动 spec 目录工件** —— 留待发起者决定是否同步修订） |
| **3** | **`typing_extensions` 的可得性是「偶然」的**（非任何声明依赖 · v1.0 依赖面 = 零）⇒ 在**未装**该包的 CI 档，SC-018 会被 `pytest.importorskip` **skip** ⇒ **skip ≠ pass** | **B3F1 步骤 5.5**（v2.0 预验证包的传递带入 · **偶然**可得）· 本机**未 skip**（§3.2） |
| **4** | **多版本实测覆盖两档**：**CPython 3.11.16**（最低档 · typing 构件上限档）与 **3.14.7**（最高档）**均已实跑并全绿**（§3.12 / §3.13）；**3.12 / 3.13** 两档**本轮未跑** | **CI 矩阵**（`.github/workflows/ci.yml` 的 7 作业 · 3 平台 × 2 版本 + arm64 最低档）自动覆盖 —— 本记录**不**代跑 |
| **5** | **上游实时对照未做**（`langgraph` 不在本 feature 的依赖面 · 澄清 Q5）⇒ 判定表是上游行为的**固化快照**；**换上游版本时 MUST 重新核实** | **B5F2 / B8F1** 的差分夹具（research **DR-1**） |
| **6** | `Annotated[Required[T], reducer]`（`Required` 在 `Annotated` **内层**）形态下 freegraph 与上游是否逐字一致 —— 本 feature **只剥离顶层**包装 | **B5F2** 的差分夹具核实（research **DR-9**） |
| **7** | `src/freegraph/contracts/errors.py` 的「内核异常族**唯一定义处**」措辞的适用范围（= 基类与既有子类；未来子类可落在 L2） | **登记，不改文件**（research **DR-7**）· 本 feature **零改动**契约层 |

---

## 6. 来源覆盖表（宪法原则 VIII · FR-018 · SC-013）

> 每条判据 → 上游 `路径:行号`（核实版本 `langgraph 1.2.11`）· Q8 条号 ·
> 契约条款 · 宪法条款号。**无来源项数 == 0**。

| 判据 | 来源 | 备注 |
|---|---|---|
| **A1**（验收判据 · 二元归约器识别） | Q8 §3.4 **C1**（状态 schema）+ §3.4 **C2**（归约器机制）· `langgraph/graph/state.py:1904-1922` · spec FR-003 / FR-004 | 核实版本 `langgraph 1.2.11` |
| **A2**（验收判据 · 判据与上游一致） | Q8 §3.2.1（归约器提取机制）+ §3.4 **C2** · `contracts/binary-criterion.md` §1 / §2 / §3 | 契约 §2 是**判据的唯一权威** |
| **A3**（验收判据 · 无归约器走覆盖） | Q8 §3.4 **C3**（默认归约语义）· spec FR-006 ① | 执行归 **B5F1** |
| **SC-001** | spec FR-002 / FR-003 / FR-004 / FR-012 / FR-020 ① · `state.py:1904-1922` | — |
| **SC-002** | spec FR-006 · `state.py:1850-1874`（`_get_channel` 的默认通道推导） | — |
| **SC-003** | spec FR-003 ① / FR-005 / FR-007 ② · `state.py:1905-1907` | — |
| **SC-004** | spec FR-016 ①-a·①-b·②·③ · `contracts/binary-criterion.md` §2（16 行）/ §3（2 行）/ §4（夹具清单） | 上游行号逐条载于判定表 |
| **SC-005** | spec FR-010 / FR-011 · research **D-01** / **D-02** / **D-05** / **D-06** | — |
| **SC-006** | spec FR-007 ①–④ · 澄清 **Q3** · 澄清 **Q7** | — |
| **SC-007** | spec FR-013 · 宪法**原则 I**（零环境变量 · 零出站） | 门禁 G4 / G24 / G26 / G27 |
| **SC-008** | spec FR-002 / FR-009 · 裁定 12 · `state.py:1815-1836`（`_get_channels` 跳过 `__slots__`） | — |
| **SC-009** | spec FR-012 / FR-013 · 裁定 10 | — |
| **SC-010** | spec FR-008 · 裁定 4 · `state.py:1850-1858`（**先剥离** `Required` / `NotRequired`） | — |
| **SC-011** | spec FR-001 ② / FR-013 / FR-019 · 宪法**原则 II**（内核纯净）+ **原则 IX**（许可证 / 商标红线 · NON-NEGOTIABLE） | 门禁 G21 / G22 / G23 |
| **SC-012** | spec FR-014 / FR-019 · `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（`src/freegraph/runtime/` = **L2**）· 宪法**原则 X** | 门禁 G25 / G30 |
| **SC-013** | spec FR-018 · 宪法**原则 V**（人工验收）+ **原则 VIII**（证据纪律） | 本文件 |
| **SC-014** | spec FR-017 · 立项书 §10 的风险提示 | 五类负向用例 |
| **SC-015** | spec FR-015 / FR-019 · 裁定 6 ③ · `contracts/public-api.md` §0（18 个）· `src/freegraph/graph.py`（7 个） | 门禁 G7 / G15 / G19 |
| **SC-016** | spec FR-021 · 澄清 **Q2** | 校验归 **B7F3** |
| **SC-017** | spec FR-007 ⑤⑥ · 裁定 2 / 裁定 14 · 澄清 **Q4** / **Q7** | 与仓库既有异常体系同构（`contracts/errors.py`） |
| **SC-018** | spec FR-001 ① · 裁定 3 · `harness/demo/target.py:59-61`（**只读基准** · 宪法**原则 III**） | `typing.is_typeddict` 对 `typing_extensions.TypedDict` 返回 `False`（实测） |
| **零新增依赖** | spec FR-016 ②③ / FR-019 · 澄清 **Q5** · 宪法**原则 IX** | 三处声明 + `ci.yml` 安装步骤 = **第 4 处**声明位 |
| **人工验收脚本** | `harness/verification/B4F1/acceptance.py`（tasks **T058** · 沿用 **B1F1 / B2F1 / B2F2** 的既有形态）· 判据表**解析** `contracts/binary-criterion.md`（**唯一权威**）⇒ 不另抄一份 | 零第三方依赖 · 两态运行 · `--record` 产出五段式片段 |
| **人工门禁 3 / 4 / 5 的偏离** | plan.md **登记项 R-1** · 宪法 **v1.6.0**「质量门禁的分阶段落地与发起者追认」 | **§4.3 追认栏已填**（追认人 **杨家成** · 结论 **追认** · 日期 2026-11-08） |

---

## 7. 移交后续 feature

| 承接方 | 消费什么 | 本 feature 提供什么 |
|---|---|---|
| **B5F1**（通道实现 · M1） | `SchemaSpec` / `ChannelSpec` ⇒ 推导 `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue` | 解析产物 + `semantics` 标记（`overwrite` / `reduce`） |
| **B6F1**（`StateGraph` 构建器 · M2） | `StateGraph(schema)` 内部调用解析入口 | 解析入口 `freegraph.runtime.parse_state_schema`（**L2 内部 API** · 非公开门面） |
| **B5F2**（稀疏读取 · C4 · M1） | 无（只消费通道的运行期语义） | —（**C4 的回归测试由 B5F2 落地** —— 见 §4.3 ①） |
| **B7F3**（调用入参校验 · M2） | `required` 标记 | 必填性事实（**只记录不执行**） |
| **B8F1**（条件边 fresh 读 · C8 · M2） | 无 | —（**C8 的回归测试由 B8F1 落地** —— 见 §4.3 ①） |
| **B25F1**（双跑验收 · M4） | 无 | —（**fake 轮 / 真实模型轮**由后续 feature 承接 —— 见 §4.3 ②③） |
