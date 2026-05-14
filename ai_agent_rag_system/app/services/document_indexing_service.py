from pathlib import Path
import hashlib

from sqlalchemy.orm import Session
from app.models.document import Document
from app.rag.loaders import load_document
from app.rag.splitters import split_normal_chunks,split_parent_child_chunks
from app.services.document_chunk_service import DocumentChunkCreate, get_existing_chunk
from app.services.document_chunk_service import chunk_exist,create_document_chunk


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

# 将chunk文档存入数据库
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
        db.rollback()
        document.status = "failed"
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise

# 将父子 chunk保存到数据库中
def index_document_parent_child_chunks(
        db:Session,
        document:Document,
        parent_chunk_size:int = 1800,
        parent_chunk_overlap:int = 120,
        child_chunk_size:int = 400,
        child_chunk_overlap:int = 80
)->None:
    try:
        # 先更新文档的状态
        document.status = "chunking"
        db.add(document)
        db.commit()
        # 拿到处理过的文本
        parsed_document = load_document(Path(document.file_path))
        # 进行父子切片
        parent_child_splits = split_parent_child_chunks(
            text=parsed_document.text,
            file_type=document.file_type,
            parent_chunk_size=parent_chunk_size,
            parent_chunk_overlap=parent_chunk_overlap,
            child_chunk_size=child_chunk_size,
            child_chunk_overlap=child_chunk_overlap,
        )

        # 遍历切片,拿到parent和child
        for split in parent_child_splits:
            parent = split.parent

            parent_content_hash = calculate_content_hash(parent.content)

            # 查看 parent 是否存在
            parent_chunk = get_existing_chunk(
                db=db,
                document_id=document.id,
                content_hash=parent_content_hash,
                chunk_index=parent.chunk_index,
                chunk_type="parent",
                parent_id=None,
            )

            # 如果不存在,保存
            if parent_chunk is None:
                # 保存parent chunk
                parent_chunk = create_document_chunk(
                    db,
                    data=DocumentChunkCreate(
                        document_id=document.id,
                        parent_id=None,
                        chunk_type="parent",
                        chunk_index=parent.chunk_index,
                        content=parent.content,
                        content_hash=parent_content_hash,
                        token_count=len(parent.content),
                        char_count=len(parent.content),
                        start_char=parent.start_char,
                        end_char=parent.end_char,
                        embedding_model=None,
                        extra_metadata={
                            **parent.metadata,
                            "parent_chunk_size":parent_chunk_size,
                            "parent_chunk_overlap":parent_chunk_overlap,
                        }
                    )
                )
            # 这里不 continue 因为还要处理child
            else:
                print(f"SKIP existing parent chunk:{parent.chunk_index}")

            # 拿到child chunk
            for child in split.children:
                child_content_hash = calculate_content_hash(child.content)

                # 如果 chunk 已经处理过
                if chunk_exist(
                        db=db,
                        document_id=document.id,
                        content_hash=child_content_hash,
                        chunk_index=child.chunk_index,
                        chunk_type="child",
                        parent_id=parent_chunk.id,
                ):
                    print(f"SKIP existing child chunk:{parent.chunk_index}.{child.chunk_index}")
                    continue

                # 将 child chunk保存到数据库
                child_chunk = create_document_chunk(
                    db,
                    data=DocumentChunkCreate(
                        document_id=document.id,
                        parent_id=parent_chunk.id,
                        chunk_type="child",
                        chunk_index=child.chunk_index,
                        content=child.content,
                        content_hash=child_content_hash,
                        token_count=len(child.content),
                        char_count=len(child.content),
                        start_char=child.start_char,
                        end_char=child.end_char,
                        embedding_model=None,
                        extra_metadata={
                            **child.metadata,
                            "parent_chunk_index": parent.chunk_index,
                            "parent_chunk_size": parent_chunk_size,
                            "parent_chunk_overlap": parent_chunk_overlap,
                            "child_chunk_size": child_chunk_size,
                            "child_chunk_overlap": child_chunk_overlap,
                        }
                    )
                )

        # 更新文档状态
        document.status = "indexed"
        document.error_message = None
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception as exc:
        db.rollback()
        document.status = "failed"
        document.error_message = str(exc)
        db.add(document)
        db.commit()
        raise
