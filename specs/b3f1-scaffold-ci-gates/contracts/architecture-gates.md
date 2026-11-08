# 架构门禁契约（architecture-gates.md）

**功能块**: B3F1 · 项目脚手架 + extras 划分 + CI 门禁 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-005 ~ FR-020 · 裁定 1 ~ 裁定 20）·
[dependency-gate.md](./dependency-gate.md) · [layer-registry.md](./layer-registry.md) ·
[ci-matrix.md](./ci-matrix.md) · [research.md](../research.md)
**契约性质**: **冻结面** —— 每条门禁的**判定方式**即实现契约；改判定方式 = 改冻结面

> G1–G13 **继承自 B2F1**（`specs/b1f1-contracts-core/contracts/architecture-gates.md`），
> G14–G20 **继承自 B2F2**（`specs/b2f2-public-api-facade/contracts/architecture-gates.md`），
> 本 feature **新增 G21–G30**（spec 裁定 4）。
> 本文件是**累计门禁清单**的当前版本；B1F1 / B2F2 的同名文件保留为历史快照。

---

## 0. 门禁总览

| 门禁 | 内容 | 判定方式 | 本 feature 状态 |
|---|---|---|---|
| **G1** | 顶层包**惰性** | 子进程 `sys.modules` 快照 | 继承（**只接线** · 判据零改动） |
| **G2** | 契约层**零**内部 import + **零**第三方 import | AST | 继承（只接线） |
| **G3** | 依赖闭包**为空**（基础安装零第三方依赖） | `importlib.metadata.requires()` 递归展开 | 继承（**占位常量填充** —— 见 §4 · plan.md「唯一一处例外」） |
| **G4** | **零**环境变量读取 + **零**出站 | AST | 继承（只接线） |
| **G5** | 每个新源文件带署名头且 docstring 为首个语句 | 逐文件首行逐字相等 | 继承（**范围不变** · 硬编码清单**不扩** —— 本 feature 的新文件由 **G30** 覆盖，见 §3） |
| **G6** | `py.typed` 存在且为空 | 文件存在 + 大小 == 0 | 继承（只接线） |
| **G7** | 契约层公开符号面**恰为 18 个** | `__all__` 集合相等 | 继承（只接线） |
| **G8** | 文档合规门禁（兼容矩阵覆盖**契约层 18 个**符号） | 逐符号覆盖 + 4 列 | 继承（只接线） |
| **G9** | **运行时环境基线**：typing 构件上限 = 3.11 | AST 扫描禁用构件 | 继承（**只接线进 CI 矩阵** —— 否则 G9 永远不在 CI 上跑） |
| **G10** | 协议**纯抽象**（方法体只有 `...`） | AST | 继承（只接线） |
| **G11** | 结构化子类型判定可用 | 运行时 | 继承（只接线） |
| **G12** | 公开符号面**唯一权威** | 机器标记 `<!-- authority: yes\|no -->` | 继承（只接线） |
| **G13** | **纯数据纪律** | 注解扫描 | 继承（只接线） |
| **G14** | 门面**零实现体** | AST | 继承（只接线） |
| **G15** | 门面导出面**两处相等** | `__all` ∩ 公开名 | 继承（只接线） |
| **G16** | **API 快照**逐字节比对 + **可复现** | 生成 vs 入库快照 | 继承（只接线） |
| **G17** | 门面**依赖卫生**（两档） | AST | 继承（只接线） |
| **G18** | 门面的**模块加载面** | 子进程 `sys.modules` 快照 | 继承（只接线） |
| **G19** | 兼容矩阵**覆盖门面 7 个符号** | 章节内取行 | 继承（只接线） |
| **G20** | B2F2 **新建源文件**的署名头 | 逐文件首行逐字相等 | 继承（**范围不变** · 本 feature 的新文件由 **G30** 覆盖） |
| **G21** | **依赖闭包黑名单**（声明级 · **含全部 extras 变体**） | `Requires-Dist` 求值 + 递归展开 | **新增** |
| **G22** | **隔离环境断言**（依赖闭包为空集 + `sys.modules` 无 langchain 家族） | 隔离 venv + 子进程 | **新增** |
| **G23** | **许可证白名单**（4 级证据链 · 5 个精确 SPDX id） | `importlib.metadata` + SPDX 表达式解析 | **新增** |
| **G24** | **配置层**（`LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` 零读取 + 内核零环境变量） | AST 扫描 `src/freegraph/**` | **新增** |
| **G25** | **导入图单向**（ARCH-1） | AST + 层注册表 | **新增** |
| **G26** | **网络静态扫描**（`src/freegraph/**` 无网络客户端调用） | AST 扫描 `src/freegraph/**` | **新增** |
| **G27** | **零出站动态断言**（只观测不阻断 + 第一个非标准库帧归因） | socket 夹具 | **新增** |
| **G28** | **断网等价性**（全量测试套件 + 可机读排除清单） | Linux 网络命名空间 | **新增** |
| **G29** | **契约门禁载体**（只读基准 diff + 验收脚本集退出码 + C4 / C8 挂载点） | `git show` + `difflib` + 退出码来源解析 + 挂载点占位 | **新增** |
| **G30** | **全仓署名头**（覆盖率 == 100%）**+ 第三方品牌资产**（FR-021） | `git ls-files '*.py'` 逐文件首行 + 品牌资产扫描 | **新增** |

---

## 1. 逐条判定细则（G21–G30）

### G21 · 依赖闭包黑名单（**新增**）

**判定**（**声明级** —— 读 `pyproject.toml` 的声明，freegraph 本身**无需安装**；但**递归展开传递依赖**需要传递依赖**已安装** ⇒ 见下方警告）：

1. 从 `pyproject.toml` 读出 freegraph 的**全部** `Requires-Dist` 声明
   （等价于 `importlib.metadata.requires("freegraph")`，但**在未安装时也能跑**）；
2. 按 **freegraph 自身的 extras 变体**逐一枚举（基础 + 每个 extra 单独 + 全部同时），
   对每种变体求值 marker，得到该变体下的直接依赖集合；
3. 对每个依赖**递归展开**其**基础依赖**（传递依赖按**基础依赖**展开，**不**展开它们自己的 extras
   —— 见 [dependency-gate.md](./dependency-gate.md) §2.3）；
4. 断言闭包中**无**任何包命中黑名单。

> **⚠️ v1.0 的判据对象 = v2.0 清单**（2026-11-08 · 裁定 26 · 宪法 v1.7.0）：
> v1.0 的发行元数据**零依赖包名** ⇒ 本门禁的「被检依赖声明文件」默认指向
> **`contracts/extras-v2.toml`**（**不进发行包**）⇒ **v1.0 即完成预验证**
> ⇒ v2.0 落地时只需把清单搬进 `pyproject.toml`，**门禁实现零改动**。
>
> **⚠️ 变体数 = 6（不是 5）**（2026-11-07 分析轮修正）：基础 1 + **每个 extra 单独 4** + 全部同时 1
> ⇒ 漏掉任一**单独** extra 都会让该 extra 的依赖**永不被判**（例：漏 `[png]` ⇒ `playwright` 不受检 —— 该 extra 的后端 = **`playwright`**，**宪法 v1.5.0 已列明**）。
> **⚠️ 「未安装的依赖」的处理（不可静默跳过 · 2026-11-07 分析轮补入）**：递归展开需要读取
> **传递依赖自身的元数据** ⇒ 该依赖**未安装**时 MUST **显式报「未安装 ⇒ 无法取证」并判失败**（指名该包），
> **MUST NOT** 静默 `except` 跳过 —— 静默跳过会把「闭包只到第一层」伪装成「闭包干净」，
> 使「间接引入的黑名单包」**永远抓不到**（spec Edge Case「递归展开 MUST 走到闭包末端」）。
> ⇒ 这正是 **CI 必须装齐四个 extras 的依赖**的原因（ci-matrix §2 的「为什么 extras 必须装」）。
> **⚠️ 由此得出的 CI 约束（2026-11-07 分析轮补入）**：本规则要求 extras 的**传递依赖已安装**才能完成取证 ⇒
> **全部 7 个作业（含 macOS / Windows）MUST 装齐四个 extras 的依赖**（ci-matrix §2 **步骤 5.5** · **不再仅限 Linux 全量作业**）——
> 否则非 Linux 作业上 G21 会因「未安装 ⇒ 判失败」而**必然变红**（**实测**：仅装基础包时 `importlib.metadata.requires('pydantic')` 抛 `PackageNotFoundError`）。

**黑名单**（三族 + 点名名单 + `deepagents` + 全部 provider 包）：

| 族 | 匹配规则 | 覆盖 |
|---|---|---|
| `langsmith` | 精确名 + `langsmith-*` | `langsmith` / `langsmith[otel]` / `langsmith[sandbox]` / `langsmith-sdk` |
| `langchain*` | 前缀 `langchain` | `langchain` / `langchain-core` / `langchain-classic` / `langchain-protocol` / `langchain-anthropic` / `langchain-openai` / `langchain-google-genai` … |
| `langgraph*` | 前缀 `langgraph` | `langgraph` / `langgraph-checkpoint` / `langgraph-sdk` / `langgraph-prebuilt` / `langgraph-cli` … |
| **全部 provider 包** | 前缀 `langchain-` | 它们会把 `langchain-core` 拉回来（**由 `langchain*` 族覆盖** · 显式登记以与 `dependency-gate.md` §5 逐行一致） |
| **点名名单** | 精确名 | `langgraph-api` · `langgraph-runtime-inmem` · `phoenix`（ELv2 组件 · 宪法原则 IX） |
| `deepagents` | 精确名 | `deepagents`（宪法原则 IX 与立项书 §5.5 的**包层黑名单**明列项） |

> **📌 黑名单的逐项一致性（2026-11-08 分析轮订正 · H1 + Q4）**：本表与
> [dependency-gate.md](./dependency-gate.md) **§5「依赖黑名单」** MUST **逐行一致**
> （族 · 匹配规则 · **全部 provider 包** · 点名名单 · `deepagents` —— 五项**缺一不可**）⇒
> **冻结契约 MUST NOT 比红线少一条**（`deepagents` 是宪法原则 IX 与立项书 §5.5 **明列**的黑名单项，
> 而 `dependency-gate.md` §5 / `tasks.md` **T022** / 宪法「包层黑名单」/ 立项书 §5.5 **四处**都有它
> ⇒ 原表**漏列** ⇒ 本轮补齐）。
> **ELv2 点名名单**在 `dependency-gate.md` **§4.5** 登记（许可证维度）· 本表以「**点名名单**」行承载**同一组精确名**
> ⇒ 两表指向同一组包，MUST NOT 出现「一条有、一条无」。

**报错格式**（FR-016 ①）：MUST 含 **包名** + **命中的规则编号** + **它出现在哪个 extras 变体** + 修复指引。

> **为何前缀匹配不误伤**：前缀 `langchain` 会误伤 `langchainx` 这类无关包。
> **取舍**：**保守方向**（宁可多拦）—— 依赖黑名单**宁可错杀不可漏放**；
> 且 `langchain*` 已是宪法「包层黑名单」的原文表述。
> 用户自建的同名包被误拦是**已知代价**，MUST NOT 引入「按需新增的白名单豁免」（FR-018 ①）。

**反向用例（FR-014 ② · 强制）**：在**临时副本**的 `pyproject.toml` 里加一行
`"langchain-core>=0.3"` ⇒ G21 MUST 失败并指名 `langchain-core`（裁定 9 · research D-12）。

---

### G22 · 隔离环境断言（**新增**）

**判定**（**必须在隔离 venv 中执行** —— 测试进程自身已装 pytest 与开发依赖，不可用作依据）：

1. 用 `uv venv` 在临时目录建一个**全新虚拟环境**；
2. `uv pip install <本仓库>`（**只装基础包**，**不装任何 extra**）；
3. 断言 **基础安装的第三方依赖闭包 == 空集**（SC-002）——
   即环境内除 `freegraph` 自身与安装器自带组件外**无任何第三方包**；
4. 在该环境中 `python -c "import freegraph; ..."` ⇒ 断言 `sys.modules` 中
   **无** `langsmith` / `langchain_core` / `langgraph`（FR-005 ②）。

**场景 ② · 验收环境（FR-005 ③ · 立项书 §9.2 断言③ · D12 的「两套断言」之第二套 · **裁定 22 分阶段落地**）**：

5. 在**同一** venv 里**额外**装 `langchain-core`（模拟「脚本自带的 `langchain` 系」）⇒
   断言 **③① 声明级**：freegraph 自身 `Requires-Dist` **无** `langchain*` / `langsmith` / `langgraph*`；
6. 在该环境 `import freegraph` **及** `import freegraph.graph`（公开 API 门面）⇒ 断言
   `sys.modules` 中**从未**出现 `langchain` / `langchain_core` / `langgraph`
   —— **运行环境里有 ≠ 被 freegraph 引入**；
7. 同时断言**零出站**（复用 G27 的归因函数，「框架出站 == 0」）；
8. **③② 运行期（最小图）**：**B3F1 不交付** —— 待 B6F1（建图）/ B7F2（compile）/ B7F3（invoke）交付内核运行时后由 **M2** 的 feature 承接（**裁定 22** · 里程碑依据 立项书 §6.2）
   （**FR-005 ③②** · 裁定 22）。

> **为何 MUST 有场景 ②**：场景 ① 只证明「freegraph 自己的依赖闭包干净」；
> 场景 ② 才证明「**即使** `langchain` 就在旁边，freegraph 也**不碰**它」
> —— 这正是 D12「依赖红线的作用域 = freegraph 自身」的**可判定形式**。
> **反向用例（B3F1 形态 = 声明级 + 导入级）**：① 在副本的 `pyproject.toml` 加 `langchain-core`
> ⇒ 场景 ② MUST 失败并指名（**须以 `--target-root <副本>` 调用**，否则注入不被观察到）；
> ② 在**可达**位置注入 `import langchain` —— **MUST 改写副本的 `src/freegraph/__init__.py`**：
> 顶层包是**惰性空壳**（只暴露 `__version__`，不导入任何子模块）⇒ 新建的 `_probe.py` **永不被加载**
> ⇒ 注入落在其上会**空转**、证明不了任何事 ⇒ 场景 ② MUST 失败（证明该断言**不是空转**）。

**与 G3 的分工**：G3 判**已安装环境**的闭包（可 `skip`）；G22 判**真隔离环境** ⇒ G22 是**证据级**的。

**反向用例（强制）**：在隔离环境里 `uv pip install langchain-core` 后断言 G22 失败 ⇒ 或更省：
在副本的 `pyproject.toml` 加 `langchain-core` ⇒ G21 与 G22 **同时**失败。

---

### G23 · 许可证白名单（**新增**）

**判定**：对**每一个**出现在依赖闭包中的包：

1. 按 [dependency-gate.md](./dependency-gate.md) §3 的**四级有序证据链**取许可标识
   （`License-Expression` → `License` → `License ::` 分类器 → `dist-info/licenses/` 授权文件原文）；
2. 把取到的标识解析为 **SPDX 表达式**（用 `packaging>=24.2` 的 `packaging.licenses`
   —— 该模块自 24.2 才存在 · research D-05 有实测验证）；
3. 断言表达式的**每一个叶子标识符** ∈ **{MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}**；
4. 断言**取不到**许可证明的包 ⇒ **失败并指名**（FR-006 ② · **不 skip**）。

**禁用清单**：出现 `Elastic-2.0` / `AGPL` / `SSPL` / `BUSL` / `GPL-2` / `GPL-3` / `MPL-2.0` / `LGPL` 等
⇒ **失败**（宪法原则 IX 的传染性 / 限制性名单）。

> **📌 v1.0 的闭包来源 = v2.0 清单**（2026-11-08 · 裁定 26 · 宪法 v1.7.0）：
> 本门禁的「依赖闭包」取自 **`--project`** 指向的**依赖声明文件**
> （**同名同义**于 G21 的 `--project`；**MUST NOT** 当作 `--root` 的别名）
> —— v1.0 ⇒ `contracts/extras-v2.toml`（预验证）；v2.0 ⇒ `pyproject.toml`。
>
> **📌 `--root` 的取证作用域 = **并集口径**（2026-11-08 分析轮订正 · MUST 照此实现 · 与 §2.1 的 CLI 契约配套 · spec 裁定 25）**：
> `--root` = **被检的环境根** —— 它界定「**许可证据的取证作用域**」。
>
> **被检查的包集合 =（依赖闭包中的包）∪（在该根目录下扫到的 `*.dist-info` / `*.egg-info` 所对应的包）** —— **两部分都要查**。
> **许可证据的读取顺序（先到先得）**：① 该根目录下的 `<name>-<version>.dist-info/METADATA`（或 `.egg-info/PKG-INFO`）⇒ ② 该包**已安装**的元数据（`importlib.metadata`）。
>
> ⇒ **正常路径**：闭包里的 12 个包（其元数据在 venv 的 site-packages，**不在** `--root` 下）⇒ 由 ② 取证 ⇒ 门禁**非空**（MUST NOT 退化为空门禁）。
> ⇒ **反向路径**：`<root>` 下注入的假元数据 ⇒ 由 ① 取证 ⇒ 进入被检查集 ⇒ 命中 `AGPL-3.0-or-later` ⇒ 失败并指名。
> ⇒ **反向用例的假元数据 MUST 落成 `<root>/<name>-<version>.dist-info/METADATA`**，
> 其中 `METADATA` MUST 至少含 **`Metadata-Version` / `Name` / `Version` / `License-Expression`** 四个头，
> 且 `Name` / `Version` MUST 与目录名 `<name>-<version>` **一致**
> —— 否则 `importlib.metadata` 解析不出合法 distribution ⇒ 用例**空转**（与 `tasks.md` **T016** 逐字一致）。
> ⇒ **等价实现路径**（任一即可，语义相同）：`importlib.metadata.distributions(
> context=importlib.metadata.DistributionFinder.Context(path=[<root>]))` **并上**已安装集；
> 或直接扫描 `<root>/*.dist-info` / `<root>/*.egg-info` 的 `METADATA` / `PKG-INFO`。
> ⇒ **MUST NOT** 只查该根（正常路径一个包都查不到 ⇒ **空门禁 ⇒ 违宪**），
> 也 **MUST NOT** 只查已安装包（反向用例**空转**）。
> ⇒ **MUST NOT** 因此放宽「取不到许可证明 ⇒ 判失败」（FR-006 ②）——
> 作用域扩大**只**意味着取证范围变宽，MUST NOT 变成「查不到就放过」。

**边界（裁定 18）**：
- MUST **不**引入等价标识符对照表 / 许可证家族判定 / 豁免入口；
- MUST **不**使用「子串包含」判定（`"MIT" in upper` 会放行 `MIT-CMU`）；
- 散文式标识（如 `protobuf` 的 `3-Clause BSD License`）**无法归一为 SPDX id** ⇒ **判失败**。

**反向用例（强制）**：造一份**假元数据**（`License-Expression: AGPL-3.0-or-later`）⇒ G23 MUST 失败并指名。

---

### G24 · 配置层（**新增**）

**判定**（AST 扫描 · 扫描域 **限于 `src/freegraph/**`** —— FR-007 ①）：

1. `freegraph` 包内 MUST NOT 出现对 `LANGSMITH_*` / `LANGCHAIN_*` /
   `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` 的**读取**；
2. `freegraph` **内核**（`src/freegraph/**`）MUST NOT 读取**任何**环境变量
   （`os.environ` / `os.getenv` / `os.environb` 等一律违规）。

**扫描域的必要性（FR-007 ①）**：门禁脚本、测试夹具与 CI 配置**必然**读环境变量
（`CI` / `GITHUB_*` / `PYTHONPATH`）⇒ 若扫它们，门禁会**把自己判红**。

**反向用例（强制）**：在临时副本的 `src/freegraph/_probe.py` 里写
`os.environ["LANGSMITH_API_KEY"]` ⇒ G24 MUST 失败并指名**文件 + 行号**。

---

### G25 · 导入图单向（ARCH-1 · **新增**）

**判定**（AST + 层注册表）：

1. 层的归属由 [layer-registry.md](./layer-registry.md)（**唯一权威** · 机器可读）解析
   —— MUST NOT 靠路径前缀猜测（FR-008 ②）；
2. 扫描域 = **`src/freegraph/**` ∪ [layer-registry.md](./layer-registry.md) 中声明的
   **全部跨层单元路径**（当前 = `harness/scripts/gates/` 与 `harness/proposals/`
   —— `src/freegraph/graph.py` 已在 `src/freegraph/**` 之内）—— 跨层单元自身的 import 方向
   **同样受检**（「只能 import L1 与更低层」），否则注册表里的跨层单元条目**形同虚设**；
   对扫描域内的每个模块，解析其**全部** import（`import` / `from ... import`），
   解析出被导入模块的**层归属**；
3. **允许方向**（**口径三处逐字一致** —— spec FR-008 · [layer-registry.md](./layer-registry.md) §0.2 规则 2 ·
   [data-model.md](../data-model.md) §5.2 方向矩阵）：
   **层编号递增**（高层可 import 低层）；**反向 import 违规**；
   **同层 import 仅 L1 与 L6 允许，L2–L5 之间禁止横向依赖**（立项书 §5.1「依赖方向铁律」第 3 条）。
   > **📌 同层口径的裁定（2026-11-08 分析轮订正 · 已拍板 · 不得重新讨论）**：立项书 §5.1 铁律 3 只禁
   > 「**L2–L5 之间**」的横向依赖，**未禁 L1 / L6 的同层 import**；且**仓库现状**存在 **L1 → L1 同层 import**
   > （`src/freegraph/contracts/__init__.py` 与 `src/freegraph/contracts/protocols.py` 的 `from .xxx import ...`）
   > ⇒ 若按「层编号严格递增」实现，G25 上线当天即把**已冻结的契约层代码判红** ⇒ 违反 PR-4
   > 「feature 必须能独立通过门禁」⇒ 故**同层 import 的唯一例外 = L1 与 L6**。
4. **跨层单元**（层 = 「—」）MUST 只能 import **L1 与更低层**，且 MUST NOT 被 **L2–L5** import；
   **同一跨层单元内部**的模块互相 import ⇒ **不产生层边 ⇒ 不构成违规**
   （spec FR-008 ④ · 2026-11-08 分析轮订正）—— **不同**跨层单元之间的 import **仍**按上句判违规；
   **模块定位口径**：import 的目标 MUST 先被**定位到具体路径**（以被检根 + `sys.path` 解析）⇒
   落在**同一注册表条目**下 ⇒ 单元内部引用（不产生层边）· 落在**其它条目**下 ⇒ 按层间方向判定 ·
   **无法解析到仓库内路径** ⇒ 视为第三方 ⇒ 不产生层边；
5. **公开 API 门面**是 ARCH-1 的**唯一既有例外**（横跨 L1–L3，允许 import L1–L3，仍不得 import L4 / L5）
   —— 由层注册表显式声明，MUST NOT 硬编码在门禁实现里；
6. **本门禁 NOT 重复判的两条（2026-11-08 分析轮订正 · M10）**：
   - **「L1 契约层内部零内部层 import」由既有门禁 G2 承担**（范围 = `src/freegraph/contracts/**`）⇒
     **G25 不重复判**（注册表 §0.3 **L-2**）；
   - **「顶层包 `src/freegraph/__init__.py` MUST NOT import 任何内部层（含同层 L1）」由注册表 §0.3
     **L-1** 声明、G25 判**（具名例外** · 优先于第 3 条的「L1 与 L6 允许同层 import」）——
     ⇒ **顶层包仍是惰性空壳**（ARCH-2 · D1 决议附加约束），而「L1 契约层**内部**的同层 import」仍然允许。

**反向用例（强制）**：造一个 `src/freegraph/_probe.py` 写 `from freegraph.contracts import StateDict`
并把它登记为 L3 ⇒ 它 import L1 是**合法**的；反向用例 MUST 用 **L1 import L3** 的形态构造
⇒ G25 MUST 失败。
> **⚠️ 同层方向的反向用例（2026-11-08 分析轮订正 · 与 §0.3 L-1 配套）**：
> **L2–L5 之间的同层 import MUST 判失败**（如登记为 L4 的模块 import 另一个 L4 模块 ⇒ 红）；
> 而 **L1 → L1**（契约层内部）与 **L6 → L6**（应用层内部）MUST **判通过** ⇒
> **反向用例 MUST NOT** 用「L1 → L1」构造（同层 L1 是**允许**方向 —— 否则会把已冻结的契约层判红）。

---

### G26 · 网络静态扫描（**新增**）

**判定**（AST 扫描 · `src/freegraph/**`）：MUST NOT 出现下列网络客户端的 import 或使用：

`socket` · `ssl` · `http` · `http.client` · `urllib.request` · `urllib3` · `requests` · `httpx` ·
`aiohttp` · `websockets` · `ftplib` · `smtplib` · `telnetlib` · `xmlrpc` · `asyncio.open_connection`

**判定口径（2026-11-07 分析轮补入）**：本扫描 MUST 以 **import 形式**判定
（`import X` / `from X import ...` / 属性链调用）⇒ 清单内的**纯 stdlib 常量用法**
（如 `http.HTTPStatus` 这类不含任何网络行为的常量）会被**一并命中** ⇒ 实现时 MUST 区分
「导入网络客户端模块」与「仅引用其常量」两种形态，后者需**具名例外**才可通过；
MUST NOT 因此放宽清单本身。

**唯一例外**（FR-009 ① · FR-018 ① 的「已写死的、具名例外」）：**可选的 OTLP exporter 模块** ——
它是**用户显式启用**才生效的合法出站方。例外 MUST 以**显式名单**表达（模块路径逐个列出），
MUST NOT 放宽扫描域本身。**当前该例外名单为空**（OTLP exporter 属 B21F1）。

**反向用例（强制）**：在临时副本的 `src/freegraph/_probe.py` 写 `import socket` ⇒ G26 MUST 失败并指名。

---

### G27 · 零出站动态断言（**新增** · **不强制反向用例**）

**判定**（pytest 夹具 · 只观测不阻断）：

> **两个入口 · 同一实现**（2026-11-07 分析轮补入）：归因函数与 socket 包装 MUST 落在
> `harness/scripts/gates/_gatekit.py`（纯函数 / 上下文管理器）⇒
> ① `gate_G27_zero_egress.py` 作为**独立可执行入口**调用它（FR-016「退出码即判定」· CI 可逐条调用）；
> ② pytest 夹具调用**同一实现** ⇒ **MUST NOT** 各写一份归因逻辑。

1. 夹具**只包装** `socket.connect` 与 `socket.create_connection` ⇒ **记录**目标与调用栈，
   **放行**全部连接（FR-009 ② · 裁定 7）；
2. 每次连接按**第一个非标准库帧**规则归因（裁定 19 · research D-11）：
   从栈顶向下**跳过全部标准库帧**，遇到的**第一个非标准库帧**在 `freegraph/` 内 ⇒ 「框架出站」；
   否则 ⇒ 「用户出站」；
3. 断言**「框架出站」条目数 == 0**；「用户出站」**记录在案但不判失败**。

**四种栈形态 MUST 全判对**（FR-009 ②②）：用**合成调用栈**驱动的单元断言
（MUST NOT 依赖真实出网 · FR-009 ②③）——
① freegraph 内部模块直接联网 ⇒ 框架出站；② 用户工具函数联网（freegraph 只是调用方）⇒ **用户出站**；
③ 用户脚本直接联网 ⇒ 用户出站；④ freegraph 直接使用 socket ⇒ 框架出站。

**freegraph MUST NOT 安装任何出网拦截机制**（FR-009 ③）⇒ 夹具是**测试侧**工件，
MUST NOT 出现在 `src/freegraph/**` 内（否则 G26 会判它红）。

**独立入口的观测面（MUST 声明 · 2026-11-07 分析轮补入）**：
`gate_G27_zero_egress.py` 作为**独立可执行入口**时，其**观测面** MUST **非空**且在输出中**显式打印** ——
**B3F1 = 「在 egress 监测下跑整个测试套件」**（`pytest tests/`，夹具全程监测 · 裁定 7），
输出 MUST 同时打印「**当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）**」。
MUST NOT 让「空断言 / 极窄观测面」被误读为「零出站已被证明」；
运行期观测面（最小图执行）待 **M2** 承接（与裁定 22 同源 · 里程碑依据 立项书 §6.2）。
**SC-006 的双向可验证**（注入一次用户出站 ⇒ 归因为「用户出站」）由 **pytest 夹具路径**承担
（T036 · `tests/gates/conftest.py` 的 `egress_recorder`），独立入口**不**承担该反向验证。

**覆盖方式**（裁定 14）：**正向断言 + 人工验证记录取证**（人工记录 MUST 留「框架出站 = 0」的实测证据）。

---

### G28 · 断网等价性（**新增** · **不强制反向用例** · **Linux 专属**）

**判定**：

1. 在**网络命名空间**中执行（`unshare --net --map-root-user`）⇒ **全部网络接口不可用**
   （含回环 · FR-010）；
2. 重跑**核心用例** = **全量测试套件**（`tests/`），**扣除**排除清单中的条目；
3. 排除清单 = `tests/gates/data/offline_exclusions.txt`（**可机读** · **逐条理由** · FR-010 ④）；
   排除项 **仅限两类**（FR-010 ③）：(a) **断网任务自身**（不可嵌套）；(b) **语义上必须能建立连接**的用例；
4. 断言**通过率 == 100%**（SC-004）；
5. **排除清单的自校验（MUST · 2026-11-08 分析轮订正 · 关闭 A5 的失败模式）**：
   清单中的**每一条**用例标识 MUST **实际存在且确实被排除** ⇒
   ① **先收集**本次运行的测试 node ID 全集；
   ② **逐条比对**清单里的每个标识：不存在 ⇒ **判失败并指名该条**（清单漂移）；
   存在 ⇒ 确认它**未出现在**实际执行的测试集中（确实被排除）。
   > **为什么必须加这条**：实测 **pytest 7.4.4 与 9.2.0 对「指向不存在 node id 的 `--deselect`」均不报错**
   > （静默忽略 · 退出码 0）⇒ 清单与用例名一旦漂移，**排除会静默失效** ⇒ 被排除的用例在断网下**假红**
   > （而非「静默放过」）⇒ 失败虽可察觉，但**原因会被误判为「断网等价性失败」**。
   > 本条把「清单漂移」变成**指名报错**，与「假红」区分开。

**平台**：**仅 Linux**（裁定 10 · FR-010 ①）；macOS / Windows **不要求**。

**覆盖方式**（裁定 14）：**正向断言 + 人工验证记录取证**（人工记录 MUST 留「断网全绿」的实测证据）。

---

### G29 · 契约门禁载体（**新增**）

**判定**：

1. **只读基准 diff 断言**：`harness/demo/target.py` 的内容 MUST 与**入库基准**逐字相同
   ⇒ 改动即失败（FR-011 ① · **不设「已批准豁免」通道**）；
   **基准载体（MUST 明确 · 2026-11-07 分析轮补入）**：**入库基准** = **Git 索引中的 `HEAD:harness/demo/target.py`**（`git show HEAD:harness/demo/target.py`）——
   仓库内**不存在**第二份基准副本（**实测**：`git ls-files` 中 `target.py` 仅一份）⇒ MUST NOT 依赖「仓库内另一份文件」；
   读取基准 MUST 经 `git show`（**只读**，MUST NOT 改动工作树）。
2. **验收脚本集的退出码断言**（立项书 §9.1 门禁 3 的「固定脚本**原样可跑**」半边）：
   跑 `harness/demo/{graph_core,agent_loop,visualization}.py` ⇒ 断言退出码 ∈ **{0, 1, 2}**——
   **0 = PASS** · **2 = 环境未就绪**（freegraph **不可导入**）· **1 = 断言失败**。
   **⚠️ 「1」的细分口径（2026-11-07 分析轮定案 · 关键修正）**：CI 中 freegraph **已安装**（ci-matrix §2 步骤 5 · 装发行形态）⇒ 三个脚本
   **能成功 import** ⇒ 退出码 2 的分支（`except ImportError`）**不会触发** ⇒ 脚本会走到用例体并因 `NotImplementedError`
   被记为**断言失败** ⇒ **退出码为 1**（**实测**：freegraph 可导入时三个脚本退出码**全为 1**；不可导入时才是 2）。
   故本门禁 MUST 按**失败来源**细分退出码 1：
   - **1 且全部失败均源于 `NotImplementedError`** ⇒ 判为**环境未就绪**（内核运行时未接线 · 属**预期**状态）⇒ **通过**；
   - **1 且存在非 `NotImplementedError` 的失败** ⇒ 判为**真断言失败** ⇒ **CI 失败**。
   该细分即 立项书 §9.2「内核未开工时 CI 应显示『环境未就绪』而非『验收失败』」的可判定实现
   （**替代口径已废弃**：原「断言退出码 ∈ {0, 2}」在 CI 条件下**必然失败** ⇒ 7/7 作业全红，违反 PR-4）；
   **落地时 MUST 解析脚本输出**以区分失败来源（不得只看退出码）。
3. **C4 / C8 两条独立回归测试的挂载点** MUST 存在（FR-011 ②）：
   - **C4**（稀疏状态读）：`"llm_calls" not in node_input` 且 `.get("llm_calls", 0) == 0`；
   - **C8**（条件边 fresh 状态读）：路由函数看到本节点刚写入的值；
   - **C4 在 M1 建立**（B5F2）· **C8 在 M2 建立**（B8F1）⇒ **挂载点 MUST 明确标记为「未落地」**
     （MUST NOT 伪装成「已通过」）。
4. `--check-compat` 模式（**分层判定** · 裁定 13 · FR-012 ② · research D-14）：
   - **终版 `COMPAT.md`**：**存在** ⇒ **严格比对**；**有不一致** ⇒ **退出码非 0**（阻断，指名**哪一行、哪一个符号** ·
     FR-012 ②③④）；**一致** ⇒ **退出码 0**；**不存在** ⇒ 输出「**未落地**」且**退出码 0**（非阻断 · MUST NOT 静默跳过）。
     ⇒ 「**自动转为严格比对**」由**文件是否存在**驱动，**同一套判据、无需改门禁实现**（FR-012 ②）。
     > **⚠️ 阻断条件的口径（2026-11-08 分析轮订正 · 消除「存在即红」的误读）**：MUST NOT 仅因「`COMPAT.md` **存在**」而非 0 ——
     > 否则后续 feature 建出 `COMPAT.md` 后该步骤**永久红**（违宪 v1.6.0 红线「MUST NOT 写永久红的 CI」）⇒ 阻断条件是「**有不一致**」，不是「存在」。
   - **已入库章节（`README.md`「API 兼容矩阵」）**：其严格比对由**既有门禁 G8 / G19** 承担
     （pytest 步骤已跑）⇒ 本模式 MUST **引用**其判据来源，MUST NOT **重复实现**
     （裁定 8 第三条理由：避免「同一判据两处实现」）。

**反向用例（强制）**：把 `target.py` 的副本改一个字 ⇒ G29 MUST 失败并给出 **diff**（**须经 `--baseline` 指定基准** —— 见 §2.1）。

---

### G30 · 全仓署名头（**新增**）

**判定**（FR-013 ④）：

1. 取仓库内**全部受版本控制的 `.py` 文件**（`git ls-files '*.py'`）——
   即 `src/` + `tests/` + `harness/` **三个目录**，**无例外目录**；
2. 每个文件 MUST 在**顶部**含署名声明（作者 · 许可证 · 项目地址），**逐字**等于：

```
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
```

3. **两个具名例外**：`py.typed`（PEP 561 要求为空）· `harness/demo/target.py`（只读基准 · 宪法原则 III）；
4. 带 shebang 的脚本：署名头 MUST 在 shebang **之后**；模块 docstring MUST 仍是**首个语句**（FR-013 ②）；
5. 缺失的文件 MUST 被**逐个指名**（含路径）⇒ MUST NOT 只报总数（FR-013 ③）；
6. **第三方品牌资产断言**（宪法原则 IX 第三条 · 立项书 §9.1 门禁 2 · **spec FR-021**）：
   断言仓库内**无第三方品牌资产**（FR-021 ① 的三类扫描域）：
   - **图像资产**：`.svg` / `.png` / `.ico` / `.jpg` / `.jpeg` / `.webp` / `.gif` 等扩展名的文件；
   - **品牌色定义**：样式文件（`.css` / `.scss`）与文档中的**第三方品牌色值** ——
     **判据 = 与下方「禁止色值清单」逐值比对**（hex 归一：`#RGB` ⇒ `#RRGGBB`；大小写不敏感）。
   - **官方描述文案**：官方《Brand Assets & Usage Guidelines》的 "Approved copy" 描述文案 ——
     **判据 = 与下方「禁止文案指纹清单」逐条子串比对**（大小写不敏感）。
   **两份具名清单（本节即载体 · 不另立文件 · 2026-11-08 分析轮定案 · 与 spec FR-021 ①「判定分工」逐字一致）**：

   | 清单 | 条目 | 判据 | 来源（URL + as-of 日期） |
   |---|---|---|---|
   | **禁止色值清单** | *（**当前为空集** —— 官方品牌色值**尚未逐字取证并落入本仓库** ⇒ MUST NOT 凭记忆写入 hex）* | hex 归一后逐值比对 | *（待取证 —— 官方《Brand Assets & Usage Guidelines》页）* |
   | **禁止文案指纹清单** | `enables every company to own their intelligence` | 大小写不敏感**子串**比对 | `harness/reports/Q7-开源边界地图与许可证合规.md` §3.3.3（来源 **D10** · `https://www.langchain.com/brand-assets` · as-of **2026-11-01**） |
   | **禁止文案指纹清单** | `model-agnostic harnesses give teams choice and control` | 同上 | 同上 |
   | **禁止文案指纹清单** | `brings testing, deployment, and monitoring together` | 同上 | 同上 |

   > **⚠️ 三条清单纪律（2026-11-08 分析轮定案 · MUST 照此执行）**：
   > ① **来源标记**：每个条目 MUST 附**官方页面 URL + as-of 日期**（原则 VIII）⇒ **MUST NOT** 凭记忆写入 hex 或文案；**无来源可依 ⇒ MUST NOT 入清单**（宁可漏判，不得引入无源断言）。
   > ② **指纹而非全文**：文案条目 MUST 取**可识别的指纹片段**（上表三条）⇒ 既能捕获「照抄」，又 **MUST NOT** 把官方 "Approved copy" 全文收入本仓库（与「MUST NOT 照抄官方文案」同一精神）。
   > ③ **扩充须走评审**：清单的扩充 MUST 走**评审**（同 `layer-registry.md` §3）⇒ **MUST NOT** 成为「按需新增」的豁免入口（FR-018 ①）—— **追加色值 ≠ 豁免**；**MUST NOT** 把「清单为空」当作「放过第三方资产」的理由（图像类仍 MUST 逐个指名）。
    > **清单为空的后果（不可回避）**：**禁止色值清单**为空 ⇒ 该子域**当前天然成立**（实测：仓库内无 `.css` / `.scss`，README 无第三方品牌色值）⇒ 但 **MUST NOT** 声称该子域「已自动判定」⇒ MUST 在人工验证记录中标注「**待取证**」（spec SC-016 的限定语）。
    >
    > **📌 「禁止文案指纹」子域的具名例外（2026-11-08 实现轮补入 · MUST 照此实现）**：
    > **两个条目缺一不可** —— 否则门禁**永久红**（违反宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」）：
    > ① **指纹清单的载体**（= 本文件）—— 指纹 MUST 记录在某处（否则无从判定）⇒ 载体必然包含这些片段 ⇒ MUST 排除；
    > ② **证据文档**（`harness/reports/Q7-开源边界地图与许可证合规.md`）—— 调研报告引用官方原文以**记录商标边界**（宪法原则 VIII 的来源标记义务）⇒ MUST 排除。
    > ⇒ 该例外清单**已写死、具名**（`harness/scripts/gates/_gatekit.py` 的 `BRAND_COPY_EXCLUDED_FILES`）⇒ **不是**「按需新增」的豁免入口（FR-018 ①）；扩充 MUST 走**评审**（同 §3 纪律）。
    > ⇒ **只排除「文案指纹」子域** —— **图像资产**子域 MUST 仍逐个指名（**MUST NOT** 把「清单为空 / 有例外」当作放过图像资产的理由）。


   **扫描域（两个清单子域 · 已定案）**：受版本控制的 **`.md` 文档** + **`.css` / `.scss` 样式文件**（图像资产子域另按扩展名全量扫描，不受此限）。
   **白名单口径（FR-021 ② · 关键修正 · MUST NOT 用过宽口径）**：
   正确口径 = **禁止第三方品牌资产**；**自有资产**（项目自有 logo / 架构图 / 演示截图等）MUST 登记在
   **已具名的「自有品牌资产白名单」**中（该白名单**当前为空集** —— **实测**：仓库内**无任何**受版本控制的
   图像 / 样式文件，README 中无第三方品牌色值与官方 "Approved copy" 文案 ⇒ 故当前「白名单外图像文件数 == 0」**天然成立**）。
   ⇒ **MUST NOT** 采用「白名单为空 ⇒ 禁止一切图像」的过宽口径（该口径会连**自有** logo 一并禁掉，**超出**宪法原则 IX 第三条的范围）。
   违例 MUST **逐个指名**（文件路径）。
   > **与既有 G8 的分工（FR-021 ③）**：宪法原则 IX 第三条第 ③ 项（README / 文档 MUST 声明
   > 「独立实现、非 LangChain Inc. 产品」）**已由既有门禁 G8 覆盖**（`tests/contracts/test_architecture.py` 的
   > `INDEPENDENCE_STATEMENT` 断言 + `test_compat_matrix_declares_no_affiliation`）⇒ 本断言段 **MUST NOT** 重复实现该条。
   > **为何并入 G30**：G30 已是「仓库卫生」类门禁 ⇒ 并入**不新增编号**
   > （裁定 4 的 G21–G30 连续性不受影响）。

**存量补齐**（FR-013 ⑤ · 裁定 5）：**实测**（2026-11-07 分析轮复核修正）——全仓受版本控制的 `.py`
共 **37** 个 ⇒ **35 个已合规**（**26** 个在首行 + **9** 个在 **shebang 之后**）⇒ **真正缺头的只有 1 个**：
`harness/scripts/audit_feature_drafts.py` ⇒ 它 MUST 在本 feature 内补齐（**MUST NOT** 给已合规的文件重复加头）。
`harness/demo/target.py` 为只读基准（宪法原则 III）· 具名例外 · 不动。
⇒ **G30 上线不会红**（原「`harness/` 下 10 个缺头」的判断经复核不成立）。

**反向用例（强制）**：
- **署名头段**：把某文件副本的**署名头**删掉 ⇒ G30 MUST 失败并指名该文件；
- **品牌资产段（FR-021 · SC-016）**：在**被检树**内放入一个第三方品牌资产（如带第三方 logo 的 `.svg`）
  ⇒ G30 MUST 失败并**指名该文件** ⇒ 该反向用例 MUST 经 `--root`（见 §2.1）在**隔离副本**上执行。

---

## 2. 门禁的执行方式

- **全部以「可独立执行的检查」交付**：每个门禁一个入口脚本（`harness/scripts/gates/gate_GNN_*.py`），
  **退出码即判定**（0 = 通过 · 非 0 = 失败），CI **逐条调用**（FR-016 · 裁定 12）。
- **重活集中在共享库** `harness/scripts/gates/_gatekit.py` ⇒ 「一处判据一处实现」（裁定 8 第三条理由）。
- **需要子进程 / 隔离环境的判定**（G22 · G27 的模块加载面）**必须在子进程中执行**。
- **每条门禁的失败输出 MUST 含**：违规条目（包名 或 文件路径:行号）+ **命中的规则编号** + 修复指引（FR-016 ①）。
- **反向用例**：8 条**强制**（G21 · G22 · G23 · G24 · G25 · G26 · G29 · G30）；
  G27 / G28 以「正向断言 + 人工取证」覆盖（裁定 14）。

### 2.1 门禁的 CLI 契约（**唯一权威** · 2026-11-07 分析轮补入）

> 本表是**门禁命令行接口的唯一权威** —— `tasks.md` 的实现任务 MUST 引用本表，MUST NOT 各自另定参数。
> 参数名一旦发布即冻结（改名 = 改契约）。

| 门禁 | 参数 | 默认值 | 语义 | 退出码 |
|---|---|---|---|---|
| **G21** | `--project <pyproject 路径>` | 仓库根的 `pyproject.toml` | **被检**的依赖声明文件 | 0 = 通过 · 非 0 = 失败 |
| **G21** | `--self-test-negative` | — | **内置负向验证**：在隔离副本注入 `langchain-core` ⇒ 断言门禁**必须失败** ⇒ **自检通过 ⇒ 退出码 0**；自检失败 ⇒ 退出码非 0 | 0 = 自检通过 · 非 0 = 自检失败 |
| **G22** | `--target-root <路径>` | 仓库根 | **被检**的源码根（隔离 venv 里 `uv pip install` 的目标） | 0 = 通过 · 非 0 = 失败 |
| **G22** | `--project <pyproject 路径>` | `<target-root>/pyproject.toml` | **被检**的依赖声明文件 | 同上 |
| **G23** | `--project <pyproject 路径>` | `<root>/pyproject.toml` | **被检**的**依赖声明文件**（**依赖闭包**的来源 · **同名同义**于 G21 的 `--project`；**MUST NOT** 当作 `--root` 的别名）。**v1.0** ⇒ `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`（**预验证** · 裁定 26） | 0 = 通过 · 非 0 = 失败 |
| **G23** | `--root <路径>` | 仓库根 | **被检**的环境根（**许可证据的取证作用域 · 并集口径** —— G23 的**被检查包集合 =（依赖闭包中的包）∪（本根目录下 `*.dist-info` / `*.egg-info` 所对应的包）**；许可证据**先**取本根目录下的元数据、**后**回落**已安装**元数据。反向用例 MUST 在隔离副本上注入假元数据 ⇒ 无此参数则注入不可见 ⇒ 用例**空转**） | 0 = 通过 · 非 0 = 失败 |
| **G24 / G25 / G26 / G30** | `--root <路径>` | 仓库根 | **被检**的树根（源码扫描 / 层归属解析 / 品牌资产扫描的作用域） | 0 = 通过 · 非 0 = 失败 |
| **G25** | `--registry <路径>` | `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` | **被检**的层注册表（**只读**；MUST NOT 改动冻结面） | 同上 |
| **G29** | `--root <路径>` | 仓库根 | **被检**的树根（**与 `--baseline` 组合使用** —— 只读基准 diff 的被检侧；`--baseline` 给基准侧） | 0 = 通过 · 非 0 = 失败 |
| **G29** | `--check-compat` | — | **兼容矩阵分层报告**：见 G29 §4 | `COMPAT.md` **不存在** ⇒ 0（报告「未落地」）· **存在** ⇒ **严格比对**：**有不一致** ⇒ 非 0（阻断，指名行/符号）；**一致** ⇒ 0 |
| **G29** | `--baseline <git ref>` | `HEAD` | **只读基准**的来源（`git show <ref>:harness/demo/target.py`） | 0 = 通过 · 非 0 = 失败 |

> **📌 作用域参数名不得混用（2026-11-08 分析轮订正 · H2 · **2026-11-08 裁定 26 补充**）**：
> **G21 与 G23 用 `--project`**（被检**依赖声明文件** · **同名同义**）·
> **G22 用 `--target-root`**（被检**源码根**）·
> **G23 与 G29 用 `--root`**（被检**环境根 / 树根**）——
> 三类**作用域参数名 MUST NOT 混用**（各行语义以上表为准）⇒
> 实现时 MUST NOT 把 `--root` 当作 `--project` 或 `--target-root` 的别名（否则反向用例会静默扫错对象）。
> **G29 的 `--root` 与 `--baseline` MUST 成对使用**：前者给**被检侧**、后者给**基准侧**
> （`tasks.md` **T020** 明确要求「以 `--root <isolated_copy>` + `--baseline HEAD` 调用 G29」）。

> **G21 `--self-test-negative` 的退出码语义（易错 · MUST 照此实现）**：该模式断言的是「门禁**必须**失败」，
> 故**自检通过 ⇒ 退出码 0**（**不是**「门禁失败 ⇒ 非 0」）。若把「退出码 ≠ 0」当作该命令的期望，
> 会在 CI 里把「成功」判成「失败」。
>
> **⚠️ `--root` / `--registry` / `--baseline` 的补入理由（2026-11-07 分析轮补入 · 必读）**：
> 本表原只覆盖 G21 / G22 / G29 三条门禁 ⇒ **6 条强制反向用例无法在隔离副本上执行**——
> G24 / G25 / G26 / G30 的反向用例（T017 · T018 · T019 · T021）均须把违规注入**隔离副本**，
> 而它们既无「被检树根」参数、又固定读仓库根下的路径 ⇒ **注入不可见 ⇒ 用例空转**；
> G25 的反向用例还须指定**另一个层注册表**（否则只能改动**冻结面** `layer-registry.md`，违反其 §3「改动须走评审」）。
> ⇒ 补入 `--root`（统一的作用域参数）与 `--registry`（G25 专用）；G29 的 diff 基准补 `--baseline`（默认 `HEAD`）。
> **参数名一旦发布即冻结** —— 本次补入后，MUST NOT 另起新名。

---

## 3. 与既有门禁的分工（避免重复判定）

| 主题 | 既有门禁 | 本 feature 的门禁 | 关系 |
|---|---|---|---|
| 依赖闭包 | **G3**（已安装环境 · 基础安装闭包 + extras 闭包 ⊆ 宪法白名单） | **G21**（**声明级** · 全部 extras 变体 · 黑名单）· **G22**（**真隔离 venv**） | **不重叠**：G3 判「白名单包名集合」，G21 判「黑名单」，G22 判「真隔离环境」 |
| 许可证 | **G3**（子串匹配 · 两条来源 · skip-on-missing） | **G23**（4 级证据链 · 精确 SPDX id · **fail-on-missing**） | **并存** —— **G23 严于 G3** ⇒ 总体效果为严。⚠️ 已知差异：`MIT-CMU` 在 G3 通过 / 在 G23 被拒（登记于 research DR-6） |
| 零环境变量 / 零出站 | **G4**（契约层 + 夹具目录）· **G17**（门面） | **G24**（`src/freegraph/**` 全域 · 配置层黑名单）· **G26**（网络静态） | **范围不重叠**：G4 / G17 判**既有目录**，G24 / G26 判**全域**且判据更细（配置层前缀 / 网络客户端清单） |
| 署名头 | **G5**（B1F1 的 8 个文件 · 硬编码清单）· **G20**（B2F2 的 10 个文件） | **G30**（**全仓** · `git ls-files` 驱动） | **兜底** —— G5 / G20 的**硬编码清单不扩**（保住「既有门禁实现零改动」纪律），G30 覆盖新增文件 |
| 兼容矩阵 | **G8**（契约层 18 个）· **G19**（门面 7 个） | 无新门禁 —— **只接线** + 「`COMPAT.md` 未落地」的**非阻断**报告 | **不重叠** |
| API 快照 | **G16** | 无新门禁 —— **只接线** | **不重叠** |
| typing 构件上限 | **G9** | 无新门禁 —— **只接线进 CI 矩阵** | **不重叠** |
| 导入图 | **G2**（契约层零内部 import）· **G18**（门面不横依赖 L4/L5） | **G25**（**全包** ARCH-1 单向 · 层注册表驱动） | **不重叠**：G2 / G18 判**特定目录的特定方向**，G25 判**全包的层间方向** |

---

## 4. 对既有门禁 G3 的占位填充（**裁定 8 的唯一一处例外**）

见 [plan.md](../plan.md)「Constitution Check · 唯一一处例外」与 [research.md](../research.md) **D-06**。

**改动**（**判据句零改动**）：

1. `CONSTITUTION_DEPENDENCY_WHITELIST`：4 个占位包名 → **四个 extra 的真实闭包确切包名集合**
   （有限 · 逐个列名 · **无通配符 · 无前缀匹配**）
   —— **⚠️ v1.0（裁定 26 · 宪法 v1.7.0）**：v1.0 **不声明任何 extra** ⇒ 本条在 v1.0 是
   **空断言**；这 12 个包名是 **v2.0 的目标闭包**（v2.0 落地时本条**自动变实质**
   ⇒ 门禁实现零改动）；
2. extras 变体枚举：从「无差别剥离 / 保留 extras marker」→ **只枚举 freegraph 自身的 extras 变体**
   （传递依赖按其**基础依赖**展开）。

**净效果 = 变严**（白名单更精确 · 枚举不再过近似）⇒ 符合 FR-018「不得放宽」。
**待发起者追认**（见 `tasks.md` 的追认项）。

> **⚠️ 实测澄清（2026-11-07 分析轮复核）**：extras 声明后**实际变红的是「白名单子集断言」**
> （**实测**：旧枚举语义下 extras 闭包为 **20** 个包，其中 **8** 个不在 4 个占位包名内 ——
> `email-validator` / `furo` / `objgraph` / `opentelemetry-configuration` / `psutil` / `setuptools` / `sphinx` / `tzdata`）；
> 而「许可证断言」实为 **`pytest.skip`**（这 8 个包**均未安装** ⇒ `_license_of()` 返回 `None` ⇒ 落入 G3 既有的
> `missing` 分支）⇒ **不构成变红原因**（这也正是新门禁 **G23**「fail-on-missing」不可省略的理由）。
> **修正后的枚举语义（②）实测**：extras 闭包**恰为**上述 12 个包名 ⇒ 与 ① 逐一命中、子集断言**绿**。

---

## 5. 本 feature 新建的源文件（宪法原则 X · 署名头适用范围）

```
harness/scripts/gates/_gatekit.py
harness/scripts/gates/gate_G21_dependencies.py
harness/scripts/gates/gate_G22_isolated_env.py
harness/scripts/gates/gate_G23_licenses.py
harness/scripts/gates/gate_G24_config_layer.py
harness/scripts/gates/gate_G25_import_graph.py
harness/scripts/gates/gate_G26_network_static.py
harness/scripts/gates/gate_G27_zero_egress.py
harness/scripts/gates/gate_G28_offline_equiv.py
harness/scripts/gates/gate_G29_contract_carrier.py
harness/scripts/gates/gate_G30_attribution.py
tests/gates/__init__.py
tests/gates/conftest.py
tests/gates/test_gates.py
tests/gates/data/offline_exclusions.txt（**非** .py · 不需署名头）
.github/workflows/ci.yml（**非** .py · 不需署名头）
```

**例外**：`py.typed` · `harness/demo/target.py`（G30 §1 第 3 条）。
