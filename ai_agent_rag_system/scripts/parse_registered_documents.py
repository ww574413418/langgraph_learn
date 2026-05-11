'''
这个脚本的目标：
从 documents 表里找 status = uploaded 的文档
逐个调用 save_parsed_assets()
成功后变 parsed
失败后变 failed
'''

import argparse
from app.db import base
from sqlalchemy import select
from app.db.session import  SessionLocal
from app.models.document import Document
from app.services.document_parse_service import save_parsed_assets


def parse_uploaded_documents(limit:int|None = None) ->None:
    db = SessionLocal()

    try:
        statement = (
            select(Document).
            where(Document.status=="uploaded")
            .order_by(Document.created_at.asc()))

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

    return parser.parse_args()


def main() ->None:
    args = parse_args()
    parse_uploaded_documents(limit=args.limit)

if __name__ == '__main__':
    main()

