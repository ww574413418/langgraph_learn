# RAG 详细设计：父子 Chunk 与图片资产召回

## 1. 目标

RAG 模块需要支持两类文档检索能力：

- 文本检索：支持普通 chunk 和父子 chunk。
- 图片召回：支持从 Word 等文档中抽取图片，保存图片 URL，并在检索结果中召回相关图片。

这个设计面向工程落地，不只追求能回答文本问题，也要能处理“示例图、流程图、截图、架构图很多”的文档。

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
