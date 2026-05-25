from uuid import uuid4


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.services.document_retrieval_service import (
    calculate_keyword_score,
    search_chunks_by_keyword,
)

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
) -> DocumentChunk:
    chunk = DocumentChunk(
        id=uuid4(),
        document_id=document_id,
        parent_id=None,
        chunk_type=chunk_type,
        chunk_index=chunk_index,
        content=content,
        content_hash=f"keyword-test-hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        start_char=0,
        end_char=len(content),
        embedding_model=None,
        extra_metadata={},
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