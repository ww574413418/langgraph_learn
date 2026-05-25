# RAG 详细设计：父子 Chunk 与图片资产召回

## 1. 目标

RAG 模块需要支持两类文档检索能力：

- 文本检索：支持普通 chunk 和父子 chunk。
- 图片召回：支持从 Word 等文档中抽取图片，保存图片 URL，并在检索结果中召回相关图片。

这个设计面向工程落地，不只追求能回答文本问题，也要能处理“示例图、流程图、截图、架构图很多”的文档。

## 1.1 实现原则

RAG 模块不以最小 demo 为目标，而以可维护、可验证、可扩展的生产级链路为目标。

实现时遵循以下原则：

- loader 只负责把不同文件格式解析成统一文档结构，不承担 chunk、embedding 或数据库写入职责。
- splitter 只负责文本切分和 chunk metadata 生成，不直接访问数据库。
- indexing service 负责编排解析、切分、幂等入库、状态更新和错误记录。
- retrieval service 负责检索、父子 chunk 回填、去重、上下文组装和引用信息生成。
- Agent / LangGraph 节点不直接操作数据库细节，而是调用稳定的 service 或 tool。
- embedding 和 pgvector 是检索命中方式的一种实现，不应和父子 chunk 回填规则耦合。
- 每个核心链路都要先能用 SQL 或 service 单独验证，再接入 Agent 工作流。
- 任何“临时 keyword 检索”只能作为验证 child 命中与 parent 回填规则的教学步骤，不能作为最终生产检索方案。

## 2. Chunk 模式

### 2.1 普通 Chunk

适用场景：

- TXT
- Markdown
- FAQ
- 短说明文档
- 结构较简单的文档

处理方式：

1. 文档解析为纯文本。
2. 按 token 数、标题或段落切分。
3. 每个 chunk 独立生成 embedding。
4. 检索命中后直接作为上下文候选。

优点：

- 简单。
- 入库速度快。
- 检索链路短。

缺点：

- 对长文档不友好。
- 容易丢失上层标题、示例背景、图片上下文。

### 2.2 父子 Chunk

适用场景：

- Word
- PDF
- 技术手册
- 制度文档
- 带大量示例图的教程类文档

处理方式：

1. 先按标题、小节、页面或语义边界切成 parent chunk。
2. 再把 parent chunk 切成更小的 child chunk。
3. parent chunk 负责保存完整上下文。
4. child chunk 负责向量召回。
5. 检索时先命中 child，再通过 `parent_chunk_id` 回填 parent。

推荐参数：

- parent chunk：1200-2500 tokens。
- child chunk：200-500 tokens。
- child overlap：30-80 tokens。

注意事项：

- parent chunk 可以不参与向量检索，也可以生成 embedding 用于兜底召回。
- child chunk 必须保存 `parent_chunk_id`。
- 最终上下文组装优先使用 parent 内容，而不是只使用 child 内容。
- 如果 parent 太长，需要再做上下文压缩或 rerank 后裁剪。

## 3. 图片资产设计

### 3.1 为什么图片要单独设计

很多 Word 文档中，关键信息不只在文字里，也在：

- 架构图
- 流程图
- 示例截图
- 配置截图
- 表格截图
- 操作步骤图片

如果只抽取文字，RAG 会丢掉这些信息。更好的方式是：

- 图片文件单独保存。
- 数据库保存图片元数据。
- 文档正文中原图片位置替换成 URL。
- 检索时把相关图片 URL 一起返回。

## 4. 数据表设计

### 4.1 document_chunks

核心字段：

- `id`
- `knowledge_base_id`
- `document_id`
- `parent_chunk_id`
- `chunk_type`
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

`chunk_type` 取值：

- `normal`
- `parent`
- `child`

### 4.2 document_assets

核心字段：

- `id`
- `knowledge_base_id`
- `document_id`
- `linked_chunk_id`
- `asset_type`
- `source_format`
- `storage_key`
- `url`
- `original_filename`
- `mime_type`
- `page_number`
- `paragraph_index`
- `caption`
- `ocr_text`
- `surrounding_text`
- `embedding`
- `metadata`
- `created_at`

`asset_type` 取值：

- `image`
- `table_image`
- `chart`
- `page_snapshot`

说明：

- `url` 用于最终回答返回。
- `surrounding_text` 是图片前后段落和标题。
- `caption` 可以来自文档标题、图片说明、OCR 或多模态模型。
- `embedding` 可以基于 `caption + ocr_text + surrounding_text` 生成。

## 5. Word 文档入库流程

流程：

1. 读取 `.docx`。
2. 按文档顺序解析段落、标题、表格、图片。
3. 图片写入资产存储。
4. 生成图片 URL。
5. 在正文中原图片位置写入占位符：

```markdown
![asset:{asset_id}]({asset_url})
```

6. 记录图片上下文：
   - 当前标题。
   - 前 1-3 个段落。
   - 后 1-3 个段落。
   - 图片说明。
   - 页码或段落序号。
7. 将带图片 URL 的正文送入 chunk 切分。
8. chunk 入库。
9. 图片资产入库，并绑定最近的 chunk 或 parent chunk。
10. 对 chunk 和图片资产文本分别生成 embedding。

## 6. 检索流程

### 6.1 普通文本检索

```text
query
  -> query embedding
  -> search document_chunks where chunk_type = normal
  -> rerank optional
  -> context assembly
```

### 6.2 父子 Chunk 检索

```text
query
  -> query embedding
  -> search child chunks
  -> collect parent_chunk_id
  -> load parent chunks
  -> deduplicate parents
  -> rerank parents optional
  -> context assembly
```

父子 chunk 回填规则：

- retrieval service 接收已经命中的 child hits，而不是直接绑定某一种检索方式。
- child hit 至少包含 `DocumentChunk` 和可选 `score`。
- score 来自上游检索层，例如 pgvector similarity、BM25、RRF 或 rerank model，parent 回填层不负责计算分数。
- 回填前必须校验命中的 chunk 是 `chunk_type = child`。
- child 必须存在 `parent_id`。
- `parent_id` 必须指向 `chunk_type = parent` 的 chunk。
- parent 和 child 必须属于同一个 `document_id`。
- 多个 child 命中同一个 parent 时，parent 只返回一次，避免重复上下文。
- 同一个 parent 下多个 child 命中时，保留 score 最高的 child 作为 citation child。
- 返回结果按 score 降序排列，score 为空的结果排在后面。
- 返回 parent 内容作为主要上下文，但引用信息应保留命中的 child，便于解释“为什么召回这个 parent”。
- 回填层不直接组装最终 prompt；prompt 上下文组装应在 context assembly 阶段处理 token budget、引用片段和图片资产。

推荐结构：

```text
ChildChunkHit
  -> chunk: DocumentChunk
  -> score: float | None

ParentBackfillResult
  -> parent: DocumentChunk
  -> child: DocumentChunk
  -> score: float | None
```

### 6.3 图片资产召回

图片召回有三条路径：

1. chunk 内容中含图片占位符。
2. chunk 附近有关联图片资产。
3. 图片资产自己的 embedding 被 query 命中。

检索流程：

```text
query
  -> query embedding
  -> search text chunks
  -> search document_assets by caption/ocr/surrounding_text embedding
  -> merge assets from chunk placeholders
  -> merge assets linked to retrieved chunks
  -> deduplicate assets
  -> return assets with answer
```

## 7. 上下文组装

给 LLM 的 prompt 以文本为主，图片不要盲目塞进 prompt。

推荐做法：

- 文本上下文中保留图片占位符和图片说明。
- 如果模型支持多模态，后续再把图片 URL 作为 image input。
- 如果当前使用文本模型，回答时明确引用“相关图片见 assets”。
- API 响应中单独返回 `assets` 数组。

Context Assembly 职责：

- 输入统一的 `ContextCandidate` 列表。
- 按 score / rerank score 排序。
- 使用模型 tokenizer 控制 token budget，不使用字符数作为最终预算。
- 对超长 `context_chunk` 做可控截断。
- 父子 chunk 场景下，优先围绕 `citation_chunk` 在 `context_chunk` 中的位置选取上下文窗口。
- 为每个上下文块生成 citation id，例如 `C1`、`C2`。
- citation 使用 `citation_chunk` 的 metadata 和 preview，因为它代表真正命中的证据片段。
- 输出结构化 `AssembledContext`，包含 `context_text`、`citations`、`used_candidates`、`dropped_candidates`、`total_tokens`、`max_context_tokens` 和 `truncated`。
- 不调用 LLM。
- 不查数据库。
- 不处理图片资产，只保留图片 placeholder，图片资产解析由后续 asset resolve 阶段负责。

当前验证结果：

- 能把 parent-child `ContextCandidate` 组装成带 citation id 的上下文。
- 能限制总 token budget。
- 能记录 used / dropped candidates。
- 能标记 chunk 截断或候选丢弃。
- 验证中发现代码类文档对上下文窗口更敏感。过小的 `max_chunk_tokens` 会导致代码片段不完整；增大 `max_context_tokens` 和 `max_chunk_tokens` 后，dropped candidate 消失，truncated 变为 false。
- citation preview 如果显示代码块边界 ```，通常说明命中的 child 位于代码块边界附近。这可能需要在 child chunk 质量控制、retrieval 或 rerank 阶段处理，而不是由 context assembly 静默修正。

Chunking budget 与 prompt context budget 区别：

- chunking budget 在文档入库时使用，例如 `parent_chunk_size`、`child_chunk_size`、`chunk_overlap`，决定数据库中 chunk 的大小和结构。
- prompt context budget 在用户提问时使用，例如 `max_context_tokens`、`max_chunk_tokens`、`citation_preview_tokens`，决定本次请求能放入 LLM prompt 的上下文规模。
- 即使 parent chunk 入库时较大，也不代表每次请求都能完整放入 prompt。Context Assembly 必须根据模型窗口、系统 prompt、用户问题、历史消息、回答预留 tokens 和候选数量控制上下文。
- 代码类文档通常需要更大的 `max_chunk_tokens`，否则函数体、分支和返回值容易被截断。
- Context Assembly 应保留可配置 budget 参数，并允许上层根据模型、文档类型、检索模式和任务类型动态传入预算。

动态 token budget 当前策略：

- 策略模块：`app/rag/token_budget.py`。
- 输入结构：`TokenBudgetRequest`，包含模型窗口、任务类型、retrieval mode、候选数量、文档类型、用户问题 tokens、历史 tokens、系统 prompt tokens 和回答预留 tokens。
- 输出结构：`TokenBudgetPlan`，包含 `max_context_tokens`、`max_chunk_tokens`、`citation_preview_tokens`、实际模型窗口、可用 prompt tokens 和回答预留 tokens。
- 预算计算先从模型窗口扣除系统 prompt、用户问题、历史消息和回答预留，再从剩余空间中按任务类型、retrieval mode 和文档类型切出 RAG context 总预算。
- `parent_child` 模式会提高上下文比例和单 chunk 下限，因为最终上下文来自 parent chunk。
- 代码类文档或代码类任务会提高单 chunk 下限和 citation preview，避免代码片段过短。
- `build_token_budget_request_from_candidates()` 可从 `ContextCandidate` 列表推断 `candidate_count`、`retrieval_mode` 和 `document_types`。
- `assemble_context_with_dynamic_budget()` 是后续 retrieval / chat pipeline 更适合调用的入口，底层 `assemble_context()` 继续保留显式预算参数，方便测试和调试。

最小 keyword retrieval：

- 当前已在 `app/services/document_retrieval_service.py` 实现 `search_chunks_by_keyword()`，使用 PostgreSQL `ILIKE` 做子串匹配。
- 该实现不是 BM25，目标是先跑通 retrieval pipeline 的边界：`query -> list[ChunkHit]`。
- `calculate_keyword_score()` 目前只提供稳定的粗粒度分数，后续可替换为 BM25、`pg_trgm`、向量检索或 hybrid RRF。
- keyword retrieval 只负责返回 `ChunkHit`，不做 parent backfill、不做 context assembly。
- PostgreSQL integration test 已覆盖 keyword score、真实表查询、`chunk_type` 过滤和 `document_ids` 限定，避免本地历史数据影响测试结果。

响应结构：

```json
{
  "answer": "这里是回答正文。",
  "citations": [
    {
      "document_id": "doc_001",
      "chunk_id": "chunk_001",
      "page_number": 2,
      "section_title": "操作示例",
      "text": "引用片段"
    }
  ],
  "assets": [
    {
      "asset_id": "asset_001",
      "type": "image",
      "url": "http://localhost:8000/static/assets/asset_001.png",
      "caption": "配置页面示例图",
      "page_number": 2,
      "linked_chunk_id": "chunk_001"
    }
  ]
}
```

## 8. 第一版实现边界

第一版必须做：

- 普通 chunk。
- 父子 chunk。
- Word 图片抽取。
- 本地静态资源 URL。
- document_assets 表。
- 基于图片周围文本的图片召回。
- 回答结果返回 `assets`。

第一版暂不做：

- 图片 OCR。
- 多模态图片理解。
- MinIO / S3。
- PDF 页面截图。
- 复杂表格结构化抽取。

这些能力后续作为增强项。
