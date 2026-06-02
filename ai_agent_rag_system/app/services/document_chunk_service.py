from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.document_chunk import DocumentChunkCreate

def create_document_chunk(
        db:Session,
        data:DocumentChunkCreate,
)->DocumentChunk:
    # 业务层必须先验证 document 是否存在。
    # 不要等数据库外键报错，因为数据库错误对 API 和测试都不友好。
    document = db.get(Document, data.document_id)

    if document is None:
        raise ValueError("Document not found")

    # 如果是 child chunk，必须确认 parent 存在且属于同一篇文档。
    # 这是父子 chunk 的数据一致性边界。
    if data.parent_id is not None:
        parent = db.get(DocumentChunk,data.parent_id)

        if parent is None:
            raise ValueError("Parent document chunk not found")

        if parent.document_id != data.document_id:
            raise ValueError("Parent document chunk does not belong to the same document")

    chunk = DocumentChunk(
        document_id=data.document_id,
        parent_id=data.parent_id,
        chunk_type=data.chunk_type,
        chunk_index=data.chunk_index,
        content=data.content,
        content_hash=data.content_hash,
        token_count=data.token_count,
        char_count=data.char_count,
        start_char=data.start_char,
        end_char=data.end_char,
        # embedding 相关字段必须和 chunk 同时入库，避免出现“文本已索引但无法向量检索”的半成品状态。
        embedding_model=data.embedding_model,
        embedding=data.embedding,
        embedding_dimensions=data.embedding_dimensions,
        extra_metadata=data.extra_metadata,
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk

def list_document_chunks(
        db:Session,
        document:UUID,
        chunk_type:str|None = None
)->list[DocumentChunk]:
    statement = (
        select(DocumentChunk).where(DocumentChunk.document_id==document).
        order_by(DocumentChunk.chunk_index.asc())
    )

    if chunk_type is not None:
        statement = statement.where(DocumentChunk.chunk_type==chunk_type)

    result = db.execute(statement)
    return list(result.scalars().all())

def get_document_chunk(
        db:Session,
        chunk_id:UUID
) -> DocumentChunk:
    return db.get(DocumentChunk,chunk_id)


# 直接复用get_existing_chunk 判断chunk在不在
def chunk_exist(
    db: Session,
    document_id: UUID,
    content_hash: str,
    chunk_index: int,
    chunk_type: str,
    parent_id: UUID | None = None,
) -> bool:
    return (
        get_existing_chunk(
            db=db,
            document_id=document_id,
            content_hash=content_hash,
            chunk_index=chunk_index,
            chunk_type=chunk_type,
            parent_id=parent_id,
        )
        is not None
    )


def get_existing_chunk(
    db: Session,
    document_id: UUID,
    content_hash: str,
    chunk_index: int,
    chunk_type: str,
    parent_id: UUID | None = None,
) -> DocumentChunk | None:
    statement = select(DocumentChunk).where(
        DocumentChunk.document_id == document_id,
        DocumentChunk.content_hash == content_hash,
        DocumentChunk.chunk_type == chunk_type,
        DocumentChunk.chunk_index == chunk_index,
    )

    if parent_id is None:
        statement = statement.where(DocumentChunk.parent_id.is_(None))
    else:
        statement = statement.where(DocumentChunk.parent_id == parent_id)

    result = db.execute(statement)
    return result.scalar_one_or_none()
