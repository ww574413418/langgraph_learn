from app.db.base_class import Base
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import DateTime,String,Integer,Text,ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from uuid import UUID,uuid4

class DocumentAssets(Base):

    __tablename__ = "document_assets"

    id:Mapped[UUID] = mapped_column(primary_key=True,default=uuid4)
    document_id:Mapped[UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    asset_type:Mapped[str] = mapped_column(String(30),nullable=False,index=True)
    source_path:Mapped[str] = mapped_column(Text,nullable=False)
    storage_path:Mapped[str] = mapped_column(Text,nullable=False) # 系统保存后的本地路径
    url:Mapped[str] = mapped_column(Text,nullable=False) # 前端可访问 URL
    alt_text:Mapped[str|None] = mapped_column(Text,nullable=True)
    placeholder:Mapped[str|None] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    extra_metadata:Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict
    )
    created_at:Mapped[datetime] = mapped_column(DateTime,
                                                nullable=False,
                                                default=datetime.utcnow)

