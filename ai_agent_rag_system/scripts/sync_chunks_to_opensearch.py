from opensearchpy import OpenSearch, helpers
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def extract_section_title(extra_metadata: dict | None) -> str:
    if not extra_metadata:
        return ""

    return (
        extra_metadata.get("section_title")
        or extra_metadata.get("heading")
        or extra_metadata.get("parent_heading")
        or ""
    )


def main() -> None:
    """
    把 PostgreSQL 中已 indexed 文档的 chunks 同步到 OpenSearch。

    PostgreSQL 是 source of truth。
    OpenSearch 只是 lexical retrieval index。
    """
    client = OpenSearch(hosts=[settings.opensearch_url])
    db = SessionLocal()

    try:
        stmt = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.status == "indexed")
        )

        rows = db.execute(stmt).all()
        actions = []

        for chunk, document in rows:
            actions.append(
                {
                    "_index": settings.opensearch_chunks_index,
                    "_id": str(chunk.id),
                    "_source": {
                        "chunk_id": str(chunk.id),
                        "document_id": str(chunk.document_id),
                        "parent_id": str(chunk.parent_id) if chunk.parent_id else None,
                        "chunk_type": chunk.chunk_type,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "filename": document.filename,
                        "section_title": extract_section_title(chunk.extra_metadata),
                        "content_hash": chunk.content_hash,
                        "token_count": chunk.token_count,
                        "char_count": chunk.char_count,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "extra_metadata": chunk.extra_metadata or {},
                    },
                }
            )

        if not actions:
            print("no chunks to sync")
            return

        success, errors = helpers.bulk(
            client,
            actions,
            raise_on_error=False,
        )

        print(f"synced chunks: {success}")

        if errors:
            print(f"errors: {errors[:3]}")

    finally:
        db.close()


if __name__ == "__main__":
    main()