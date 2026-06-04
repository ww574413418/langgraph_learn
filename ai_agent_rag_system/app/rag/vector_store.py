# app/rag/vector_store.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.retrieval_types import ChunkHit


def cosine_distance_to_score(distance: float) -> float:
    """
    pgvector cosine_distance 是“越小越相似”。
    但系统内部 ChunkHit.score 约定是“越大越好”。

    所以这里统一转换：
    - distance 接近 0：score 接近 1
    - distance 越大：score 越低

    注意：这不是唯一算法，但它让上层排序语义保持一致。
    """
    return max(0.0, min(1.0, 1.0 - distance / 2.0))


def search_chunks_by_vector(
    db: Session,
    *,
    query_embedding: list[float],
    chunk_type: str,
    embedding_model: str,
    embedding_dimensions: int,
    document_ids: list[UUID] | None = None,
    top_k: int = 5,
) -> list[ChunkHit]:
    """
    pgvector 查询边界。

    这个函数只做一件事：
    用 query_embedding 在 document_chunks 中查最相似的 chunk。

    它不负责：
    - 调 embedding API
    - 做 parent-child 回填
    - 拼 prompt
    - 生成 citation

    这样以后你加 hybrid / rerank 时，这个函数仍然稳定可复用。
    """

    if not query_embedding:
        return []

    # 空列表表示明确限定到“没有文档”，必须直接返回空。
    # 否则容易误查全库，造成知识库数据泄漏。
    if document_ids == []:
        return []

    # cosine_distance 是 pgvector.sqlalchemy 提供的方法。
    # SQL 中大致会变成：embedding <=> query_embedding
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        select(DocumentChunk, distance)
        .where(
            DocumentChunk.chunk_type == chunk_type,

            # 没有 embedding 的 chunk 不能参与向量检索。
            DocumentChunk.embedding.is_not(None),

            # 生产关键点：必须过滤模型和维度。
            # 不同 embedding 模型生成的向量不能直接比较。
            DocumentChunk.embedding_model == embedding_model,
            DocumentChunk.embedding_dimensions == embedding_dimensions,
        )
        .order_by(
            distance.asc(),

            # 稳定排序。
            # 如果两个 chunk 距离一样，按 id 排，避免 citation 顺序漂移。
            DocumentChunk.id.asc(),
        )
        .limit(top_k)
    )

    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    rows = db.execute(stmt).all()

    hits: list[ChunkHit] = []

    for rank, (chunk, raw_distance) in enumerate(rows, start=1):
        normalized_score = cosine_distance_to_score(float(raw_distance))

        hits.append(
            ChunkHit(
                chunk=chunk,
                rank=rank,
                score=normalized_score,
                raw_score=float(raw_distance),
                normalized_score=normalized_score,
                retrieval_source="vector",
            )
        )

    return hits