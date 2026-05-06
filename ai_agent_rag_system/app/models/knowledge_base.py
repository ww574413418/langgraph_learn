'''
它负责描述一个知识库，以及这个知识库默认怎么入库、怎么检索。
'''
from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import DateTime, String, Text, Integer
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID,uuid4

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id:Mapped[UUID] = mapped_column(primary_key=True,default=uuid4)
    name:Mapped[str] = mapped_column(String(100),nullable=False,index=True)
    description:Mapped[str|None] = mapped_column(Text,nullable=True)
    # 领域标签 后面 Agent Router 可以根据领域选择知识库。
    domain:Mapped[str|None] = mapped_column(String(100),nullable=True,index=True)
    # active disabled indexing  failed
    status:Mapped[str] = mapped_column(String(30),nullable=False,default="active")
    default_chunk_strategy:Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="parent_child"
    )
    default_parent_chunk_size:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1500
    )
    default_child_chunk_size:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=400
    )
    default_chunk_overlap:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=80
    )
    embedding_model:Mapped[str|None] = mapped_column(String(100),nullable=True)
    # 检索配置
    # {
    #   "top_k": 8,
    #   "use_rerank": false,
    #   "include_assets": true,
    #   "include_parent": true
    # }
    retrieval_config:Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    # Python 属性叫 extra_metadata，数据库列名叫 metadata。
    extra_metadata:Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict
    )
    created_at:Mapped[datetime] = mapped_column(DateTime,
                                                nullable=False,
                                                default=datetime.utcnow)
    updated_at:Mapped[datetime] = mapped_column(DateTime,
                                            nullable=False,
                                            default=datetime.utcnow,
                                            onupdate=datetime.utcnow)

