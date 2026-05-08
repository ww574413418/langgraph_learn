from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,Field,ConfigDict

class DocumentCreate(BaseModel):
    knowledge_base_id:UUID
    filename:str = Field(min_length=1,max_length=255)
    file_type:str = Field(min_length=1,max_length=50)
    file_path:str = Field(min_length=1)
    file_hash:str = Field(min_length=1,max_length=128)


class DocumentRead(BaseModel):
    # 允许pydantic直接从对象中读取属性
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    knowledge_base_id:UUID
    filename:str
    file_type:str
    file_path:str
    file_hash:str
    status:str
    error_message:str|None
    extra_metadata:dict
    created_at:datetime
    updated_at:datetime