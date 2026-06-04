from uuid import uuid4

from app.models.document_chunk import DocumentChunk
from app.models.retrieval_types import ChunkHit
from app.rag.retrieval_fusion import fuse_hits_by_rrf


def make_chunk(content: str) -> DocumentChunk:
    """
    构造一个不入库的 DocumentChunk。

    RRF 纯函数只需要 chunk.id 来判断“是不是同一个 chunk”，
    所以这里不需要真实数据库 Session。
    """
    return DocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        chunk_type="normal",
        chunk_index=0,
        content=content,
        content_hash=f"hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        extra_metadata={},
    )


def test_fuse_hits_by_rrf_combines_bm25_and_vector_rankings() -> None:
    """
    验证 RRF 能融合 BM25 和 vector 的排名。

    这个测试不关心原始 score。
    因为 BM25 score 和 vector score 不是同一个量纲，不能直接相加或比较。

    设计：
    - chunk_a 同时出现在 BM25 rank 1 和 vector rank 2
    - chunk_b 只出现在 BM25 rank 2
    - chunk_c 只出现在 vector rank 1

    按 RRF：
    - chunk_a 得分 = 1 / (60 + 1) + 1 / (60 + 2)
    - chunk_c 得分 = 1 / (60 + 1)
    - chunk_b 得分 = 1 / (60 + 2)

    所以 chunk_a 应该排第一。
    """
    chunk_a = make_chunk("same chunk matched by both retrievers")
    chunk_b = make_chunk("bm25 only chunk")
    chunk_c = make_chunk("vector only chunk")

    bm25_hits = [
        ChunkHit(chunk=chunk_a, rank=1, score=12.0, retrieval_source="bm25"),
        ChunkHit(chunk=chunk_b, rank=2, score=8.0, retrieval_source="bm25"),
    ]

    vector_hits = [
        ChunkHit(chunk=chunk_c, rank=1, score=0.92, retrieval_source="vector"),
        ChunkHit(chunk=chunk_a, rank=2, score=0.88, retrieval_source="vector"),
    ]

    fused_hits = fuse_hits_by_rrf(
        hit_groups={
            "bm25": bm25_hits,
            "vector": vector_hits,
        },
        k=60,
    )

    assert len(fused_hits) == 3

    assert fused_hits[0].chunk.id == chunk_a.id
    assert fused_hits[0].retrieval_source == "hybrid"
    assert fused_hits[0].rank == 1

    assert fused_hits[0].score is not None
    assert fused_hits[0].score > fused_hits[1].score

    assert fused_hits[0].extra_metadata["source_ranks"] == {
        "bm25": 1,
        "vector": 2,
    }


def test_fuse_hits_by_rrf_uses_position_when_rank_missing_and_applies_top_k() -> None:
    """
    验证两个生产边界：

    1. 如果某个 retriever 没有返回 rank，RRF 使用列表位置作为兜底排名。
    2. 如果传入 top_k，只返回融合后的前 top_k 条。

    这能避免某个检索后端漏填 rank 时，整个 hybrid pipeline 直接失效。
    """
    chunk_a = make_chunk("first item without explicit rank")
    chunk_b = make_chunk("second item without explicit rank")

    fused_hits = fuse_hits_by_rrf(
        hit_groups={
            "bm25": [
                ChunkHit(chunk=chunk_a, score=10.0, retrieval_source="bm25"),
                ChunkHit(chunk=chunk_b, score=9.0, retrieval_source="bm25"),
            ],
        },
        k=60,
        top_k=1,
    )

    assert len(fused_hits) == 1
    assert fused_hits[0].chunk.id == chunk_a.id
    assert fused_hits[0].rank == 1
    assert fused_hits[0].retrieval_source == "hybrid"
    assert fused_hits[0].extra_metadata["source_ranks"] == {"bm25": 1}
