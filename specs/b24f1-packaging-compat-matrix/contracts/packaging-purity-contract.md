# Contract: 打包产物与发行纯度门禁

**Feature**: B24F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

---

## 1. 发行元数据（`pyproject.toml`）

| 项 | 规则 |
|---|---|
| `requires-python` | `>=3.11`，**不设上限** |
| `dependencies` | `[]`（零第三方运行时依赖） |
| `[project.optional-dependencies]` | **有且仅有 `otlp`** 一个键；`pydantic` / `checkpoint` / `otel` / `png` MUST NOT 出现 |
| `[otlp]` 内容 | `opentelemetry-api` · `opentelemetry-sdk` · `opentelemetry-exporter-otlp-proto-grpc` |
| `[otlp]` 禁止（**精确包名**） | `opentelemetry-exporter-otlp` 元包 · `opentelemetry-exporter-otlp-proto-http` · `requests` · `certifi`；MUST NOT 用子串匹配（允许 `opentelemetry-exporter-otlp-proto-grpc`） |
| 构建后端 | `hatchling`（既有） |
| wheel | `packages = ["src/freegraph"]` |
| sdist | `only-include = ["src/freegraph", "README.md", "LICENSE"]`；`exclude` 含 `harness` / `.specify` / `.opencode` / `.github` / `specs` / `dist` / `tests` / `.gitignore` / `COMPAT.md` / `THIRD_PARTY_NOTICES` / `**/node_modules` / `**/__pycache__`（即使 `only-include` 已排除，仍显式兜底） |
| 仓库文档 | `COMPAT.md` / `THIRD_PARTY_NOTICES` / `.gitignore` MUST NOT 进入 wheel / sdist |
| `py.typed` | 存在于 `src/freegraph/py.typed` |
| 许可证 | MIT（**D3 已决 2026-11-05：保持 MIT**）；`[otlp]` 闭包 ∈ {MIT, Apache-2.0, BSD-2/3, PSF}；`protobuf` 具名归一 |

> 本 feature **不改变**依赖面；只做验证与可选显式 `exclude` 兜底（意图可见）。
>
> **`.gitignore` 的两处含义 MUST 区分**：`exclude` 里的 `.gitignore` 指 **sdist 根级** `.gitignore`；
> `uv build` 在输出目录生成的 `dist/.gitignore` 是**构建目录标记**，**不在此排除范围**（见 §4.2 豁免）。
> **hatchling 的 sdist builder 会强制把根 `.gitignore` 加入 sdist**（VCS 忽略文件，`exclude` 无法拦截）
> ⇒ 允许使用 **sdist-only** 构建钩子（`harness/build_hooks/sdist_prune.py`）在 `finalize` 阶段移除；
> 钩子文件位于 `harness/`，MUST NOT 进入 sdist。

---

## 2. wheel 允许 / 禁止

### 2.1 允许

```text
freegraph/**                       # 包代码（含 py.typed）
freegraph-*.dist-info/**           # 构建元数据
```

### 2.2 必需

| 路径 | 原因 |
|---|---|
| `freegraph/__init__.py` | 包可导入 |
| `freegraph/py.typed` | PEP 561 |

### 2.3 禁止（任一命中 ⇒ 失败）

```text
harness/  .specify/  .opencode/  .github/  specs/  tests/  test/
dist/  .venv/  node_modules/  __pycache__/
COMPAT.md  THIRD_PARTY_NOTICES  .gitignore
```

---

## 3. sdist 允许 / 禁止

### 3.1 允许

```text
src/freegraph/**
README.md
LICENSE
pyproject.toml
PKG-INFO
```

### 3.2 必需

`src/freegraph/__init__.py` · `README.md` · `LICENSE` · `pyproject.toml` · `PKG-INFO`。

### 3.3 禁止

同 §2.3（另含 `COMPAT.md` / `THIRD_PARTY_NOTICES` / `.gitignore`）。

---

## 4. 纯度门禁（`harness/scripts/check_dist_purity.py`）

### 4.1 独立性

- MUST NOT 读取 `pyproject.toml` 的 `only-include` / `exclude` 作为判据；
- 判据全部写死在脚本内（允许列表 + 禁止目录 + 必需文件）；
- **发行元数据（wheel `freegraph-*.dist-info/METADATA`）MUST 一并检查**：
  `Provides-Extra` ⊆ `{"otlp"}`；无 `extra` marker 的 `Requires-Dist` 归为基础依赖且 MUST 为空；
  marker 含 `extra == "otlp"` 的项才归入 `[otlp]` 闭包；`[otlp]` 的 `Requires-Dist` MUST NOT 含
  **精确包名** `certifi` / `requests` / `opentelemetry-exporter-otlp` 元包 /
  `opentelemetry-exporter-otlp-proto-http`。
- 包名比较 MUST 先做 **PEP 503 规范化**（小写，`-` / `_` / `.` 统一为 `-`）后精确相等；
  **MUST NOT** 用子串（`opentelemetry-exporter-otlp-proto-grpc` 是允许项）。
- 本脚本 MUST **只使用标准库**解析 METADATA（如 `email.parser.Parser`）；
  **MUST NOT** `import packaging`（发布流水线用系统 `python3` 直接执行，见 `publish.yml`
  的「脚本只用标准库，无版本要求」约束）。

### 4.2 退出码

| 情况 | 退出码 |
|---|---|
| 全部产物干净 | `0` |
| 任一产物违规（含 `dist/` 内**归档类**非 `.whl` / `.tar.gz` 文件；`dist/.gitignore` 豁免） | `1` |
| `dist/` 不存在 / 无 `.whl` 与 `.tar.gz` | `2` |

### 4.3 输出

- 每个产物一行：`✅ <name>（wheel/sdist）——仅含包代码与必要元数据`；
- 违规：`❌ <name>` + 逐条问题 + 「**拒绝发布**」；
- MUST 指名具体违规路径（不只报总数）。

---

## 5. 发布流水线（`.github/workflows/publish.yml`）

步骤顺序 MUST 为：

```text
1. actions/checkout
2. setup-uv
3. uv build
4. Verify artifact purity   ← 调用 harness/scripts/check_dist_purity.py dist/
5. uv publish --trusted-publishing always
```

- purity 步骤失败 ⇒ job 失败 ⇒ publish **不执行**。
- 解释器三级回退（`python3` → `python` → `uv run --offline --no-project python`）保留。
- 不引入 API token / 密码；使用 Trusted Publishing（OIDC）。

---

## 6. 负向验证（自动化）

在 `tmp_path` 合成产物，**不触碰真实 `dist/`**：

| 用例 | 构造 | 期望 |
|---|---|---|
| 正向 wheel | 只含 `freegraph/__init__.py` + `py.typed` + dist-info | 退出码 0 |
| 正向 sdist | 只含允许文件 | 退出码 0 |
| 负向 wheel | 注入 `harness/report.md` | 退出码 1 · 指出路径 |
| 负向 sdist | 注入 `specs/x/spec.md` | 退出码 1 · 指出路径 |
| 空目录 | `tmp_path/empty` | 退出码 2 |
| 缺 py.typed | wheel 去掉 `py.typed` | 退出码 1 |
| sdist 缺 pyproject | sdist 去掉 `pyproject.toml` | 退出码 1 |
| sdist 含 `.gitignore` | sdist 根级含 `.gitignore` | 退出码 1（非必要元数据） |
| 额外归档产物 | `dist/` 混入 `evil.zip` | 退出码 1（不得静默忽略） |
| 构建目录标记 | `dist/` 含合法产物 + `dist/.gitignore` | 退出码 **0**（`uv build` 生成的目录标记豁免） |
| 非法 wheel 根文件 | wheel 根级混入 `freegraph-evil.txt` | 退出码 1（只允许 `freegraph/` + `freegraph-*.dist-info/`） |
| 非法 extra | wheel `METADATA` 写 `Provides-Extra: png` | 退出码 1 |
| `[otlp]` 被污染 | wheel `METADATA` 写 `Requires-Dist: requests; extra == "otlp"` | 退出码 1 |
| 工作流顺序 | 解析 `publish.yml` | `Verify artifact purity` 在 `Publish to PyPI` 之前 |

---

## 7. 与既有门禁的关系

| 门禁 | 关系 |
|---|---|
| G21 / G23 | 依赖 / 许可证判据不变；`[otlp]` 不被误判为「v1.0 不允许的 extra」 |
| G22 | 隔离环境安装 + 零 langchain 家族；本 feature 复用 |
| G26 / G27 | 网络静态 / 零出站；本 feature 不新增网络代码 |
| G30 | 署名头 / 品牌资产；新增 `.py` MUST 带署名头 |
| 发布门禁 | 本契约即其细化；**不新增门禁编号** |

---

## 8. 不变量

- 基础安装依赖闭包 **== 空集**。
- `[otlp]` 唯一 extra；默认关闭。
- `COMPAT.md` / `THIRD_PARTY_NOTICES` 不随包分发。
- `src/freegraph/` 零改动。
