'''
文档检索辅助逻辑。

负责把 ChunkHit 转成统一的 ContextCandidate，
并处理父子 chunk 的 parent 回填。
'''
from dataclasses import dataclass
from uuid import UUID
from app.models.document_chunk import DocumentChunk
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.retrieval_types import (
    ContextCandidate,
    RetrievalSource,
    RetrievalMode,
    RetrievalStrategy,
    RetrievalTrace,
    RetrievalResult,
    ChunkHit
)
from app.rag.embeddings import EmbeddingProvider
from app.rag.vector_store import search_chunks_by_vector
from app.rag.lexical_retriever import LexicalRetriever
from app.rag.retrieval_fusion import fuse_hits_by_rrf


@dataclass
class CollectedHits:
    """
    表示一次底层召回完成后的 hit pool 和 trace 统计。

    为什么需要这个小结构：
    - retrieve_context() 不应该关心 bm25/vector/hybrid 各自怎样查。
    - retrieve_context() 只需要知道：最终用于后续 pipeline 的 hits 是什么，
      以及 trace 里应该记录哪些来源、每个来源命中多少、原始总命中多少。
    - hybrid 的 total_hits 应该统计融合前的原始命中数，而不是 RRF 去重后的数量。
    """
    hits: list[ChunkHit]
    sources: list[RetrievalSource]
    source_hit_counts: dict[str, int]
    total_hits: int


def get_parent_for_child(
        db:Session,
        child:DocumentChunk
) -> DocumentChunk:
    '''
    单个child 先验证chunk是否合法, 根据child_chunk_parenid查找一个 parent
    :return:
    '''

    if child.chunk_type != "child":
        raise ValueError("Only child chunks can be backfilled to parent chunks")

    if child.parent_id is None:
        raise ValueError("Child chunk does not have a parent")

    parent = db.get(DocumentChunk,child.parent_id)

    if parent is None:
        raise ValueError("Parent chunk not found")

    if parent.chunk_type != "parent":
        raise ValueError("Parent chunk is not a parent chunk")

    if parent.document_id != child.document_id:
        raise ValueError("Parent chunk does not belong to the same document")

    return parent


def is_better_score(
    new_score: float | None,
    old_score: float | None,
) -> bool:
    if old_score is None:
        return new_score is not None

    if new_score is None:
        return False

    return new_score > old_score


def build_parent_child_context_candidate(
    parent: DocumentChunk,
    child: DocumentChunk,
    score: float | None,
    retrieval_source: RetrievalSource,
    extra_metadata: dict | None = None
) -> ContextCandidate:
    return ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        score=score,
        retrieval_mode="parent_child",
        retrieval_source=retrieval_source,
        extra_metadata=extra_metadata or {},
    )

def build_normal_context_candidate(
    chunk: DocumentChunk,
    score: float | None,
    retrieval_source: RetrievalSource,
    extra_metadata: dict | None = None,
) -> ContextCandidate:
    return ContextCandidate(
        context_chunk=chunk,
        citation_chunk=chunk,
        score=score,
        retrieval_mode="normal",
        retrieval_source=retrieval_source,
        extra_metadata=extra_metadata or {},
    )

def normalize_normal_chunk_hits(
    hits: list[ChunkHit],
    max_contexts: int = 5,
) -> list[ContextCandidate]:
    candidates: list[ContextCandidate] = []

    for hit in hits:
        chunk = hit.chunk

        if chunk.chunk_type != "normal":
            raise ValueError("Only normal chunks can be normalized as normal context candidates")

        candidates.append(
            build_normal_context_candidate(
                chunk=chunk,
                score=hit.score,
                retrieval_source=hit.retrieval_source,
                extra_metadata=hit.extra_metadata,
            )
        )

    candidates.sort(
        key=lambda item: item.score if item.score is not None else float("-inf"),
        reverse=True,
    )

    return candidates[:max_contexts]

# 通过关键字 like 去搜 chunk
def search_chunks_by_keyword(
    db: Session,
    query: str,
    chunk_type: str,
    document_ids: list[UUID] | None = None,
    top_k: int = 5,
) -> list[ChunkHit]:
    """
    最小 keyword retrieval。

    当前使用 ILIKE 做子串匹配，目标是先跑通 retrieval pipeline。
    后续可以替换为 BM25、pg_trgm、pgvector 或 hybrid search。
    """

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
            score=calculate_keyword_score(
                content=chunk.content,
                query=normalized_query,
            ),
            retrieval_source="keyword",
        )
        for chunk in chunks
    ]

def calculate_keyword_score(
    content: str,
    query: str,
) -> float:
    """
    最小 keyword score。

    不是 BM25，只用于让 ChunkHit 有稳定分数。
    """

    normalized_content = content.lower()
    normalized_query = query.lower()

    if not normalized_query:
        return 0.0

    exact_count = normalized_content.count(normalized_query)

    if exact_count == 0:
        return 0.0

    length_penalty = max(len(normalized_content), 1)

    return exact_count / length_penalty

# 目的：对外部输入做“硬边界”，避免一次请求把数据库/上下文撑爆
# - 太小：体验差
# - 太大：token budget 肯定溢出、SQL 变慢、返回体变大、前端渲染变慢
TOP_K_MIN = 1
TOP_K_MAX = 50

def _clamp_top_k(value: int) -> int:
    """
    目的：把 top_k 控制在安全范围内，避免线上被恶意/误用打爆。
    """
    return max(TOP_K_MIN, min(TOP_K_MAX, value))

def _stable_sort_and_rank(candidates: list[ContextCandidate]) -> list[ContextCandidate]:
    """
    目的：
    1) 排序稳定：score 相同的情况下要有 tie-breaker，否则不同运行/不同 DB 返回顺序可能不一致，
       会导致“同一个 query 偶尔引用编号变化”，这是生产环境很讨厌的问题。
    2) 生成 rank：rank 是可观测字段，方便 trace/日志/前端展示，也方便后续做 rerank 对比。
    """
    sorted_items = sorted(
        candidates,
        key=lambda item: (
            item.score if item.score is not None else float("-inf"),
            str(item.citation_chunk.id),  # tie-breaker：稳定即可，也可以换 chunk_index
        ),
        reverse=True,
    )

    for idx, item in enumerate(sorted_items, start=1):
        item.rank = idx

    return sorted_items


#  retrieval pipeline 的统一入口
def retrieve_context_candidates(
    db: Session,
    query: str,
    document_ids: list[UUID] | None = None,
    mode: RetrievalMode = "parent_child",
    strategy: RetrievalStrategy = "bm25",
    embedding_provider: EmbeddingProvider | None = None,
    lexical_retriever: LexicalRetriever | None = None,
    top_k: int = 5,
) -> list[ContextCandidate]:
    """
    目的：保持现有调用方式不变（兼容层）。
    未来你做 API 时建议直接用 retrieve_context() 以便拿到 trace。
    """
    return retrieve_context(
        db=db,
        query=query,
        document_ids=document_ids,
        mode=mode,
        strategy=strategy,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever,
        top_k=top_k,
    ).candidates



def retrieve_parent_contexts_best_effort(
    db: Session,
    child_hits: list[ChunkHit],
    max_parent_contexts: int = 5,
) -> tuple[list[ContextCandidate], int]:
    """
    目的：生产级健壮性（best-effort）
    - child chunk 数据不完整/脏数据：跳过该条，不影响整体请求
    - 同一个 parent 多个 child 命中：只保留“最好的 child”（你文件里已有 is_better_score 逻辑）

    返回：
    - candidates：最终 parent 级上下文候选
    - orphan_children：回填失败的 child 数量，用于 trace
    """
    best_by_parent_id: dict[UUID, ContextCandidate] = {}
    orphan_children = 0

    for child_hit in child_hits:
        child = child_hit.chunk

        try:
            parent = get_parent_for_child(db=db, child=child)
        except ValueError:
            orphan_children += 1
            continue

        existing = best_by_parent_id.get(parent.id)
        new_candidate = build_parent_child_context_candidate(
            parent=parent,
            child=child,
            score=child_hit.score,
            retrieval_source=child_hit.retrieval_source,
            extra_metadata=child_hit.extra_metadata,
        )

        if existing is None:
            best_by_parent_id[parent.id] = new_candidate
            continue

        if is_better_score(child_hit.score, existing.score):
            best_by_parent_id[parent.id] = new_candidate

    results = list(best_by_parent_id.values())
    results.sort(
        key=lambda item: item.score if item.score is not None else float("-inf"),
        reverse=True,
    )

    return results[:max_parent_contexts], orphan_children


def _collect_normal_hits(
    db: Session,
    *,
    query: str,
    strategy: RetrievalStrategy,
    document_ids: list[UUID] | None,
    top_k: int,
    embedding_provider: EmbeddingProvider | None,
    lexical_retriever: LexicalRetriever | None,
) -> CollectedHits:
    """
    收集 normal mode 的 ChunkHit。

    normal mode 的召回单元就是 normal chunk：
    - bm25：检索 normal chunk。
    - vector：检索 normal chunk。
    - hybrid：BM25 和 vector 都检索 normal chunk，再用 RRF 在 normal chunk 粒度融合。

    注意：
    这个函数只负责“拿到 hit pool + 统计 trace 所需信息”，
    不负责把 hit 转成 ContextCandidate，也不负责 token budget / context assembly。
    """
    if strategy == "bm25":
        hits = lexical_retriever.search(
            db=db,
            query=query,
            chunk_type="normal",
            document_ids=document_ids,
            top_k=top_k,
        )

        return CollectedHits(
            hits=hits,
            sources=["bm25"],
            source_hit_counts={"bm25": len(hits)},
            total_hits=len(hits),
        )

    if strategy == "vector":
        hits = search_normal_chunks_by_vector(
            db=db,
            query=query,
            embedding_provider=embedding_provider,
            document_ids=document_ids,
            top_k=top_k,
        )

        return CollectedHits(
            hits=hits,
            sources=["vector"],
            source_hit_counts={"vector": len(hits)},
            total_hits=len(hits),
        )

    bm25_hits = lexical_retriever.search(
        db=db,
        query=query,
        chunk_type="normal",
        document_ids=document_ids,
        top_k=top_k,
    )

    vector_hits = search_normal_chunks_by_vector(
        db=db,
        query=query,
        embedding_provider=embedding_provider,
        document_ids=document_ids,
        top_k=top_k,
    )

    fused_hits = fuse_hits_by_rrf(
        hit_groups={
            "bm25": bm25_hits,
            "vector": vector_hits,
        },
        top_k=top_k,
    )

    return CollectedHits(
        hits=fused_hits,
        sources=["bm25", "vector"],
        source_hit_counts={
            "bm25": len(bm25_hits),
            "vector": len(vector_hits),
        },
        total_hits=len(bm25_hits) + len(vector_hits),
    )


def _collect_child_hits(
    db: Session,
    *,
    query: str,
    strategy: RetrievalStrategy,
    document_ids: list[UUID] | None,
    top_k: int,
    embedding_provider: EmbeddingProvider | None,
    lexical_retriever: LexicalRetriever | None,
) -> CollectedHits:
    """
    收集 parent_child mode 的 child hits。

    parent-child RAG 的关键点：
    - 召回单元是 child chunk，因为 child 更短、更聚焦，适合匹配 query。
    - 上下文单元是 parent chunk，因为 parent 更完整，适合放进 prompt。
    - 所以 hybrid/RRF 必须先在 child 粒度完成，再进入 parent backfill。
    """
    if strategy == "bm25":
        hits = lexical_retriever.search(
            db=db,
            query=query,
            chunk_type="child",
            document_ids=document_ids,
            top_k=top_k,
        )

        return CollectedHits(
            hits=hits,
            sources=["bm25"],
            source_hit_counts={"bm25": len(hits)},
            total_hits=len(hits),
        )

    if strategy == "vector":
        hits = search_child_chunks_by_vector(
            db=db,
            query=query,
            embedding_provider=embedding_provider,
            document_ids=document_ids,
            top_k=top_k,
        )

        return CollectedHits(
            hits=hits,
            sources=["vector"],
            source_hit_counts={"vector": len(hits)},
            total_hits=len(hits),
        )

    bm25_hits = lexical_retriever.search(
        db=db,
        query=query,
        chunk_type="child",
        document_ids=document_ids,
        top_k=top_k,
    )

    vector_hits = search_child_chunks_by_vector(
        db=db,
        query=query,
        embedding_provider=embedding_provider,
        document_ids=document_ids,
        top_k=top_k,
    )

    fused_hits = fuse_hits_by_rrf(
        hit_groups={
            "bm25": bm25_hits,
            "vector": vector_hits,
        },
        top_k=top_k,
    )

    return CollectedHits(
        hits=fused_hits,
        sources=["bm25", "vector"],
        source_hit_counts={
            "bm25": len(bm25_hits),
            "vector": len(vector_hits),
        },
        total_hits=len(bm25_hits) + len(vector_hits),
    )


def retrieve_context(
    db: Session,
    query: str,
    document_ids: list[UUID] | None = None,
    mode: RetrievalMode = "parent_child",
    strategy: RetrievalStrategy = "bm25",
    embedding_provider: EmbeddingProvider | None = None,
    lexical_retriever: LexicalRetriever | None = None,
    top_k: int = 5,
) -> RetrievalResult:
    """
    目的：
    - 统一检索入口：把 normal / parent_child 两种模式封装起来
    - 返回 trace：让你能在 API/日志里回答“用了什么策略、命中多少、丢弃多少、最终用了多少”
    - 未来把 keyword 换成向量/FTS/hybrid 时，上层 API 不用改
    """
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

    if mode not in ("normal", "parent_child"):
        raise ValueError("Invalid retrieval mode")

    if strategy not in ("bm25", "vector", "hybrid"):
        raise ValueError("Invalid retrieval strategy")

    if strategy in ("bm25", "hybrid") and lexical_retriever is None:
        raise ValueError("lexical_retriever is required for bm25 or hybrid retrieval")

    if strategy in ("vector", "hybrid") and embedding_provider is None:
        raise ValueError("embedding_provider is required for vector or hybrid retrieval")

    if mode == "normal":
        collected = _collect_normal_hits(
            db=db,
            query=normalized_query,
            strategy=strategy,
            document_ids=document_ids,
            top_k=top_k,
            embedding_provider=embedding_provider,
            lexical_retriever=lexical_retriever,
        )

        candidates = normalize_normal_chunk_hits(
            hits=collected.hits,
            max_contexts=top_k,
        )
        candidates = _stable_sort_and_rank(candidates)

        return RetrievalResult(
            candidates=candidates,
            trace=RetrievalTrace(
                query=query,
                mode=mode,
                sources=collected.sources,
                total_hits=collected.total_hits,
                used_hits=len(candidates),
                source_hit_counts=collected.source_hit_counts,
                dropped_hit_counts={},
            ),
        )

    collected = _collect_child_hits(
        db=db,
        query=normalized_query,
        strategy=strategy,
        document_ids=document_ids,
        top_k=top_k,
        embedding_provider=embedding_provider,
        lexical_retriever=lexical_retriever,
    )

    candidates, orphan_children = retrieve_parent_contexts_best_effort(
        db=db,
        child_hits=collected.hits,
        max_parent_contexts=top_k,
    )

    candidates = _stable_sort_and_rank(candidates)

    dropped: dict[str, int] = {}
    if orphan_children:
        dropped["orphan_child"] = orphan_children

    return RetrievalResult(
        candidates=candidates,
        trace=RetrievalTrace(
            query=query,
            mode=mode,
            sources=collected.sources,
            total_hits=collected.total_hits,
            used_hits=len(candidates),
            source_hit_counts=collected.source_hit_counts,
            dropped_hit_counts=dropped,
        ),
    )


def search_normal_chunks_by_vector(
    db: Session,
    *,
    query: str,
    embedding_provider: EmbeddingProvider,
    document_ids: list[UUID] | None = None,
    top_k: int = 5,
) -> list[ChunkHit]:
    """
    这是 retrieval service 层的编排函数。

    它负责：
    1. 把 query 转成 embedding
    2. 调 vector_store 做数据库检索

    注意：
    - embedding_provider 从外部传入，方便测试替换。
    - 不要在这里直接写 OpenAI client。
    """

    normalized_query = query.strip()

    if not normalized_query:
        return []

    query_embedding = embedding_provider.embed_query(normalized_query)

    return search_chunks_by_vector(
        db=db,
        query_embedding=query_embedding,
        chunk_type="normal",
        embedding_model=embedding_provider.model_name,
        embedding_dimensions=embedding_provider.dimensions,
        document_ids=document_ids,
        top_k=top_k,
    )


def search_child_chunks_by_vector(
    db: Session,
    *,
    query: str,
    embedding_provider: EmbeddingProvider,
    document_ids: list[UUID] | None = None,
    top_k: int = 5,
) -> list[ChunkHit]:
    """
    用 vector 检索 child chunk。

    为什么检索 child，而不是 parent？

    parent chunk 更长，语义更宽，适合作为上下文；
    child chunk 更短，语义更集中，适合作为召回单元。

    所以 parent-child RAG 的典型流程是：

        query -> 检索 child -> 回填 parent -> parent 进上下文

    这能兼顾：
    - 召回精准度
    - 上下文完整度
    """

    normalized_query = query.strip()

    if not normalized_query:
        return []

    query_embedding = embedding_provider.embed_query(normalized_query)

    return search_chunks_by_vector(
        db=db,
        query_embedding=query_embedding,
        chunk_type="child",
        embedding_model=embedding_provider.model_name,
        embedding_dimensions=embedding_provider.dimensions,
        document_ids=document_ids,
        top_k=top_k,
    )
