# B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue` —— 人工验证记录

**feature**: B5F1（M1 运行时内核 · L2 执行内核层 · 通道抽象 + 三类通道）
**验收依据**: `specs/b5f1-channels/spec.md` · `plan.md` · `tasks.md` · `contracts/channel-contract.md` · `contracts/upstream-parity.md`
**验收指南**: [`specs/b5f1-channels/quickstart.md`](../../../specs/b5f1-channels/quickstart.md)
**记录日期**: 2026-11-09
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：① 环境 ② 步骤 ③ 实际输出 ④ 结论
> ⑤ 遗留问题 + ⑥ 来源覆盖表 + ⑦ 移交后续 feature）。
> 第 3 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的项逐条登记在第 5 节。
>
> **✅ 发起者追认已作出**（T042 · plan 登记项 **R-1**）—— 发起者于 **2026-11-09**
> 在本会话中明示「**追认**」并指示收尾与提交推送 ⇒ 追认栏见 **§4.3**。
> 依宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」，该追认由**发起者本人**作出，
> 实现者**未代签**、**未改**宪法正文、**未**写一条永久红的 CI、**未**把 C4 / C8 的
> ``GATE-MOUNT:`` 标记改成 ``landed`` ⇒ 执行闸口 **A5 通过** ⇒ **可合入**。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python（**主判定档** · `.venv`） | **3.11.16**（CI 矩阵的**最低档**） |
| 平台 | Linux-6.8.0-139-generic-x86_64-with-glibc2.39 |
| uv / pytest / coverage | **0.12.7** / **9.2.0** / **7.17.2**（coverage 是**开发期工具** · 未进 `pyproject.toml`） |
| freegraph 版本 | **0.0.3**（**可编辑安装** · `uv pip install -e .`） |
| `requires-python` | `>=3.11` |
| **v1.0 的发行元数据** | **零依赖包名** —— `dependencies = []`（**三处**声明零新增） |
| **人工验收入口** | `harness/verification/B5F1/acceptance.py`（**单文件 · 零第三方依赖** · **一条命令跑完全部验收** · 149 条断言 · 两态运行：已安装 ⇒ 测发行产物 / 未安装 ⇒ 测源码树 · 退出码 0 / 1 / 2） |
| 核实环境（上游行号） | **`langgraph 1.2.11`**（`contracts/upstream-parity.md` 的 `路径:行号` 全部指向该版本） |
| 基线提交 | `51a862e`（B4F1 落地后的仓库状态） |

---

## 2. 步骤

### 2.0 · ★ 前置准备（**先做这一步** · 一次装齐）

> ⚠️ **必须用 `.venv` 的解释器** —— 仓库自带 `.venv`（**主判定档** · CPython 3.11.16
> = CI 矩阵的**最低档**）。系统 `/usr/bin/python3` 是 **externally managed**
> （PEP 668）⇒ 在那儿 `pip install` 会**失败**（退出码 2）。

```bash
cd /home/ctyun/workspace/github/freegraph

# ① 发行产物（**可编辑安装**）—— 门禁 G27 / G28 会重跑 pytest，
#    其中 7 条用例读 freegraph 的 dist-info 元数据 ⇒ **不装会假红**
uv pip install --python .venv/bin/python -e .

# ② 开发期取证工具（**不进**仓库依赖声明 · research D-13）
#    ⇒ 缺它时「覆盖率取证」段标「◌ 环境未就绪」（**skip ≠ pass**）
uv pip install --python .venv/bin/python coverage
```

**然后用**同一个解释器**跑验收**（**装与跑必须是同一个 python**）：

```bash
.venv/bin/python harness/verification/B5F1/acceptance.py
```

> ⚠️ **常见错位**：`uv pip install -e .`（**不带** `--python`）会**自动发现**
> 项目里的 `.venv` ⇒ 装进 `.venv`；而 `python3 harness/...` 跑的是
> `/usr/bin/python3` ⇒ 那边**仍然没有** freegraph ⇒ 脚本报「未安装」。
> ⇒ **要么**用 `--python .venv/bin/python` 显式指定，**要么**先
> `source .venv/bin/activate` 再用 `python3`。
> ⇒ 验收脚本在这种情况下会**点名**你的解释器并给出上表的**确切**命令。

**两条都装齐后**，验收脚本才是 **149 条硬断言全绿**；
只装 ① 时是 **143 条**（覆盖率段整段跳过），只装 ② 时门禁 G27 / G28 会报
「共 1 条违规」——那**不是** B5F1 的缺陷，是 ① 没做（或装错了解释器）。

### 2.1 · 验收步骤一览

| # | 场景 | 命令 | 关联判据 |
|---|---|---|---|
| **★** | **一条命令跑完全部验收**（**推荐入口**） | `.venv/bin/python harness/verification/B5F1/acceptance.py` | A1–A3 + SC-001…SC-028（**149 条**）· 输出见 §3.1 |
| ★ | 同上 · 只跑语义与冻结面（**快档**，≈ 0.1 s） | `.venv/bin/python harness/verification/B5F1/acceptance.py --skip-coverage --skip-gates` | 同上（131 条） |
| ★ | 同上 · 产出可并入本记录的**五段式片段** | `.venv/bin/python harness/verification/B5F1/acceptance.py --record out.md` | FR-026 ② |
| 0 | 前置条件 · 依赖面 | quickstart §0.2 的 `python -c` 脚本 | FR-015 |
| 1 | 覆盖语义（**验收判据 A2**） | quickstart §1 的 `python -c` 脚本 | SC-001 · SC-020 |
| 2 | 归约语义（**验收判据 A1**） | quickstart §2 的 `python -c` 脚本 | SC-002 · SC-010 · SC-021 |
| 3 | 路由通道清空（**验收判据 A3**） | quickstart §3 的 `python -c` 脚本 | SC-003 · SC-023 |
| 4 | 一步内多值冲突 ⇒ 显式失败 | quickstart §4 的 `python -c` 脚本 | SC-006 · SC-025 |
| 5 | 映射入口（schema → 通道） | quickstart §5 的 `python -c` 脚本 | SC-008 · SC-019 |
| 6 | 零副作用（`sys.modules` / 环境变量 / 出站） | quickstart §6 的 `python -c` 脚本 · `pytest tests/runtime/test_channel_purity.py` | SC-005 |
| 7 | 规模口径（引用白名单 + 计数探针） | quickstart §7 的 `python -c` 脚本 | SC-022 |
| 8 | 全量测试套件 | `pytest tests/ -ra` | 全部（既有门禁零破坏） |
| 8.1 | 覆盖率取证（`--branch` **必须**） | `coverage run --branch -m pytest -q tests/runtime` → `coverage json -o cov.json` → `coverage report --include="src/freegraph/runtime/*" --show-missing` | SC-015（**阻断判据**） |
| 9 | 冻结面审计（公开面 / 兼容矩阵 / 层注册表 / 门禁编号 / C4·C8 挂载点） | quickstart §9 的四段命令 | SC-011 · SC-012 |
| — | 10 条门禁脚本 | `harness/scripts/gates/gate_G*.py`（**不传参数** ⇒ 与 CI 逐字同构） | SC-011 · SC-012 |

> 📌 验收脚本已把上表里的 **8.1（覆盖率取证）** 与 **门禁** 两段**自动跑掉** ⇒
> 日常**只需 §2.0 的两条安装 + 一条命令**。

---

## 3. 实际输出

> **原样粘贴真实输出**（FR-020 · MUST NOT 伪造输出）。

### 3.0 · ★ **一条命令**的人工验收（**推荐入口**）

```bash
.venv/bin/python harness/verification/B5F1/acceptance.py
```

**汇总**：

```text
── B5F1 人工验收 汇总 ──
硬断言 149 条 · 通过 149 · 失败 0
结论：PASS
  · 耗时 47.6s
```

<details>
<summary><b>展开完整输出（149 条断言 · 14 个分组）</b></summary>

```text
══ acceptance · B5F1 通道抽象 + 三类通道 ══

[运行环境]

[验收判据 A1 · 归约语义]
  ✔ A1 归约型通道初始「有值」（空值）
  ✔ A1 初始值 == 推导出的空值 []
  ✔ A1 累积结果 == 逐元素 [m1, m2]
  ✔ A1 结果 == **从初始空值起**的逐次归约（SC-021）
  ✔ A1 归约器**按引用**持有（身份判定）
  ✔ A1 `max` 归约器同样按「空值起折」基准

[验收判据 A2 · 覆盖语义]
  ✔ A2 覆盖型通道初始「无值」
  ✔ A2 首次写入返回**真**（本次写了值）
  ✔ A2 写 1 后读到 1
  ✔ A2 第二次写入返回**真**
  ✔ A2 连续写入后读到**末值** 2（不是累加 3）
  ✔ A2 结果**不是** 1 + 2（未走归约路径）
  ✔ A2 覆盖型**不持有**归约器（reducer is None）
  ✔ A2 空序列写入返回**假**（无操作）

[验收判据 A3 · 路由清空]
  ✔ A3 路由型初始「无值」
  ✔ A3 写入后读得到
  ✔ A3 `clear()` 返回**真**（状态真的变化）
  ✔ A3 清空后判定为「无值」
  ✔ A3 清空后读取抛 `EmptyChannelError`（不是 None 冒充有值）
  ✔ A3 清空后再写入恢复「有值」
  ✔ A3 清空后新值 == 刚写入的值（无残余状态）
  ✔ A3 再次 `clear()`（从「有值」清成「无值」）返回**真**
  ✔ A3 已是「无值」再 `clear()` 返回**假**（幂等）

[冲突显式失败]
  ✔ 冲突错误的 `key` == 通道 key
  ✔ 冲突错误的 `received_count` == 2
  ✔ 冲突错误的 `expected_count` **恒为 1**
  ✔ 冲突时通道**值不变**（仍无值）
  ✔ 冲突错误的 `key` == 通道 key
  ✔ 冲突错误的 `received_count` == 2
  ✔ 冲突错误的 `expected_count` **恒为 1**
  ✔ 冲突时通道**值不变**（仍无值）
  ✔ 冲突后通道的**原值**仍在（先检测后写入）

[有值 / 无值可判定]
  ✔ 从未写入 ⇒ 判定为「无值」
  ✔ 从未写入 ⇒ 读取抛错
  ✔ 写入 `None` ⇒ 判定为「有值」
  ✔ 写入 `None` ⇒ 读取返回 `None`
  ✔ 从未写入 ⇒ 判定为「无值」
  ✔ 从未写入 ⇒ 读取抛错
  ✔ 写入 `None` ⇒ 判定为「有值」
  ✔ 写入 `None` ⇒ 读取返回 `None`
  ✔ 归约型初始「有值（空值）」
  ✔ 归约型初始值 == 推导出的空值
  ✔ LastValue 清空后一律「无值」
  ✔ BinaryOperatorAggregate 清空后一律「无值」
  ✔ EphemeralValue 清空后一律「无值」

[空值推导（6 类）]
  ✔ 空值推导 list ⇒ []
  ✔ 空值推导 int ⇒ 0
  ✔ 空值推导 str ⇒ ''
  ✔ 空值推导 dict ⇒ {}
  ✔ 空值推导 Sequence ⇒ []
  ✔ 空值推导 MutableSequence ⇒ []
  ✔ 空值推导 Set ⇒ set()
  ✔ 空值推导 Mapping ⇒ {}
  ✔ 不可实例化类型 ⇒ 初始「无值」
  ✔ 不可实例化类型的首次**单值**写入 ⇒ 归约器调用次数 == 0
  ✔ 不可实例化类型的首次写入**直存**新值
  ✔ 两个同类型通道的空值**不是同一对象**
  ✔ 多值首写 ⇒ 归约器调用次数 == 值数 − 1

[映射入口]
  ✔ 映射**保序**（键序 == `SchemaSpec.keys` 序）
  ✔ 通道数 == schema 的 key 数
  ✔ 有归约器 ⇒ `BinaryOperatorAggregate`
  ✔ 无归约器 ⇒ `LastValue`
  ✔ 归约型通道的 `reducer` **就是**规格里的同一引用
  ✔ `build_channel` 单入口 ⇒ `LastValue`
  ✔ 路由通道**不由** schema 派生
  ✔ 路由通道支持**直接实例化**
  ✔ 规格标注「有归约器」但归约器为空 ⇒ 内置 `ValueError`

[纯净性与规模探针]
  ✔ LastValue 公开属性集合恰为四项
  ✔ LastValue 实例槽位集合 ⊆ 四项
  ✔ LastValue 实例**无** `__dict__`
  ✔ BinaryOperatorAggregate 公开属性集合恰为四项
  ✔ BinaryOperatorAggregate 实例槽位集合 ⊆ 四项
  ✔ BinaryOperatorAggregate 实例**无** `__dict__`
  ✔ EphemeralValue 公开属性集合恰为四项
  ✔ EphemeralValue 实例槽位集合 ⊆ 四项
  ✔ EphemeralValue 实例**无** `__dict__`
  ✔ N=1 引用类型**白名单**违例 == 0
  ✔ N=1000 引用类型**白名单**违例 == 0
  ✔ 引用数与 key 数**无关**（计数探针 · 辅助判据）
  ✔ 通道**浅引用**用户对象（身份判定）
  ✔ 通道**不校验**写入值的类型
  ✔ 写入入口**只有** `update()`（无同步原语）

[名字面逐字一致]
  ✔ 操作名 `update` 在位
  ✔ 操作名 `get` 在位
  ✔ 操作名 `is_available` 在位
  ✔ 操作名 `clear` 在位
  ✔ 属性名 `reducer` 在位（只读 property）
  ✔ 属性名 `value` 在位（只读 property）
  ✔ 属性名 `value_type` 在位（只读 property）
  ✔ 属性名 `key` 在位（只读 property）
  ✔ 类名 `Channel` 在位
  ✔ 类名 `LastValue` 在位
  ✔ 类名 `BinaryOperatorAggregate` 在位
  ✔ 类名 `EphemeralValue` 在位
  ✔ 映射入口名 `build_channel` 在位
  ✔ 映射入口名 `build_channels` 在位
  ✔ 错误名 `EmptyChannelError` 在位
  ✔ 错误名 `InvalidChannelUpdateError` 在位

[构造期校验]
  ✔ 归约器不可调用 ⇒ 内置 `TypeError`
  ✔ 归约器为空 ⇒ 内置 `ValueError`
  ✔ 通道层**不重做**二元性校验（非二元归约器不报错）

[错误契约]
  ✔ `EmptyChannelError` 可被 `except FreegraphError` 捕获
  ✔ `EmptyChannelError` **不是** `ValueError` 的子类
  ✔ `InvalidChannelUpdateError` **双重继承** `FreegraphError` + `ValueError`
  ✔ `EmptyChannelError.key` == 通道 key
  ✔ 错误对象**不携带**用户写入的值
  ✔ 清空后的错误**不携带**旧值

[零副作用]
  ✔ 导入 `freegraph.runtime` 的 `sys.modules` **非标准库增量 == 0**
  ✔ L2 内部 API 的导出符号数 == 12

[契约守卫]
  ✔ 契约权威标记在位
  ✔ 契约 §6 的不变量 **I-1…I-23** 齐全
  ✔ 上游对照表 **P-01…P-12** 齐全
  ✔ 上游对照表标注核实版本（`langgraph 1.2.11`）
  ✔ 六类语义 ① 覆盖语义
  ✔ 六类语义 ③ 空值推导
  ✔ 六类语义 ⑤ 清空语义
  ✔ 六类语义 ⑥ 有值 / 无值判定

[冻结面审计]
  ✔ SC-012 契约层公开符号面仍为 **18** 个
  ✔ SC-012 门面公开符号面仍为 **7** 个
  ✔ SC-012 兼容矩阵**零新增行**（符号集合 == 契约层 18 + 门面 7）
  ✔ SC-012 依赖三处声明**零**「langgraph」
  ✔ SC-012 依赖三处声明**零**「langchain」
  ✔ SC-012 依赖三处声明**零**「langsmith」
  ✔ SC-012 依赖三处声明**零**「typing_extensions」
  ✔ SC-012 依赖三处声明**零**「typing-extensions」
  ✔ SC-012 CI 作业内 `langgraph` 安装次数 == 0
  ✔ SC-011 层注册表把 `src/freegraph/runtime/` 登记为 **L2**（零改动）
  ✔ SC-011 L2 → L3 / L4 / L5 的边数 == 0
  ✔ SC-012 门禁编号总数仍为 **30** 且连续
  ✔ SC-011 新建源文件署名头 + docstring 覆盖率 == 100%（7 个文件）
  ✔ SC-012 `THIRD_PARTY_NOTICES` 的第三方运行时依赖表**无数据行**（零新增依赖）

[覆盖率取证（SC-015）]
  ✔ SC-015 `src/freegraph/runtime/channel.py` **行覆盖 == 100%**
  ✔ SC-015 `src/freegraph/runtime/channel.py` **分支覆盖 == 100%**
  ✔ SC-015 `src/freegraph/runtime/mapping.py` **行覆盖 == 100%**
  ✔ SC-015 `src/freegraph/runtime/mapping.py` **分支覆盖 == 100%**
  ✔ SC-015 `src/freegraph/runtime/errors.py` 的**新增部分**未覆盖行 == 0（差分口径）
  ✔ SC-015 `src/freegraph/runtime/errors.py` 的**新增部分**未覆盖分支 == 0（差分口径）
  ✔ SC-015 `src/freegraph/runtime/__init__.py` 的**新增部分**未覆盖行 == 0（差分口径）
  ✔ SC-015 `src/freegraph/runtime/__init__.py` 的**新增部分**未覆盖分支 == 0（差分口径）
  · 整包 src/freegraph/runtime/ 覆盖率（记录 · 不阻断）：行 93.93939393939394%

[门禁实跑（10 条）]
  ✔ 门禁 G21 通过（gate_G21_dependencies.py）
  ✔ 门禁 G23 通过（gate_G23_licenses.py）
  ✔ 门禁 G24 通过（gate_G24_config_layer.py）
  ✔ 门禁 G25 通过（gate_G25_import_graph.py）
  ✔ 门禁 G26 通过（gate_G26_network_static.py）
  ✔ 门禁 G29 通过（gate_G29_contract_carrier.py）
  ✔ 门禁 G30 通过（gate_G30_attribution.py）
  ✔ 门禁 G22 通过（gate_G22_isolated_env.py）〔Linux only · 只观测不阻断〕
  ✔ 门禁 G27 通过（gate_G27_zero_egress.py）〔Linux only · 只观测不阻断〕
  ✔ 门禁 G28 通过（gate_G28_offline_equiv.py）〔Linux only · 只观测不阻断〕

── B5F1 人工验收 汇总 ──
硬断言 149 条 · 通过 149 · 失败 0
结论：PASS
  · 耗时 45.8s
```

</details>

### 3.1 · quickstart §1–§9 的实测输出（**验收闸口 V1–V9**）

```text
── §1 覆盖语义 ──
初始有值？ False
写 1 后 = 1
再写 2 后 = 2
归约器 = None
── §2 归约语义 ──
初始有值？ True 初值 = []
累积结果 = ['m1', 'm2']
与空值起折一致？ True
归约器是 operator.add 本身？ True
── §3 路由清空 ──
清空前 = tool_node
清空后有值？ False
清空后读取抛出 = EmptyChannelError
清空后再写 = other
── §4 冲突 ──
抛出 = InvalidChannelUpdateError
结构化字段：key = k · received = 2 · expected = 1
仍无值？ True
── §5 映射 ──
通道类型： {'messages': 'BinaryOperatorAggregate', 'llm_calls': 'LastValue'}
保序？ True
归约器是同一引用？ True
单入口类型： LastValue
── §6 零副作用 ──
非标准库增量 = []
导出符号数 = 12
── §7 规模口径 ──
N=    1 直接引用数=5  白名单违例=[]
N= 1000 直接引用数=5  白名单违例=[]
⇒ 计数相等？ True
── §9 冻结面 ──
契约层符号数 = 18 · 门面符号数 = 7
```

**验收闸口 V1–V9 的逐条结论**：

| 闸口 | 内容 | 对应判据 | 实测 | 结论 |
|---|---|---|---|---|
| **V1** | 覆盖语义：连续两次写入 ⇒ 读到**末值** | A2 · SC-001 | `再写 2 后 = 2` · `归约器 = None` | ✅ |
| **V2** | 归约语义：写入序列 == **从空值起**的逐次归约 | A1 · SC-002 / SC-021 | `与空值起折一致？ True` | ✅ |
| **V3** | 路由清空：`clear()` ⇒ **无值**（抛错，不返回 `None`） | A3 · SC-003 | `清空后有值？ False` · `抛出 = EmptyChannelError` | ✅ |
| **V4** | 冲突显式失败：多值 ⇒ `InvalidChannelUpdateError` + **值不变** | SC-006 · SC-025 | `received = 2 · expected = 1` · `仍无值？ True` | ✅ |
| **V5** | 可判定性：「无值」与「值为 `None`」严格可分；清空后**一律**无值 | SC-004 · SC-023 | 见 §3.0 的「有值 / 无值可判定」组 | ✅ |
| **V6** | 映射正确：类型 / 保序 / 归约器**身份** | SC-008 · SC-019 | `保序？ True` · `归约器是同一引用？ True` | ✅ |
| **V7** | 纯净性与规模：属性集 ⊆ 4 项；引用数与 key 数**无关**；浅引用 | SC-009 · SC-022 · SC-025 | `白名单违例=[]` · `⇒ 计数相等？ True` | ✅ |
| **V8** | 零副作用：导入无副作用 / 零环境变量 / 零出站；依赖三处零新增 | SC-005 · SC-012 | `非标准库增量 = []` | ✅ |
| **V9** | 交付面：覆盖率 **100%**（行 + 分支）+ 验收脚本 **PASS** + 记录五段式 | SC-015 · SC-027 · SC-013 | §3.2 + §3.0 + 本文件 | ✅ |

### 3.2 · §8 · 覆盖率取证（SC-015 · FR-019 ② · 裁定 17 ⑤）

```bash
coverage run --branch -m pytest -q tests/runtime
coverage json -o cov.json
coverage report --include="src/freegraph/runtime/*" --show-missing
```

```text
315 passed in 2.27s
Name                                Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------
src/freegraph/runtime/__init__.py       6      0      0      0   100%
src/freegraph/runtime/channel.py      125      0     34      0   100%
src/freegraph/runtime/errors.py        30      1      6      1    94%   102
src/freegraph/runtime/mapping.py       12      0      4      0   100%
src/freegraph/runtime/reducer.py       20      0      4      0   100%
src/freegraph/runtime/schema.py       109      7     32      6    89%   272, 280, 292->294, 320, 346-349
-------------------------------------------------------------------------------
TOTAL                                 302      8     80      7    96%
```

**三个数字**（口径见 spec FR-019 ② / SC-015 · 澄清轮 Q14）：

| # | 口径 | 实测 | 判据 |
|---|---|---|---|
| ① | **本 feature 新增**的 `channel.py` / `mapping.py` **全文** | **行 100% · 分支 100%** | ✅ **阻断判据**已达成 |
| ① | `errors.py` / `__init__.py` 的**新增部分**（**差分口径**） | 见下 | ✅ 未覆盖新增行 == 0 · 新增分支 == 0 |
| ② | **整包** `src/freegraph/runtime/` 的覆盖率 | **96%** | ✅ **记录但 MUST NOT 阻断**（B4F1 无 100% 基线） |

**差分口径**（`git diff -U0` 的新增行号集合 ∩ `coverage json` 的 `missing_lines` / `missing_branches`）：

```text
src/freegraph/runtime/errors.py: 新增行=97 未覆盖新增行=[] 未覆盖新增分支=[]
src/freegraph/runtime/__init__.py: 新增行=40 未覆盖新增行=[] 未覆盖新增分支=[]
```

> ⚠️ **三条取证纪律**（裁定 17 ⑤ · research D-17 实测）：
> ① 分支覆盖 MUST 以 **`--branch`** 取证（无 `--branch` 时 `coverage report`
> **不输出 Branch 列** ⇒ 分支覆盖**无从判定**）；
> ② **文件级**报告**无法**区分「既有行」与「新增行」⇒ MUST NOT 单独作判据；
> ③ 「新增部分」**必须**走上面的**差分口径**。

### 3.3 · §8 · 全量测试套件（既有门禁零破坏）

```bash
pytest tests/ -ra
```

```text
720 passed, 4 skipped in 19.48s
```

> **对照实现前的绿基线**（T005 · B5F1 落地**之前**）：**495 passed / 4 skipped**
> ⇒ **既有门禁零破坏**（4 条 skip 的**条目**逐条一致 · 无新增 skip）。

### 3.4 · 门禁实跑（10 条 · SC-011 / SC-012）

| 门禁 | 分组 | 退出码 | 输出摘要 |
|---|---|---|---|
| **G21** 依赖黑名单 | 本地直跑（**硬断言**） | **0** | 通过 |
| **G23** 许可证 | 本地直跑（**硬断言**） | **0** | 通过 |
| **G24** 配置层扫描 | 本地直跑（**硬断言**） | **0** | 通过 |
| **G25** 导入图单向 | 本地直跑（**硬断言**） | **0** | 通过（新增的 `channel.py` / `mapping.py` = **L2** ⇒ 自动纳入扫描） |
| **G26** 网络静态扫描 | 本地直跑（**硬断言**） | **0** | 通过 |
| **G29** 契约载体 | 本地直跑（**硬断言**） | **0** | 通过 |
| **G30** 全仓署名头 | 本地直跑（**硬断言**） | **0** | 通过（新增 7 个源文件署名头 + docstring 覆盖率 == **100%**） |
| **G22** 隔离环境 | Linux only（只观测） | **0** | `[G22] PASS —— 隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）` |
| **G27** 零出站动态 | Linux only（只观测） | **0** | `[G27] PASS —— 零出站动态断言（只观测不阻断 + 第一个非标准库帧归因）` |
| **G28** 断网等价性 | Linux only（只观测） | **0** | `[G28] PASS —— 断网等价性（Linux 网络命名空间 · 全量测试套件 + 可读排除清单）`；`717 passed, 4 skipped, 3 deselected` |

> ⚠️ **G28 的环境限制**：本机 `unshare --net --map-root-user` **不可用**
> （`/proc/self/uid_map` 写失败 —— 容器 **AppArmor** 限制）⇒ **命名空间由外层施加**
> 的那一步在本机**无法完成** ⇒ 按 tasks T043 的**纪律**（**MUST NOT** 在无命名空间
> 权限的环境下裸跑并把失败当作本 feature 的缺陷），此处记录的是**脚本本体**的实测
> ⇒ **命名空间隔离这一层**归 CI 的 Linux 作业实测（见 §5 的遗留 #1）。

---

## 4. 结论

### 4.1 验收判据 **A1–A3**（引文 §6 / 立项书 §5.2 · FR-020 · SC-013）

| 判据 | 内容 | 实测 | 结论 |
|---|---|---|---|
| **A1** | 归约器 `operator(current, new)` 语义一致（**从空值起折**） | `累积结果 = ['m1', 'm2']` · `与空值起折一致？ True` · `归约器是 operator.add 本身？ True` | ✅ **通过** |
| **A2** | 无归约器 key 被覆盖（连续写入 ⇒ 读到**末值**） | `再写 2 后 = 2` · `归约器 = None` | ✅ **通过** |
| **A3** | 路由通道每 super-step 清空（清空后**无值**） | `清空后有值？ False` · `清空后读取抛出 = EmptyChannelError` · `清空后再写 = other` | ✅ **通过** |

### 4.2 逐条成功标准（SC-001 ~ SC-028）

| SC | 摘要 | 承载 | 实测 | 结论 |
|---|---|---|---|---|
| SC-001 | 覆盖语义 · 末值 · 归约器调用 0 | T009/T012 | §3.1 §1 | ✅ |
| SC-002 | 归约语义 == 逐次归约 | T014/T019 | §3.1 §2 | ✅ |
| SC-003 | 路由清空后无值 | T021/T024 | §3.1 §3 | ✅ |
| SC-004 | 有值 / 无值 100% 可判定 · 无第三态 | T007/T010 | §3.0 | ✅ |
| SC-005 | 零副作用（三断言） | T030 | §3.1 §6 | ✅ |
| SC-006 | 多值抛错率 100% · 值不变 | T012/T016/T022 | §3.1 §4 | ✅ |
| SC-007 | 空值推导 6 类 + 空值独立 | T015/T018 | §3.0 | ✅ |
| SC-008 | 映射正确率 100% · 保序 · 身份 | T026/T027 | §3.1 §5 | ✅ |
| SC-009 | 纯净性（属性集 + 槽位集） | T007/T010/T029 | §3.0 | ✅ |
| SC-010 | 归约器引用保持率 100% | T014/T019 | §3.1 §2 | ✅ |
| SC-011 | L2 → L3/L4/L5 边数 0 · 署名头 100% | T008/T039/T043 | §3.4 | ✅ |
| SC-012 | 公开面 18 / 7 未变 · 兼容矩阵零新增 | T035/T039/T043 | §3.1 §9 | ✅ |
| SC-013 | 人工记录五段式 + A1–A3 逐条结论 + 来源覆盖表 100% | T005/T041 | 本文件 | ✅ |
| SC-014 | 六类语义逐条标上游行号 | T035 | §6.2 | ✅ |
| SC-015 | 新增代码行 / 分支覆盖 100% | T036 | §3.2 | ✅ |
| SC-016 | 四类负向用例存在且全绿 | T016/T022 | §3.0 | ✅ |
| SC-017 | 可替换性（自定义子类） | T028 | `tests/runtime/test_channel_semantics.py` | ✅ |
| SC-018 | 错误捕获 100% · 字段齐备 · 不带用户值 | T006/T011/T022 | §3.0 | ✅ |
| SC-019 | 名字面逐字一致 | T013/T020/T025/T026/T028/T034 | §3.0 | ✅ |
| SC-020 | `update()` 返回值口径 | T007/T009/T012 | §3.0 | ✅ |
| SC-021 | 折叠基准 = 从初始值起 | T014/T015/T018/T019 | §3.1 §2 | ✅ |
| SC-022 | 规模口径（白名单 + 计数探针） | T029 | §3.1 §7 | ✅ |
| SC-023 | 初始状态三档 + 清空后无值 | T007/T010/T017/T023 | §3.0 | ✅ |
| SC-024 | 无锁 · 写入入口唯一 · 不进公开面 | T029/T039 | §3.0 | ✅ |
| SC-025 | 浅引用 · 身份判定 · 不校验类型 | T029 | §3.0 | ✅ |
| SC-026 | 构造期校验（内置异常）· 不重做二元性 | T016/T027/T032 | §3.0 | ✅ |
| SC-027 | 独立验收脚本存在 · 全绿 · 五段式 · 零第三方 | T004/T037/T038/T040 | §3.0 | ✅ |
| SC-028 | 参数化组合 ≥ 12 · 无 skip/xfail | T031 | `tests/runtime/test_channel_semantics.py`（14 组 × 3 组断言 = 42 条） | ✅ |

⇒ **SC 28/28 全覆盖**（逐条对应 `tasks.md` 的**反向覆盖核对**）。

### 4.3 ✅ **发起者追认**（T042 · plan 登记项 **R-1**）

> **依据**：宪法 **v1.7.0**「质量门禁的分阶段落地与发起者追认」（该条于
> **v1.6.0** 引入 · **窄口径**通则 · 首次适用 = B3F1 · B4F1 沿用同一处置）。
>
> **三条共享同一根因**：它们都要求**完整内核运行时**（状态读取层 + 调度循环 +
> 编译执行）存在，而 B5F1 按立项书 §5.2 / §6.2 只交付**通道层**
> （读取 = **B5F2** · fresh 读 = **B8F1** · 调度 = **B7F1** ·
> 编译与执行 = **B7F2 / B7F3**）⇒ **任何 spec 设计都无法在本 feature 满足这四条**。

| # | 被偏离的门禁项 | 不可达成的根因 | 判据未被放宽的论证 | 承接方（feature + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**C4**（稀疏状态）+ **C8**（条件边 fresh 状态）两条**独立回归测试**」 | 二者都要求**状态读取层**与**调度循环**存在；C4 的读取属 **B5F2**、C8 的 fresh 读属 **B8F1**、super-step 循环属 **B7F1** ⇒ B5F1 属 M1 第 6 个，**按里程碑不交付其前置能力** | 本 feature 交付的是 C2 / C3 的**执行侧**（通道语义）+ C4 的**前置**（有值 / 无值判定）；C4 / C8 的**判据一字未改** | **B5F2**（C4 · M1）· **B8F1**（C8 · M2） | 挂载点已存在（`tests/contracts/test_contract_regressions.py:28-29` 的 `GATE-MOUNT: C4/C8 · status=not-landed · owner=B5F2/B8F1`）⇒ 本 feature **零改动**该文件（**未**把 `status` 改成 `landed`） |
| ② | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」 | 验收基线跑通需要**完整内核运行时**（编译 + 执行），属 **B7F2 / B7F3**（M1 尾 / M2）⇒ B5F1 **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；本 feature 只落**挂载点**并在人工记录中标记「未落地」 | **B7F2 + B7F3**（M1 / M2） | 已就位：B3F1 的裁定 22 已把「fake 轮」的承接条款写入 **B7F2 / B7F3** 的提示词初稿 |
| ③ | **门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 无图可跑 ⇒ 无从接真实模型 | **五段式记录 + 来源覆盖表照常落地**（FR-020 / FR-021）；被延后的只是「真实模型一轮」这一**部分** | **B7F3 / B25F1**（M2 / M4） | 已就位：**B25F1**（双跑验收）的提示词初稿承接 fake 轮 |

**红线未被触碰**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 ·
商标红线 · 零出站红线 —— **全部在本 feature 照常执行**
（FR-015 + 门禁 G21 / G23 / G24 / G26 / G27 实测全绿）。

> **🔓 追认栏 ——【已由发起者追认 · 2026-11-09】**
>
> | 项 | 内容 |
> |---|---|
> | **追认对象** | plan.md 的**登记项 R-1**（宪法「质量门禁 3 / 4 / 5」的偏离登记） |
> | **追认人（发起者）** | **杨家成**（仓库发起者）—— 依宪法 v1.6.0 由**发起者本人**作出；实现者**未代签** |
> | **追认结论** | ✅ **追认** —— 上表三条偏离在本 feature **物理不可达成**（根因：**无图可跑** —— 状态读取层 = B5F2 · fresh 读 = B8F1 · 调度 = B7F1 · 编译执行 = B7F2 / B7F3，按立项书 §6.2 的 M1 / M2 切分尚未落地）；**判据一字未放宽**（C4 / C8 的判据原样保留 · 挂载点 `status=not-landed` **未**改动）；**承接方与里程碑不变**（B5F2 / B8F1 / B7F2 / B7F3 / B25F1） |
> | **追认日期** | **2026-11-09** |
> | **签署** | 发起者于本会话中明示「**追认**」并指示收尾与提交推送（**未另留书面签名** —— 实现者**不得**代签 · 宪法 v1.6.0） |
>
> **⇒ 追认完成，执行闸口 A5 通过 ⇒ 本 feature 达「可合入」状态。**
> ⚠️ 实现者**未**改宪法正文 · **未**写一条永久红的 CI · **未**把
> `tests/contracts/test_contract_regressions.py` 的 `GATE-MOUNT:` 标记改成 `landed`
> （C4 / C8 **未**由本 feature 落地）。

### 4.4 纪律复核小结

| 纪律 | 状态 | 实测依据 |
|---|---|---|
| 依赖零新增（三处声明） | ✅ | §3.4 · 门禁 G21 / G23 |
| 公开面零变更（18 / 7） | ✅ | §3.1 §9 |
| 兼容矩阵零新增行 | ✅ | `git diff --stat -- README.md` **无输出** |
| 层注册表零改动 | ✅ | §3.4 · 门禁 G25 |
| 门禁编号仍为 30 | ✅ | §3.4 |
| CI 配置零改动 | ✅ | `git diff --stat -- .github/workflows/ci.yml` **无输出** |
| `THIRD_PARTY_NOTICES` 零改动 | ✅ | §3.4 · 门禁 G30 |
| 署名头 + docstring 覆盖率 100% | ✅ | §3.4 · 门禁 G30（新增 7 个源文件） |
| L2 → L3/L4/L5 边数 == 0 | ✅ | §3.4 · 门禁 G25 |
| 零环境变量 / 零出站 / 零文件 I/O | ✅ | §3.1 §6 + 子进程计数断言 |
| 覆盖率（新增部分）行 / 分支 100% | ✅ | §3.2 |
| 零改动清单未被触碰 | ✅ | §4.5 |

### 4.5 零改动清单复核（tasks.md「Path Conventions」）

| 文件 | 状态 |
|---|---|
| `src/freegraph/__init__.py` | ✅ **零改动**（顶层包惰性 · 门禁 G1 / L-1） |
| `src/freegraph/graph.py` | ✅ **零改动**（门面 7 符号面） |
| `src/freegraph/contracts/**` | ✅ **零改动**（18 符号面 · 含 `errors.py` 的「唯一定义处」措辞） |
| `src/freegraph/runtime/schema.py` | ✅ **零改动**（B4F1） |
| `src/freegraph/runtime/reducer.py` | ✅ **零改动**（B4F1） |
| `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` | ✅ **零改动**（⚠️ 其 `:98` 的「尚未存在」措辞已过时 ⇒ **只登记不修改** · research DR-5） |
| `tests/contracts/test_contract_regressions.py` | ✅ **零改动**（C4 / C8 的 `GATE-MOUNT:` 仍为 `not-landed`） |
| `tests/runtime/conftest.py` + 6 个既有测试模块 | ✅ **零改动**（复用 `run_in_subprocess` 夹具） |
| `pyproject.toml` | ✅ **零改动**（三处依赖声明零新增 · 覆盖率工具**不进**依赖） |
| `.github/workflows/ci.yml` | ✅ **零改动**（`testpaths = ["tests"]` ⇒ 零改动即被收集） |
| `README.md` | ✅ **零改动**（兼容矩阵零新增行） |

**本 feature 唯一改动的既有源文件**：`src/freegraph/runtime/errors.py`（**追加**两个
错误类型 · 既有 `InvalidSchemaError` **一字不动**）与
`src/freegraph/runtime/__init__.py`（**追加**导出 4 → 12 个符号）。

---

## 5. 遗留问题

| # | 遗留项 | 影响 | 承接方 | 处置 |
|---|---|---|---|---|
| **1** | **G28 的网络命名空间隔离未在本机实测** —— 本机 `unshare --net --map-root-user` **不可用**（`/proc/self/uid_map` 写失败 · 容器 **AppArmor** 限制）⇒ 只实测了**脚本本体**（`717 passed, 4 skipped, 3 deselected` + PASS） | **低** —— **平台性**限制，非本 feature 的缺陷；G28 的断网等价性由 **CI 的 Linux 作业**实测 | **CI**（Linux 作业） | 记录在案；**MUST NOT** 把本机环境限制当作本 feature 的缺陷（tasks T043 纪律） |
| **2** | ~~**登记项 R-1 的发起者追认未完成**~~ —— **✅ 已闭合**：发起者于 **2026-11-09** 明示「**追认**」并指示收尾与提交推送（见 §4.3 的追认栏）⇒ 执行闸口 **A5 通过** | **无**（已闭合） | — | 已闭合 · **未**改宪法正文 · **未**写永久红的 CI · **未**把 C4 / C8 的 `GATE-MOUNT:` 改成 `landed` |
| **DR-1** | 通道的**相等判定 `__eq__`** 与**可打印表示 `repr`** 未在 spec 冻结 | **低** —— v1.0 无消费者（快照 / checkpoint 尚未存在） | **B14F1**（checkpoint 落地时按需冻结） | 本 feature **不实现** `__eq__`；测试**不用**通道相等做断言（改用属性逐项断言） |
| **DR-2** | `value_type` 的**「类型可读文本」口径**未冻结（含泛型参数如何展示） | **低** —— 本 feature 只保留**类型对象**本身 | **B4F1**（已有投影口径）· **B14F1** | 本 feature **不做**类型文本投影；`value_type` 直接暴露类型对象 |
| **DR-3** | 上游的 **`Overwrite` 旁路值**（`binop.py:31-51`） | **无** —— 不在最小契约 C1–C27 内 | 无（v1.0 不做） | spec FR-018 已列为 Out of Scope |
| **DR-4** | **`EphemeralValue` 的清空机制**与上游不同（freegraph = 显式 `clear()`；上游 = `update(空序列)`） | **无**（可观察语义等价） | 无 | spec 裁定 6 已登记；**不进**兼容矩阵（本 feature 零新增公开 API） |
| **DR-5** | **层注册表的一处措辞已过时**：`layer-registry.md:98` 仍写着 `src/freegraph/runtime/`「**尚未存在**」 | **无**（行的**层归属（L2）**本身正确） | **B3F1**（层注册表的**权威持有者**） | 本 feature **MUST NOT** 改层注册表（**冻结面**）⇒ **只登记、不修改** |
| **DR-6** | **步末「清空哪些通道」的范围**由调度层决定（B7F1）—— 若 B7F1 在步末对**全部**通道调 `clear()`，覆盖型的「末值保留」与归约型的「累积保留」会被抹掉 ⇒ **与上游分叉** | **中** —— 影响 C2 / C3 的跨步等价 | **B7F1**（调度层） | 本 feature 只**冻结 `clear()` 的语义**（三类一律 ⇒ 无值）；**步末调用范围**归 B7F1 ⇒ 已写入 contract §7 `B-2` + upstream-parity **P-12 / S-05** + spec 裁定 17 ② |

> ⚠️ **不适用项的显式记录**（原则 V：非忽略）：
> ① **「真实模型一轮」** —— 本 feature **无图可跑** ⇒ **不适用**
> （已登记于 §4.3 的门禁 5 行 ⇒ 承接方 **B7F3 / B25F1**）；
> ② **「fake 模型跑通验收基线的一轮」** —— 同上 ⇒ **不适用**（承接方 **B7F2 / B7F3**）；
> ③ **C4 / C8 的两条独立回归** —— 依赖**状态读取层 / 调度循环** ⇒ 本 feature
> **不交付**其前置能力 ⇒ **不适用**（承接方 **B5F2 / B8F1**）⇒
> **挂载点已存在**（B3F1 落）且本 feature **零改动** `test_contract_regressions.py`。

---

## 6. 来源覆盖表（宪法原则 VIII · FR-020 · FR-021 · SC-013 · SC-014）

> **核实环境**：上游 `langgraph` **1.2.11**（`…/site-packages/langgraph/`）· CPython **3.11.16**
> —— 核实于 **2026-11-08**（`contracts/upstream-parity.md`）· **换上游版本后 MUST 重新核实全部行号**。
> **A1–A3 的 Q8 条号映射**（FR-020 要求标注）：**A1** → **Q8 §3.4 C2（归约器机制）** ·
> **A2** → **Q8 §3.4 C3（默认归约语义）** · **A3** → **Q8 §3.4 C7（路由函数契约）+ C8（条件边读状态）**。

### 6.1 验收判据 A1–A3

| 判据 | 来源（上游 `路径:行号` + 核实版本） | 澄清条号 | 宪法条款号 | 断言落点 | 结论 |
|---|---|---|---|---|---|
| **A1** 归约器 `operator(current, new)` | `langgraph/channels/binop.py:143`（归约调用形式）· `:126-128`（首次写入直存）· `:82-92`（空值推导）—— **langgraph 1.2.11** | **Q8 §3.4 C2** · **Q6**（折叠起点） | 原则 II（状态语义与 LangGraph 等价）· 原则 VIII（证据纪律） | `test_channel_semantics.py::test_binary_operator_aggregate_reduces_in_order` · `..._folds_from_the_initial_empty_value` | ✅ |
| **A2** 无归约器 key 被覆盖 | `langgraph/channels/last_value.py:66`（覆盖）· `:56-64`（冲突抛错）· `:57-58`（空序列 no-op）—— **langgraph 1.2.11** | **Q8 §3.4 C3** | 原则 II · 原则 VIII | `...::test_last_value_overwrites_on_consecutive_writes` · `..._never_holds_or_calls_a_reducer` | ✅ |
| **A3** 路由通道每 super-step 清空 | `langgraph/channels/ephemeral_value.py:55-61`（清空为 `MISSING`）· `pregel/_algo.py:326-334`（步末重置）—— **langgraph 1.2.11** | **Q8 §3.4 C7 + C8** · **Q15**（清空机制差异） | 原则 II · 原则 VIII | `...::test_ephemeral_value_clear_resets_to_no_value` · `..._write_after_clear_restores_availability` | ✅ |

### 6.2 六类语义（FR-021 · SC-014）

| # | 语义 | 上游 `路径:行号`（**langgraph 1.2.11**） | 对照表 | 断言落点 | 结论 |
|---|---|---|---|---|---|
| ① | 覆盖语义 | `channels/last_value.py:66` | **P-01** | `test_last_value_overwrites_on_consecutive_writes` | ✅ |
| ② | 一步内多值冲突 | `channels/last_value.py:56-64` · `channels/ephemeral_value.py:62-65` | **P-02 / P-11** | `test_channel_errors.py::test_invalid_channel_update_error_structured_fields` | ✅ |
| ③ | 空值推导 | `channels/binop.py:22-28` · `:82-92` | **P-05 / P-06** | `test_binary_operator_aggregate_starts_with_the_derived_empty_value` · `test_empty_value_derivation_covers_six_categories` | ✅ |
| ④ | 首次写入的 `current` | `channels/binop.py:126-128` | **P-07** | `test_first_write_on_an_empty_channel_stores_the_value_directly` | ✅ |
| ⑤ | 清空语义（三类统一） | `channels/base.py:19-121`（**无** `clear`）· `last_value.py:56-58` · `binop.py:123-125` · `ephemeral_value.py:55-61` | **P-10 / P-12** | `test_channel_contract.py::test_i12_clear_always_yields_no_value` | ✅ |
| ⑥ | 有值 / 无值判定 | `channels/last_value.py:69-75` | **P-04** | `test_channel_contract.py::test_i4_is_available_never_raises_and_get_always_raises_when_empty` | ✅ |

### 6.3 全部成功标准（SC-001 ~ SC-028）

| SC | 来源 | 澄清条号 | 宪法条款号 | 结论 |
|---|---|---|---|---|
| SC-001 | 本 spec **FR-003 / FR-004** · 上游 `channels/last_value.py:66` | Q8 §3.4 C3 | 原则 II | ✅ |
| SC-002 | 本 spec **FR-005 / FR-007** · 上游 `channels/binop.py:143` | Q6 · Q8 §3.4 C2 | 原则 II | ✅ |
| SC-003 | 本 spec **FR-009 / FR-010** · 上游 `channels/ephemeral_value.py:55-61` | Q8 §3.4 C7 | 原则 II · 原则 VII（C7） | ✅ |
| SC-004 | 本 spec **FR-011 / FR-022** · 上游 `channels/last_value.py:69-75` | Q3 · Q9 | 原则 VII（C4 前置） | ✅ |
| SC-005 | 本 spec **FR-015** | — | 原则 I（零出站 · 零环境变量） | ✅ |
| SC-006 | 本 spec **FR-004 / FR-008 / FR-010** | Q1 | 原则 II | ✅ |
| SC-007 | 本 spec **FR-006 / FR-007** · 上游 `channels/binop.py:82-92` | Q2 | 原则 II | ✅ |
| SC-008 | 本 spec **FR-012** · 上游 `graph/state.py:1850-1873` | Q4 | 原则 VII（C1–C27） | ✅ |
| SC-009 | 本 spec **FR-013 ①** | Q15 | 原则 II（内核纯净） | ✅ |
| SC-010 | 本 spec **FR-014** · 上游 `channels/binop.py:143` | — | 原则 II | ✅ |
| SC-011 | 本 spec **FR-016** | — | 原则 XII（分层）· 原则 X（署名头） | ✅ |
| SC-012 | 本 spec **FR-018** | — | 原则 III（契约优先）· 原则 X（文档合规） | ✅ |
| SC-013 | 本 spec **FR-020** | — | 原则 V（人工门禁）· 原则 VIII | ✅ |
| SC-014 | 本 spec **FR-021** · `contracts/upstream-parity.md` | — | 原则 VIII（证据与术语纪律） | ✅ |
| SC-015 | 本 spec **FR-019 ②** | Q14 | 原则 V（无图可跑 ⇒ 覆盖率要求最高） | ✅ |
| SC-016 | 本 spec **FR-019 ①** | — | 原则 V | ✅ |
| SC-017 | 本 spec **FR-001 / FR-019 ③** | — | 原则 VII（唯一实现点） | ✅ |
| SC-018 | 本 spec **FR-017** | Q7 | 原则 IV（可诊断性） | ✅ |
| SC-019 | 本 spec **FR-002 / FR-012 / FR-017** | Q4 | 原则 VI（规格驱动） | ✅ |
| SC-020 | 本 spec **FR-002 📌** · 上游 `pregel/_algo.py:319-324` | Q5 | 原则 II | ✅ |
| SC-021 | 本 spec **FR-005 / FR-007** · 上游 `channels/binop.py:126-128` + `:143` | Q6 | 原则 II | ✅ |
| SC-022 | 本 spec **FR-013 ②③** | Q8 · Q15 | 原则 II | ✅ |
| SC-023 | 本 spec **FR-022** | Q9 | 原则 II | ✅ |
| SC-024 | 本 spec **FR-023** | Q10 | 原则 II（内核纯净） | ✅ |
| SC-025 | 本 spec **FR-024** | Q11 | 原则 II | ✅ |
| SC-026 | 本 spec **FR-025** | Q12 | 原则 IV（可诊断性） | ✅ |
| SC-027 | 本 spec **FR-026** | Q13 | 原则 V（人工门禁） | ✅ |
| SC-028 | 本 spec **FR-027** | Q15 ③ | 立项书 §4.2 S5 ③ | ✅ |

### 6.4 冻结面与纪律

| 判据 | 来源 | 宪法条款号 | 结论 |
|---|---|---|---|
| 依赖三处零新增 | 本 spec **FR-015** · `pyproject.toml` | 原则 I · 原则 IX（许可证红线） | ✅ |
| 公开面 18 / 7 未变 | 本 spec **FR-018** · `contracts/__init__.py` · `graph.py` | 原则 III（契约优先） | ✅ |
| 兼容矩阵零新增行 | `README.md` 的「API 兼容矩阵」章节 | 原则 X（文档合规） | ✅ |
| 层注册表零改动 | `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` | 原则 XII（分层） | ✅ |
| 门禁编号仍为 30 | `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` §0 | 原则 VI | ✅ |
| 署名头 + docstring 100% | `harness/scripts/gates/gate_G30_attribution.py` | 原则 X | ✅ |
| L2 → L3/L4/L5 边数 == 0 | `harness/scripts/gates/gate_G25_import_graph.py` | 原则 XII（ARCH-1） | ✅ |
| 零环境变量 / 零出站 | 门禁 **G24 / G26 / G27** | 原则 I | ✅ |
| 覆盖率（新增部分）行 / 分支 100% | `coverage report --branch` + **差分口径** | 原则 V | ✅ |
| 五段式 + 来源覆盖表 | 本 spec **FR-020** | 原则 V · 原则 VIII | ✅ |

⇒ **来源覆盖表对全部判据的覆盖率 == 100%**（**无来源项数 == 0** · SC-013）。

---

## 7. 移交后续 feature

| 下游 | 承接的内容 | 落点 |
|---|---|---|
| **B5F2**（读取层 · M1） | `Channel.get()` / `is_available()` / `EmptyChannelError` 的**稀疏读**口径；C4 的**独立回归**（`GATE-MOUNT:` 仍为 `not-landed`） | contract §7 `B-1` · upstream-parity **S-03** |
| **B6F1**（`StateGraph` 构建器 · M1） | `build_channel` / `build_channels`（**唯一**映射入口） | contract §4 |
| **B7F1**（调度层 · M2） | **步末只对路由型通道调 `clear()`**（覆盖型 / 归约型**保留**其值）⇒ MUST 与上游逐字同构 | contract §7 `B-2` · upstream-parity **P-12 / S-05** · research **DR-6** |
| **B8F1**（条件边 · M2） | C8 的**独立回归**（`GATE-MOUNT:` 仍为 `not-landed`） | plan 登记项 R-1 ① |
| **B14F1**（checkpoint · M4） | 通道的 `__eq__` / `repr`（**DR-1**）· 通道复制 / 回滚 | contract §7 `B-3 / B-4` · research **DR-1** |
