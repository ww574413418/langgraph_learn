'''
文档检索辅助逻辑。

负责把 ChunkHit 转成统一的 ContextCandidate，
并处理父子 chunk 的 parent 回填。
'''
from uuid import UUID
from app.models.document_chunk import DocumentChunk
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.rag.retrieval_types import ChunkHit, ContextCandidate,RetrievalSource,RetrievalMode



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


def backfill_parents_for_children(
        db:Session,
        child_hits: list[ChunkHit],
        max_parent_contexts:int = 5
) -> list[ContextCandidate]:
    '''
    1. 多个 child 可能命中同一个 parent。
    2. 同一个 parent 只返回一次，避免上下文重复。
    3. 如果同一个 parent 有多个 child 命中，保留 score 最高的 child 作为 citation child。
    4. 最终返回数量不能超过 max_parent_contexts。
    5. 返回顺序应该按 score 从高到低；score 为 None 时排后面。
    :return:
    '''
    best_result_by_parent_id: dict[UUID, ContextCandidate] = {}

    for child_hit in child_hits:
        child = child_hit.chunk

        parent:DocumentChunk = get_parent_for_child(db=db,child=child)

        existing = best_result_by_parent_id.get(parent.id)

        new_result = build_parent_child_context_candidate(
            parent=parent,
            child=child,
            score=child_hit.score,
            retrieval_source=child_hit.retrieval_source,
        )

        if existing is None:
            best_result_by_parent_id[parent.id] = new_result
            continue
        if is_better_score(child_hit.score,existing.score):
            best_result_by_parent_id[parent.id] = new_result

    results = list(best_result_by_parent_id.values())


    results.sort(
        key=lambda item: item.score if item.score is not None else float("-inf"),
        reverse=True,
    )

    return results[:max_parent_contexts]


def is_better_score(
    new_score: float | None,
    old_score: float | None,
) -> bool:
    if old_score is None:
        return new_score is not None

    if new_score is None:
        return False

    return new_score > old_score


def retrieve_parent_contexts_by_child_hits(
        db:Session,
        child_hits:list[ChunkHit],
        max_parent_contexts:int = 5
)->list[ContextCandidate]:
    '''
    接收已经命中的 child hits，回填 parent
    :param child_hits:
    :param max_parent_contexts:
    :return:
    '''
    return backfill_parents_for_children(
        db=db,
        child_hits=child_hits,
        max_parent_contexts=max_parent_contexts
    )

def build_parent_child_context_candidate(
    parent: DocumentChunk,
    child: DocumentChunk,
    score: float | None,
    retrieval_source: RetrievalSource,
) -> ContextCandidate:
    return ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        score=score,
        retrieval_mode="parent_child",
        retrieval_source=retrieval_source,
    )

def build_normal_context_candidate(
    chunk: DocumentChunk,
    score: float | None,
    retrieval_source: RetrievalSource,
) -> ContextCandidate:
    return ContextCandidate(
        context_chunk=chunk,
        citation_chunk=chunk,
        score=score,
        retrieval_mode="normal",
        retrieval_source=retrieval_source,
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

#  retrieval pipeline 的统一入口
def retrieve_context_candidates(
    db: Session,
    query: str,
    document_ids: list[UUID] | None = None,
    mode: RetrievalMode = "parent_child",
    top_k: int = 5,
) -> list[ContextCandidate]:
    ...