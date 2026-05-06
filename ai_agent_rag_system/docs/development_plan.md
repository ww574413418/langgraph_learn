# AI Agent RAG 系统开发文档

## 1. 项目定位

本项目不是一个只演示 API 调用的最小 demo，而是一个具备工程落地结构的 AI Agent 后端系统。项目会串联 FastAPI、PostgreSQL、Redis、LangChain、LangGraph、Multi-Agent、RAG、异步任务、权限、日志、测试和部署。

项目名称暂定为：`AI Agent Knowledge Workspace`

核心目标：

- 支持用户上传和管理知识库文档。
- 对文档进行解析、切分、向量化、索引和检索。
- 提供基于 RAG 的问答能力，并返回引用来源。
- 使用 LangGraph 构建 Multi-Agent 工作流。
- 使用 PostgreSQL 存储业务数据、会话、任务、知识库元数据。
- 使用 Redis 承担缓存、会话状态、任务状态和限流。
- 通过 FastAPI 暴露稳定、可测试、可扩展的后端接口。
- 使用 Vue 实现类主流大模型产品的聊天前端，支持历史会话、编辑会话、流式输出和停止生成。
- 形成一套可以写进简历、可以面试讲清楚、可以继续扩展的项目。

## 2. 协作与学习原则

本项目的主要目标是学习和掌握系统实现过程，而不是让 AI 直接代写完整代码。

默认协作方式：

- 如果没有明确要求“帮我写代码”“帮我实现”“直接修改文件”，AI 不自动替学习者完成代码。
- AI 应优先解释实现思路、模块边界、关键概念、数据流和编码步骤。
- AI 可以给出必要的示例代码片段，但示例应服务于理解，不默认写入项目文件。
- 每个阶段先讲清楚为什么这么设计，再说明如何实现，最后由学习者动手推进。
- 当学习者要求检查、排错、评审或解释代码时，AI 可以阅读和分析代码，但不擅自重写。
- 当学习者明确授权实现某个模块时，AI 才进入代码修改模式，并说明将修改哪些文件。

这个原则优先于开发速度。系统可以慢一点完成，但每一步都要让学习者理解为什么这样做。

## 3. 推荐业务场景

项目场景选择：企业知识库 + 岗位/简历分析 Multi-Agent 系统。

这个场景适合学习和求职展示，因为它同时覆盖：

- 文档上传与知识库问答。
- RAG 检索增强生成。
- Multi-Agent 分工协作。
- 工作流编排。
- 后端工程设计。
- 数据库建模。
- 用户会话和任务管理。

典型使用流程：

1. 用户创建知识库。
2. 用户上传岗位 JD、公司文档、技术文档、简历等文件。
3. 系统解析文档并建立向量索引。
4. 用户发起问题，例如：
   - “这份 JD 需要哪些能力？”
   - “我的简历和这个岗位匹配度是多少？”
   - “请根据知识库内容生成一份面试准备计划。”
5. Multi-Agent 工作流开始执行：
   - Query Router 判断任务类型。
   - Retriever Agent 检索相关材料。
   - Analyzer Agent 分析岗位或简历。
   - Planner Agent 生成学习计划或行动方案。
   - Reviewer Agent 检查输出是否有依据、是否偏离问题。
6. 系统返回答案、引用来源、任务轨迹和可追踪日志。

## 4. 技术栈

后端：

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- Redis

前端：

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Element Plus 或 Naive UI，第一版建议 Element Plus
- Markdown 渲染：`markdown-it`
- 代码高亮：`shiki` 或 `highlight.js`
- 流式响应：Server-Sent Events 或 Fetch Stream

部署形态：

- 第一阶段不做前后端分离部署。
- Vue 前端源码放在同一个项目仓库。
- 开发环境中 Vite 负责前端热更新，FastAPI 负责 API。
- 生产或演示环境中，Vue 构建成静态文件，由 FastAPI 挂载并返回。
- API 路径统一使用 `/api/*`，页面路由由 Vue Router 管理。

AI 应用层：

- LangChain：模型封装、Prompt、Tool、Retriever 组件。
- LangGraph：Agent 状态机、Multi-Agent 工作流、条件分支、循环控制。
- Embedding 模型：优先支持可配置 provider。
- 向量存储：第一阶段建议使用 PostgreSQL + pgvector，后续可扩展 Qdrant/Milvus。

工程化：

- Docker / Docker Compose
- pytest
- ruff
- mypy 可后置
- structured logging
- `.env` 配置

## 5. 系统架构

```text
Vue Web UI
  |
  v
FastAPI App
  |
  +-- Static Vue Assets / SPA fallback
  +-- API Layer
  |
  +-- Auth / User / Knowledge Base APIs
  +-- Document Upload APIs
  +-- Chat / Streaming / Agent Task APIs
  |
  v
Service Layer
  |
  +-- KnowledgeBaseService
  +-- DocumentIngestionService
  +-- ChatService
  +-- AgentWorkflowService
  +-- RetrievalService
  |
  v
Domain / Infrastructure
  |
  +-- PostgreSQL: users, documents, chunks, assets, conversations, messages, tasks
  +-- pgvector: document chunk embeddings
  +-- Redis: cache, task status, rate limit, graph checkpoint
  +-- LangChain: model, embeddings, retriever, tools
  +-- LangGraph: multi-agent workflow
```

前端不作为独立系统单独部署，但源码独立放在 `frontend/` 目录。这样能兼顾当前学习阶段的简单性和后续工程扩展性。

## 6. 目录规划

当前项目根目录：`ai_agent_rag_system`

建议结构：

```text
ai_agent_rag_system/
  app/
    main.py
    static/
    web/
      spa.py
    api/
      routes/
        health.py
        auth.py
        knowledge_bases.py
        documents.py
        chat.py
        conversations.py
        agent_tasks.py
        stream.py
      deps.py
    core/
      config.py
      logging.py
      security.py
      errors.py
    db/
      session.py
      base.py
      migrations/
    models/
      user.py
      knowledge_base.py
      document.py
      chunk.py
      document_asset.py
      conversation.py
      message.py
      agent_task.py
    schemas/
      auth.py
      knowledge_base.py
      document.py
      chat.py
      agent_task.py
    services/
      knowledge_base_service.py
      document_service.py
      ingestion_service.py
      chat_service.py
      agent_task_service.py
    rag/
      loaders.py
      asset_extractors.py
      splitters.py
      embeddings.py
      vector_store.py
      retriever.py
      parent_child_retriever.py
      image_retriever.py
      reranker.py
      prompts.py
    agents/
      state.py
      workflow.py
      tools.py
      nodes/
        router.py
        retriever.py
        analyzer.py
        planner.py
        reviewer.py
  tests/
  frontend/
    index.html
    package.json
    vite.config.ts
    src/
      main.ts
      App.vue
      router/
      stores/
        conversation.ts
        chat.ts
        knowledge_base.ts
      api/
        client.ts
        chat.ts
        conversations.ts
        documents.ts
      views/
        ChatWorkspace.vue
        KnowledgeBase.vue
        Settings.vue
      components/
        chat/
          ConversationSidebar.vue
          MessageList.vue
          MessageItem.vue
          ChatInput.vue
          ThinkingPanel.vue
          CitationList.vue
          AssetPreview.vue
        layout/
          AppShell.vue
  scripts/
  docs/
    development_plan.md
    frontend_design.md
    rag_design.md
  docker-compose.yml
  Dockerfile
  pyproject.toml
  .env.example
  README.md
```

## 7. 核心模块设计

### 7.1 FastAPI API 层

API 层只负责协议转换、参数校验、依赖注入和错误响应，不直接写复杂业务逻辑。

第一阶段接口：

- `GET /health`：健康检查。
- `POST /knowledge-bases`：创建知识库。
- `GET /knowledge-bases`：知识库列表。
- `POST /knowledge-bases/{id}/documents`：上传文档。
- `GET /documents/{id}`：查看文档处理状态。
- `POST /chat`：普通 RAG 问答。
- `POST /chat/stream`：流式聊天输出。
- `POST /chat/stop`：停止当前生成或 Agent 执行。
- `GET /conversations`：历史会话列表。
- `POST /conversations`：创建新会话。
- `GET /conversations/{id}`：查看会话详情。
- `PATCH /conversations/{id}`：编辑会话标题、归档状态等。
- `DELETE /conversations/{id}`：删除或软删除会话。
- `PATCH /messages/{id}`：编辑用户消息并触发重新生成。
- `POST /agent-tasks`：创建 Multi-Agent 任务。
- `GET /agent-tasks/{id}`：查看 Agent 任务状态和结果。

### 7.1.1 Vue 前端

前端目标是做一个可真实使用的 AI 工作台，而不是接口 demo 页面。第一版界面参考主流大模型产品的交互范式。

核心页面：

- Chat Workspace：主聊天界面。
- Knowledge Base：知识库和文档管理。
- Settings：模型、知识库、检索策略配置。

聊天工作台功能：

- 左侧历史会话列表。
- 新建会话。
- 搜索历史会话。
- 重命名会话。
- 删除或归档会话。
- 主区域展示消息列表。
- 用户消息和 AI 消息分角色展示。
- AI 消息支持 Markdown、代码块、复制。
- 支持流式输出。
- 支持“停止生成”。
- 支持“重新生成”。
- 支持编辑上一条用户消息并基于编辑内容重新生成。
- 支持显示 Agent 思考过程或执行轨迹。
- 支持折叠/展开思考过程。
- 支持展示引用来源。
- 支持展示召回图片资产。
- 支持选择知识库和检索模式。

前端状态管理：

- `conversation store`：会话列表、当前会话、会话标题、归档状态。
- `chat store`：当前消息流、生成状态、停止控制器、错误状态。
- `knowledge base store`：知识库列表、当前选中知识库、文档处理状态。

流式输出建议：

- 第一版优先使用 Server-Sent Events。
- 后端每次生成返回事件：`message_delta`、`thinking_delta`、`tool_event`、`citation`、`asset`、`done`、`error`。
- 前端收到 `done` 前显示停止按钮。
- 用户点击停止时调用 `POST /chat/stop`，后端通过 Redis 或内存任务注册表中断当前任务。

### 7.2 PostgreSQL 数据模型

核心表：

- `users`
- `knowledge_bases`
- `documents`
- `document_chunks`
- `document_assets`
- `conversations`
- `messages`
- `agent_tasks`
- `agent_task_events`

关键设计：

- 文档和 chunk 分开存储。
- chunk 支持普通 chunk 和父子 chunk 两种模式。
- chunk 保存原文、位置、层级关系、元数据、embedding。
- document_assets 保存从文档中抽取的图片、表格截图等资产，并记录原始位置、访问 URL、上下文文本和关联 chunk。
- message 保存用户问题、模型回答、引用来源。
- agent_task 保存长任务状态。
- agent_task_events 保存每个 Agent 节点的执行轨迹，方便调试和展示。

`document_chunks` 建议字段：

- `id`
- `document_id`
- `knowledge_base_id`
- `parent_chunk_id`
- `chunk_type`：`normal`、`parent`、`child`
- `content`
- `content_with_asset_urls`
- `summary`
- `section_title`
- `page_number`
- `start_offset`
- `end_offset`
- `token_count`
- `embedding`
- `metadata`
- `created_at`

普通 chunk：

- `chunk_type = normal`
- `parent_chunk_id = null`
- 用于简单文本类文档，直接检索、直接拼上下文。

父子 chunk：

- `chunk_type = parent`：保存较大的上下文段落，例如一个标题章节、一个页面、一个完整小节。
- `chunk_type = child`：保存更小的检索单元，例如 200-500 tokens。
- child chunk 用于向量召回，命中 child 后回填 parent chunk 作为最终上下文。
- 适合制度文档、技术文档、带大量例子的长文档，能兼顾召回精度和回答上下文完整性。

`document_assets` 建议字段：

- `id`
- `document_id`
- `knowledge_base_id`
- `asset_type`：`image`、`table_image`、`chart`、`page_snapshot`
- `source_format`：`docx`、`pdf`、`html` 等。
- `storage_key`
- `url`
- `original_filename`
- `mime_type`
- `page_number`
- `paragraph_index`
- `caption`
- `ocr_text`
- `surrounding_text`
- `linked_chunk_id`
- `metadata`
- `created_at`

图片资产不只作为附件保存，还要参与检索：

- 文档解析时抽取 Word/PDF 中的图片。
- 图片保存到对象存储或本地静态资源目录，数据库保存 URL。
- 原文中图片位置替换为稳定占位符，例如：`![image:asset_id](asset_url)`。
- chunk 的 `content_with_asset_urls` 保存替换后的文本。
- 如果图片有标题、上下文段落、OCR 结果或多模态 caption，要写入 `document_assets` 并参与检索。
- 检索命中相关文本 chunk 时，可以通过占位符或关联关系返回图片 URL。
- 检索命中图片资产时，返回图片 URL、所在页、上下文文本和相邻 chunk。

### 7.3 Redis 使用场景

Redis 不替代 PostgreSQL，它只处理高频、短生命周期、状态型数据。

使用场景：

- 文档处理进度缓存。
- Agent 任务运行状态。
- 会话短期上下文缓存。
- 接口限流。
- RAG 检索结果短缓存。
- LangGraph checkpoint 后续可接入 Redis。

### 7.4 RAG 模块

RAG 流程：

1. 文档上传。
2. 文档解析。
3. 抽取图片、图表、表格截图等资产。
4. 保存资产并生成可访问 URL。
5. 将文档正文中的图片位置替换为 URL 或 Markdown 图片占位符。
6. 文本清洗。
7. 根据知识库配置选择普通 chunk 或父子 chunk。
8. embedding 生成。
9. chunk + asset metadata + embedding 入库。
10. 用户提问。
11. query rewrite 可选。
12. 向量检索。
13. 父子 chunk 回填可选。
14. 图片资产召回可选。
15. 关键词检索可选。
16. rerank 可选。
17. 组装文本上下文和图片引用。
18. LLM 生成回答。
19. 返回答案、文本引用来源和图片 URL。

第一阶段必须实现：

- 文档文本导入。
- chunk 切分。
- 支持普通 chunk。
- embedding。
- pgvector 检索。
- 带引用来源的回答。

第二阶段增强：

- 父子 chunk 检索。
- Word 文档图片抽取、存储和 URL 替换。
- 图片资产基于上下文文本召回。
- 混合检索。
- rerank。
- 查询改写。
- 上下文压缩。
- RAG 评估。

### 7.4.1 Chunk 策略

系统需要同时支持两类 chunk 策略，并允许在知识库或文档级别配置。

普通 chunk 策略：

- 适用场景：短文档、纯文本 FAQ、Markdown 笔记、结构简单的说明文。
- 入库方式：将文本直接切成相对均匀的小块，每个 chunk 独立生成 embedding。
- 检索方式：命中 chunk 后直接进入 rerank 和上下文组装。
- 优点：实现简单、成本低、延迟低。
- 缺点：长文档中容易丢失上层标题、示例背景和跨段落上下文。

父子 chunk 策略：

- 适用场景：Word/PDF 技术手册、制度文档、包含大量示例图片或代码块的长文档。
- parent chunk：按标题、小节、页面或语义段落切分，保留较完整上下文。
- child chunk：从 parent chunk 内继续切小块，用于更精确的向量召回。
- 入库方式：parent 和 child 都入库，child 保存 `parent_chunk_id`。
- 检索方式：先召回 child，再根据 `parent_chunk_id` 回填 parent，最终把 parent 内容作为上下文候选。
- 优点：召回精度和上下文完整性更平衡。
- 缺点：入库、去重、rerank 和上下文裁剪更复杂。

建议默认策略：

- Markdown、TXT：默认普通 chunk。
- Word、PDF：默认父子 chunk。
- 用户可以在知识库配置中切换。

### 7.4.2 图片资产召回

图片召回的目标不是让图片单独“向量化后回答一切”，而是让文档中的图片在 RAG 上下文中保持可追踪、可引用、可返回。

Word 文档处理要求：

- 解析 `.docx` 时提取正文、标题层级、段落顺序、表格和内嵌图片。
- 每张图片保存为独立资产，生成稳定 URL。
- 图片在原文位置替换为 Markdown 格式：`![asset:{asset_id}]({url})`。
- 图片前后的段落、标题、页码、caption 写入 `document_assets.surrounding_text`。
- 如果后续接入 OCR 或多模态模型，可以把 OCR/caption 写入 `ocr_text` 或 `caption`。

图片入库策略：

- 图片文件本体保存到对象存储、本地静态目录或后续 MinIO。
- PostgreSQL 保存图片元数据、URL、位置、关联 chunk。
- 文本 chunk 保存替换后的 URL，占位符作为上下文的一部分。
- 对 `caption + ocr_text + surrounding_text` 生成 embedding，可作为图片资产召回索引。

图片召回策略：

- 文本召回命中含图片占位符的 chunk：直接返回该 chunk 内图片 URL。
- 文本召回命中图片附近的 chunk：返回相邻图片资产。
- 图片资产召回命中：返回图片 URL、所在页、caption、surrounding_text 和 linked chunk。
- 父子 chunk 模式下，如果 child 命中图片说明文字，回填 parent 时要保留 parent 中的图片 URL。

最终回答返回结构建议：

```json
{
  "answer": "根据文档中的示例流程，...",
  "citations": [
    {
      "document_id": "doc_123",
      "chunk_id": "chunk_456",
      "page_number": 3,
      "text": "引用片段..."
    }
  ],
  "assets": [
    {
      "asset_id": "asset_789",
      "type": "image",
      "url": "https://example.com/assets/asset_789.png",
      "caption": "系统架构示例图",
      "page_number": 3,
      "linked_chunk_id": "chunk_456"
    }
  ]
}
```

### 7.5 Multi-Agent 工作流

使用 LangGraph 实现状态机，而不是简单链式调用。

初始 Agent 分工：

- `Router Agent`：判断用户任务类型。
- `Retriever Agent`：检索知识库材料。
- `Analyzer Agent`：分析 JD、简历、文档或问题。
- `Planner Agent`：生成学习计划、行动方案或报告。
- `Reviewer Agent`：检查答案是否引用充分、逻辑是否完整。

状态对象建议字段：

- `task_id`
- `user_id`
- `question`
- `task_type`
- `knowledge_base_ids`
- `retrieved_chunks`
- `analysis_result`
- `draft_answer`
- `review_result`
- `final_answer`
- `errors`
- `events`

工作流示例：

```text
START
  -> router
  -> retriever
  -> analyzer
  -> planner
  -> reviewer
  -> if approved: final
  -> if rejected: planner
END
```

注意：Multi-Agent 不追求 Agent 数量，而是要能解释为什么需要拆分。这个项目里拆分的理由是：检索、分析、计划、审核的职责不同，状态和失败处理也不同。

## 8. 分阶段开发路线

### Phase 0：项目骨架

目标：建立可运行工程结构。

任务：

- 初始化 `pyproject.toml`。
- 初始化 `frontend/package.json` 和 Vite Vue 项目。
- 建立 FastAPI `app/main.py`。
- 建立 FastAPI 静态文件挂载和 SPA fallback。
- 建立配置系统。
- 建立日志系统。
- 建立 Docker Compose：PostgreSQL + Redis。
- 建立健康检查接口。
- 建立基础测试。

验收标准：

- `uvicorn app.main:app --reload` 可启动。
- `frontend` 可通过 Vite 启动开发服务。
- `GET /health` 返回正常。
- PostgreSQL 和 Redis 可连接。
- pytest 能跑通。

### Phase 1：业务基础与数据库

目标：完成知识库、文档、会话的基础模型。

任务：

- SQLAlchemy 模型。
- Alembic 迁移。
- Knowledge Base CRUD。
- Document 元数据入库。
- Conversation / Message 数据模型。

验收标准：

- 可以创建知识库。
- 可以登记上传文档。
- 可以查询文档状态。

### Phase 2：RAG 文档入库链路

目标：完成从文档到向量索引的链路。

任务：

- 文档解析。
- 普通 chunk 切分。
- 父子 chunk 切分。
- Word 文档图片抽取。
- 图片资产保存和 URL 生成。
- 文档正文图片位置替换为 URL 占位符。
- embedding provider 封装。
- pgvector 接入。
- chunk 入库。
- document_assets 入库。
- 处理状态更新。

验收标准：

- 上传一份文本或 Markdown 文档后，可以生成 chunks。
- 上传一份 Word 文档后，可以抽取图片并保存 URL。
- Word 文档正文中图片位置被替换为对应 URL 占位符。
- 可以按知识库配置选择普通 chunk 或父子 chunk。
- chunks 有 embedding。
- 可以按 query 检索出相关 chunk。
- 可以通过图片周围文本召回相关图片 URL。

### Phase 3：RAG 问答接口

目标：实现企业知识库问答。

任务：

- Retriever 封装。
- Parent-child retriever 封装。
- Image asset retriever 封装。
- Prompt 模板。
- LLM provider 封装。
- `POST /chat`。
- `POST /chat/stream`。
- 停止生成机制。
- 文本引用来源返回。
- 图片 URL 和图片上下文返回。
- 消息历史入库。

验收标准：

- 用户提问后，系统能基于知识库回答。
- 前端可以看到流式输出。
- 用户可以停止当前生成。
- 回答包含引用来源。
- 当问题命中示例图、流程图、截图说明时，回答能返回相关图片 URL。
- 父子 chunk 模式下，child 命中后能回填 parent 上下文。
- conversation/message 有完整记录。

### Phase 4：Vue 聊天工作台

目标：实现接近主流大模型产品的基础前端体验。

任务：

- 应用布局：左侧会话栏、顶部工具区、主聊天区、输入区。
- 历史会话列表。
- 新建、重命名、删除会话。
- 消息列表渲染。
- Markdown 和代码块渲染。
- 流式输出渲染。
- 停止生成按钮。
- 编辑用户消息并重新生成。
- 重新生成 AI 回复。
- 思考过程/Agent 执行轨迹展示。
- 引用来源展示。
- 图片资产预览。

验收标准：

- 可以在页面中创建和切换会话。
- 可以看到历史消息。
- 可以编辑用户消息并生成新的回答。
- 生成中可以停止。
- 回答能展示引用来源和召回图片。

### Phase 5：LangGraph Multi-Agent

目标：完成具备状态流转的 Agent 工作流。

任务：

- AgentState 定义。
- Router 节点。
- Retriever 节点。
- Analyzer 节点。
- Planner 节点。
- Reviewer 节点。
- `POST /agent-tasks`。
- `GET /agent-tasks/{id}`。
- 执行事件入库。

验收标准：

- 可以提交一个复杂任务。
- 系统按节点执行并记录轨迹。
- Reviewer 可以通过或打回。
- 最终返回结构化结果。

### Phase 6：工程增强

目标：让项目更像真实工程。

任务：

- 后台任务队列。
- Redis 状态缓存。
- 接口鉴权。
- 参数校验和统一错误处理。
- 单元测试和集成测试。
- Dockerfile。
- README。
- 示例数据和演示脚本。

验收标准：

- 本地一条命令启动依赖。
- API 有清晰文档。
- 关键模块有测试。
- 项目可以作为简历项目展示。

## 9. 学习计划和路径

这份学习计划不按“先学完再做项目”的方式推进，而是每个阶段都围绕项目产出学习。

### 第 1 阶段：后端工程骨架

学习目标：

- 理解 FastAPI 项目分层。
- 理解 Vue + FastAPI 同仓库开发模式。
- 理解 Pydantic 配置和请求响应模型。
- 理解 SQLAlchemy session 管理。
- 理解 Docker Compose 本地依赖管理。

边做边学：

- FastAPI 路由、依赖注入、异常处理。
- Vue 3、Vite、Pinia、Vue Router 基础。
- `.env` 配置。
- PostgreSQL / Redis 连接。
- pytest 基础。

对应产出：

- 可启动后端服务。
- 可启动 Vue 前端页面。
- 健康检查接口。
- 数据库和 Redis 连接检查。

### 第 2 阶段：数据库建模

学习目标：

- 能为 AI 应用设计业务表。
- 理解文档、chunk、会话、任务之间的关系。
- 理解普通 chunk、父子 chunk、图片资产之间的关系。
- 掌握 Alembic 迁移。

边做边学：

- SQLAlchemy 2.x。
- 一对多、多对一关系。
- 自关联表设计。
- 索引设计。
- JSONB 元数据字段。
- pgvector 字段。
- 文件资产元数据设计。

对应产出：

- 知识库、文档、chunk、图片资产、会话、任务模型。
- 数据库迁移脚本。

### 第 3 阶段：RAG 入库链路

学习目标：

- 掌握 RAG 的数据准备流程。
- 理解 chunk、embedding、向量检索。
- 理解父子 chunk 如何平衡召回精度和上下文完整性。
- 理解图片资产如何和文档文本保持位置关系。

边做边学：

- 文档解析。
- 普通 chunk 和父子 chunk 策略。
- Word 图片抽取。
- 图片 URL 替换。
- embedding provider 抽象。
- pgvector 相似度检索。

对应产出：

- 上传文档后自动切分、向量化、入库。
- Word 文档中的图片能够保存到数据库资产表，并在正文中替换为 URL。
- 支持普通 chunk 和父子 chunk 两种入库策略。
- 支持 query 检索相关 chunks。
- 支持通过图片说明文字、图片周围文本召回图片 URL。

### 第 4 阶段：RAG 问答

学习目标：

- 掌握如何把检索结果和 LLM 结合。
- 理解 Prompt 模板、引用来源、上下文窗口限制。
- 理解图片引用如何进入问答结果，但不强行塞进纯文本 prompt。
- 理解流式输出、停止生成和会话历史如何配合。

边做边学：

- LangChain chat model。
- Retriever。
- Parent-child retriever。
- Image asset retriever。
- PromptTemplate。
- 输出结构化。
- 引用来源设计。
- SSE 或 Fetch Stream。
- 前端消息状态管理。

对应产出：

- `POST /chat` 问答接口。
- 回答带文本来源和图片资产。
- 会话记录入库。
- Vue 页面可以显示流式回答、引用来源和图片资产。

### 第 4.5 阶段：Vue 聊天工作台

学习目标：

- 掌握大模型聊天产品的前端交互。
- 理解会话、消息、生成任务、停止生成之间的数据关系。

边做边学：

- Vue 组件拆分。
- Pinia 状态管理。
- Markdown 渲染。
- 流式消息追加。
- 编辑消息和重新生成。

对应产出：

- 左侧历史会话。
- 主聊天区域。
- 输入框。
- 停止生成。
- 编辑消息。
- Agent 思考过程展示。
- 引用来源和图片预览。

### 第 5 阶段：LangGraph Agent 工作流

学习目标：

- 掌握状态机式 Agent 开发。
- 理解 Multi-Agent 的职责拆分。
- 理解条件分支、循环和失败恢复。

边做边学：

- LangGraph State。
- node / edge / conditional edge。
- graph compile。
- 工具调用。
- 工作流事件记录。

对应产出：

- 可执行的 Multi-Agent 分析任务。
- Agent 执行轨迹可查看。

### 第 6 阶段：工程落地增强

学习目标：

- 让项目从能跑变成能维护。

边做边学：

- Redis 缓存和任务状态。
- 后台任务。
- 日志链路。
- 错误处理。
- 接口测试。
- Docker 部署。

对应产出：

- Docker Compose 一键启动。
- 关键接口测试。
- README 演示流程。

## 10. 每个技术点在项目里的位置

FastAPI：

- API 入口、依赖注入、接口文档、请求响应校验。

Vue：

- 聊天工作台、历史会话、流式输出、停止生成、编辑消息、引用来源和图片预览。

PostgreSQL：

- 用户、知识库、文档、chunk、图片资产、会话、Agent 任务。

Redis：

- 任务状态、缓存、限流、短期会话状态。

LangChain：

- LLM 调用、Prompt、Retriever、Tool 抽象。

LangGraph：

- Multi-Agent 工作流和状态流转。

RAG：

- 文档问答、知识库检索、父子 chunk、图片资产召回、引用来源。

Multi-Agent：

- 复杂任务拆分、分析、规划、审核。

## 11. 简历包装方向

项目名称：

AI Agent 企业知识库与智能分析系统

简历描述示例：

- 基于 FastAPI、PostgreSQL、Redis 构建 AI Agent 后端服务，支持知识库管理、文档入库、会话管理和异步任务状态追踪。
- 设计并实现 RAG 检索增强问答链路，包含文档解析、普通 chunk、父子 chunk、embedding、pgvector 向量检索和引用来源返回。
- 支持 Word 文档图片抽取和图片资产召回，将文档中的图片替换为可访问 URL，并在问答结果中返回相关示例图。
- 使用 Vue 3 构建类大模型产品的聊天工作台，支持历史会话、流式输出、停止生成、编辑消息、重新生成和引用来源展示。
- 使用 LangGraph 构建 Multi-Agent 工作流，将复杂任务拆分为路由、检索、分析、规划、审核等节点，并支持条件分支和失败重试。
- 使用 Redis 缓存任务状态和检索结果，提升接口响应速度并支持长任务进度查询。
- 编写 Docker Compose、数据库迁移和接口测试，提升项目可部署性和可维护性。

## 12. 面试讲解主线

面试时建议按这条线讲：

1. 为什么做这个系统：企业内部知识散落，普通 LLM 无法直接回答私有数据问题。
2. 系统怎么解决：用 RAG 接入私有知识库，用 Agent 工作流处理复杂任务。
3. 数据怎么流转：文档上传、解析、图片抽取、URL 替换、切分、向量化、检索、生成、引用。
4. Agent 怎么设计：不同节点职责不同，LangGraph 管理状态和流程。
5. 前端怎么交互：Vue 实现历史会话、流式输出、停止生成、编辑消息、引用来源和图片预览。
6. 工程上怎么落地：PostgreSQL 存长期数据，Redis 存短期状态，FastAPI 暴露接口并挂载 Vue 静态资源。
7. 遇到的问题：检索不准、上下文过长、幻觉、任务失败、接口耗时。
8. 怎么优化：父子 chunk、图片资产召回、混合检索、rerank、查询改写、缓存、异步任务、可观测日志。

## 13. 下一步执行顺序

建议接下来按这个顺序真正开始写代码：

1. 初始化工程配置：`pyproject.toml`、`.env.example`、`README.md`。
2. 初始化 Vue + Vite 前端骨架。
3. 创建 FastAPI 应用和健康检查接口。
4. 加入 Docker Compose：PostgreSQL、Redis。
5. 加入 SQLAlchemy 和数据库连接。
6. 建立第一批模型和迁移。
7. 实现会话和消息模型。
8. 实现 Vue 聊天工作台基础布局。
9. 实现知识库 CRUD。
10. 实现文档入库和 chunk。
11. 增加父子 chunk 策略。
12. 增加 Word 图片抽取、URL 替换和图片资产表。
13. 接入 embedding 和 pgvector。
14. 实现 RAG 问答和流式输出。
15. 实现停止生成、编辑消息和重新生成。
16. 实现图片资产召回。
17. 实现 LangGraph Multi-Agent。

当前阶段不要急着接入太多平台。先把一个代码型系统做扎实，Dify、Langflow、Flowise 后续作为对比和扩展。
