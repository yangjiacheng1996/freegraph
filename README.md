# freegraph

> **⚠️ 状态：v0.0.1 是「占位版」（name-reservation placeholder），内核尚未实现。**
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

License: MIT
