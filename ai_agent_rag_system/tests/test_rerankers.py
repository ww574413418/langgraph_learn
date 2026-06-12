from app.rag.rerankers import FakeReranker, RerankItem, SiliconFlowReranker
from uuid import uuid4

def test_fake_reranker_sorts_items_by_configured_score() -> None:
    items = [
        RerankItem(item_id="chunk-a", text="A", original_score=10.0, original_rank=1),
        RerankItem(item_id="chunk-b", text="B", original_score=5.0, original_rank=2),
    ]

    reranker = FakeReranker(
        scores_by_item_id={
            "chunk-a": 0.2,
            "chunk-b": 0.9,
        }
    )

    results = reranker.rerank(
        query="test query",
        items=items,
    )

    assert [item.item_id for item in results] == ["chunk-b", "chunk-a"]
    assert [item.rank for item in results] == [1, 2]
    assert results[0].score == 0.9
    assert results[0].metadata["reranker"] == "fake-reranker"


def test_fake_reranker_applies_top_k() -> None:
    items = [
        RerankItem(item_id="chunk-a", text="A"),
        RerankItem(item_id="chunk-b", text="B"),
        RerankItem(item_id="chunk-c", text="C"),
    ]

    reranker = FakeReranker(
        scores_by_item_id={
            "chunk-a": 0.1,
            "chunk-b": 0.9,
            "chunk-c": 0.5,
        }
    )

    results = reranker.rerank(
        query="test query",
        items=items,
        top_k=2,
    )

    assert [item.item_id for item in results] == ["chunk-b", "chunk-c"]
    assert [item.rank for item in results] == [1, 2]


def test_fake_reranker_returns_empty_results_for_empty_query() -> None:
    reranker = FakeReranker(scores_by_item_id={"chunk-a": 1.0})

    results = reranker.rerank(
        query="   ",
        items=[RerankItem(item_id="chunk-a", text="A")],
    )

    assert results == []



from app.models.document_chunk import DocumentChunk
from app.models.retrieval_types import ContextCandidate
from app.rag.rerankers import (
    RerankResult,
    apply_rerank_results_to_candidates,
    build_rerank_items_from_candidates,
)


def make_chunk(
    *,
    chunk_type: str,
    content: str,
    parent_id=None,
) -> DocumentChunk:
    return DocumentChunk(
        id=uuid4(),
        document_id=uuid4(),
        parent_id=parent_id,
        chunk_type=chunk_type,
        chunk_index=0,
        content=content,
        content_hash=f"hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        extra_metadata={},
    )


def test_build_rerank_items_uses_citation_chunk_content_for_parent_child() -> None:
    parent = make_chunk(
        chunk_type="parent",
        content="很长的 parent 上下文",
    )
    child = make_chunk(
        chunk_type="child",
        content="精准命中的 child 文本",
        parent_id=parent.id,
    )

    candidate = ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        score=3.0,
        rank=1,
        retrieval_mode="parent_child",
        retrieval_source="bm25",
    )

    items = build_rerank_items_from_candidates([candidate])

    assert len(items) == 1
    assert items[0].item_id == str(child.id)
    assert items[0].text == "精准命中的 child 文本"
    assert items[0].metadata["context_chunk_id"] == str(parent.id)
    assert items[0].metadata["citation_chunk_id"] == str(child.id)
    assert items[0].metadata["chunk_type"] == "child"


def test_apply_rerank_results_updates_score_rank_and_preserves_parent_child_relation() -> None:
    parent = make_chunk(
        chunk_type="parent",
        content="完整 parent 上下文",
    )
    child = make_chunk(
        chunk_type="child",
        content="child 命中文本",
        parent_id=parent.id,
    )

    candidate = ContextCandidate(
        context_chunk=parent,
        citation_chunk=child,
        score=1.2,
        rank=2,
        retrieval_mode="parent_child",
        retrieval_source="hybrid",
        extra_metadata={"source_ranks": {"bm25": 2, "vector": 4}},
    )

    results = [
        RerankResult(
            item_id=str(child.id),
            score=0.95,
            rank=1,
            raw_score=0.95,
            metadata={"reranker": "fake-reranker"},
        )
    ]

    reranked = apply_rerank_results_to_candidates(
        candidates=[candidate],
        rerank_results=results,
    )

    assert len(reranked) == 1

    item = reranked[0]

    assert item.score == 0.95
    assert item.rank == 1
    assert item.retrieval_source == "rerank"

    # parent-child 的核心关系不能被 rerank 破坏。
    assert item.context_chunk.id == parent.id
    assert item.citation_chunk.id == child.id

    assert item.extra_metadata["before_rerank"]["score"] == 1.2
    assert item.extra_metadata["before_rerank"]["rank"] == 2
    assert item.extra_metadata["before_rerank"]["retrieval_source"] == "hybrid"
    assert item.extra_metadata["rerank"]["metadata"]["reranker"] == "fake-reranker"


def test_siliconflow_reranker_maps_payload_and_provider_index_to_item_id() -> None:
    captured_payload = {}

    def fake_post(payload: dict) -> dict:
        captured_payload.update(payload)
        return {
            "id": "rerank-test-id",
            "results": [
                {
                    "index": 1,
                    "document": {"text": "banana"},
                    "relevance_score": 0.85,
                },
                {
                    "index": 0,
                    "document": {"text": "apple"},
                    "relevance_score": 0.2,
                },
            ],
            "meta": {
                "tokens": {
                    "input_tokens": 10,
                    "output_tokens": 0,
                    "image_tokens": 0,
                }
            },
        }

    reranker = SiliconFlowReranker(
        api_key="test-key",
        post_fn=fake_post,
    )

    items = [
        RerankItem(item_id="chunk-a", text="apple", original_score=1.0, original_rank=1),
        RerankItem(item_id="chunk-b", text="banana", original_score=0.5, original_rank=2),
    ]

    results = reranker.rerank(
        query=" Apple ",
        items=items,
        top_k=2,
    )

    assert captured_payload == {
        "model": "BAAI/bge-reranker-v2-m3",
        "query": "Apple",
        "documents": ["apple", "banana"],
        "return_documents": False,
        "top_n": 2,
    }

    assert [item.item_id for item in results] == ["chunk-b", "chunk-a"]
    assert [item.rank for item in results] == [1, 2]
    assert results[0].score == 0.85
    assert results[0].raw_score == 0.85
    assert results[0].metadata["reranker"] == "siliconflow-reranker"
    assert results[0].metadata["model"] == "BAAI/bge-reranker-v2-m3"
    assert results[0].metadata["provider"] == "siliconflow"
    assert results[0].metadata["provider_index"] == 1
    assert results[0].metadata["provider_id"] == "rerank-test-id"
    assert results[0].metadata["meta"]["tokens"]["input_tokens"] == 10


def test_siliconflow_reranker_clamps_top_k_to_item_count() -> None:
    captured_payload = {}

    def fake_post(payload: dict) -> dict:
        captured_payload.update(payload)
        return {
            "results": [
                {
                    "index": 0,
                    "relevance_score": 0.9,
                }
            ]
        }

    reranker = SiliconFlowReranker(
        api_key="test-key",
        post_fn=fake_post,
    )

    reranker.rerank(
        query="Apple",
        items=[RerankItem(item_id="chunk-a", text="apple")],
        top_k=10,
    )

    assert captured_payload["top_n"] == 1


def test_siliconflow_reranker_returns_empty_results_without_calling_provider_for_empty_query() -> None:
    calls = []

    def fake_post(payload: dict) -> dict:
        calls.append(payload)
        return {"results": []}

    reranker = SiliconFlowReranker(
        api_key="test-key",
        post_fn=fake_post,
    )

    results = reranker.rerank(
        query="   ",
        items=[RerankItem(item_id="chunk-a", text="apple")],
    )

    assert results == []
    assert calls == []


def test_siliconflow_reranker_rejects_invalid_provider_index() -> None:
    def fake_post(payload: dict) -> dict:
        return {
            "results": [
                {
                    "index": 99,
                    "relevance_score": 0.9,
                }
            ]
        }

    reranker = SiliconFlowReranker(
        api_key="test-key",
        post_fn=fake_post,
    )

    try:
        reranker.rerank(
            query="Apple",
            items=[RerankItem(item_id="chunk-a", text="apple")],
        )
    except ValueError as exc:
        assert "Invalid rerank result index" in str(exc)
        return

    raise AssertionError("Expected ValueError")
