# freegraph

> **⚠️ 状态：v0.0.x 是「占位版」（name-reservation placeholder），内核尚未实现。**
> **v0.0.2 起**：每个源文件带署名头（Copyright + MIT + 项目地址）——MIT 允许文件被单独
> 复制，而复制不会带走 `LICENSE`，因此署名必须随每个文件流动。
> **v0.0.2 已发布**（2026-11-05）：发行产物纯度门禁在真实发布链路上首次执行并通过——
> wheel / sdist 均无任何仓库内容，`Requires-Dist` 只有 `typing-extensions` 一个依赖。
>
> 本次发布**只为在 PyPI 上锁定 `freegraph` 这个发行名**（发行名 = 导入名）。
> 目前 `import freegraph` 只会返回一个版本号，**没有任何图运行时能力**——
> 请勿用于生产，也不要把它当作 LangGraph 的可用替代品。
>
> 实现路线见仓库内 `harness/proposals/立项书.md`（32 个 Phase / 96 人日 / v1.0）。

**English:** FreeGraph is a fully account-free, drop-in replacement for LangGraph,
faithfully replicating its API while maintaining LangChain compatibility — build and
run graph-based AI workflows without LangSmith or external account dependencies.

三条对外承诺（v1.0 交付时兑现）：

| 承诺 | 含义 |
|---|---|
| **零账号** | 无需 LangSmith 账号、API key 或 license key |
| **零出站** | freegraph **自身**不主动发起任何出站连接，且**不阻断用户代码**出网 |
| **零第三方运行时依赖** | 基础安装只有 `typing-extensions` |

**设计与实现原理全部公开**：仓库
[`yangjiacheng1996/freegraph`](https://github.com/yangjiacheng1996/freegraph) 含有

- 立项书（范围、成本、里程碑与契约 C1–C26）
- Q1–Q9 调研报告（LangSmith / LangGraph / DeepAgents 的实测取证）
- 项目宪法（原则 I–X 与质量门禁）、开发指南与全部提示词
- 验收脚本集（`harness/demo/`，零第三方依赖）

**发行包本身是干净的**：PyPI 上的 `freegraph` 只含 `src/freegraph/` 下的包代码与
必要的元数据（README / LICENSE / pyproject.toml）——仓库里的调研报告、提示词与
验收脚本是**开发辅助材料**，留在 GitHub 上供学习，不会被 `import` 引入。
发布流水线有一道**纯度门禁**（`harness/scripts/check_dist_purity.py`）对此做断言。

License: MIT
