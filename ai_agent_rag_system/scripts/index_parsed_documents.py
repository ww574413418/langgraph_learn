'''
从 documents 表里找 status = parsed 的文档
逐个调用 index_document_normal_chunks()
成功后文档变 indexed
失败后文档变 failed，并记录 error_message
'''

import argparse
from app.db import base # noqa: F401
from sqlalchemy import select
from app.db.session import  SessionLocal
from app.models.document import Document
from app.services.document_indexing_service import index_document_normal_chunks


def index_parsed_documents(limit: int | None = None,
                           chunk_size: int = 800,
                           chunk_overlap: int = 120,) -> None:
    db = SessionLocal()

    try:
        statement = select(Document).where(Document.status=="parsed").order_by(Document.created_at.asc())

        if limit is not None:
            statement = statement.limit(limit)

        documents = list(db.execute(statement).scalars().all())

        for document in documents:
            print(f"indexing:{document.id} {document.file_path}")

            try:
                index_document_normal_chunks(db=db,
                                             document=document,
                                             chunk_size=chunk_size,
                                             chunk_overlap=chunk_overlap)

                print(f"indexed:{document.id} {document.file_path}")
            except Exception as exc:
                db.rollback()
                document.status = "failed"
                document.error_message = str(exc)
                db.add(document)
                db.commit()
                print(f"FAILED:{document.id} {document.file_path} {exc}")


    finally:
        db.close()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index parsed documents."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="limit number of documents to index"
    )
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)

    return parser.parse_args()

def main() -> None:
    args = parse_args()
    index_parsed_documents(limit=args.limit,
                           chunk_size=args.chunk_size,
                           chunk_overlap=args.chunk_overlap)

if __name__ == "__main__":
    main()
