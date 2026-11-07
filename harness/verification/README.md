# 人工验证记录（verification）

> 本目录存放**每个 feature 的人工验证记录**与**可运行的验收脚本**（原则 V 人工门禁 · 立项书 §9.1 门禁 5）。

## 目录约定

```text
harness/verification/
├── README.md                      ← 本文件
└── <feature>/
    ├── acceptance.py              ← 该 feature 的**可运行验收脚本**
    └── manual-verification.md     ← 该 feature 的人工验证记录
```

- **`<feature>` = feature ID**（= `B<n>F<m>`，与 `harness/features/B<n>F<m>_*.md` 一一对应），
  例如 `B1F1` / `B2F1` / `B3F1` / `B24F1`。
- **文件名固定** —— `acceptance.py`（脚本）与 `manual-verification.md`（记录），
  便于按统一路径检索与批处理。
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

## 相关

- **原则 V 人工验收是最终验收标准** —— `.specify/memory/constitution.md`
- **质量门禁第 5 项（人工门禁）** —— 同上
- **feature 提示词初稿** —— `harness/features/`
- **v1.0 端到端验收脚本** —— `harness/demo/`
- **验收指南** —— 每个 feature 的 `specs/<feature>/quickstart.md`
