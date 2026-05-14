from pathlib import Path
import hashlib

from sqlalchemy.orm import Session
from app.models.document import Document
from app.rag.loaders import load_document
from app.rag.splitters import split_normal_chunks
from app.schemas.document_chunk import DocumentChunkCreate
from app.services.document_chunk_service import DocumentChunkCreate
from app.services.document_chunk_service import chunk_exist,create_document_chunk


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def index_document_normal_chunks(
        db:Session,
        document:Document,
        chunk_size:int = 1000,
        chunk_overlap:int = 120
) -> None:
    try:
        document.status = "chunking"
        db.add(document)
        db.commit()

        parsed_document = load_document(Path(document.file_path))

        chunks = split_normal_chunks(
            parsed_document.text,
            file_type=document.file_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in chunks:
            content_hash = calculate_content_hash(chunk.content)

            if chunk_exist(db,document_id=document.id,content_hash=content_hash,
                           chunk_index=chunk.chunk_index,chunk_type="normal"):
                print(f"SKIP existing chunk:{chunk.chunk_index}")
                continue

            create_document_chunk(
                db,
                data=DocumentChunkCreate(
                    document_id=document.id,
                    parent_id=None,
                    chunk_type="normal",
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=content_hash,
                    token_count=len(chunk.content),
                    char_count=len(chunk.content),
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    embedding_model=None,
                    extra_metadata={
                        **chunk.metadata,
                        "chunk_size":chunk_size,
                        "chunk_overlap":chunk_overlap,
                    }
                )
            )

            document.status = "indexed"
            document.error_message = None
            db.add(document)
            db.commit()
            db.refresh( document)
    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise
