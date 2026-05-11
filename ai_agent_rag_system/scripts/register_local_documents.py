from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import select
import hashlib
from app.models.document import Document
from app.services.document_service import create_document
from app.schemas.document import DocumentCreate
from app.db.session import SessionLocal
import argparse

'''
用于解析文件
1.将文件计算hash值
2.如果hash不重复,将文件名,类型,路径保存到document表中
'''
SUPPORTED_FILE_TYPES = {"txt", "md", "pdf", "docx"}

def calculate_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

def detect_file_type(file_path: Path) -> str:
    return file_path.suffix.lower().lstrip(".")


def iter_files(data_dir: Path) -> list[Path]:
    files:list[Path] = []

    # .rglob("*")递归扫描目录下的所有文件
    for file_path in data_dir.rglob("*"):
        if not file_path.is_file():
            continue

        file_type = detect_file_type(file_path)

        if file_type not in SUPPORTED_FILE_TYPES:
            continue

        files.append(file_path)

    return sorted(files)

def document_exists(db: Session, file_hash: str) -> bool:
    '''
    检查文件是否已经被处理过了
    :param db:
    :param file_hash:
    :return:
    '''
    statement = select(Document.id).where(Document.file_hash == file_hash)
    result = db.execute(statement)
    return result.scalar_one_or_none() is not None

def register_documents(knowledge_base_id: UUID, data_dir: Path) -> None:
    db = SessionLocal()

    try:
        files = iter_files(data_dir)

        for file_path in files:
            file_hash = calculate_file_hash(file_path)

            if document_exists(db, file_hash):
                print(f"SKIP EXIST FILE:{file_path} {file_hash}")
                continue

            data = DocumentCreate(
                knowledge_base_id=knowledge_base_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_type=detect_file_type(file_path),
                file_hash=file_hash,
            )

            document = create_document(db, data)

            print(f"REGISTER:{document.id}{file_path}")
    finally:
        db.close()

def parse_args() -> argparse.Namespace:
    parse = argparse.ArgumentParser(
        description="register local files into documents table"
    )

    parse.add_argument(
        "--knowledge-base-id",
        required=True,
        help="knowledge base UUID"
    )

    parse.add_argument(
        "--data-dir",
        default="data",
        help="local data directory to scan"
    )

    return parse.parse_args()

def main() -> None:
    args = parse_args()
    register_documents(
        knowledge_base_id=UUID(args.knowledge_base_id),
        data_dir=Path(args.data_dir)
    )

if __name__ == '__main__':
    main()