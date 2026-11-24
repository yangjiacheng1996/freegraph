# 人工验证记录（verification）

> 本目录存放**每个 feature 的人工验证记录**与**可运行的验收脚本**（原则 V 人工门禁 · 立项书 §9.1 门禁 5）。

## 目录约定

```text
harness/verification/
├── README.md                      ← 本文件
└── <feature>/
    ├── acceptance.py              ← 该 feature 的**可运行验收脚本**（**可选**）
    └── manual-verification.md     ← 该 feature 的人工验证记录（**必落** · 宪法门禁 5）
```

- **`<feature>` = feature ID**（= `B<n>F<m>`，与 `harness/features/B<n>F<m>_*.md` 一一对应），
  例如 `B1F1` / `B2F1` / `B3F1` / `B24F1`。
- **文件名固定** —— `acceptance.py`（脚本）与 `manual-verification.md`（记录），
  便于按统一路径检索与批处理。
- **`manual-verification.md` 必落** —— 宪法「质量门禁 5」与原则 V 要求**每个 feature** 都有
  人工验证记录 ⇒ **无一例外**。
- **`acceptance.py` 可选** —— 只在该 feature 有**可独立运行**的验收脚本时才落
  （如 `B1F1` / `B2F1` / `B2F2` / `B4F1` / `B5F1`）；**无此类脚本的 feature 不必强行补**
  （如 `B3F1` —— 其判据以 `pytest` 断言 + `manual-verification.md` 承载）。
  ⇒ 判定某 feature 是否需要 `acceptance.py` 的依据 = 「该 feature 的判据能否脱离
  `pytest` 单独跑成一段脚本」，**不是**「目录里必须凑齐两个文件」。
  > **📌 B4F1 的追加（2026-11-08 · 发起者要求）**：B4F1 原按本条判为「不落」
  > ⇒ 人工验收环节发起者要求「**一条命令跑完全部验收**」⇒ **补落** `acceptance.py`
  > （89 条断言 · 单文件 · 零第三方依赖）⇒ 本条的判定依据对 B4F1 **成立**
  > （判据是纯计算 · 零依赖）。
  > **📌 B5F1 的追加（2026-11-09 · 同一依据）**：B5F1 的判据（通道语义 · 映射 ·
  > 纯净性 · 冻结面审计）**全部是纯计算 · 零依赖** ⇒ **落** `acceptance.py`
  > （**149 条断言** · 单文件 · 零第三方依赖 · 退出码 **0 / 1 / 2** 三态）。
  > **📌 B5F2 的追加（2026-11-10 · 发起者提出 · spec 裁定 34）**：B5F2 原按本条
  > 判为「不落」（其验收闸口散落在 `quickstart.md` 的 12 节里）⇒ 人工验收环节
  > 发起者提出「**B5F2 缺一键验收入口**」⇒ **补落** `acceptance.py`
  > （**88 条硬断言** · 单文件 · 零第三方依赖 · 退出码 **0 / 1 / 2** 三态 ·
  > **一条命令**跑完验收闸口 **V1–V12** + 覆盖率取证 + 10 条门禁）⇒ 本条的
  > 判定依据对 B5F2 **成立**（判据是纯计算 · 零依赖）。
- **一个 feature 一个目录** —— 同一 feature 若需补记（如「后续 feature 注意事项」），
  追加到该文件相应小节，**不另起文件**。

> **为什么独立成目录**：`harness/features/` 是 **feature 提示词初稿**的目录
> （每 feature 一份 `/speckit.specify` 提示词）。人工验证记录是**验收产物**，
> 与提示词是两类性质完全不同的文档 —— 混在一个目录里会让「每个 feature 的验收
> 记录在哪」变成一个需要回忆的约定。独立成目录后，它是一个一眼可见的规则。

## 两类验收脚本的分工

| 位置 | 定位 | 何时跑 |
|---|---|---|
| **`harness/verification/<feature>/acceptance.py`** | **逐 feature**（v1.0 之前）的验收脚本 —— 把该 feature 的验收判据落成**可判定的断言**，跑一遍即知「这个 feature 交付到位没有」 | 每个 feature 实现完成后，由**人**执行 |
| **`harness/demo/acceptance.py`** | **v1.0 完成后**的端到端验收 —— 跑整张图、Agent 循环、可视化与 LangChain 兼容性 | v1.0 收官时 |

两者**都是零第三方依赖**（只 import Python 标准库 + 被验收的 freegraph 本身）。

### 逐 feature 验收脚本的用法

```bash
python3 harness/verification/<feature>/acceptance.py                    # 跑全部
python3 harness/verification/<feature>/acceptance.py --record out.md    # 同时生成验收记录片段
python3 harness/verification/<feature>/acceptance.py --require-installed # 要求当前环境已安装 freegraph
```

- **两态运行**：环境**已安装** freegraph ⇒ 测**发行产物**；**未安装** ⇒ 自动把
  `<repo>/src` 插入 `sys.path` 测**源码树**，且「依赖闭包为空集」那条判据标
  「◌ 环境未就绪」（**不判失败**）。
- **退出码**：`0` = PASS · `1` = FAIL · `2` = 环境未就绪。
- **`--record`** 产出**五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）的
  markdown 片段，可直接并入该 feature 的 `manual-verification.md`。
- **判据的权威处**：机器门禁在 `tests/contracts/test_architecture.py`（G1–G13）；
  验收脚本是**面向人**的同口径对照，**不替代**门禁。

## 记录必须包含的五段

依宪法原则 V 与 quickstart 第 4 节，每份记录**MUST** 含：

| # | 段 | 要求 |
|---|---|---|
| 1 | **环境** | Python 版本 / 平台 / 包版本 / 依赖闭包 实测结果 |
| 2 | **步骤** | 照 `quickstart.md` 第 1–3 节的可复制命令 |
| 3 | **实际输出** | 粘贴**真实**输出（非「符合预期」）；单测取原始末行 |
| 4 | **结论** | 逐条对照验收判据；**不适用**的子项须**显式记一句**，非忽略 |
| 5 | **遗留问题** | 已知限制与其归属 feature |

## 当前已有记录

| feature | 记录 | 验收脚本 | 状态 |
|---|---|---|---|
| **B1F1** | [B1F1/manual-verification.md](B1F1/manual-verification.md) | [B1F1/acceptance.py](B1F1/acceptance.py) | ✅ 契约层骨架（四个核心类型 + 异常体系）—— 47 条断言全绿 |
| **B2F1** | [B2F1/manual-verification.md](B2F1/manual-verification.md) | [B2F1/acceptance.py](B2F1/acceptance.py) | ✅ **已回填实测输出**（5 个协议 + 5 个纯数据类）—— 119 条断言全绿；3.11 / 3.13 / 3.14 三档多版本实测**未执行**（本机仅 CPython 3.12.3），已记入该记录的 §7 遗留问题 |
| **B2F2** | [B2F2/manual-verification.md](B2F2/manual-verification.md) | [B2F2/acceptance.py](B2F2/acceptance.py) | ✅ **已回填实测输出**（公开 API 门面 7 符号 + API 签名快照 + 顶层包惰性）—— 76 条断言全绿；隔离 venv（CPython **3.11.16**）实测通过，3.13 / 3.14 档**未执行**，已记入该记录的 §5 遗留问题 |
| **B3F1** | [B3F1/manual-verification.md](B3F1/manual-verification.md) | （无 —— 判据以 `pytest` 断言 + 门禁脚本承载） | ✅ **项目脚手架 + extras 划分 + CI 门禁** —— **10 条新门禁 G21–G30**（**逐条**退出码 0）+ **8 条强制反向用例**全绿 + 7 作业 CI 矩阵（**7/7 作业全绿** · 含 Windows / macOS / arm64）；交付时全量 **402 passed / 4 skipped**（3.11 / 3.14 两档）；**T049 / T057 两条发起者追认均已作出**（§3.6 / §5.1）；⚠️ 遗留 #5「禁止色值清单待取证」· #6「自有品牌资产白名单待登记」**仍未关闭** |
| **B4F1** | [B4F1/manual-verification.md](B4F1/manual-verification.md) | [B4F1/acceptance.py](B4F1/acceptance.py) | ✅ **已回填实测输出**（状态 schema 解析 + 归约器提取 · 二元性判定表逐条比对）—— **pytest 90 条新断言全绿**（CPython **3.11.16** / **3.14.7** 两档）+ **验收脚本 89 条断言全绿**；⚠️ **T053 发起者追认（plan 登记项 R-1）待办 ⇒ 阻断合入**，详见该记录 §4.3 |
| **B5F1** | [B5F1/manual-verification.md](B5F1/manual-verification.md) | [B5F1/acceptance.py](B5F1/acceptance.py) | ✅ **已回填实测输出**（通道抽象 + 三类通道 · 契约守卫逐条比对）—— **pytest 315 条新断言全绿**（CPython **3.11.16**）+ **验收脚本 149 条断言全绿**（**一条命令**跑完 A1–A3 + 全部 SC + 覆盖率取证 + 10 条门禁 · 退出码 0 / 1 / 2 三态自测通过）+ **覆盖率行 / 分支 100%**（`channel.py` / `mapping.py` 全文）；✅ **T042 发起者追认已作出**（plan 登记项 R-1 · **2026-11-09**）⇒ 执行闸口 **A5 通过** · **可合入**，详见该记录 §4.3 |
| **B5F2** | [B5F2/manual-verification.md](B5F2/manual-verification.md) | [B5F2/acceptance.py](B5F2/acceptance.py) | ✅ **已回填实测输出**（稀疏状态读取 + fresh 读 + 差分测试夹具）—— **pytest 802 条断言全绿**（基线 720 → 802 · **+82**）+ **验收脚本 88 条硬断言全绿**（**一条命令**跑完闸口 **V1–V12** + 覆盖率取证 + 10 条门禁 · 退出码 0 / 1 / 2 三态自测通过）+ **覆盖率行 / 分支 100%**（`read.py` 全文）+ **差分夹具三项投影 17 字段逐项相等**（`langgraph 1.2.11` · 3.11 / 3.14 两档实测）；✅ **T037 / T038 / T043 / T049 四条发起者追认均已作出**（登记项 **R-1 / R-2 / R-3 / R-4** · **2026-11-10**）⇒ 执行闸口 **A7 通过** · **可合入**；⚠️ 遗留「**SC-014 的 CI 日志侧证据**待首次 CI 实跑后补录」· 「macOS / Windows / arm64 三档**档位实测**未执行」，详见该记录 §4 |

| **B9F1** | [B9F1/manual-verification.md](B9F1/manual-verification.md) | [B9F1/acceptance.py](B9F1/acceptance.py) | ✅ **已回填实测输出**（`Command` 原语 · `goto` / `update` + `Command.PARENT`）—— **pytest 1044 条断言全绿**（基线 916 → 1044 · **+128** · 11 个新模块 / 128 条新用例）+ **验收脚本 75 条硬断言全绿**（**一条命令**跑完闸口 **V1–V12** + 覆盖率取证 + 10 条门禁 · 退出码 0 / 1 / 2 三态自测通过）+ **覆盖率行 / 分支 100%**（**差分口径** · 新增 314 行 · 新增语句行 85 · 未覆盖 **0**）；✅ **T039 发起者追认已作出**（登记项 **R-1 / R-2 / R-3 / R-4 / R-5 / R-7 / R-8 / R-9** 共 **八项** · **2026-11-11**）⇒ 执行闸口 **A10 通过** · **可合入**；✅ **CI 实跑 7/7 作业全绿**（run `43047327076` · `head_sha = 1896e16` · 3.11 / 3.14 × 5 平台 · 7 条门禁在全部 7 档实跑并全 success）**+ 7 份 junitxml 逐档逐模块解析**（七档 failures == 0 且 errors == 0 · B9F1 的 **128 条**在七档逐字相同且零 skip · 差分组在 Linux x86_64 两档**真实执行**）；⚠️ 遗留「**门禁 3 / 4 / 5**物理不可达成」（登记项 **R-1**），详见该记录 §5 |
| **B13F1** | [B13F1/manual-verification.md](B13F1/manual-verification.md) | [B13F1/acceptance.py](B13F1/acceptance.py) | ✅ **静态中断点 + `recursion_limit`** —— pytest **1281 passed / 4 skipped**（基线 1203 / 4）；一键验收 **37 条断言全绿**；新增模块行 / 分支覆盖率 **100%**；差分 **51/51**（D-38…D-49）；门禁 G21 / G25 / G26 / G27 / G29 通过；`graph_core` 以退出码 2 表示 M1 门面未就绪（EV-1）；✅ **T114 发起者追认已签字**（2026-11-15） |
| **B6F1** | [B6F1/manual-verification.md](B6F1/manual-verification.md) | [B6F1/acceptance.py](B6F1/acceptance.py) | ✅ **`StateGraph` 构建器** —— pytest **1323 passed / 4 skipped**（基线 1281 / 4）；一键验收 **40 条断言全绿**；`_stategraph.py` 行覆盖率 **100%**（227 / 0 missed）；builder 差分 **25/25**（D-50…D-74）；门禁 G21 / G24 / G25 / G26 / G27 / G29 / G30 通过；`target.py` diff 为空；`graph_core` 退出码 2（compile / invoke 未就绪，属预期）；✅ **EV-1a / EV-1b / EV-1c 发起者追认已签字**（2026-11-15） |
| **B7F2** | [B7F2/manual-verification.md](B7F2/manual-verification.md) | [B7F2/acceptance.py](B7F2/acceptance.py) | ✅ **`compile()` → `CompiledGraph`** —— pytest **1421 passed / 4 skipped**（基线 1323 / 4）；一键验收 **33 条断言全绿**；compile-only 差分 **D-75…D-91 逐条符合判词**；门禁 G21 / G23 / G24 / G25 / G26 / G27 / G29 通过（G30 的 8 条违规为 B7F2 之前已有的 tracked 文档问题）；`target.py` diff 为空；`graph_core` A3 真跑通过后以**退出码 2** 结束（`invoke` 归 B7F3 · EV-1）；✅ **X-9 / X-11 / X-12 已登记**；⚠️ EV-1a / EV-1b / EV-1c 承接 **B7F3 / B8F1 / B22F1 / B23F1 / B25F1**；✅ **CI 实跑 7/7 作业全绿**（run `43810829179` · ubuntu 3.11/3.14 + arm 3.11 + windows 3.11/3.14 + macos 3.11/3.14） |
| **B7F3** | [B7F3/manual-verification.md](B7F3/manual-verification.md) | [B7F3/acceptance.py](B7F3/acceptance.py) | ✅ **已回填实测输出**（`invoke()` 返回完整状态 + `InvalidUpdateError`）—— pytest **1486 passed / 4 skipped**（基线 1421 / 4 · **+65**）+ 一键验收 **14 条断言全绿**（退出码 0）+ 验收脚本 `graph_core` / `agent_loop` 均**退出码 0** + 执行期差分 **D-92…D-102**（判词 **SAME 7 / STRICTER 3 / DIFF 1**）全绿（整体 **127/127**）+ 门禁 G21 / G22 / G23 / G24 / G25 / G26 / G27 / G29 通过（G30 **8 条既有违规 · 零新增**）；✅ **T045 发起者追认已由发起者本人签署**（**2026-11-17** · 追认次数 == 1）⇒ ⇒ **合入闸口已打开**；✅ **CI 实跑 7/7 作业全绿**（run **44027833345** · 3.11 / 3.14 × ubuntu-24.04 / ubuntu-24.04-arm / macos-15 / windows-2025 · 步骤 9 的 G22 / G27 / **G28 断网**在 Linux 档真跑通过）· ⚠️ 遗留「**真实模型轮**环境不可用（已登记**环境偏离**）」· 「EV-1 / EV-2 / EV-4 具名承接 B8F1 / B8F2 / B8F3 / B14F1 / B22F1 / B23F1 / B25F1」，详见该记录 §5 / §6 / §8 |
| **B19F1** | [B19F1/manual-verification.md](B19F1/manual-verification.md) | [B19F1/acceptance.py](B19F1/acceptance.py) | ✅ **`TraceSink` 接入 + `current_span()` + 默认关闭** —— pytest **1917 passed / 6 skipped**（基线 1863 / 6 · **+54**）；一键验收 **31 条断言全绿**（A1–A7）；G21 / G23 / G24 / G25 / G26 / G27 通过（G27 框架出站 0）；R-1 / R-2 / R-3 一次性追认；B8F2 R-6 收窄；`CompiledGraph` 新增私有 `_tracer`（11 → 12 键）已登记；✅ **CI 实跑 7/7 作业全绿**（run `44902066559`） |
| **B20F1** | [B20F1/manual-verification.md](B20F1/manual-verification.md) | [B20F1/acceptance.py](B20F1/acceptance.py) | ✅ **本地 JSONL trace 存储（写入侧）** —— pytest **1991 passed / 7 skipped**（基线 1917 / 6 · **+74**；B20F1 定向 **72 passed / 1 skipped**）；一键验收 **23 项检查全绿**（`B20F1 acceptance: PASS`）；零出站 / 零 env / `0o600` / 逐行生命周期 / per-instance 锁 / 四路诊断；G25 与 `tests/gates` 42 条全绿；✅ **质量门禁 5 偏离已由发起者追认（2026-11-21）**：真实模型轮由 **B25F1（M4）** 承接 |
| **B20F2** | [B20F2/manual-verification.md](B20F2/manual-verification.md) | [B20F2/acceptance.py](B20F2/acceptance.py) | ✅ **Trace 查询 API + SQLite 后端（读取侧）** —— pytest **2111 passed / 8 skipped**（基线 1991 / 7 · **+120**；B20F2 定向 **87 passed / 1 skipped**）；一键验收 **A1–A6 全绿**（`B20F2 acceptance: PASS` · **35 项检查**）；四类过滤 / 组合 / 空过滤器 / 稳定排序 / 两后端逐条等价 / 容错只读 / SQLite 生命周期 / 并发；零出站 / 零 env / 零第三方；质量门禁 5 偏离沿用 B20F1 先例，真实模型轮由 **B25F1（M4）** 承接（T058 守卫） |
| **B21F1** | [B21F1/manual-verification.md](B21F1/manual-verification.md) | [B21F1/acceptance.py](B21F1/acceptance.py) | ✅ **OTLP 导出插件（可选 `[otlp]`）+ 三后端示例** —— 导出器模式 / 端点模式（最小 gRPC 接收端）/ 默认关闭 / 失败隔离 / 同步并发 / `protobuf` 具名 SPDX 归一；三示例并列、无默认推荐；一键验收 **A1–A5 全绿**（`B21F1 acceptance: PASS`）；质量门禁 5 偏离沿用 B20F1 / B20F2 先例，真实模型轮由 **B25F1（M4）** 承接 |

## 相关

- **原则 V 人工验收是最终验收标准** —— `.specify/memory/constitution.md`
- **质量门禁第 5 项（人工门禁）** —— 同上
- **feature 提示词初稿** —— `harness/features/`
- **v1.0 端到端验收脚本** —— `harness/demo/`
- **验收指南** —— 每个 feature 的 `specs/<feature>/quickstart.md`
