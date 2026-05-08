from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import DateTime, String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from uuid import UUID,uuid4
from sqlalchemy.dialects.postgresql import JSONB

class Document(Base):

    __tablename__ = "documents"

    id:Mapped[UUID] = mapped_column(primary_key=True,default=uuid4)

    knowledge_base_id:Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id"),
        nullable=False,
        index=True
    )

    filename:Mapped[str] = mapped_column(String(255),nullable=False)
    file_type:Mapped[str] = mapped_column(String(50),nullable=False)
    file_path:Mapped[str] = mapped_column(Text,nullable=False)
    file_hash:Mapped[str] = mapped_column(String(128),nullable=False,index=True)

    # uploaded parsing parsed chunking indexed failed
    status:Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="uploaded",
        index=True
    )

    error_message:Mapped[str|None] = mapped_column(Text,nullable=True)
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