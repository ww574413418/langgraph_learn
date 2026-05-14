from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column,Mapped
from app.db.base_class import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id:Mapped[UUID] = mapped_column(primary_key=True,default=uuid4)
    document_id:Mapped[UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    parent_id:Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chunks.id"),
        nullable=True,
        index=True
    )
    chunk_type:Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )
    chunk_index:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content:Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    content_hash:Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True
    )

    token_count:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    char_count:Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    start_char:Mapped[int|None] = mapped_column(
        Integer,
        nullable=True
    )
    end_char:Mapped[int|None] = mapped_column(
        Integer,
        nullable=True
    )

    embedding_model:Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    extra_metadata:Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict
    )

    created_at:Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )