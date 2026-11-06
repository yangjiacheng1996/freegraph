# 人工验证记录（verification）

> 本目录存放**每个 feature 的人工验证记录**（原则 V 人工门禁 · 立项书 §9.1 门禁 5）。

## 目录约定

```text
harness/verification/
├── README.md                      ← 本文件
└── <feature>/
    └── manual-verification.md      ← 该 feature 的人工验证记录
```

- **`<feature>` = feature ID**（= `B<n>F<m>`，与 `harness/features/B<n>F<m>_*.md` 一一对应），
  例如 `B1F1` / `B2F1` / `B3F1` / `B24F1`。
- **文件名固定为 `manual-verification.md`** —— 便于按统一路径检索与批处理。
- **一个 feature 一个目录** —— 同一 feature 若需补记（如「后续 feature 注意事项」），
  追加到该文件相应小节，**不另起文件**。

> **为什么独立成目录**：`harness/features/` 是 **feature 提示词初稿**的目录
> （每 feature 一份 `/speckit.specify` 提示词）。人工验证记录是**验收产物**，
> 与提示词是两类性质完全不同的文档 —— 混在一个目录里会让「每个 feature 的验收
> 记录在哪」变成一个需要回忆的约定。独立成目录后，它是一个一眼可见的规则。

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

| feature | 记录 | 状态 |
|---|---|---|
| **B1F1** | [B1F1/manual-verification.md](B1F1/manual-verification.md) | ✅ 契约层骨架（四个核心类型 + 异常体系） |
| **B2F1** | [B2F1/manual-verification.md](B2F1/manual-verification.md) | ✅ **已回填实测输出**（5 个协议 + 5 个纯数据类；284 个用例 · 依赖闭包空集 · `mypy --strict` 全绿）—— 3.11 / 3.13 / 3.14 三档多版本实测**未执行**（本机仅 CPython 3.12.3），已记入该记录的 §7 遗留问题 |

## 相关

- **原则 V 人工验收是最终验收标准** —— `.specify/memory/constitution.md`
- **质量门禁第 5 项（人工门禁）** —— 同上
- **feature 提示词初稿** —— `harness/features/`
- **验收指南** —— 每个 feature 的 `specs/<feature>/quickstart.md`
