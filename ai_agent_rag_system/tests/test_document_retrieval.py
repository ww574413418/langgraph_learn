from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.retrieval_types import ChunkHit
from app.services.document_retrieval_service import (
    calculate_keyword_score,
    search_chunks_by_keyword,
)
from app.rag.embeddings import DeterministicEmbeddingProvider



def test_calculate_keyword_score_returns_zero_for_empty_query() -> None:
    assert calculate_keyword_score("hello world", "") == 0.0


def test_calculate_keyword_score_returns_zero_when_query_not_found() -> None:
    assert calculate_keyword_score("hello world", "missing") == 0.0


def test_calculate_keyword_score_counts_exact_matches_case_insensitive() -> None:
    score = calculate_keyword_score(
        content="RAG can use rag retrieval.",
        query="rag",
    )

    assert score > 0


def create_test_session() -> Session:
    engine = create_engine(settings.database_url)
    return Session(engine)

def create_test_document(db: Session) -> Document:
    marker = str(uuid4())

    knowledge_base = KnowledgeBase(
        name=f"keyword-test-kb-{marker}",
        description="keyword retrieval integration test",
        domain="test",
        status="active",
        extra_metadata={"test_marker": marker},
        retrieval_config={},
    )

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    document = Document(
        knowledge_base_id=knowledge_base.id,
        filename=f"keyword-test-{marker}.txt",
        file_type="txt",
        file_path=f"data/keyword-test-{marker}.txt",
        file_hash=f"keyword-test-hash-{marker}",
        status="indexed",
        extra_metadata={"test_marker": marker},
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

def create_chunk(
    db: Session,
    *,
    document_id,
    chunk_type: str,
    content: str,
    chunk_index: int,
    parent_id=None,
    embedding_model: str | None = None,
    embedding: list[float] | None = None,
    embedding_dimensions: int | None = None,
) -> DocumentChunk:
    chunk = DocumentChunk(
        id=uuid4(),
        document_id=document_id,
        parent_id=parent_id,
        chunk_type=chunk_type,
        chunk_index=chunk_index,
        content=content,
        content_hash=f"keyword-test-hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        start_char=0,
        end_char=len(content),
        embedding_model=embedding_model,
        embedding=embedding,
        embedding_dimensions=embedding_dimensions,
        extra_metadata={"file_type": "txt"},
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk

def cleanup_test_document(db: Session, document: Document) -> None:
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
    ).delete()

    knowledge_base_id = document.knowledge_base_id

    db.query(Document).filter(
        Document.id == document.id,
    ).delete()

    db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_base_id,
    ).delete()

    db.commit()

def test_search_chunks_by_keyword_returns_matching_chunk_hits() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        matched = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="RAG retrieval uses keyword search.",
            chunk_index=0,
        )

        create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="This chunk is unrelated.",
            chunk_index=1,
        )

        hits = search_chunks_by_keyword(
            db=db,
            query="retrieval",
            chunk_type="normal",
            document_ids=[document.id],
            top_k=5,
        )

        assert len(hits) == 1
        assert hits[0].chunk.id == matched.id
        assert hits[0].retrieval_source == "keyword"
        assert hits[0].score is not None
        assert hits[0].score > 0

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_search_chunks_by_keyword_filters_by_chunk_type() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="RAG retrieval normal chunk.",
            chunk_index=0,
        )

        child = create_chunk(
            db,
            document_id=document.id,
            chunk_type="child",
            content="RAG retrieval child chunk.",
            chunk_index=1,
        )

        hits = search_chunks_by_keyword(
            db=db,
            query="retrieval",
            chunk_type="child",
            document_ids=[document.id],
            top_k=5,
        )

        assert len(hits) == 1
        assert hits[0].chunk.id == child.id

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_search_chunks_by_keyword_empty_document_scope_returns_no_hits() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="RAG retrieval must not leak across an empty document scope.",
            chunk_index=0,
        )

        hits = search_chunks_by_keyword(
            db=db,
            query="retrieval",
            chunk_type="normal",
            document_ids=[],
            top_k=5,
        )

        assert hits == []

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_retrieve_context_candidates_normal_mode_adds_rank() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        matched = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="RAG retrieval uses keyword search.",
            chunk_index=0,
        )

        retriever = FakeLexicalRetriever(
            hits=[
                ChunkHit(
                    chunk=matched,
                    score=8.0,
                    raw_score=8.0,
                    rank=1,
                    retrieval_source="bm25",
                )
            ]
        )

        items = retrieve_context_candidates(
            db=db,
            query="retrieval",
            document_ids=[document.id],
            mode="normal",
            strategy="bm25",
            lexical_retriever=retriever,
            top_k=5,
        )

        assert len(items) == 1
        assert items[0].retrieval_mode == "normal"
        assert items[0].context_chunk.id == items[0].citation_chunk.id
        assert items[0].rank == 1
        assert items[0].retrieval_source == "bm25"
        assert retriever.calls[0]["chunk_type"] == "normal"

    finally:
        cleanup_test_document(db, document)
        db.close()

from uuid import uuid4
from app.models.document_chunk import DocumentChunk
from app.services.document_retrieval_service import retrieve_context_candidates

def test_retrieve_context_candidates_parent_child_backfills_parent() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        parent = create_chunk(
            db,
            document_id=document.id,
            chunk_type="parent",
            content="Parent content.",
            chunk_index=0,
        )

        child = create_chunk(
            db,
            document_id=document.id,
            chunk_type="child",
            content="Child mentions retrieval keyword.",
            chunk_index=1,
            parent_id=parent.id,
        )

        retriever = FakeLexicalRetriever(
            hits=[
                ChunkHit(
                    chunk=child,
                    score=9.0,
                    raw_score=9.0,
                    rank=1,
                    retrieval_source="bm25",
                )
            ]
        )

        items = retrieve_context_candidates(
            db=db,
            query="retrieval",
            document_ids=[document.id],
            mode="parent_child",
            strategy="bm25",
            lexical_retriever=retriever,
            top_k=5,
        )

        assert len(items) == 1
        assert items[0].retrieval_mode == "parent_child"
        assert items[0].context_chunk.id == parent.id
        assert items[0].citation_chunk.id == child.id
        assert items[0].rank == 1
        assert items[0].retrieval_source == "bm25"
        assert retriever.calls[0]["chunk_type"] == "child"

    finally:
        cleanup_test_document(db, document)
        db.close()

from app.services.document_retrieval_service import retrieve_context

def test_retrieve_context_parent_child_best_effort_tracks_orphan_children() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        orphan_child = create_chunk(
            db,
            document_id=document.id,
            chunk_type="child",
            content="retrieval keyword but missing parent.",
            chunk_index=0,
        )

        retriever = FakeLexicalRetriever(
            hits=[
                ChunkHit(
                    chunk=orphan_child,
                    score=7.0,
                    raw_score=7.0,
                    rank=1,
                    retrieval_source="bm25",
                )
            ]
        )

        result = retrieve_context(
            db=db,
            query="retrieval",
            document_ids=[document.id],
            mode="parent_child",
            strategy="bm25",
            lexical_retriever=retriever,
            top_k=5,
        )

        assert result.candidates == []
        assert result.trace.sources == ["bm25"]
        assert result.trace.source_hit_counts == {"bm25": 1}
        assert result.trace.dropped_hit_counts.get("orphan_child") == 1
        assert retriever.calls[0]["chunk_type"] == "child"

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_retrieve_context_normal_mode_with_vector_strategy() -> None:
    """
    验证 retrieve_context 支持 normal + vector。

    这个测试不是测 pgvector 底层查询。
    pgvector 已经由 test_vector_retrieval.py 覆盖。

    这里测的是：
    - vector hit 能进入 retrieval pipeline
    - normal mode 能把 hit 转成 ContextCandidate
    - trace 能正确记录 source
    """
    db = create_test_session()
    document = create_test_document(db)
    provider = DeterministicEmbeddingProvider(dimensions=settings.embedding_dimensions)

    try:
        target_text = "机器人无法充电时，需要检查充电底座和电源。"

        target_chunk = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content=target_text,
            chunk_index=0,
            embedding_model=provider.model_name,
            embedding=provider.embed_query(target_text),
            embedding_dimensions=provider.dimensions,
        )

        result = retrieve_context(
            db=db,
            query=target_text,
            document_ids=[document.id],
            mode="normal",
            strategy="vector",
            embedding_provider=provider,
            top_k=5,
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].citation_chunk.id == target_chunk.id
        assert result.candidates[0].context_chunk.id == target_chunk.id
        assert result.candidates[0].retrieval_mode == "normal"
        assert result.candidates[0].retrieval_source == "vector"

        assert result.trace.sources == ["vector"]
        assert result.trace.total_hits == 1
        assert result.trace.used_hits == 1
        assert result.trace.source_hit_counts == {"vector": 1}

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_retrieve_context_parent_child_mode_with_vector_strategy_backfills_parent() -> None:
    """
    验证 parent_child + vector。

    这个测试覆盖的是完整 retrieval pipeline：
    - vector 检索 child chunk
    - 根据 child.parent_id 回填 parent chunk
    - parent 作为 context_chunk
    - child 作为 citation_chunk
    - trace 正确记录 vector source

    注意：
    pgvector 底层查询已经由 test_vector_retrieval.py 覆盖。
    这里测试的是“vector hit 如何进入父子 chunk 流程”。
    """
    db = create_test_session()
    document = create_test_document(db)
    provider = DeterministicEmbeddingProvider(dimensions=settings.embedding_dimensions)

    try:
        parent = create_chunk(
            db,
            document_id=document.id,
            chunk_type="parent",
            content="机器人充电故障排查完整说明：检查电源、底座、金属触点和摆放位置。",
            chunk_index=0,
        )

        child_text = "机器人无法充电时，需要检查充电底座和电源。"

        child = create_chunk(
            db,
            document_id=document.id,
            chunk_type="child",
            content=child_text,
            chunk_index=1,
            parent_id=parent.id,
            embedding_model=provider.model_name,
            embedding=provider.embed_query(child_text),
            embedding_dimensions=provider.dimensions,
        )

        result = retrieve_context(
            db=db,
            query=child_text,
            document_ids=[document.id],
            mode="parent_child",
            strategy="vector",
            embedding_provider=provider,
            top_k=5,
        )

        assert len(result.candidates) == 1

        candidate = result.candidates[0]

        assert candidate.retrieval_mode == "parent_child"
        assert candidate.retrieval_source == "vector"

        # 父子 chunk 的核心语义：
        # context 用 parent，citation 用 child。
        assert candidate.context_chunk.id == parent.id
        assert candidate.citation_chunk.id == child.id

        assert result.trace.sources == ["vector"]
        assert result.trace.total_hits == 1
        assert result.trace.used_hits == 1
        assert result.trace.source_hit_counts == {"vector": 1}
        assert result.trace.dropped_hit_counts == {}
    finally:
        cleanup_test_document(db, document)
        db.close()

class FakeLexicalRetriever:
    """
    用 fake retriever 测 retrieval pipeline。

    这里不测试 OpenSearch query body；那个由 test_lexical_store.py 覆盖。
    这里测试的是：
    - retrieve_context 是否调用了 lexical_retriever
    - normal 模式是否检索 normal chunk
    - parent_child 模式是否检索 child chunk
    - BM25 hits 是否能进入 candidate normalization / parent backfill
    """

    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def search(
        self,
        db,
        *,
        query,
        chunk_type,
        document_ids,
        top_k,
    ):
        self.calls.append(
            {
                "query": query,
                "chunk_type": chunk_type,
                "document_ids": document_ids,
                "top_k": top_k,
            }
        )
        return self.hits


def test_retrieve_context_normal_mode_with_bm25_strategy() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        chunk = create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="机器人无法充电时，需要检查充电底座。",
            chunk_index=0,
        )

        retriever = FakeLexicalRetriever(
            hits=[
                ChunkHit(
                    chunk=chunk,
                    score=12.5,
                    raw_score=12.5,
                    rank=1,
                    retrieval_source="bm25",
                )
            ]
        )

        result = retrieve_context(
            db=db,
            query="机器人 充电",
            document_ids=[document.id],
            mode="normal",
            strategy="bm25",
            lexical_retriever=retriever,
            top_k=5,
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].context_chunk.id == chunk.id
        assert result.candidates[0].citation_chunk.id == chunk.id
        assert result.candidates[0].retrieval_mode == "normal"
        assert result.candidates[0].retrieval_source == "bm25"
        assert result.candidates[0].rank == 1

        assert result.trace.sources == ["bm25"]
        assert result.trace.total_hits == 1
        assert result.trace.used_hits == 1
        assert result.trace.source_hit_counts == {"bm25": 1}

        assert retriever.calls[0]["chunk_type"] == "normal"

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_retrieve_context_parent_child_mode_with_bm25_strategy_backfills_parent() -> None:
    db = create_test_session()
    document = create_test_document(db)

    try:
        parent = create_chunk(
            db,
            document_id=document.id,
            chunk_type="parent",
            content="机器人充电故障排查完整说明。",
            chunk_index=0,
        )

        child = create_chunk(
            db,
            document_id=document.id,
            chunk_type="child",
            content="机器人无法充电，需要检查充电底座。",
            chunk_index=1,
            parent_id=parent.id,
        )

        retriever = FakeLexicalRetriever(
            hits=[
                ChunkHit(
                    chunk=child,
                    score=10.0,
                    raw_score=10.0,
                    rank=1,
                    retrieval_source="bm25",
                )
            ]
        )

        result = retrieve_context(
            db=db,
            query="机器人 充电",
            document_ids=[document.id],
            mode="parent_child",
            strategy="bm25",
            lexical_retriever=retriever,
            top_k=5,
        )

        assert len(result.candidates) == 1

        candidate = result.candidates[0]
        assert candidate.context_chunk.id == parent.id
        assert candidate.citation_chunk.id == child.id
        assert candidate.retrieval_mode == "parent_child"
        assert candidate.retrieval_source == "bm25"
        assert candidate.rank == 1

        assert result.trace.sources == ["bm25"]
        assert result.trace.source_hit_counts == {"bm25": 1}
        assert result.trace.dropped_hit_counts == {}

        assert retriever.calls[0]["chunk_type"] == "child"

    finally:
        cleanup_test_document(db, document)
        db.close()

def test_retrieve_context_bm25_strategy_requires_lexical_retriever() -> None:
    db = create_test_session()

    try:
        try:
            retrieve_context(
                db=db,
                query="机器人",
                mode="normal",
                strategy="bm25",
                lexical_retriever=None,
            )
        except ValueError as exc:
            assert "lexical_retriever is required" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    finally:
        db.close()