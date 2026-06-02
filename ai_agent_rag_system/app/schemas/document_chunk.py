from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,Field,ConfigDict

class DocumentChunkCreate(BaseModel):
    document_id:UUID
    parent_id:UUID | None = None
    chunk_type:str = Field(min_length=1,max_length=30)
    chunk_index:int
    content:str = Field(min_length=1)
    content_hash:str = Field(min_length=1,max_length=128)
    token_count:int = 0
    char_count:int = 0
    start_char:int | None = None
    end_char:int | None = None
    # 记录向量来自哪个模型。
    # 生产中不能只保存 embedding，不保存模型名，否则以后换模型会混用不同向量空间。
    embedding_model: str | None = None

    # 真正写入 pgvector 的向量。
    # 测试阶段可以用 DeterministicEmbeddingProvider，生产阶段再换 OpenAI embedding provider。
    embedding: list[float] | None = None

    # 保存维度，便于查询时过滤，也方便排查线上数据问题。
    embedding_dimensions: int | None = None

    extra_metadata:dict =  Field(default_factory=dict)

class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    parent_id: UUID | None
    chunk_type: str
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    char_count: int
    start_char: int | None
    end_char: int | None
    embedding_model: str | None
    extra_metadata: dict
    created_at: datetime