# CI 矩阵契约（ci-matrix.md）

**功能块**: B3F1 · 项目脚手架 + extras 划分 + CI 门禁 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-009 ~ FR-012 · FR-015 ~ FR-020 · SC-002b · SC-004 · SC-012 · SC-015 ·
裁定 2 · 裁定 3 · 裁定 10 · 裁定 13 · 裁定 15 · 裁定 20）· [architecture-gates.md](./architecture-gates.md) ·
[research.md](../research.md)（D-08 · D-10 · D-13 · D-14）
**契约性质**: **冻结面** —— 矩阵的**形状**与**分层**即实现契约

---

## 1. 作业矩阵（7 个作业 · FR-015 ④ · SC-012）

| # | runner | 架构 | Python | 门禁集合 | 断网任务（G28） |
|---|---|---|---|---|---|
| 1 | `ubuntu-24.04` | x86_64 | 3.11 | **全量** | ✅ |
| 2 | `ubuntu-24.04` | x86_64 | 3.14 | **全量** | ✅ |
| 3 | `macos-15` | arm64 | 3.11 | **子集** | ❌ |
| 4 | `macos-15` | arm64 | 3.14 | **子集** | ❌ |
| 5 | `windows-2025` | x86_64 | 3.11 | **子集** | ❌ |
| 6 | `windows-2025` | x86_64 | 3.14 | **子集** | ❌ |
| 7 | `ubuntu-24.04-arm` | arm64 | 3.11 | **全量** | ✅ |

**规则**

- **最低版本档 MUST 为 3.11 且 MUST 跑全量测试**（含**架构门禁的测试** —— `tests/contracts/` 与
  `tests/facade/` 承载的 G1–G20）—— 这是「typing 构件上限 = 3.11」的**主判定**（FR-015 ① · 裁定 2 · SC-002b）：
  任何 3.12+ / 3.13+ 构件在该档**天然不可用**（`ImportError` / `AttributeError` / `SyntaxError`）。
- **每个 Python 版本档 MUST 跑全量测试**（不只是最低档 · FR-015 ③）——
  新版本引入的行为差异由矩阵暴露。
- **Linux 跑全量门禁，其余平台跑子集**（FR-015 ②）——避免矩阵成本爆炸。
  **口径闭合（2026-11-08 分析轮订正 · H4）**：**测试** = 全量测试套件（平台专属用例按 marker 过滤）；
  **门禁** = Linux 全量（G21–G30）/ 其余平台子集（G21 · G23 · G24 · G25 · G26 · G29 · G30）
  ⇒ 二者是**两件事**，MUST NOT 混为一谈（「全量测试（含架构门禁的测试）」**≠**「全量门禁」）。
- **⚠️ 但「依赖安装范围」是 7/7 作业**（FR-015 ⑤）——**子集**只影响**跑哪些门禁**，**不影响装什么**：G21 在子集内、且其判定是「递归展开闭包 + 未安装 ⇒ 判失败」⇒ 非 Linux 作业不装 extras 即**必红**。
  > **⚠️ v1.0 的口径（2026-11-08 · 裁定 26 · 宪法 v1.7.0）**：v1.0 的**发行元数据零依赖包名**
  > ⇒ 7 个作业装的那 5 个包**不是 v1.0 的依赖**，而是「**v2.0 预验证依赖**」
  > （**不进发行包 · 不进 `Requires-Dist`**）⇒ 门禁 **G21 / G23** 对
  > **`contracts/extras-v2.toml`** 取证 ⇒ **v1.0 即完成预验证**。
- **arm64**：补 **Linux arm64 最低档**一个作业（裁定 15 · 兑现立项书 §3.5「x86_64 与 arm64」的支持承诺）；
  `macos-15` 的 runner **本身即 arm64** ⇒ **不另设作业**；**Windows arm64 v1 不纳入**。
- **runner 标签 MUST 钉死到具体镜像**（FR-015 ④③）⇒ MUST NOT 用 `ubuntu-latest` / `macos-latest` /
  `windows-latest` 这类**浮动标签**。

> **「全量」与「子集」的定义**（避免歧义）：
> - **全量** = 全量测试套件（`pytest tests/`）**+** 全部 **10 条**新门禁（G21–G30）**+**
>   全部既有门禁（G1–G20，经 pytest 承载）**+** 兼容矩阵 / API 快照的**接线**；
>   **且**该作业的环境**必须装齐四个 extras 的依赖**（见 §2 步骤 5.5）。
> - **子集** = 全量测试套件 **− 平台专属用例**（`@pytest.mark.linux_only` / `@pytest.mark.full_install`
>   —— 标记由**门禁用例自身**声明，pytest 步骤用 `-m` 过滤；**标记在 `pyproject.toml` 的
>   `[tool.pytest.ini_options] markers` 注册** · tasks T001）
>   **+** 全部既有门禁 **+** **平台无关**的新门禁
>   （**G21 · G23 · G24 · G25 · G26 · G29 · G30**）；
>   **不含**：**G22**（隔离 venv · 需联网安装 · 仅 Linux 跑以控制成本）·
>   **G27 的独立可执行入口**（socket 夹具 · 平台行为差异大 —— **其 pytest 夹具断言仍在全平台执行**）·
>   **G28**（断网 · Linux 专属 · 裁定 10）。
>   ⇒ **G23 在子集内**（**2026-11-08 分析轮订正 · H6**）：其判据是**纯元数据读取**（`importlib.metadata`
>   + SPDX 解析；**取证作用域 = 并集口径** · spec **裁定 25** ——（闭包包集）∪（`--root` 下扫到的 dist-info）），
>   **跨平台无差异**；原把它排除出子集的理由（「须完整安装环境才能取到许可证据」）
>   **已被自己撤回**——「『完整安装环境』一项已从该原则中移除」（2026-11-07 分析轮订正）且 extras **已 7/7 装齐**
>   ⇒ **理由失效 ⇒ 纳入子集**。
>   ⇒ **子集**的取舍原则：**凡需要「真实网络 / 隔离环境 / 平台特权」的判定，均只在 Linux 跑**；
>   **「完整安装环境」一项已从该原则中移除**（2026-11-07 分析轮订正）—— 四个 extras 的依赖**纯 Python 包**、
>   跨平台可得（`playwright` 只装 Python 包、不装浏览器二进制），且 **G21 的判定要求 extras 的传递依赖已安装**
>   才能完成取证（architecture-gates G21「未安装 ⇒ 判失败」）⇒ **全部 7 个作业 MUST 装齐四个 extras 的依赖**
>   （§2 步骤 5.5）—— 否则非 Linux 作业的 G21 **必然变红**（**实测**：仅装基础包时
>   `importlib.metadata.requires('pydantic')` 抛 `PackageNotFoundError`）。

---

## 2. 每个作业的步骤（统一顺序）

### 2.0 跨平台的解释器调用约定（**2026-11-08 分析轮订正 · C1 · 必读**）

> **问题**：本节原写的** POSIX 专属解释器路径**（`.venv/bin/` 形态）是 **Windows 上不存在**的路径 ——
> Windows 上 `uv venv` 生成的是 `.venv\Scripts\python.exe` ⇒ **`windows-2025` 的 2 个作业（7 个中的 2 个）每一条命令路径失效**
> ⇒ **CI 上线即红**（违反 PR-4「feature 必须能独立通过门禁」）⇒ 且与 spec Edge Case
> 「Windows 上的文件锁 / 路径分隔符」（门禁脚本 MUST 跨平台可运行）相悖。
>
> **口径（MUST NOT 再出现任何平台专属解释器路径）**：
>
> | 用途 | **跨平台写法**（三个平台逐字相同） | 说明 |
> |---|---|---|
> | **venv 目录** | `.venv` | **所有平台同路径** —— POSIX 下解释器落在 `.venv/bin/` 下，Windows 下落在 `.venv\Scripts/` 下；**命令串里只出现 `.venv`** |
> | **pip 安装** | `uv pip install --python .venv …` | **uv 接受 venv 目录路径**（**实测 uv 0.12.7**）⇒ 一个写法通吃三个平台，**不依赖隐式环境变量** |
> | **解释器调用** | `uv run --no-project --python .venv python …` | `--no-project` ⇒ uv **不解析项目、不同步环境** ⇒ **MUST NOT** 让它把已装的四个 extras 依赖卸掉（否则 G21 因「未安装 ⇒ 判失败」而必红） |
>
> ⇒ **`ci.yml` 的每一条命令 MUST 用上表的写法**；MUST NOT 出现 `.venv/bin/` 或 `.venv\Scripts/` 这类
> **平台专属解释器路径**（含在 `run:` 里按 `$PY` / `%PY%` 分平台拼装的写法 —— 那会把平台差异重新引回命令串）。

| 步 | 动作 | 说明 |
|---|---|---|
| 1 | `actions/checkout@v7`（**钉版本**） | 与既有 `publish.yml` 一致 |
| 2 | `actions/setup-python@v5` + `python-version: <矩阵档位>` | 版本**钉死** |
| 3 | `astral-sh/setup-uv@v10.3.3`（**钉版本**） | 与既有 `publish.yml` 一致 |
| 3.5 | **`uv venv --python <矩阵档位>`** | **建 venv**（**必做** —— `uv pip install` 在**无活动虚拟环境**时报 `error: No virtual environment found` 并以**退出码 2** 失败（**实测**）⇒ 无此步则**步骤 4 在 7/7 作业上直接失败**。`setup-python` 的产物与本 venv **不是同一个解释器**；真正的解释器由本步决定（用**矩阵档位**而非 `setup-python` 的解释器，以保证 Python 版本与矩阵一致） |
| 4 | `uv pip install --python .venv --group dev` | 装**开发期依赖组**（`pytest` + `packaging` · PEP 735）—— **不进发行包**、**不进 `Requires-Dist`** ⇒ 基础闭包仍为空集（G3 不受影响）。**显式 `--python .venv`**（**跨平台** · 不依赖隐式环境变量 ⇒ 后续 step 漏传 env 也不会跑偏） |
| 5 | `uv pip install --python .venv -e .` | 装**发行形态**（`src/` 布局 ⇒ 可编辑安装） |
| 5.5 | `uv pip install --python .venv "pydantic>=2.0" "ormsgpack>=1.0" "opentelemetry-api>=1.20" "opentelemetry-sdk>=1.20" "playwright>=1.40"` | **v2.0 extras 的「预验证」依赖**（**不是** v1.0 的依赖 · 裁定 26 · 宪法 v1.7.0）—— 只装 Python 包、不装浏览器二进制。**全部 7 个作业 MUST 执行** ⇒ G21 / G23 对 `contracts/extras-v2.toml` 的递归取证可完成（architecture-gates G21 / G23） |
| 6 | `uv run --no-project --python .venv python -m pytest tests/ -ra ${{ matrix.pytest_args }}`（环境变量 `FREEGRAPH_TEST_INSTALLED=1` **写在 job 的 `env:` 段**） | **全量测试套件**（平台专属用例按标记排除） |
| 7 | **逐条**调用门禁：`uv run --no-project --python .venv python harness/scripts/gates/gate_GNN_*.py`（**G21 / G23 追加 `--project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`** · 裁定 26 ⇒ 判据对象 = v2.0 清单） | FR-016 · 退出码即判定 · **本步 MUST NOT 含 G22 / G27 / G28**（它们在步骤 9；**2026-11-08 分析轮订正 · M4** —— 否则 Linux 作业上 G22 / G28 会被**跑两遍**） |
| 8 | 兼容矩阵 / 快照的**接线**（G8 · G16 · G19 已在第 6 步）+ 「`COMPAT.md` 未落地」的**非阻断**报告 | 裁定 13 · research D-14 |
| 9 | **Linux only**：G22（隔离 venv）· G28（断网）· **G27 的独立可执行入口** | 见 §3 · **MUST NOT** 与步骤 7 重复 |

> **⚠️ 步骤 6 / 7 的平台差异只有一处**：`-m "not linux_only and not full_install"`（**仅非 Linux 作业追加**）
> —— 其余部分（`uv venv` / `uv pip install --python .venv` / `uv run --no-project --python .venv python`）
> **三个平台逐字相同**（**2026-11-08 分析轮订正 · C1**）。
>
> **📌 步骤 6 的「按平台条件追加」的**实现配方**（2026-11-08 二轮复核补入 · MUST 照此写，否则 7 个作业会实现分叉）**：
> GitHub Actions 的 `run:` **无法**在命令行中间条件性追加参数 ⇒ **MUST** 用**矩阵变量**承载该参数：
>
> ```yaml
> strategy:
>   matrix:
>     include:
>       - { runner: ubuntu-24.04,  python: '3.11', os: Linux,   pytest_args: '' }
>       - { runner: ubuntu-24.04,  python: '3.14', os: Linux,   pytest_args: '' }
>       - { runner: macos-15,      python: '3.11', os: macOS,   pytest_args: '-m "not linux_only and not full_install"' }
>       - { runner: macos-15,      python: '3.14', os: macOS,   pytest_args: '-m "not linux_only and not full_install"' }
>       - { runner: windows-2025,  python: '3.11', os: Windows, pytest_args: '-m "not linux_only and not full_install"' }
>       - { runner: windows-2025,  python: '3.14', os: Windows, pytest_args: '-m "not linux_only and not full_install"' }
>       - { runner: ubuntu-24.04-arm, python: '3.11', os: Linux, pytest_args: '' }
> ```
>
> ⇒ **Linux 三档的 `pytest_args` 为空串**（**不过滤** ⇒ 跑全部用例，含 `linux_only`）；
> **非 Linux 四档**带 `-m "not linux_only and not full_install"`。
> ⇒ **MUST NOT** 用「同一 step + `if: runner.os != 'Linux'` 的第二份 run」写两遍 pytest 命令
> （那会让步骤 6 在 7 个作业上出现两份实现 ⇒ 漂移风险）；
> ⇒ **MUST NOT** 把过滤条件写进 `pyproject.toml` 的 `addopts`（那会让 **Linux 档也过滤**
> ⇒ `linux_only` 用例永不执行 ⇒ **G22 的 pytest 断言在 Linux 上也不跑** ⇒ 门禁静默失效）。
>
> **⚠️ `FREEGRAPH_TEST_INSTALLED=1` 的写法**：POSIX 下为 `VAR=1 cmd` 前缀式；
> Windows（pwsh）下 MUST 用 `$env:FREEGRAPH_TEST_INSTALLED="1"; cmd`（或 workflow 的 `env:` 段）——
> ⇒ **MUST 统一写在 job 的 `env:` 段**（三个平台通用），MUST NOT 把平台专属的变量前缀语法写进命令串
> （**步骤 6 的命令串里只出现跨平台写法**）。

> **⚠️ 为什么这 5 个包必须装（2026-11-08 · 裁定 26 修订 · **它们是「v2.0 预验证依赖」· 不是 v1.0 的依赖**）**：
> 门禁的判据是**依赖闭包**，而闭包靠**已安装包的元数据**递归展开 ⇒ 不装 extras 时：
> ① **G23** 取不到 `pydantic` / `ormsgpack` / `opentelemetry-*` / `playwright` 的许可证据
>    ⇒ 按 FR-006 ②「取不到证明 ⇒ 失败并指名」**必红**；
>    **若只判「`--root` 下能找到的包」⇒ G23 变成空门禁**（`--root` 默认 = 仓库根，其下无任何 `dist-info`）
>    ⇒ 违反**宪法原则 IX**「本原则三条 MUST NOT **MUST** 由 CI 断言自动校验」；
>    **若只判「已安装包」⇒ 反向用例空转**（注入的假元数据不在已安装集里 ⇒ 看不见）
>    ⇒ 违反 FR-014 ②「反向用例 MUST 可自动执行」与 data-model 不变量 9「闭包 == 完整闭包」；
>    ⇒ **两者皆不可接受 ⇒ MUST 取并集口径**（被检查集 =（闭包包集）∪（`--root` 下扫到的 dist-info）· spec **裁定 25** / architecture-gates G23 📌 块）；
> ② **G21** 的递归展开在第一层就终止 ⇒ spec Edge Case「递归展开 MUST 走到闭包末端」**不可判定**
>    （「某个允许的依赖间接拉进 `langsmith`」这类违规抓不到）；
> ③ **G3** 的 extras 闭包只剩 5 个**直接**依赖名 ⇒ 裁定 8 登记的 **12 名白名单永不触达**
>    ⇒ 「净效果 = 变严」在 CI 中**得不到兑现**。
> ⇒ **这 5 个包的安装是 G21 / G23（对 v2.0 清单）可判定的前置条件，不是可选项**。
> **⚠️ v1.0 的发行元数据仍是零依赖**（宪法 v1.7.0）—— 本步装的包**不进发行包、
> 不进 `Requires-Dist`**（实测：v1.0 的 `importlib.metadata.requires("freegraph")`
> == **`None`**）。
> **⚠️ 安装范围（2026-11-07 分析轮订正）**：四个 extras 的依赖 MUST 在**全部 7 个作业**上安装（§2 步骤 5.5），
> **不再仅限 Linux 全量作业** —— 理由：G21 的判定要求 extras 的**传递依赖已安装**才能完成递归取证
> （architecture-gates G21：「未安装 ⇒ 显式报『未安装 ⇒ 无法取证』并判失败」）⇒ 若非 Linux 作业不装 extras，
> G21 在那 4 个作业上**必然变红**（**实测**：仅装基础包时 `importlib.metadata.requires('pydantic')` 抛
> `PackageNotFoundError`）⇒ 四个 extras 的依赖是**纯 Python 包**、跨平台可得（`playwright` 只装 Python 包、
> 不装浏览器二进制）⇒ 安装成本可接受。
> **⚠️ G23 的子集归属（2026-11-08 分析轮订正 · H6）**：**G23 已纳入非 Linux 子集**（§1）⇒
> 上面的 ① 在 **7/7 作业**上都是**硬前置**（不再只是 Linux 作业的前置）。
> **实测基准（2026-11-07 · uv 0.12.7 解析四个 extras）**：完整闭包 **恰好 12 个包**
> —— `annotated-types` · `greenlet` · `opentelemetry-api` · `opentelemetry-sdk` ·
> `opentelemetry-semantic-conventions` · `ormsgpack` · `playwright` · `pydantic` ·
> `pydantic-core` · `pyee` · `typing-extensions` · `typing-inspection`
> ⇒ **与 T003 的 12 名白名单逐一命中**（该白名单本就是「extras 已安装」环境下的产物；
> **实测**：按 T003 ② 修正后的枚举语义，闭包**恰为**这 12 个包名）。
> **只装 Python 包、不装浏览器二进制**：`playwright install chromium` 由**用户**显式执行（research D-04）。
> **⚠️ `[png]` 的后端 = `playwright`**（**宪法 v1.5.0 已列明** —— 包层白名单条里的「mermaid 相关」这一**类别式**表述**已被宪法 v1.5.0 取代**为确切包名；三条硬约束 = (a) 默认关闭 / (b) 许可证白名单 / (c) 运行期零出站）⇒ CI **只装 Python 包**即满足 (a) 与 (b) 的取证前提，**(c) 由 G27 的零出站动态断言承担**。
> **G22 的隔离 venv 仍只装基础包**（它断言的正是「基础安装闭包 == 空集」）。
> **⚠️ 隔离副本的构建前置（2026-11-07 分析轮补入）**：任何要被 `uv pip install <目录>` 的**隔离副本**
> MUST 含 `README.md` 与 `LICENSE` —— `pyproject.toml` 的 `readme = "README.md"` 与
> `license-files = ["LICENSE"]` 是**硬引用**，缺一即构建失败（**实测**：`OSError: Readme file does not exist: README.md`）
> ⇒ `tasks.md` **T014** 的 `isolated_copy` fixture MUST 补齐这两个文件。

> **`FREEGRAPH_TEST_INSTALLED=1`**：仓库既有的 `tests/contracts/conftest.py` 与
> `tests/facade/conftest.py` **已为此预留开关**（其 docstring 明写「供 **B3F1** 的 CI
> 『先 `pip install .` 再跑 pytest』用」）⇒ **沿用，零改动**。

---

## 3. Linux 专属步骤

### 3.1 G22 · 隔离环境断言（隔离 venv）

```
uv venv <tmp>
uv pip install --python <tmp> <target-root>          # 默认 = 仓库根
uv run --no-project --python <tmp> python -c "<G22 的断言>"
```

> **⚠️ 解释器路径 MUST 跨平台（2026-11-08 分析轮订正 · C1）**：第三行**只出现 venv 目录 `<tmp>`**
> （**不出现**任何平台专属的解释器子路径 —— POSIX 的 `bin/` 目录或 Windows 的 `Scripts\` 目录）⇒
> `uv run --no-project --python <venv目录>` 在三个平台上**逐字相同**（**实测 uv 0.12.7** 接受 venv 目录路径）。
>
> **CLI 契约**：G22 MUST 支持 `--target-root`（被检源码根 · 默认仓库根）与 `--project`
> （默认 `<target-root>/pyproject.toml`）—— 见 `architecture-gates.md` §2.1「门禁的 CLI 契约」。
> **平台归属**：G22 的 pytest 用例 MUST 打 `@pytest.mark.linux_only`（需隔离 venv + 联网安装）
> ⇒ **非 Linux 作业 MUST 跳过**（§2 步骤 6 的 `-m` 过滤）。
> ⇒ 断言**基础安装的第三方依赖闭包 == 空集** + `import freegraph` 后 `sys.modules` 无
> `langsmith` / `langchain_core` / `langgraph`（SC-002 · FR-005 ②）。
> **⚠️ 被检源码根的构建前置（2026-11-07 分析轮补入）**：`<target-root>` MUST 是**可构建**的目录 ——
> 其内 MUST 含 `README.md` 与 `LICENSE`（`pyproject.toml` 的 `readme = "README.md"` /
> `license-files = ["LICENSE"]` 是硬引用）⇒ **仅含 `pyproject.toml` + `src/` 的副本会构建失败**
> （**实测**：`OSError: Readme file does not exist: README.md`）⇒ `tasks.md` **T014** 的 `isolated_copy`
> fixture MUST 补齐这两个文件（否则 G22 的反向用例 T042 会在**构建阶段**失败，而非在**断言阶段**失败）。

### 3.2 G28 · 断网等价性（网络命名空间）

**权威路径（MUST 照抄）** —— 由 **G28 门禁脚本**读**排除清单**并逐条施加：

```
unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py
```

**等价的手工展开形式**（G28 脚本内部做的事 = 把清单逐条转成 `--deselect`）：

```
unshare --net --map-root-user uv run --no-project --python .venv python -m pytest tests/ -ra \
  --deselect "tests/gates/test_gates.py::test_egress_attribution_records_user_egress" \
  --deselect "tests/gates/test_gates.py::test_g22_isolated_env_closure_is_empty" \
  --deselect "tests/gates/test_gates.py::test_g22_isolated_env_negative_case"
```

- `--net` ⇒ **新建网络命名空间** ⇒ **没有任何网络接口**（含回环）⇒ **全部网络接口不可用**（FR-010）；
- `--map-root-user` ⇒ **无特权**（免 `CAP_SYS_ADMIN`）⇒ 不引入特权依赖（裁定 10 · research D-08）；
- **⚠️ Ubuntu 24.04 的发行版级前置**（**CI 首跑实测 · 2026-11-08**）：该版本默认启用 AppArmor 的
  「**限制非特权用户命名空间**」策略（`kernel.apparmor_restrict_unprivileged_userns=1`）
  ⇒ `unshare --map-root-user`（需要**用户命名空间**）对普通用户直接 `Operation not permitted`
  ⇒ **该步骤必红**（首跑 3 个 ubuntu 作业全部止步于此）⇒ CI 步骤 MUST 先
  `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`（解除**发行版级策略**，
  命名空间仍以**非特权**方式创建 ⇒ **设计前提不变**）；
- **⚠️ Windows 的输出编码**（**CI 首跑实测 · 2026-11-08**）：控制台 / 管道默认编码是
  **cp1252 / cp936** ⇒ **打印中文**（门禁报告 · pytest 的 skip 理由 · `harness/demo/*.py`
  的验收输出）会 `UnicodeEncodeError`；**读取**中文输出也会 `UnicodeDecodeError`
  ⇒ CI 的 job `env:` MUST 设 **`PYTHONUTF8=1`**（UTF-8 模式）· 门禁与测试里的子进程
  MUST 显式 `encoding="utf-8", errors="replace"` 且给子进程设 `PYTHONIOENCODING=utf-8`；
- **排除清单 = `tests/gates/data/offline_exclusions.txt`**（**单文件** · **逐条带理由** · FR-010 ④⑤）——
  排除项**仅限两类**（FR-010 ③）：(a) **断网任务自身**（不可嵌套）；(b) **语义上必须能建立连接**的用例
  （含 (b1) 验证用户出站归因的用例 · (b2) 需联网安装 / 解析依赖的用例 —— 隔离 venv 一族）；
- **施加方式 = `--deselect` 逐条列出**（**2026-11-08 分析轮订正 · H7**）——
  清单的**唯一权威**是上面那个**单文件**、每行 `用例标识 :: 排除理由`；
  **G28 脚本 MUST 读它并逐条转成 `--deselect` 参数**（与 `tasks.md` **T006 / T039** 的清单格式**逐字一致**）；
- **⚠️ 排除清单 MUST 自校验（2026-11-08 分析轮订正 · 关闭 A5 失败模式）**：**实测 pytest 7.4.4 与 9.2.0
  对「指向**不存在** node id 的 `--deselect`」均**不报错**（静默忽略 · 退出码 0）⇒ 清单与用例名一旦漂移，
  排除**静默失效** ⇒ 被排除的用例在断网下**假红**（原因会被误判为「断网等价性失败」）。
  ⇒ **G28 MUST 逐条比对清单标识与实际收集到的 node ID 全集**：不存在 ⇒ **判失败并指名该条**；
  存在 ⇒ 确认它**确实被排除**（判据见 `architecture-gates.md` G28 §5）；
- **⚠️ MUST NOT 照抄「不带排除清单的裸 pytest 命令」**（原命令 `… -m pytest tests/ -ra`）⇒
  它会在**被排除的用例**上**假红**（断网下连接必然失败 —— 属**假红**，不是 freegraph 的缺陷）
  ⇒ **SC-004 必假红** ⇒ 排除清单必须**显式施加**，MUST NOT 依赖「门禁脚本内部已过滤」的隐式行为。

### 3.3 G27 · 零出站动态断言

在测试套件执行期间由 **pytest 夹具**监测（**只观测不阻断**）；
断言**「框架出站」条目数 == 0**（SC-006）。

> **⚠️ 平台归属的两层分工（2026-11-08 分析轮订正 · M5 · MUST 写死）**：
> - **G27 的独立可执行入口**（`gate_G27_zero_egress.py`）= **Linux only**（§2 步骤 9 · 非 Linux 作业 MUST NOT 含）；
> - **G27 的 pytest 夹具断言**（`tests/gates/test_gates.py` 的归因四形态 + 「框架出站 == 0」断言）=
>   **全平台**（它在**全量测试套件**里 ⇒ 7/7 作业都跑）—— **它 MUST NOT** 打 `@pytest.mark.linux_only`。
> ⇒ 二者**不是**同一条命令：§2 步骤 9 跑的是**独立入口**；§2 步骤 6 的 pytest 跑的是**夹具断言**。

> **两个入口 · 同一实现**（2026-11-07 分析轮补入）：G27 的**归因函数与 socket 包装 MUST 落在**
> `harness/scripts/gates/_gatekit.py`（纯函数 / 上下文管理器）⇒
> ① `gate_G27_zero_egress.py` 作为**独立可执行入口**调用它（满足 FR-016「退出码即判定」· CI 可逐条调用）；
> ② pytest 夹具调用**同一实现**（满足「一处判据一处实现」）。
> ⇒ **MUST NOT** 在脚本与夹具里各写一份归因逻辑。

---

## 4. 分支保护与 required check（FR-020 · 裁定 20）

> **执行方 = 发起者**（本环境**无 `gh` CLI、无 GitHub 令牌** —— 实测）⇒
> 本契约给出**设置项清单**，**可照抄的步骤**写入
> [`harness/verification/B3F1/manual-verification.md`](../../../../harness/verification/B3F1/manual-verification.md)。

### 4.1 必过检查（required checks）—— 建议勾选

| 检查名 | 出现在 | 必过？ |
|---|---|---|
| `gates (ubuntu-24.04, 3.11)` | 作业 1 | ✅ |
| `gates (ubuntu-24.04, 3.14)` | 作业 2 | ✅ |
| `gates (macos-15, 3.11)` | 作业 3 | ✅ |
| `gates (macos-15, 3.14)` | 作业 4 | ✅ |
| `gates (windows-2025, 3.11)` | 作业 5 | ✅ |
| `gates (windows-2025, 3.14)` | 作业 6 | ✅ |
| `gates (ubuntu-24.04-arm, 3.11)` | 作业 7 | ✅ |

> **7 个全勾** ⇒ 任一平台上任一版本的门禁变红 ⇒ **合不进去** ⇒
> 「CI 失败 ⇒ 无法合并」成立（FR-020 · SC-015）。
>
> **⚠️ job 名与「平台」的对应（2026-11-08 分析轮订正 · C1）**：上表的 job 名**只含 runner 标签与 Python 版本**，
> **不含**任何平台专属的解释器信息 ⇒ **三个平台的 job 名格式完全一致**（required check 的匹配与平台无关）；
> **各作业内部的命令串也完全一致**（§2.0 的跨平台写法）⇒ MUST NOT 因为「Windows 的路径不同」而改动 job 名
> （那会让 §4.1 与 `ci.yml` 两处漂移 ⇒ 分支保护静默失效）。
>
> **⚠️ job 名 MUST 逐字一致（2026-11-07 分析轮补入 · M5）**：GitHub 的 required check 按 **job 的
> `name:` 字符串精确匹配** ⇒ 上表的 7 个名字 MUST **逐字**出现在 `ci.yml` 各 job 的 `name:` 字段中
> （否则分支保护**静默失效** —— 设置项已勾选、但实际无同名检查在跑 ⇒ FR-020③ 的「已启用」名存实亡）。
> ⇒ `tasks.md` **T030** MUST 明确要求 job `name:` 等于本表；**T034**（可照抄的设置步骤）MUST **回指本表**、
> MUST NOT 另抄一份（两份一旦漂移，分支保护即失效）。
> **命名规则**：`gates (<runner 标签>, <Python 版本>)` —— **MUST NOT** 掺入矩阵表达式展开后的其他文本。

### 4.2 分支保护设置项

| 设置项 | 取值 |
|---|---|
| 保护的分支 | `main` |
| 「必须先通过检查才能合并」 | **启用** |
| 「要求分支保持最新」 | **启用**（保持线性历史） |
| 「管理员也必须遵守」 | 建议**启用**（否则红线可被管理员绕过） |

### 4.3 文档兜底（FR-020 ⑤）

仓库 MUST 在 README 或贡献指南中写明「**合入前 CI 必须全绿**」——
这是**分支保护未启用期间**的**人工**保障，MUST NOT 替代 §4.2 的设置步骤。

---

## 5. 触发条件

| 事件 | 是否触发 | 说明 |
|---|---|---|
| `push` 到 `main` | ✅ | |
| `pull_request`（目标 `main`） | ✅ | **PR 阶段就拦住**（「门禁立刻生效」的兑现 · spec P1） |
| `workflow_dispatch` | ✅ | 手动重跑 |

---

## 6. 兼容性：与既有 `publish.yml` 的关系

- `publish.yml`（`release: published` 触发）**本 feature 不接入**（spec §8 · B24F1）⇒ **零改动**。
- 本 feature 新增 `.github/workflows/ci.yml`；两个工作流**互不触发**（事件不重叠）⇒ 无相互影响。
- 发行产物纯度门禁（`harness/scripts/check_dist_purity.py`）**已**在 `publish.yml` 中接线 ⇒ 本 feature
  只在 CI 中提供**先行检查**（SC-005），MUST NOT 改动 `publish.yml`。
