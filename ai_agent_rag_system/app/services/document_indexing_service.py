from pathlib import Path
import hashlib

from sqlalchemy.orm import Session
from app.models.document import Document
from app.rag.loaders import load_document
from app.rag.splitters import split_normal_chunks,split_parent_child_chunks
from app.services.document_chunk_service import DocumentChunkCreate, get_existing_chunk
from app.services.document_chunk_service import chunk_exist,create_document_chunk
from app.rag.embeddings import EmbeddingProvider


def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

# 将chunk文档存入数据库
def index_document_normal_chunks(
        db:Session,
        document:Document,
        embedding_provider: EmbeddingProvider,
        chunk_size:int = 1000,
        chunk_overlap:int = 120
) -> None:
    """
        普通 chunk 索引。

        关键变化：
        - split 完之后批量生成 embedding
        - chunk 入库时保存 embedding_model / embedding_dimensions / embedding
        """
    try:
        document.status = "chunking"
        document.error_message = None
        db.add(document)
        db.commit()

        parsed_document = load_document(Path(document.file_path))


        chunks = split_normal_chunks(
            parsed_document.text,
            file_type=document.file_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # 2. 先筛出真正需要新建的 chunk。
        # 不要对已经存在的 chunk 重复调用 embedding API。
        # 真实 embedding API 是付费且慢的，重复 embedding 是生产事故级浪费。
        chunks_to_create = []

        for chunk in chunks:
            content_hash = calculate_content_hash(chunk.content)

            if chunk_exist(db,document_id=document.id,content_hash=content_hash,
                           chunk_index=chunk.chunk_index,chunk_type="normal"):
                print(f"SKIP existing chunk:{chunk.chunk_index}")
                continue

            chunks_to_create.append((chunk, content_hash))

        # 3. 只给新增 chunk 生成 embedding。
        # 如果没有新增 chunk，也应该把文档标记为 indexed。
        if chunks_to_create:
            texts = [chunk.content for chunk, _content_hash in chunks_to_create]
            embeddings = embedding_provider.embed_documents(texts)
        else:
            embeddings = []

        if len(embeddings) != len(chunks_to_create):
            raise RuntimeError("Embedding count does not match chunk count")

        for (chunk, content_hash),embedding in zip(
            chunks_to_create,
            embeddings,
            strict=True
        ):
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
                    # embedding 相关字段必须和 chunk 一起落库。
                    embedding_model=embedding_provider.model_name,
                    embedding=embedding,
                    embedding_dimensions=embedding_provider.dimensions,

                    extra_metadata={
                        **chunk.metadata,
                        "chunk_size":chunk_size,
                        "chunk_overlap":chunk_overlap,
                    }
                )
            )

        # 5. 无论本次是新增了 chunk，还是全部 skip，
        # 只要流程正常结束，文档都应该是 indexed。
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

# 将父子 chunk保存到数据库中
def index_document_parent_child_chunks(
        db:Session,
        document:Document,
        embedding_provider: EmbeddingProvider,
        parent_chunk_size: int = 1800,
        parent_chunk_overlap: int = 120,
        child_chunk_size: int = 400,
        child_chunk_overlap: int = 80,
)->None:
    try:
        # 先更新文档的状态
        document.status = "chunking"
        db.add(document)
        db.commit()

        children_to_create = []

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

                children_to_create.append(
                    (parent_chunk, parent, child, child_content_hash)
                )

        if children_to_create:
            child_texts = [
                child.content
                for _parent_chunk, _parent, child, _child_content_hash in children_to_create
            ]
            child_embeddings = embedding_provider.embed_documents(child_texts)
        else:
            child_embeddings = []

        if len(child_embeddings) != len(children_to_create):
            raise RuntimeError("Embedding count does not match child chunk count")

        for (
            parent_chunk,
            parent,
            child,
            child_content_hash,
        ), child_embedding in zip(children_to_create, child_embeddings, strict=True):
            create_document_chunk(
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
                    embedding_model=embedding_provider.model_name,
                    embedding=child_embedding,
                    embedding_dimensions=embedding_provider.dimensions,
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
