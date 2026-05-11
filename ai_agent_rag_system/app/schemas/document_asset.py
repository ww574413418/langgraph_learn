from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field

class DocumentAssetCreate(BaseModel):
    document_id:UUID
    asset_type:str = Field(min_length=1,max_length=30)
    source_path:str = Field(min_length=1)
    storage_path:str = Field(min_length=1)
    url:str = Field(min_length=1)
    alt_text:str|None = None
    placeholder:str = Field(min_length=1,max_length=100)

class DocumentAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    asset_type: str
    source_path: str
    storage_path: str
    url: str
    alt_text: str | None
    placeholder: str
    extra_metadata: dict
    created_at: datetime
