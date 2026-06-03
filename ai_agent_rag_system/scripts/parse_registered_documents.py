'''
这个脚本的目标：
从 documents 表里找 status = uploaded 的文档
逐个调用 save_parsed_assets()
成功后变 parsed
失败后变 failed
'''

import argparse
from uuid import UUID

from app.db import base
from sqlalchemy import select
from app.db.session import  SessionLocal
from app.models.document import Document
from app.services.document_parse_service import save_parsed_assets


def parse_uploaded_documents(
    limit:int|None = None,
    document_ids: list[UUID] | None = None,
) ->None:
    """
    解析 uploaded 文档并保存解析资产。

    document_ids 是生产排障和本地验证常用的精准过滤：
    - 不传时：保持旧行为，批量处理所有 uploaded 文档。
    - 传入时：只处理指定 id 且 status = uploaded 的文档。
    """
    db = SessionLocal()

    try:
        statement = (
            select(Document).
            where(Document.status=="uploaded")
            .order_by(Document.created_at.asc()))

        if document_ids is not None:
            statement = statement.where(Document.id.in_(document_ids))

        # 调试时不要一次处理太多。
        if limit is not None:
            statement = statement.limit(limit)

        documents = list(db.execute(statement).scalars().all())

        for document in documents:
            print(f"PARSING:{document.id} {document.file_path}")

            try:
                save_parsed_assets(db=db,document=document)
                print(f"PARSED:{document.id} {document.file_path}")

            except Exception as exc:
                document.status = "failed"
                document.error_message = str(exc)
                db.add(document)
                db.commit()
                print(f"FAILD:{document.id} {document.file_path} {exc}")

    finally:
        db.close()

def parse_args() ->argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse uploaded documents and save discovered assets."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="limit number of documents to parse"
    )
    parser.add_argument(
        "--document-id",
        action="append",
        default=None,
        help="only parse this document id; can be passed multiple times",
    )

    return parser.parse_args()


def main() ->None:
    args = parse_args()

    document_ids = (
        [UUID(document_id) for document_id in args.document_id]
        if args.document_id is not None
        else None
    )

    parse_uploaded_documents(
        limit=args.limit,
        document_ids=document_ids,
    )

if __name__ == '__main__':
    main()
