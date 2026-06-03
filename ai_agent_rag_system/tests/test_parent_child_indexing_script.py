from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.rag.embeddings import DeterministicEmbeddingProvider


def create_test_session() -> Session:
    engine = create_engine(settings.database_url)
    return Session(engine)


def create_test_document_file(tmp_path: Path) -> Path:
    file_path = tmp_path / f"script-parent-child-{uuid4()}.txt"
    file_path.write_text(
        (
            "机器人无法充电时，需要检查充电底座、电源适配器和金属触点。\n\n"
            "机器人无法回充时，需要检查底座摆放位置、地图路径和障碍物。"
        ),
        encoding="utf-8",
    )
    return file_path


def create_test_document(db: Session, file_path: Path) -> Document:
    marker = str(uuid4())

    kb = KnowledgeBase(
        name=f"script-parent-child-kb-{marker}",
        description="script parent child indexing test",
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
        filename=file_path.name,
        file_type="txt",
        file_path=str(file_path),
        file_hash=f"script-parent-child-hash-{marker}",
        status="parsed",
        extra_metadata={"test_marker": marker},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def cleanup_test_document(db: Session, document_id: UUID, knowledge_base_id: UUID) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.query(Document).filter(Document.id == document_id).delete()
    db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).delete()
    db.commit()


def test_parent_child_indexing_script_indexes_selected_parsed_document(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    脚本层测试：

    - 从 documents 表中选择 parsed 文档
    - 调用 parent-child indexing service
    - parent chunk 不写 embedding
    - child chunk 写 embedding
    - 文档状态变 indexed
    """
    import scripts.index_parent_child_documents as script

    db = create_test_session()
    file_path = create_test_document_file(tmp_path)
    document = create_test_document(db, file_path)
    document_id = document.id
    knowledge_base_id = document.knowledge_base_id

    provider = DeterministicEmbeddingProvider(
        dimensions=settings.embedding_dimensions,
    )
    monkeypatch.setattr(script, "create_embedding_provider", lambda: provider)

    try:
        script.index_parent_child_documents(
            limit=1,
            document_ids=[document_id],
            parent_chunk_size=120,
            parent_chunk_overlap=0,
            child_chunk_size=60,
            child_chunk_overlap=0,
        )

        db.expire_all()

        indexed_document = db.get(Document, document_id)
        assert indexed_document is not None
        assert indexed_document.status == "indexed"

        parents = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_type == "parent",
            )
            .all()
        )
        children = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_type == "child",
            )
            .all()
        )

        assert len(parents) >= 1
        assert len(children) >= 1
        assert all(parent.embedding is None for parent in parents)
        assert all(child.embedding is not None for child in children)
        assert all(child.embedding_model == provider.model_name for child in children)
        assert all(child.embedding_dimensions == provider.dimensions for child in children)

    finally:
        cleanup_test_document(db, document_id, knowledge_base_id)
        db.close()
