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

#### clarify 的收窄纪律（**2026-11-12 宪法 v1.9.0 原则 XI** · MUST）
- **先自查**：每个要问的点 MUST 先查上游 ⇒ **上游有答案 ⇒ 照抄 ⇒ 不许问**。
- 只许问**「上游没答案」**的点（即落在**必须自研区**的 4 类里、或上游自身无定论之处）。
- **MUST NOT** 把「可以照抄但抄起来麻烦」的点拿来问 ⇒ 那不是决策点，是执行点。

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
我更新了 B12F1 的 spec、plan、tasks，请你阅读相关文档，检查三者内容是否有问题，是否对齐。如果遇到难以决策的地方可以question问我，提问时给出推荐选项，语言中文。分析之前，建议先阅读`harness/proposals/立项书.md`。

# analyse之后
好的，我看到你发现了一些问题。我授权你可以直接修改所有spec/中的文件，以修复以上问题。修复完成后我会新开会话再次执行/speckit.analyse检查。
如果宪法有问题，请直接修改宪法。
如果你认为这些问题太小，忽略不计，无需修复，也可以建议我直接执行/speckit.implement 。
我不会人工修改文档和代码，因为我担心我的失误导致项目走偏，并且人工修改成本过高，我没有这个时间。

# 直接修复（无critical问题可用）
本次analyse检查没有发现critical问题，所以都是小问题，我授权你可以修改本项目的任何文件，请你直接修改文件，修复上述问题，有难以决策的地方可以询问我。

# constitution问题
我看到了你的回答，明白现在需要更新宪法。请你给出宪法更新的提示词，我会新建另一个会话，开始执行/speckit.constitution +提示词 ，来修改宪法。

# /speckit.implement
根据 harness/docs/ 目录中的 LangChain、LangGraph 官方文档，harness/proposals/立项书.md，以及相关 spec，完成 B12F1（specs/b12f1-concurrency-errors）的 TDD 软件开发和测试。

# /sepckit.converge
我更新了 B<n>F<m> 的代码，请你根据代码改动，反向更新相关的 spec、plan、tasks。


# 收尾
人工验收通过，请你做收尾工作，该勾选的文件就勾掉，该签的就签。
收尾完成后，看看是否需要更新harness/features/后续feature的提示词。
以上两个工作完成后，请你提交和push代码。
