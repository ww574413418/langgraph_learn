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
from app.rag.rerankers import SiliconFlowReranker
from app.services.retrieval_service import build_reranker_for_request


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

def test_retrieval_request_accepts_bm25_strategy() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="bm25",
        top_k=5,
        task_type="qa",
    )

    assert request.strategy == "bm25"


def test_retrieval_request_defaults_to_no_rerank() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="bm25",
    )

    assert request.rerank_mode == "none"

from pydantic import ValidationError
from app.schemas.retrieval import RetrievalRequest


def test_retrieval_request_accepts_supported_rerank_mode() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="bm25",
        rerank_mode="none",
    )

    assert request.rerank_mode == "none"


def test_retrieval_request_rejects_unknown_rerank_mode() -> None:
    try:
        RetrievalRequest(
            query="retrieval",
            mode="normal",
            strategy="bm25",
            rerank_mode="unknown",
        )
    except ValidationError:
        return

    raise AssertionError("Expected ValidationError")

def test_retrieval_request_accepts_siliconflow_rerank_mode() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="bm25",
        rerank_mode="siliconflow",
    )

    assert request.rerank_mode == "siliconflow"


def test_retrieval_request_accepts_candidate_pool_top_k_controls() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="hybrid",
        top_k=5,
        retrieval_top_k=20,
        rerank_top_k=10,
        context_top_k=3,
    )

    assert request.top_k == 5
    assert request.retrieval_top_k == 20
    assert request.rerank_top_k == 10
    assert request.context_top_k == 3


def test_build_reranker_for_request_returns_siliconflow_reranker() -> None:
    request = RetrievalRequest(
        query="retrieval",
        mode="normal",
        strategy="bm25",
        rerank_mode="siliconflow",
    )

    reranker = build_reranker_for_request(request)

    assert isinstance(reranker, SiliconFlowReranker)
    assert reranker.name == "siliconflow-reranker"
