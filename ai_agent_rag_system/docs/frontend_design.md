# Vue 前端设计文档

## 1. 前端定位

前端采用 Vue 3 实现，目标是做一个类主流大模型产品的 AI 工作台，而不是简单接口测试页面。

当前阶段不做前后端分离部署：

- 前端源码放在 `frontend/`。
- 开发时使用 Vite 启动前端服务。
- FastAPI 提供 `/api/*` 接口。
- 演示或生产时，Vue 构建为静态文件，由 FastAPI 挂载。
- 页面路由由 Vue Router 管理。

## 2. 技术选型

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Element Plus
- markdown-it
- shiki 或 highlight.js

第一版优先保证功能完整和工程清晰，不追求复杂视觉效果。

## 3. 页面结构

### 3.1 Chat Workspace

主聊天页面，包含：

- 左侧会话列表。
- 中间消息区域。
- 底部输入框。
- 顶部知识库/模型/检索策略选择。
- 右侧可选调试面板，后续展示 RAG 召回和 Agent 事件。

核心能力：

- 新建会话。
- 查看历史会话。
- 搜索会话。
- 重命名会话。
- 删除或归档会话。
- 编辑用户消息。
- 重新生成 AI 回复。
- 停止生成。
- 展示流式输出。
- 展示思考过程。
- 展示引用来源。
- 展示召回图片。

### 3.2 Knowledge Base

知识库管理页面，包含：

- 知识库列表。
- 创建知识库。
- 文档上传。
- 文档处理状态。
- chunk 策略配置：普通 chunk / 父子 chunk。
- 查看文档资产，例如图片 URL。

### 3.3 Settings

配置页面，包含：

- 模型 provider。
- embedding provider。
- 默认知识库。
- 默认检索模式。
- 是否显示 Agent 思考过程。

## 4. 组件规划

```text
frontend/src/
  views/
    ChatWorkspace.vue
    KnowledgeBase.vue
    Settings.vue
  components/
    layout/
      AppShell.vue
    chat/
      ConversationSidebar.vue
      ConversationListItem.vue
      MessageList.vue
      MessageItem.vue
      ChatInput.vue
      ThinkingPanel.vue
      CitationList.vue
      AssetPreview.vue
      RegenerateButton.vue
      StopButton.vue
    knowledge/
      KnowledgeBaseList.vue
      DocumentUploader.vue
      DocumentStatusTable.vue
      ChunkStrategySelector.vue
```

## 5. 状态管理

### 5.1 conversation store

职责：

- 会话列表。
- 当前会话。
- 会话标题。
- 会话搜索关键字。
- 会话归档和删除状态。

核心状态：

```ts
interface ConversationState {
  conversations: ConversationSummary[]
  currentConversationId: string | null
  currentMessages: ChatMessage[]
  loading: boolean
}
```

### 5.2 chat store

职责：

- 当前输入内容。
- 当前生成状态。
- 流式输出内容。
- 停止生成。
- 重新生成。
- 编辑消息。

核心状态：

```ts
interface ChatState {
  input: string
  generating: boolean
  currentRunId: string | null
  thinkingText: string
  streamingMessageId: string | null
  error: string | null
}
```

### 5.3 knowledge base store

职责：

- 知识库列表。
- 当前选中知识库。
- 文档上传状态。
- chunk 策略。

## 6. API 约定

### 6.1 会话

- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{id}`
- `PATCH /api/conversations/{id}`
- `DELETE /api/conversations/{id}`

### 6.2 消息

- `PATCH /api/messages/{id}`：编辑用户消息。
- `POST /api/messages/{id}/regenerate`：从指定消息重新生成。

### 6.3 聊天

- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/chat/stop`

### 6.4 知识库

- `GET /api/knowledge-bases`
- `POST /api/knowledge-bases`
- `POST /api/knowledge-bases/{id}/documents`
- `GET /api/documents/{id}`

## 7. 流式输出设计

第一版使用 Server-Sent Events。

事件类型：

- `run_started`
- `thinking_delta`
- `message_delta`
- `tool_event`
- `citation`
- `asset`
- `run_stopped`
- `done`
- `error`

示例：

```json
{
  "event": "message_delta",
  "run_id": "run_001",
  "conversation_id": "conv_001",
  "message_id": "msg_002",
  "delta": "这里是增量文本"
}
```

前端处理规则：

- 收到 `run_started` 后进入生成状态。
- 收到 `thinking_delta` 更新思考面板。
- 收到 `message_delta` 追加 AI 消息内容。
- 收到 `citation` 更新引用来源。
- 收到 `asset` 更新图片资产列表。
- 收到 `done` 结束生成状态。
- 收到 `run_stopped` 显示已停止状态。
- 收到 `error` 展示错误并结束生成状态。

## 8. 停止生成

交互：

1. 用户发送消息。
2. 前端进入生成状态，显示停止按钮。
3. 用户点击停止。
4. 前端调用 `POST /api/chat/stop`，传入 `run_id`。
5. 后端中断对应 LLM 流或 Agent 任务。
6. 前端收到 `run_stopped` 后保留已生成内容。

后端实现建议：

- Redis 保存 `run_id -> status`。
- 流式生成过程中定期检查状态。
- 如果状态为 `cancelled`，停止继续生成。
- 对 LangGraph 长任务，需要在节点边界检查取消状态。

## 9. 编辑消息与重新生成

编辑用户消息：

1. 用户点击某条用户消息的编辑按钮。
2. 输入框进入编辑模式。
3. 保存后调用 `PATCH /api/messages/{id}`。
4. 后端删除或标记该消息之后的旧回复分支。
5. 调用重新生成接口。
6. 前端用新回复替换后续消息。

重新生成 AI 回复：

1. 用户点击 AI 消息的重新生成按钮。
2. 前端调用 `POST /api/messages/{id}/regenerate`。
3. 后端基于上一条用户消息和当前会话上下文重新生成。
4. 前端以流式方式更新新回复。

第一版可以简化为：

- 编辑用户消息后，删除该消息之后的消息。
- 重新生成只保留最新版，不做多版本分支。

后续增强：

- 支持回复多版本切换。
- 支持消息分支树。

## 10. 引用来源与图片展示

AI 消息底部展示：

- 文本引用列表。
- 图片资产列表。
- 点击引用后高亮对应片段。
- 点击图片打开预览。

图片资产结构：

```ts
interface RetrievedAsset {
  assetId: string
  type: 'image' | 'table_image' | 'chart' | 'page_snapshot'
  url: string
  caption?: string
  pageNumber?: number
  linkedChunkId?: string
}
```

## 11. 第一版验收标准

- 可以打开 Vue 页面。
- 可以新建和切换会话。
- 可以查看历史消息。
- 可以发送消息并看到流式回复。
- 可以停止生成。
- 可以编辑用户消息并重新生成。
- 可以看到引用来源。
- 可以看到召回图片。
- 可以上传文档并查看处理状态。
