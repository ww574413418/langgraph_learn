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
    document = db.get(Document,data.document_id)

    if document is None:
        raise ValueError("Document not found")

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
        embedding_model=data.embedding_model,
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


def chunk_exist(db:Session,
                document_id:UUID,
                content_hash:str,
                chunk_index:int,
                chunk_type:str) ->bool:
    statement = select(DocumentChunk.id).where(
        DocumentChunk.document_id==document_id,
        DocumentChunk.content_hash==content_hash,
        DocumentChunk.chunk_type == chunk_type,
        DocumentChunk.chunk_index==chunk_index
    )
    result = db.execute(statement)
    return result.scalar_one_or_none() is not None