# /speckit.constitution
<宪法模板>

# /speckit.specify
<feature提示词>

# 是否进行clarify
我已经更新了spec，本来应该执行/speckit.clarify，针对spec中模棱两可的地方，向我提问，我可以帮你做决策，或者给出我的想法。
但是clarify可能会引入不必要的新问题，导致我无休止的修改spec，所以能不做clarify就尽量不做。
如果你发现spec已完善无需clarify，我就继续plan。

# /speckit.clarify
请针对spec中模棱两可的地方，向我提问，我可以帮你做决策，或者给出我的想法。
注意，向我提问时，问题和选项都必须是中文，因为我读英文比较吃力。

#### 是否进行第二次clarify
是否还存在模棱两可的地方？是否需要我再执行一轮 /speckit.clarify ？

#### 第二轮clarify
我觉得spec还是有很多不确定的地方，需要再执行一轮clarify，请向我提问。

#### 注意事项
- 第一次生成spec后，至少人工回答10个选择题，clarify一轮5道题，至少两轮。
- analyse后如果发现spec问题，再次执行/speckit.specify后谨慎使用clarify，能不用就不用，否则clarify会引入新的spec问题再次被analyse检查出来，你永远死循环无法走到implement。
- 每个feature的clarify总轮数不得超过6轮，不超过30个选择题。否则重新设计spec。

# /speckit.plan
我已经更新了spec，请你接着更新plan

# /speckit.checklist
我已经更新了spec和plan，请你更新checklist

# /speckit.tasks
我已经更新了spec和plan，请你更新tasks

# /speckit.analyse 
我更新了 B1F1 的 spec、plan、tasks，请你阅读相关文档，检查三者内容是否有问题，是否对齐。如果遇到难以决策的地方可以question问我，提问时给出推荐选项，语言中文。

# analyse之后
好的，我看到你发现了一些问题。
我想知道这些问题中，是否存在某些问题由于spec设计缺陷而导致的？
如果有，需要先修复spec缺陷。请你帮我设计一段提示词。我可以用你给的提示词，新开一个会话执行 /speckit.clarify 来修复spec缺陷。
由于新开会话导致上下文丢失，需要你在提示词中把问题和处理办法描述清楚。如果在设计提示词的过程中有难以决策的地方，可以向我提问。
如果spec没有问题，说明以上问题都只是plan和tasks的问题。
如果是plan问题，给出plan提示词，我会去执行/speckit.plan命令。
如果是tasks问题，给出tasks提示词，我会去执行/speckit.tasks命令。
如果宪法有问题，请直接修改宪法。
如果你认为这些问题太小，忽略不计，无需修复，也可以建议我直接执行/speckit.implement 。
我不会人工修改文档和代码，因为我担心我的失误导致项目走偏，并且人工修改成本过高，我没有这个时间。

# 直接修复（无critical问题可用）
本次analyse检查没有发现critical问题，所以都是小问题，我授权你可以修改本项目的任何文件，请你直接修改文件，修复上述问题，有难以决策的地方可以询问我。

# constitution问题
我看到了你的回答，明白现在需要更新宪法。请你给出宪法更新的提示词，我会新建另一个会话，开始执行/speckit.constitution +提示词 ，来修改宪法。

# /speckit.implement
根据 harness/ 目录中的 LangChain、LangGraph 官方文档，harness/proposals/立项书.md，以及相关 spec，完成 B1F1（specs/b1f1-contracts-core/）的 TDD 软件开发和测试。

# /sepckit.converge
我更新了 B<n>F<m> 的代码，请你根据代码改动，反向更新相关的 spec、plan、tasks。

---

## 本仓库的 speckit 约定（2026-11-05 统一）

| 项 | 约定 |
|---|---|
| **feature ID** | `B<n>F<m>` —— 立项书的规划 ID（**唯一权威**） |
| **feature 目录** | `specs/b<n>f<m>-<slug>/` —— **直接用 feature ID**，不带 speckit 的三位序号 |
| **short-name 建议** | `b<n>f<m>-<slug>`（与目录名一致） |
| **提示词初稿** | `harness/features/B<n>F<m>_<小目标>.md` |
| **人工验证记录** | `harness/verification/B<n>F<m>/manual-verification.md` |

> **⚠️ 为什么目录名不带 `001-` 这类三位序号**：
> speckit 的 `create-new-feature.sh` 用 `printf "%03d"` 生成**创建序号**前缀，
> 而它的自动编号器（`get_highest_from_specs()`）只认 `^[0-9]{3,}-` 的目录。
> 但那个序号表达的是「第几个被创建的」，**与立项书的规划 ID 是两个不同的轴**——
> 一旦创建顺序 ≠ 规划顺序，它就会指错 feature。
> 目录名应当**只表达唯一权威的规划 ID**，故不带序号。
>
> **连带影响（须知）**：speckit 的自动编号器因此**看不见**本仓库的 feature 目录，
> 故**每个 feature 的目录由本仓库自行创建**（`mkdir specs/b<n>f<m>-<slug>` + 写 spec.md），
> 并在 `.specify/feature.json` 登记 `feature_directory` —— 工具链的路径解析只认这个文件，
> 因此读写完全正常（`check-prerequisites.sh` 已实测通过）。
>
> **⚠️ 新克隆需手动指定 feature 目录**：`.specify/feature.json` 被 speckit
> **故意 gitignore**（`.specify/.gitignore`：*"Machine-local Spec Kit state —
> not meant to be shared"*）—— 它是**每检出一份**的本地指针，不随仓库分发。
> 故在新克隆（或不在 feature 分支上）时，须显式指定：
>
> ```bash
> export SPECIFY_FEATURE_DIRECTORY=specs/b<n>f<m>-<slug>
> ```
>
> 否则 `check-prerequisites.sh` 会报
> *"Feature directory not found. Set SPECIFY_FEATURE_DIRECTORY or run the
> specify command to create .specify/feature.json."*
> 在 **feature 分支**上则无需此变量 —— speckit 会从分支名推导目录名。

