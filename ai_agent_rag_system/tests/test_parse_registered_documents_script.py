from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_asset import DocumentAssets
from app.models.knowledge_base import KnowledgeBase


def create_test_session() -> Session:
    engine = create_engine(settings.database_url)
    return Session(engine)


def create_test_document_file(tmp_path: Path, name: str) -> Path:
    file_path = tmp_path / name
    file_path.write_text(
        "这是一个用于验证 uploaded 到 parsed 链路的测试文档。",
        encoding="utf-8",
    )
    return file_path


def create_test_document(db: Session, file_path: Path) -> Document:
    marker = str(uuid4())

    kb = KnowledgeBase(
        name=f"parse-script-kb-{marker}",
        description="parse script test",
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
        file_hash=f"parse-script-hash-{marker}",
        status="uploaded",
        extra_metadata={"test_marker": marker},
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def cleanup_test_documents(
    db: Session,
    document_ids: list[UUID],
    knowledge_base_ids: list[UUID],
) -> None:
    db.query(DocumentAssets).filter(DocumentAssets.document_id.in_(document_ids)).delete()
    db.query(Document).filter(Document.id.in_(document_ids)).delete()
    db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(knowledge_base_ids)).delete()
    db.commit()


def test_parse_registered_documents_script_parses_selected_uploaded_document(
    tmp_path: Path,
) -> None:
    """
    脚本层测试：

    - 只解析指定 document id。
    - 指定文档从 uploaded 变 parsed。
    - 未指定的 uploaded 文档保持 uploaded，避免脚本误处理其它文档。
    """
    import scripts.parse_registered_documents as script

    db = create_test_session()
    selected_file = create_test_document_file(tmp_path, "selected.txt")
    untouched_file = create_test_document_file(tmp_path, "untouched.txt")
    selected_document = create_test_document(db, selected_file)
    untouched_document = create_test_document(db, untouched_file)

    document_ids = [selected_document.id, untouched_document.id]
    knowledge_base_ids = [
        selected_document.knowledge_base_id,
        untouched_document.knowledge_base_id,
    ]

    try:
        script.parse_uploaded_documents(
            limit=1,
            document_ids=[selected_document.id],
        )

        db.expire_all()

        parsed_document = db.get(Document, selected_document.id)
        still_uploaded_document = db.get(Document, untouched_document.id)

        assert parsed_document is not None
        assert still_uploaded_document is not None

        assert parsed_document.status == "parsed"
        assert parsed_document.error_message is None

        assert still_uploaded_document.status == "uploaded"
        assert still_uploaded_document.error_message is None

    finally:
        cleanup_test_documents(db, document_ids, knowledge_base_ids)
        db.close()
