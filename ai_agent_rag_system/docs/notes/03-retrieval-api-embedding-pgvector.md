# 学习笔记（三）：Chunk 检索、Retrieval API、Embedding Provider 与 pgvector

记录日期：2026-06-01

本篇承接第二份学习笔记：第二份笔记完成了文档登记、解析入口、Markdown 图片资产和 `document_assets`。本篇整理从 `document_chunks` 入库主链路，到 Retrieval API 稳定，再到 embedding provider 和 pgvector 字段落库的内容。

本篇目标不是简单记录“做了什么”，而是帮助复习：

- 每个模块解决什么问题。
- 对应哪些文件。
- 核心代码怎么写。
- 为什么这样分层。
- 有哪些容易踩坑的点。

## 1. 本阶段在系统中的位置

前两篇笔记完成了：

```text
knowledge_bases
  -> documents
  -> document_assets
```

本篇进入 RAG 可检索主链路：

```text
documents
  -> document_chunks
  -> retrieval hits
  -> parent backfill
  -> context assembly
  -> Retrieval API response
```

当前 Retrieval API 请求链路：

```text
POST /api/retrieval
  -> RetrievalRequest
  -> run_retrieval()
  -> retrieve_context()
  -> keyword hits / parent-child backfill
  -> assemble_context_with_dynamic_budget()
  -> RetrievalResponse
```

### 核心理解

RAG 系统不能只关注“能搜到文本”。生产链路至少要拆成：

```text
检索源
  -> 命中结果
  -> 父子 chunk 回填
  -> 上下文组装
  -> 引用信息
  -> trace / budget / debug 信息
```

这样后续把 keyword 替换成 pgvector、BM25、hybrid、rerank 时，上层 API 不需要重写。

## 2. `document_chunks` 模型

对应文件：

```text
app/models/document_chunk.py
migrations/versions/e01cb6c9aa11_create_document_chunks.py
migrations/versions/1ed2530eec8c_add_document_chunk_embedding.py
```

### 模块作用

`document_chunks` 保存可检索文本片段。它是 RAG 的核心数据表。

它解决的问题：

- 文档太长，不能整篇塞进 LLM。
- 检索需要可召回的最小文本单元。
- 回答需要引用来源。
- 父子 chunk 需要表达 child 和 parent 的关系。
- 后续向量检索需要保存 embedding。

### 核心字段

```python
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chunks.id"),
        nullable=True,
        index=True,
    )

    chunk_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
```

### 代码讲解

`document_id` 表示 chunk 属于哪篇文档。

`parent_id` 是自关联外键，用于父子 chunk：

```text
child.parent_id -> parent.id
```

`chunk_type` 区分三种 chunk：

```text
normal
parent
child
```

`chunk_index` 用于记录 chunk 在当前文档或 parent 内的顺序。它也是幂等判断的重要组成部分。

`content_hash` 用于判断 chunk 内容是否变化，但不能单独作为唯一判断依据。

### 关键点

普通 chunk：

```text
context_chunk = citation_chunk = normal chunk
```

父子 chunk：

```text
context_chunk = parent chunk
citation_chunk = child chunk
```

### 注意事项

不要只用 `content_hash` 判断 chunk 是否存在。

原因：

- 同一文档不同位置可能有相同内容。
- parent 和 child 可能内容重叠。
- 同一 child 必须绑定正确 parent。

更稳的判断维度：

```text
document_id
chunk_type
chunk_index
content_hash
parent_id
```

## 3. pgvector 字段设计

对应文件：

```text
app/models/document_chunk.py
app/core/config.py
migrations/versions/1ed2530eec8c_add_document_chunk_embedding.py
```

### 模块作用

为 `document_chunks` 增加向量字段，为后续 pgvector 检索做准备。

### 核心配置

```python
class Settings(BaseSettings):
    embedding_model: str = "deterministic-test-embedding"
    embedding_dimensions: int = 8
```

### 核心代码

```python
from pgvector.sqlalchemy import Vector
from app.core.config import settings

embedding_model: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True,
)

embedding: Mapped[list[float] | None] = mapped_column(
    Vector(settings.embedding_dimensions),
    nullable=True,
)

embedding_dimensions: Mapped[int | None] = mapped_column(
    Integer,
    nullable=True,
)
```

### 代码讲解

`embedding_model` 记录这个向量由哪个模型生成。

`embedding` 是真正的 pgvector 字段。

`embedding_dimensions` 记录向量维度。

注意这两句的区别：

```python
embedding: Mapped[list[float] | None]
```

这只是 Python 类型提示。

```python
mapped_column(Vector(settings.embedding_dimensions))
```

这才是告诉 SQLAlchemy 和 Alembic：数据库字段类型是 `vector(8)`。

### Alembic 迁移核心代码

```python
import pgvector.sqlalchemy

def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=8), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
    )
```

### 验证命令

```bash
alembic upgrade head
docker exec postgres psql -U agent -d agent_workspace -c "\d document_chunks"
```

预期看到：

```text
embedding              vector(8)
embedding_dimensions   integer
```

### 关键点

当前阶段约束：

```text
一个部署环境 = 一个 active embedding model = 一个 embedding dimension
```

第一阶段不支持同一个数据库混用多个 embedding 维度。

### 注意事项

Alembic autogenerate 对第三方类型不一定自动补 import。

这次生成了：

```python
pgvector.sqlalchemy.Vector(dim=8)
```

但需要手动补：

```python
import pgvector.sqlalchemy
```

否则 `alembic upgrade head` 会报 `NameError`。

## 4. 普通 chunk 切分

对应文件：

```text
app/rag/splitters.py
app/services/document_indexing_service.py
app/services/document_chunk_service.py
```

### 模块作用

把文档文本切成可检索、可引用、可入库的普通 chunk。

普通 chunk 适合：

- txt
- Markdown
- FAQ
- 较短或结构简单的文档

### 核心流程

```text
load_document()
  -> split_normal_chunks()
  -> calculate_content_hash()
  -> create_document_chunk()
  -> document.status = "indexed"
```

### splitter 设计

普通文本使用：

```python
RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    separators=[
        "\n## ",
        "\n### ",
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        ".",
        " ",
        "",
    ],
    keep_separator=True,
    add_start_index=True,
)
```

Markdown 使用：

```python
MarkdownTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
    add_start_index=True,
)
```

### 代码讲解

`add_start_index=True` 很重要，它让 splitter 返回 chunk 在原文中的起始位置。

后续可以用：

```text
start_char
end_char
```

做 citation 定位、parent-child 相对位置计算和上下文窗口截断。

### Markdown heading metadata

Markdown 标题通过正则扫描：

```python
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
```

然后根据 chunk 的 `start_char` / `end_char` 找到标题上下文。

metadata 示例：

```python
{
    "heading_1": "数组",
    "heading_2": "数组的基本操作",
    "file_type": "md",
    "chunk_strategy": "normal",
}
```

### 小块合并

过短 chunk 价值低，容易污染检索。

当前使用 `merge_small_chunks()` 将短 chunk 合并到前一个 chunk，并重新编号。

### 关键点

chunk 不是简单切字符串，而是要尽量保留：

- 语义边界
- 标题层级
- 图片 placeholder
- 代码块格式
- 原文位置

### 注意事项

`MarkdownHeaderTextSplitter` 会改写 Markdown 结构，尤其可能影响代码缩进。因此当前使用 `MarkdownTextSplitter`，再自己补 heading metadata。

## 5. 父子 chunk 入库

对应文件：

```text
app/rag/splitters.py
app/services/document_indexing_service.py
app/services/document_chunk_service.py
```

### 模块作用

父子 chunk 用于长文档：

```text
child 负责精准召回
parent 负责完整上下文
```

### 核心流程

```text
全文
  -> parent splitter
  -> parent chunks
  -> child splitter per parent
  -> child chunks
  -> parent 入库
  -> child 入库并绑定 parent_id
```

### 核心代码结构

```python
@dataclass
class ParentChildSplit:
    parent: SplitChunk
    children: list[SplitChunk]
```

写入 parent：

```python
parent_chunk = create_document_chunk(
    db,
    data=DocumentChunkCreate(
        document_id=document.id,
        parent_id=None,
        chunk_type="parent",
        chunk_index=parent.chunk_index,
        content=parent.content,
        content_hash=parent_content_hash,
        ...
    ),
)
```

写入 child：

```python
create_document_chunk(
    db,
    data=DocumentChunkCreate(
        document_id=document.id,
        parent_id=parent_chunk.id,
        chunk_type="child",
        chunk_index=child.chunk_index,
        content=child.content,
        content_hash=child_content_hash,
        ...
    ),
)
```

### 代码讲解

parent 入库后要拿到 `parent_chunk.id`，child 才能写入：

```text
child.parent_id = parent_chunk.id
```

这就是父子关系在数据库里的表达。

### 关键点

parent 已存在时不能直接跳过整个 parent，因为它下面的 child 仍然可能需要处理。

正确逻辑：

```text
parent 已存在 -> 复用 parent id -> 继续处理 children
```

### 注意事项

child 的 `chunk_index` 是 parent 内部的序号，而不是全文全局序号。后续如果需要全局排序，可以在 metadata 中保存 `parent_chunk_index`。

## 6. Retrieval 内部类型

对应文件：

```text
app/rag/retrieval_types.py
```

### 模块作用

统一不同检索源的返回结构，让 keyword、vector、BM25、hybrid、rerank 后续都能接入同一条 pipeline。

### 核心代码

```python
RetrievalSource = Literal[
    "vector",
    "keyword",
    "bm25",
    "pg_trgm",
    "full_text",
    "hybrid",
    "rerank",
    "manual",
]

RetrievalMode = Literal["normal", "parent_child"]
```

### `ChunkHit`

```python
@dataclass
class ChunkHit:
    chunk: DocumentChunk
    score: float | None = None
    rank: int | None = None
    retrieval_source: RetrievalSource = "manual"
    raw_score: float | None = None
    normalized_score: float | None = None
    extra_metadata: dict = field(default_factory=dict)
```

`ChunkHit` 表示一个检索源命中的原始 chunk。

### `ContextCandidate`

```python
@dataclass
class ContextCandidate:
    context_chunk: DocumentChunk
    citation_chunk: DocumentChunk
    score: float | None = None
    rank: int | None = None
    retrieval_mode: RetrievalMode = "normal"
    retrieval_source: RetrievalSource = "manual"
    extra_metadata: dict = field(default_factory=dict)
```

`ContextCandidate` 表示可以进入上下文组装的候选。

### 代码讲解

normal 模式：

```text
context_chunk = normal chunk
citation_chunk = normal chunk
```

parent-child 模式：

```text
context_chunk = parent chunk
citation_chunk = child chunk
```

### 关键点

`RetrievalSource` 和 `RetrievalMode` 不要混淆。

`RetrievalSource` 表示检索来源：

```text
keyword / vector / bm25 / hybrid / rerank
```

`RetrievalMode` 表示 chunk 结构：

```text
normal / parent_child
```

这是为了后续 hybrid search 不把概念揉在一起。

## 7. Keyword Retrieval

对应文件：

```text
app/services/document_retrieval_service.py
tests/test_document_retrieval.py
```

### 模块作用

先用最小 keyword 检索验证 retrieval pipeline。

### 核心代码

```python
def search_chunks_by_keyword(
    db: Session,
    query: str,
    chunk_type: str,
    document_ids: list[UUID] | None = None,
    top_k: int = 5,
) -> list[ChunkHit]:
    normalized_query = query.strip()

    if not normalized_query:
        return []

    if document_ids == []:
        return []

    stmt = select(DocumentChunk).where(
        DocumentChunk.chunk_type == chunk_type,
        DocumentChunk.content.ilike(f"%{normalized_query}%"),
    )

    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    stmt = stmt.limit(top_k)
    chunks = db.scalars(stmt).all()

    return [
        ChunkHit(
            chunk=chunk,
            score=calculate_keyword_score(chunk.content, normalized_query),
            retrieval_source="keyword",
        )
        for chunk in chunks
    ]
```

### 代码讲解

`query.strip()` 用于拒绝空查询。

`document_ids == []` 是安全边界：

```text
空文档范围 = 没有可检索文档 = 返回空结果
```

不能让空列表跳过 where 条件，否则会退化成全库检索。

`chunk_type` 用于区分：

```text
normal 模式查 normal
parent_child 模式查 child
```

### score 计算

```python
def calculate_keyword_score(content: str, query: str) -> float:
    normalized_content = content.lower()
    normalized_query = query.lower()

    if not normalized_query:
        return 0.0

    exact_count = normalized_content.count(normalized_query)

    if exact_count == 0:
        return 0.0

    return exact_count / max(len(normalized_content), 1)
```

这个 score 不是 BM25，只是教学阶段的稳定分数。

### 关键点

keyword retrieval 的价值是：

- 不依赖外部 API。
- 不依赖 embedding。
- 可以验证 parent-child 回填。
- 可以验证 context assembly。
- 可以给 API 测试提供稳定数据。

### 注意事项

当前 SQL 是：

```python
stmt = stmt.limit(top_k)
```

然后 Python 再计算 score。

这意味着数据库先截断，后排序。生产中应该改成 BM25、pg_trgm、full text 或取更大的候选池后再重排。

## 8. 父子 chunk 回填

对应文件：

```text
app/services/document_retrieval_service.py
```

### 模块作用

将 child hits 转换为 parent context candidates。

### 单条校验代码

```python
def get_parent_for_child(db: Session, child: DocumentChunk) -> DocumentChunk:
    if child.chunk_type != "child":
        raise ValueError("Only child chunks can be backfilled to parent chunks")

    if child.parent_id is None:
        raise ValueError("Child chunk does not have a parent")

    parent = db.get(DocumentChunk, child.parent_id)

    if parent is None:
        raise ValueError("Parent chunk not found")

    if parent.chunk_type != "parent":
        raise ValueError("Parent chunk is not a parent chunk")

    if parent.document_id != child.document_id:
        raise ValueError("Parent chunk does not belong to the same document")

    return parent
```

### 代码讲解

这段函数只负责一件事：

```text
验证 child 是否能合法回填到 parent
```

它不负责批量处理、不负责排序、不负责 trace。

### 批量 best-effort 回填

```python
def retrieve_parent_contexts_best_effort(
    db: Session,
    child_hits: list[ChunkHit],
    max_parent_contexts: int = 5,
) -> tuple[list[ContextCandidate], int]:
    best_by_parent_id: dict[UUID, ContextCandidate] = {}
    orphan_children = 0

    for child_hit in child_hits:
        child = child_hit.chunk

        try:
            parent = get_parent_for_child(db=db, child=child)
        except ValueError:
            orphan_children += 1
            continue

        new_candidate = build_parent_child_context_candidate(
            parent=parent,
            child=child,
            score=child_hit.score,
            retrieval_source=child_hit.retrieval_source,
        )

        existing = best_by_parent_id.get(parent.id)

        if existing is None or is_better_score(child_hit.score, existing.score):
            best_by_parent_id[parent.id] = new_candidate

    results = list(best_by_parent_id.values())
    results.sort(
        key=lambda item: item.score if item.score is not None else float("-inf"),
        reverse=True,
    )

    return results[:max_parent_contexts], orphan_children
```

### 代码讲解

`best_by_parent_id` 用于 parent 去重。

同一个 parent 多个 child 命中时，只保留 score 更好的 child 作为 citation。

`orphan_children` 记录脏数据数量，例如 child 没有 parent 或 parent 不存在。

### 关键点

线上请求不应该因为一条坏 child 直接 500。

更好的方式：

```text
跳过坏 child
返回可用结果
trace 记录 dropped reason
```

### 注意事项

不要保留两套 parent backfill 实现。之前存在严格版和 best-effort 版，职责重复。现在应该保留：

```text
get_parent_for_child()                 单条校验
retrieve_parent_contexts_best_effort() 批量生产入口
```

## 9. Retrieval 统一入口

对应文件：

```text
app/services/document_retrieval_service.py
```

### 模块作用

对上层提供统一检索入口：

```python
retrieve_context(...)
```

上层不需要知道 keyword、parent backfill、trace 的内部细节。

### 核心代码

```python
def retrieve_context(
    db: Session,
    query: str,
    document_ids: list[UUID] | None = None,
    mode: RetrievalMode = "parent_child",
    top_k: int = 5,
) -> RetrievalResult:
    top_k = _clamp_top_k(top_k)
    normalized_query = query.strip()

    if not normalized_query:
        return RetrievalResult(
            candidates=[],
            trace=RetrievalTrace(
                query=query,
                mode=mode,
                sources=[],
                total_hits=0,
                used_hits=0,
            ),
        )

    if mode == "normal":
        hits = search_chunks_by_keyword(
            db=db,
            query=normalized_query,
            chunk_type="normal",
            document_ids=document_ids,
            top_k=top_k,
        )
        candidates = normalize_normal_chunk_hits(hits=hits, max_contexts=top_k)
        candidates = _stable_sort_and_rank(candidates)
        return RetrievalResult(...)

    child_hits = search_chunks_by_keyword(
        db=db,
        query=normalized_query,
        chunk_type="child",
        document_ids=document_ids,
        top_k=top_k,
    )
    candidates, orphan_children = retrieve_parent_contexts_best_effort(...)
    candidates = _stable_sort_and_rank(candidates)
    return RetrievalResult(...)
```

### 代码讲解

`normal` 模式：

```text
查 normal chunk
normalize 成 ContextCandidate
```

`parent_child` 模式：

```text
查 child chunk
回填 parent
生成 ContextCandidate
```

两种模式最后都返回：

```python
RetrievalResult(
    candidates=...,
    trace=...,
)
```

### top-k 边界

```python
TOP_K_MIN = 1
TOP_K_MAX = 50

def _clamp_top_k(value: int) -> int:
    return max(TOP_K_MIN, min(TOP_K_MAX, value))
```

### 稳定排序

```python
def _stable_sort_and_rank(candidates: list[ContextCandidate]) -> list[ContextCandidate]:
    sorted_items = sorted(
        candidates,
        key=lambda item: (
            item.score if item.score is not None else float("-inf"),
            str(item.citation_chunk.id),
        ),
        reverse=True,
    )

    for idx, item in enumerate(sorted_items, start=1):
        item.rank = idx

    return sorted_items
```

### 关键点

trace 很重要。

它回答：

```text
用了什么 query
用了什么 mode
用了哪些 retrieval sources
命中多少
最终用了多少
丢弃多少
为什么丢弃
```

这对后续调试 RAG 质量非常重要。

## 10. Context Assembly

对应文件：

```text
app/services/context_assembly_service.py
app/rag/tokenizers.py
app/rag/token_budget.py
```

### 模块作用

把 `ContextCandidate` 变成受 token budget 控制、带 citation 的 prompt context。

### 核心数据结构

```python
@dataclass
class AssembledCitation:
    citation_id: str
    document_id: UUID
    context_chunk_id: UUID
    citation_chunk_id: UUID
    retrieval_mode: str
    retrieval_source: str
    score: float | None
    metadata: dict
    preview: str
```

```python
@dataclass
class AssembledContext:
    context_text: str
    citations: list[AssembledCitation]
    used_candidates: list[ContextCandidate]
    dropped_candidates: list[ContextCandidate]
    total_tokens: int
    max_context_tokens: int
    truncated: bool
```

### citation 构建

```python
def build_citation(
    citation_id: str,
    candidate: ContextCandidate,
    preview: str,
) -> AssembledCitation:
    return AssembledCitation(
        citation_id=citation_id,
        document_id=candidate.context_chunk.document_id,
        context_chunk_id=candidate.context_chunk.id,
        citation_chunk_id=candidate.citation_chunk.id,
        retrieval_mode=candidate.retrieval_mode,
        retrieval_source=candidate.retrieval_source,
        score=candidate.score,
        metadata=candidate.citation_chunk.extra_metadata or {},
        preview=preview,
    )
```

### 代码讲解

`context_chunk_id` 表示最终给模型看的上下文 chunk。

`citation_chunk_id` 表示真正被检索命中的证据 chunk。

在 parent-child 场景下二者不同。

citation metadata 使用 `citation_chunk.extra_metadata`，因为 child 才是真正命中的证据片段。

### 父子 chunk 中心窗口

```python
def get_relative_citation_offsets(
    candidate: ContextCandidate,
) -> CitationWindowOffsets | None:
    context = candidate.context_chunk
    citation = candidate.citation_chunk

    if citation.start_char < context.start_char:
        return None

    if citation.end_char > context.end_char:
        return None

    return CitationWindowOffsets(
        start=citation.start_char - context.start_char,
        end=citation.end_char - context.start_char,
    )
```

### 代码讲解

parent 内容可能很长，不能每次完整放入 prompt。

如果 child 在 parent 中的位置已知，就围绕 child 选一个窗口：

```text
parent: A B C D E
child 命中 C
上下文窗口取 B C D
```

### 主组装逻辑

```python
for candidate in sort_candidates(candidates):
    citation_id = f"C{len(citations) + 1}"
    selected_context = select_context_text(...)
    block = format_context_block(citation_id, selected_context.text)
    block_tokens = token_counter.count_text(block)

    if total_tokens + block_tokens > max_context_tokens:
        dropped_candidates.append(candidate)
        truncated = True
        continue

    preview = build_preview(candidate.citation_chunk.content, ...)
    citations.append(build_citation(...))
    blocks.append(block)
    used_candidates.append(candidate)
```

### 关键点

检索结果不能直接等于 prompt。

中间必须经过：

```text
排序
预算控制
截断
citation 生成
dropped 记录
```

### 注意事项

Context Assembly 不应该：

- 查数据库。
- 调 LLM。
- 解析图片资产。
- 知道 HTTP response。

它只处理上下文选择和引用。

## 11. 动态 Token Budget

对应文件：

```text
app/rag/token_budget.py
tests/test_token_budget.py
```

### 模块作用

根据模型窗口、任务类型、检索模式、候选数量、历史消息等因素，动态计算 RAG context 可以使用多少 token。

### 输入结构

```python
@dataclass(frozen=True)
class TokenBudgetRequest:
    model_name: str | None = None
    model_context_window: int | None = None
    task_type: TaskType = "qa"
    retrieval_mode: RetrievalMode = "parent_child"
    candidate_count: int = 0
    document_types: tuple[str, ...] = field(default_factory=tuple)

    user_query_tokens: int = 200
    history_tokens: int = 0
    system_prompt_tokens: int = 800
    reserved_answer_tokens: int | None = None
```

### 输出结构

```python
@dataclass(frozen=True)
class TokenBudgetPlan:
    max_context_tokens: int
    max_chunk_tokens: int
    citation_preview_tokens: int
    model_context_window: int
    available_prompt_tokens: int
    reserved_answer_tokens: int
```

### 代码讲解

预算计算顺序：

```text
模型总窗口
  - system prompt
  - user query
  - history
  - reserved answer
  = available prompt tokens
```

然后再从 available prompt tokens 里切出 RAG context 预算。

### 关键点

要区分：

```text
chunking budget
prompt context budget
```

chunking budget 是入库时怎么切。

prompt context budget 是提问时放多少上下文给模型。

### 注意事项

代码类文档需要更大的 `max_chunk_tokens`。否则函数体、分支和返回值容易被截断。

## 12. Retrieval API

对应文件：

```text
app/api/routes/retrieval.py
app/services/retrieval_service.py
app/schemas/retrieval.py
tests/test_retrieval_api.py
```

### 模块作用

对外提供 RAG 检索 API。

接口：

```text
POST /api/retrieval
```

### Route 核心代码

```python
router = APIRouter()

@router.post(
    "",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
)
def run_retrieval_api(
    data: RetrievalRequest,
    db: Session = Depends(get_db),
):
    try:
        return run_retrieval(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
```

### 代码讲解

API 层只做三件事：

- 接收请求。
- 注入数据库 session。
- 调用应用服务。

它不应该写检索逻辑、token budget、parent backfill 或 SQL。

`ValueError` 返回 400，而不是 404。

原因：

```text
ValueError 表示请求参数或业务输入不合法
404 表示资源不存在
```

### Service 核心代码

```python
def run_retrieval(
    db: Session,
    request: RetrievalRequest,
) -> RetrievalResponse:
    document_ids = resolve_retrieval_document_ids(db=db, request=request)

    retrieval_result = retrieve_context(
        db=db,
        query=request.query,
        document_ids=document_ids,
        mode=request.mode,
        top_k=request.top_k,
    )

    token_counter = TiktokenTokenCounter()

    assembled_context, budget_plan = assemble_context_with_dynamic_budget(
        candidates=retrieval_result.candidates,
        token_counter=token_counter,
        model_name=request.model_name,
        model_context_window=request.model_context_window,
        task_type=request.task_type,
        user_query_tokens=request.user_query_tokens,
        history_tokens=request.history_tokens,
        system_prompt_tokens=request.system_prompt_tokens,
        reserved_answer_tokens=request.reserved_answer_tokens,
    )

    return build_retrieval_response(...)
```

### 代码讲解

`run_retrieval()` 是应用服务层。

它负责编排：

```text
请求参数
  -> 文档范围
  -> 检索
  -> 上下文组装
  -> response schema
```

它不负责底层 SQL 检索，也不负责 HTTP。

### 文档范围解析

```python
def resolve_retrieval_document_ids(
    db: Session,
    request: RetrievalRequest,
) -> list[UUID] | None:
    if request.knowledge_base_id is None:
        return request.document_ids

    stmt = select(Document.id).where(
        Document.knowledge_base_id == request.knowledge_base_id,
        Document.status == "indexed",
    )

    if request.document_ids:
        stmt = stmt.where(Document.id.in_(request.document_ids))

    return list(db.scalars(stmt).all())
```

规则：

- 不传 `knowledge_base_id`：按 `document_ids` 检索；如果也不传，允许全库检索。
- 传 `knowledge_base_id`：只检索该知识库下 indexed 文档。
- 同时传 `knowledge_base_id` 和 `document_ids`：取交集。

### API 测试核心代码

```python
response = client.post(
    "/api/retrieval",
    json={
        "query": "retrieval",
        "mode": "normal",
        "top_k": 5,
        "document_ids": [str(document.id)],
        "task_type": "qa",
    },
)

assert response.status_code == 200
data = response.json()
assert "RAG retrieval API should return this chunk." in data["context_text"]
assert data["citations"][0]["retrieval_mode"] == "normal"
assert data["trace"]["sources"] == ["keyword"]
```

### 关键点

API 测试不是重复 service 测试。

它验证完整 HTTP 链路：

```text
FastAPI route
  -> Pydantic schema
  -> dependency injection
  -> service
  -> response_model
```

### 注意事项

测试中使用：

```python
app.dependency_overrides[get_db] = override_get_db(db)
```

这样可以让 API 测试使用当前测试创建的 DB session，方便清理数据。

## 13. Retrieval API 数据隔离

对应文件：

```text
app/services/retrieval_service.py
app/services/document_retrieval_service.py
tests/test_retrieval_api.py
tests/test_document_retrieval.py
```

### 问题

曾经有一段逻辑：

```python
if document_ids:
    stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
```

如果 `document_ids == []`，条件为 false，不会加 where。

结果：

```text
空 scope -> 全库检索
```

这是严重的数据隔离风险。

### 修正代码

```python
if document_ids == []:
    return []
```

### API 测试

```python
response = client.post(
    "/api/retrieval",
    json={
        "query": "retrieval",
        "mode": "normal",
        "top_k": 5,
        "knowledge_base_id": str(empty_knowledge_base.id),
        "task_type": "qa",
    },
)

assert response.status_code == 200
data = response.json()
assert data["context_text"] == ""
assert data["citations"] == []
assert data["trace"]["total_hits"] == 0
assert data["trace"]["used_hits"] == 0
```

### 关键点

RAG 系统的数据隔离不能只靠前端传参。

后端必须保证：

```text
用户指定了知识库范围
  -> 后端只能查这个范围
  -> 空范围就是空结果
```

## 14. Embedding Provider 抽象

对应文件：

```text
app/rag/embeddings.py
tests/test_embeddings.py
```

### 模块作用

封装“文本转向量”能力，避免业务代码直接依赖具体厂商 SDK。

### 接口代码

```python
class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...
```

### 代码讲解

`embed_query()` 用于用户 query。

`embed_documents()` 用于 chunk 批量入库。

接口只规定能力，不规定具体实现。

后续可以有：

```text
DeterministicEmbeddingProvider
OpenAIEmbeddingProvider
LocalBGEEmbeddingProvider
DashScopeEmbeddingProvider
```

### 测试用 provider

```python
class DeterministicEmbeddingProvider:
    model_name = "deterministic-test-embedding"

    def __init__(self, dimensions: int = 8) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")

        self.dimensions = dimensions

    def embed_query(self, text: str) -> list[float]:
        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Embedding text must not be empty")

        return self._hash_text_to_vector(normalized_text)
```

### hash 转向量

```python
def _hash_text_to_vector(self, text: str) -> list[float]:
    vector: list[float] = []
    seed = text.encode("utf-8")
    counter = 0

    while len(vector) < self.dimensions:
        digest = sha256(seed + str(counter).encode("utf-8")).digest()

        for byte in digest:
            if len(vector) >= self.dimensions:
                break

            value = (byte / 255.0) * 2.0 - 1.0
            vector.append(value)

        counter += 1

    return vector
```

### 代码讲解

这个 provider 不追求语义效果。

它只保证测试需要的性质：

- 同文本同向量。
- 不同文本大概率不同向量。
- 固定维度。
- 不依赖网络。
- 不依赖 API Key。

### 测试覆盖

```text
embed_query 返回固定维度
同文本返回相同向量
不同文本返回不同向量
embed_documents 保持输入顺序
空文本抛 ValueError
```

### 关键点

测试不能依赖真实 embedding API。

原因：

- 网络不稳定。
- API Key 可能缺失。
- 模型输出可能变化。
- 成本不可控。

## 15. 本阶段测试覆盖

相关测试：

```text
tests/test_document_retrieval.py
tests/test_retrieval_api.py
tests/test_token_budget.py
tests/test_embeddings.py
```

覆盖能力：

- keyword score。
- keyword chunk 命中。
- chunk_type 过滤。
- document_ids 限定。
- 空 document scope 不泄露全库。
- normal retrieval context candidate。
- parent-child 回填。
- orphan child best-effort trace。
- dynamic token budget。
- API 层 `POST /api/retrieval`。
- embedding provider 固定维度。
- embedding provider deterministic 行为。
- 空文本拒绝 embedding。

### 核心测试命令

```bash
pytest tests/test_retrieval_api.py tests/test_document_retrieval.py tests/test_token_budget.py tests/test_embeddings.py
```

## 16. 本阶段踩坑总结

### 16.1 重复 parent backfill 实现

问题：

- 同时存在严格版和 best-effort 版。
- 逻辑重复，职责不清。

解决：

- 保留单条校验 `get_parent_for_child()`。
- 保留批量生产入口 `retrieve_parent_contexts_best_effort()`。

### 16.2 parent-child retrieval 重复调用

问题：

- `retrieve_context()` 里重复调用 `retrieve_parent_contexts_best_effort()`。

解决：

```python
candidates, orphan_children = retrieve_parent_contexts_best_effort(...)
```

只调用一次。

### 16.3 空文档范围泄露

问题：

```python
if document_ids:
```

不能区分：

```text
None = 不限制范围
[]   = 限制范围为空
```

解决：

```python
if document_ids == []:
    return []
```

### 16.4 SQLAlchemy 无法自动推断 `list[float]`

问题：

```python
embedding: Mapped[list[float] | None]
```

会导致：

```text
MappedAnnotationError
```

解决：

```python
embedding: Mapped[list[float] | None] = mapped_column(
    Vector(settings.embedding_dimensions),
    nullable=True,
)
```

### 16.5 Alembic 缺少 pgvector import

问题：

Alembic 生成：

```python
pgvector.sqlalchemy.Vector(dim=8)
```

但没有 import。

解决：

```python
import pgvector.sqlalchemy
```

## 17. 面试表达

### Retrieval Pipeline

可以这样讲：

> 我把 RAG 检索链路拆成了几个稳定边界：检索源返回 `ChunkHit`，父子 chunk 回填输出 `ContextCandidate`，Context Assembly 负责 token budget、citation 和截断，最后由 Retrieval API 返回 `context_text`、`citations`、`budget_plan` 和 `trace`。这样后续把 keyword 检索替换成 pgvector、hybrid search 或 rerank 时，上层 API 不需要重写。

### 父子 chunk

可以这样讲：

> child chunk 用于精准召回，parent chunk 用于提供完整上下文。检索命中 child 后，通过 `parent_id` 回填 parent，并保留 child 作为 citation chunk，这样既能给模型足够上下文，也能解释为什么召回这段内容。

### 生产边界

可以这样讲：

> 我给 retrieval 加了 top-k 上限、稳定排序、rank、trace、best-effort orphan child 处理和空 document scope 防泄露测试。即使数据里有坏 child，也不会让整个请求 500，同时 trace 可以告诉我们丢弃了多少异常命中。

### Embedding

可以这样讲：

> 我先定义了 `EmbeddingProvider` 接口，并实现 deterministic provider 用于测试，避免测试依赖外部 API。数据库层使用 pgvector 的 `Vector(dim=8)` 字段，同时保存 `embedding_model` 和 `embedding_dimensions`，为后续真实 embedding 模型和向量检索做准备。

## 18. 下次继续

下一步应该继续：

```text
chunk 入库时生成 embedding
  -> DocumentChunkCreate 支持 embedding 字段
  -> indexing service 调用 EmbeddingProvider
  -> 写入 embedding / embedding_model / embedding_dimensions
  -> tests/test_vector_retrieval.py
  -> pgvector vector search
```

当前正确顺序仍然是：

```text
稳定 RAG 检索质量
  -> pgvector
  -> hybrid retrieval
  -> rerank
  -> asset resolution
  -> chat streaming
  -> LangGraph Agent
```

