# 开发指南
## 项目背景
本项目freegraph是我的个人项目，我启动这个项目的原因，以及我的一些想法都写到了 `harness/prompts/why_this_project.md` 。

## 可参考文档
1. LangChain、LangGraph、DeepAgents、MDA官方文档我放到了 `harness/docs` 中，可以通过 `harness/docs/MANIFEST.json`进行快速导航。
2. 关于why_this_project.md中Q1-Q8的问题调研报告，我写到了 `harness/reports` 文件名以Q开头。为了节约上下文，你可以只看报告开头的摘要部分。

## 你的任务
我现在不知道如何跨出第一步，你帮我写一个开发指南，帮我确定这几件事：
1. 是否要设计架构？如果需要，初步的架构是怎样的？如果不需要，为什么？
2. 是否要将项目拆解成多个模块？如果需要，如何将整个项目拆解成多个Feature模块？模块之间交互采取的数据格式和协议是怎样的？如果不需要，为什么？
3. 由于本项目采用speckit进行开发，受限于大模型的上下文长度目前最高1M，一次specify-plan-tasks-implement闭环只能实现不超过5000行代码，否则代码质量会严重降低。
需要判断每个模块体量是否超过5000行，如果超过，需要继续将这个Feature拆解成多个Phase开发阶段。如果项目不需要拆解成Feature，也需要拆分成多个Phase。总之Phase与speckit闭环一一对应。

请你进行充分的调研，解答我的这三个问题，将调研结果写入 `harness/prompts/guide.md` 中。


# 立项书
## 项目背景
本项目freegraph是我的个人项目，我启动这个项目的原因，以及我的一些想法都写到了 `harness/prompts/why_this_project.md` 。

## 可参考文档
1. LangChain、LangGraph、DeepAgents、MDA官方文档我放到了 `harness/docs` 中，可以通过 `harness/docs/MANIFEST.json`进行快速导航。
2. 关于why_this_project.md中Q1-Q8的问题调研报告，我写到了 `harness/reports` 文件名以Q开头。为了节约上下文，你可以只看报告开头的摘要部分。
3. 关于项目架构、排期的讨论，我写到了 `harness/prompts/guide.md` 。

现在请你理解项目目标，阅读相关参考文档，为本项目撰写“立项书”，内容写入 `harness/proposals/立项书.md` 。
你需要了解立项书的大纲，有哪些标题，再填写具体内容。


# 立项书评审
## 项目背景
本项目freegraph是我的个人项目，我启动这个项目的原因，以及我的一些想法都写到了 `harness/prompts/why_this_project.md` 。

## 可参考文档
1. LangChain、LangGraph、DeepAgents、MDA官方文档我放到了 `harness/docs` 中，可以通过 `harness/docs/MANIFEST.json`进行快速导航。
2. 关于why_this_project.md中Q1-Q8的问题调研报告，我写到了 `harness/reports` 文件名以Q开头。为了节约上下文，你可以只看报告开头的摘要部分。
3. 关于项目架构、排期的讨论，我写到了 `harness/prompts/guide.md` 。

我已经完成立项书的撰写，内容写入 `harness/proposals/立项书.md` 。
请你对立项书进行评审，找出问题，给出意见和推荐处理办法，然后将“意见+处理”逐个写入 `harness/proposals/立项书-评审1.md` 。
> **注（2026-11-04）**：该轮评审的 38 条意见（C1–C5 / H1–H10 / M1–M16 / L1–L7）**已全部落地**到 `harness/proposals/立项书.md`，
> 评审文件 `harness/proposals/立项书-评审1.md` 已随之删除；各条变更的落点与评审编号（如「评审 1 的 C5 / H8」）
> 保留在立项书的「决策变更记录」与 §12 待决事项中，可据此回溯。
注意：立项书由人工撰写底稿，最终读者也是人类，所以不允许你直接修改 立项书.md。我会根据你的评审意见，人工修改 立项书.md。你可以仿照speckit的分析法`.opencode/commands/speckit.analyze.md` ，对问题严重程度进行评级。