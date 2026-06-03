# AI Agent RAG System 文档索引

这个目录现在分成四类文档：项目纲领、专项设计、学习路线、学习记录。

## 当前主线

优先阅读顺序：

1. `development_plan.md`
2. `rag_design.md`
3. `frontend_design.md`
4. `superpowers/plans/2026-06-01-agent-rag-learning-roadmap.md`
5. `learning_record.md`

## 文档职责

### `development_plan.md`

项目纲领文档。

用途：

- 说明项目定位、业务场景、技术栈和总体架构。
- 记录全局工程原则，例如生产方案先行、分层边界、默认教学不代写。
- 适合在开始新阶段前快速回顾“这个项目为什么这么做”。

不适合：

- 记录每天学习流水账。
- 写每个功能的具体实现步骤。

### `rag_design.md`

RAG 专项设计文档。

用途：

- 记录文档解析、普通 chunk、父子 chunk、图片资产召回、context assembly、token budget 等设计。
- 作为实现 RAG 相关模块时的技术依据。
- 讨论生产级 RAG 边界：loader、splitter、indexing service、retrieval service、context assembly 各自负责什么。

不适合：

- 记录 Agent 工作流细节。
- 记录前端交互细节。

### `frontend_design.md`

前端专项设计文档。

用途：

- 记录 Vue 工作台页面结构、组件拆分、状态管理、流式输出、停止生成、引用和图片展示。
- 作为后续实现前端 Agent Workbench 的参考。

不适合：

- 记录后端 RAG 实现细节。
- 记录数据库表设计细节。

### `superpowers/plans/2026-06-01-agent-rag-learning-roadmap.md`

当前学习路线和实施规划。

用途：

- 作为后续学习和实现的主路线。
- 按阶段推进：Retrieval API、pgvector、hybrid retrieval、asset resolution、chat streaming、LangGraph、durable execution、evaluation、safety、frontend workbench。
- 每一阶段都应该能落到测试、接口、数据模型或可运行功能。

不适合：

- 放具体学习心得流水账。
- 替代 `rag_design.md` 或 `frontend_design.md` 的专项设计。

### `learning_record.md`

学习日志。

用途：

- 记录每天学了什么、写了哪些代码、遇到什么问题、如何解决、下次继续什么。
- 适合复盘学习过程。

不适合：

- 作为当前路线图。
- 作为架构设计权威来源。

### `notes/`

阶段性复习笔记。

当前文件：

- `notes/01-fastapi-knowledge-base.md`
- `notes/02-document-ingestion-assets.md`
- `notes/03-retrieval-api-embedding-pgvector.md`

用途：

- 保存阶段性复习材料。
- 面试前或间隔较久后用于快速回顾。

不适合：

- 作为最新实现计划。
- 放全局架构决策。

## 已清理文档

`teaching_plan.md` 已删除。

原因：

- 它的内容和新的 `superpowers/plans/2026-06-01-agent-rag-learning-roadmap.md` 大量重叠。
- 它停留在早期教学阶段，不能准确反映当前已经完成 Retrieval API、Embedding Provider、pgvector 字段等进度。
- 后续教学和实现以 roadmap 为准。

## 维护规则

- 新的长期架构决策写入 `development_plan.md`。
- RAG 模块设计变化写入 `rag_design.md`。
- 前端产品和组件变化写入 `frontend_design.md`。
- 后续阶段计划写入 `docs/superpowers/plans/`。
- 每次学习复盘追加到 `learning_record.md`。
- 大段复习材料放入 `docs/notes/`。
