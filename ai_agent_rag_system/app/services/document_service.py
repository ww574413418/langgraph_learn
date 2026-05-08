from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.knowledge_base import KnowledgeBase
from app.schemas.document import DocumentRead,DocumentCreate

def create_document(db:Session,data:DocumentCreate)->Document:
    knowledge_base = db.get(KnowledgeBase,data.knowledge_base_id)

    if knowledge_base is None:
        raise ValueError("Knowledge base not found")


    document = Document(
        knowledge_base_id=data.knowledge_base_id,
        filename=data.filename,
        file_type=data.file_type,
        file_path=data.file_path,
        file_hash=data.file_hash,
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db:Session,
                   knowledge_base_id:UUID)->list[Document]:
    statement = select(Document).order_by(Document.created_at.desc())

    if knowledge_base_id is not None:
        statement = statement.where(Document.knowledge_base_id==knowledge_base_id)

    result = db.execute(statement)
    return list(result.scalars().all())


def get_document(db:Session,document_id:UUID)->Document | None:
    return db.get(Document,document_id)

