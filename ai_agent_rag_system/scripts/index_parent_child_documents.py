"""
从 documents 表里找 status = parsed 的文档，
逐个调用 index_document_parent_child_chunks()。

父子 chunk 索引规则：
- parent chunk 是上下文单元，不写 embedding。
- child chunk 是召回单元，写 embedding / embedding_model / embedding_dimensions。
- 成功后 document.status = indexed。
- 失败后 document.status = failed，并记录 error_message。
"""

import argparse
from uuid import UUID

from sqlalchemy import select

from app.db import base  # noqa: F401
from app.db.session import SessionLocal
from app.models.document import Document
from app.rag.embeddings import create_embedding_provider
from app.services.document_indexing_service import index_document_parent_child_chunks


def index_parent_child_documents(
    limit: int | None = None,
    document_ids: list[UUID] | None = None,
    parent_chunk_size: int = 1800,
    parent_chunk_overlap: int = 120,
    child_chunk_size: int = 400,
    child_chunk_overlap: int = 80,
) -> None:
    """
    批量执行 parent-child chunk 索引。

    参数设计和 normal chunk 脚本保持一致：
    - limit 控制本次最多处理多少文档。
    - chunk size / overlap 控制切片策略。

    额外支持 document_ids：
    - 生产排障时可以只重跑某一个文档。
    - 测试时不会误处理数据库里其它 parsed 文档。
    """
    db = SessionLocal()
    embedding_provider = create_embedding_provider()

    try:
        statement = (
            select(Document)
            .where(Document.status == "parsed")
            .order_by(Document.created_at.asc())
        )

        if document_ids is not None:
            statement = statement.where(Document.id.in_(document_ids))

        if limit is not None:
            statement = statement.limit(limit)

        documents = list(db.execute(statement).scalars().all())

        for document in documents:
            print(f"indexing parent_child:{document.id} {document.file_path}")

            try:
                index_document_parent_child_chunks(
                    db=db,
                    document=document,
                    embedding_provider=embedding_provider,
                    parent_chunk_size=parent_chunk_size,
                    parent_chunk_overlap=parent_chunk_overlap,
                    child_chunk_size=child_chunk_size,
                    child_chunk_overlap=child_chunk_overlap,
                )

                print(f"indexed parent_child:{document.id} {document.file_path}")
            except Exception as exc:
                db.rollback()
                document.status = "failed"
                document.error_message = str(exc)
                db.add(document)
                db.commit()
                print(f"FAILED parent_child:{document.id} {document.file_path} {exc}")

    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index parsed documents with parent-child chunks."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="limit number of documents to index",
    )
    parser.add_argument(
        "--document-id",
        action="append",
        default=None,
        help="only index this document id; can be passed multiple times",
    )
    parser.add_argument("--parent-chunk-size", type=int, default=1800)
    parser.add_argument("--parent-chunk-overlap", type=int, default=120)
    parser.add_argument("--child-chunk-size", type=int, default=400)
    parser.add_argument("--child-chunk-overlap", type=int, default=80)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    document_ids = (
        [UUID(document_id) for document_id in args.document_id]
        if args.document_id is not None
        else None
    )

    index_parent_child_documents(
        limit=args.limit,
        document_ids=document_ids,
        parent_chunk_size=args.parent_chunk_size,
        parent_chunk_overlap=args.parent_chunk_overlap,
        child_chunk_size=args.child_chunk_size,
        child_chunk_overlap=args.child_chunk_overlap,
    )


if __name__ == "__main__":
    main()
