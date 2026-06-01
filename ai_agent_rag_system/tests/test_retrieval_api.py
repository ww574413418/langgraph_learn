from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase

def create_test_session() -> Session:
    engine = create_engine(settings.database_url)
    return Session(engine)

def override_get_db(db: Session):
    def _override():
        try:
            yield db
        finally:
            pass

    return _override

def create_test_document(db: Session) -> Document:
    marker = str(uuid4())

    knowledge_base = KnowledgeBase(
        name=f"retrieval-api-kb-{marker}",
        description="retrieval api test",
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
        filename=f"retrieval-api-{marker}.txt",
        file_type="txt",
        file_path=f"data/retrieval-api-{marker}.txt",
        file_hash=f"retrieval-api-hash-{marker}",
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
        content_hash=f"retrieval-api-chunk-hash-{uuid4()}",
        token_count=len(content),
        char_count=len(content),
        start_char=0,
        end_char=len(content),
        embedding_model=None,
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

def test_retrieval_api_returns_context_for_normal_chunk() -> None:
    db = create_test_session()
    document = create_test_document(db)

    app.dependency_overrides[get_db] = override_get_db(db)
    client = TestClient(app)

    try:
        create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="RAG retrieval API should return this chunk.",
            chunk_index=0,
        )

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
        assert len(data["citations"]) == 1
        assert data["citations"][0]["retrieval_mode"] == "normal"
        assert data["trace"]["sources"] == ["keyword"]
        assert data["trace"]["total_hits"] == 1

    finally:
        app.dependency_overrides.clear()
        cleanup_test_document(db, document)
        db.close()


def test_retrieval_api_empty_knowledge_base_scope_does_not_leak_other_documents() -> None:
    db = create_test_session()
    document = create_test_document(db)

    empty_knowledge_base = KnowledgeBase(
        name=f"empty-retrieval-api-kb-{uuid4()}",
        description="empty retrieval api test",
        domain="test",
        status="active",
        extra_metadata={"test_marker": str(uuid4())},
        retrieval_config={},
    )

    db.add(empty_knowledge_base)
    db.commit()
    db.refresh(empty_knowledge_base)

    app.dependency_overrides[get_db] = override_get_db(db)
    client = TestClient(app)

    try:
        create_chunk(
            db,
            document_id=document.id,
            chunk_type="normal",
            content="This retrieval chunk belongs to another knowledge base.",
            chunk_index=0,
        )

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

    finally:
        app.dependency_overrides.clear()
