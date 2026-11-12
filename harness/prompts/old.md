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
注意：立项书由人工撰写底稿，最终读者也是人类，所以不允许你直接修改 立项书.md。我会根据你的评审意见，人工修改 立项书.md。你可以仿照speckit的分析法`.opencode/commands/speckit.analyze.md` ，对问题严重程度进行评级。


# Phase初稿提示词生成
## 项目背景
本项目freegraph是我的个人项目，我启动这个项目的原因，以及我的一些想法都写到了 `harness/prompts/why_this_project.md` 。

## 可参考文档
1. LangChain、LangGraph、DeepAgents、MDA官方文档我放到了 `harness/docs` 中，可以通过 `harness/docs/MANIFEST.json`进行快速导航。
2. 关于why_this_project.md中Q1-Q8的问题调研报告，我写到了 `harness/reports` 文件名以Q开头。为了节约上下文，你可以只看报告开头的摘要部分。
3. 关于项目架构、排期的讨论，我写到了 `harness/prompts/guide.md` 。
4. 立项书（必读）。`harness/proposals/立项书.md` 。
5. 人工验收脚本，harness/demo/*.py


现在，请你阅读参考文档，根据立项书中的layer-功能块-feature设计，为每一个phase编写一个提示词初稿，放到 `harness/features`目录中。每个提示词初稿将作为 /speckit.specify 子命令的提示词。
初稿文件名以 Phase编号_Phase小目标.md 的格式来命名。并且需要一个导航文件 `harness/features/README.md` ，这是给人看的导航文件，内容是对Phase进行排序，作为开发顺序，第一步开发哪个Phase、第二步开发哪个Phase......


# 力挽狂澜
我觉得本项目再这么推进下去可能会僵死。
本来项目的目标是无账号无主动出网无依赖。就是一个上游langgraph的免费版本。
或者说难听一点，就是langgraph的“破解版”。
从设计到代码实现，可以照抄langgraph都没问题，只要能做到“无账号无主动出网无依赖”的项目目标即可。有吃不准的设计，你直接读langgraph源码就行。
并且破解版能够基本兼容下游langchain。
但是本项目自从采用speckit后，智能体+大模型开始自由发挥，导致feature之间越来越“无法对齐”，开发难度陡增。
本来就是一个照抄的工作，被你搞的越来越繁琐，偏离主路线越来越远，需要我人工决策的地方越来越多，我疲于奔命，狂做选择题。
你是否能够力挽狂澜，将本项目向上游靠拢？从最初的立项书（harness/proposals/立项书.md）到feature提示词（harness/features）再到speckit相关的spec（specs/）再到源码和测试，都尽量贴合上游，降低人工决策，降低项目风险。
如果没有langgraph，本项目重头开发一个“图框架”的成功率极低，正是langgraph的出现给了我灵感，也给了我freegraph能够成功的底气，而目前的成果越来越让我心慌，矛盾点越来越多了。