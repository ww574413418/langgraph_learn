from app.models.retrieval_types import ChunkHit


def _safe_rank(hit: ChunkHit, fallback_rank: int) -> int:
    """
    获取 hit 的 rank。

    正常情况下，BM25 / vector retriever 都应该返回 rank。
    但为了让融合函数更健壮，如果 rank 缺失，就用它在当前列表中的位置兜底。
    """
    if hit.rank is not None and hit.rank > 0:
        return hit.rank

    return fallback_rank


def fuse_hits_by_rrf(
    hit_groups: dict[str, list[ChunkHit]],
    *,
    k: int = 60,
    top_k: int | None = None,
) -> list[ChunkHit]:
    """
    用 Reciprocal Rank Fusion 融合多路召回结果。

    RRF 核心思想：
    - 不直接比较 BM25 score 和 vector score。
    - 只看每个 hit 在各自召回列表里的排名 rank。
    - 排名越靠前，贡献越大。
    - 同一个 chunk 被多路召回时，RRF 分数会累加。

    公式：
        rrf_score = sum(1 / (k + rank))

    参数：
    - hit_groups: 例如 {"bm25": bm25_hits, "vector": vector_hits}
    - k: 平滑参数，常用 60；k 越大，排名差距影响越平缓
    - top_k: 如果传入，只返回前 top_k 个融合结果

    返回：
    - retrieval_source 统一标记为 "hybrid"
    - score / raw_score 设为 RRF 分数
    - rank 设为融合后的最终排名
    - extra_metadata 记录每个来源的原始 rank 和 score，方便 trace/debug
    """
    if k <= 0:
        raise ValueError("k must be positive")

    fused_by_chunk_id: dict[str, ChunkHit] = {}
    rrf_scores: dict[str, float] = {}
    source_ranks: dict[str, dict[str, int]] = {}
    source_scores: dict[str, dict[str, float | None]] = {}

    for source_name, hits in hit_groups.items():
        for index, hit in enumerate(hits, start=1):
            chunk_id = str(hit.chunk.id)
            rank = _safe_rank(hit=hit, fallback_rank=index)

            if chunk_id not in fused_by_chunk_id:
                fused_by_chunk_id[chunk_id] = hit
                rrf_scores[chunk_id] = 0.0
                source_ranks[chunk_id] = {}
                source_scores[chunk_id] = {}

            rrf_scores[chunk_id] += 1.0 / (k + rank)
            source_ranks[chunk_id][source_name] = rank
            source_scores[chunk_id][source_name] = hit.score

    fused_hits: list[ChunkHit] = []

    for chunk_id, original_hit in fused_by_chunk_id.items():
        rrf_score = rrf_scores[chunk_id]

        fused_hits.append(
            ChunkHit(
                chunk=original_hit.chunk,
                score=rrf_score,
                raw_score=rrf_score,
                normalized_score=rrf_score,
                retrieval_source="hybrid",
                extra_metadata={
                    "source_ranks": source_ranks[chunk_id],
                    "source_scores": source_scores[chunk_id],
                },
            )
        )

    fused_hits.sort(
        key=lambda hit: (
            hit.score if hit.score is not None else float("-inf"),
            str(hit.chunk.id),
        ),
        reverse=True,
    )

    for rank, hit in enumerate(fused_hits, start=1):
        hit.rank = rank

    if top_k is not None:
        return fused_hits[:top_k]

    return fused_hits