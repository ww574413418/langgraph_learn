# tests/test_vector_retrieval.py
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.rag.embeddings import DeterministicEmbeddingProvider
from app.rag.vector_store import search_chunks_by_vector
from app.schemas.document_chunk import DocumentChunkCreate
from app.services.document_chunk_service import create_document_chunk
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings


def create_test_session() -> Session:
    """
    创建数据库 Session。

    这里复用项目真实 database_url，
    因为当前项目的旧测试也是这种写法。
    """
    engine = create_engine(settings.database_url)
    return Session(engine)


def create_test_document(db: Session) -> Document:
    """
    测试辅助函数：创建一个 indexed document。
    真实项目里可以放到 fixture 中复用。
    """
    marker = str(uuid4())

    kb = KnowledgeBase(
        name=f"vector-kb-{marker}",
        description="vector retrieval test",
        domain="test",
        status="active",
        extra_metadata={"test_marker": marker},
        retrieval_config={},
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    document = Document(
        knowledge_base_id=kb.id,
        filename=f"vector-{marker}.txt",
        file_type="txt",
        file_path=f"data/vector-{marker}.txt",
        file_hash=f"vector-hash-{marker}",
        status="indexed",
        extra_metadata={"test_marker": marker},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def test_vector_search_returns_matching_chunk() -> None:
    db = create_test_session()
    provider = DeterministicEmbeddingProvider(dimensions=settings.embedding_dimensions)
    document = create_test_document(db)

    try:
        target_text = "机器人无法充电时，需要检查充电底座和电源。"
        unrelated_text = "拖布清洗需要定期更换清洁液。"

        target_chunk = create_document_chunk(
            db,
            data=DocumentChunkCreate(
                document_id=document.id,
                parent_id=None,
                chunk_type="normal",
                chunk_index=0,
                content=target_text,
                content_hash=f"hash-{uuid4()}",
                token_count=len(target_text),
                char_count=len(target_text),
                embedding_model=provider.model_name,
                embedding=provider.embed_query(target_text),
                embedding_dimensions=provider.dimensions,
                extra_metadata={"source": "test"},
            ),
        )

        create_document_chunk(
            db,
            data=DocumentChunkCreate(
                document_id=document.id,
                parent_id=None,
                chunk_type="normal",
                chunk_index=1,
                content=unrelated_text,
                content_hash=f"hash-{uuid4()}",
                token_count=len(unrelated_text),
                char_count=len(unrelated_text),
                embedding_model=provider.model_name,
                embedding=provider.embed_query(unrelated_text),
                embedding_dimensions=provider.dimensions,
                extra_metadata={"source": "test"},
            ),
        )

        hits = search_chunks_by_vector(
            db=db,
            query_embedding=provider.embed_query(target_text),
            chunk_type="normal",
            embedding_model=provider.model_name,
            embedding_dimensions=provider.dimensions,
            document_ids=[document.id],
            top_k=5,
        )

        assert hits[0].chunk.id == target_chunk.id
        assert hits[0].retrieval_source == "vector"
        assert hits[0].rank == 1
        assert hits[0].raw_score is not None
        assert hits[0].normalized_score is not None

    finally:
        db.close()
