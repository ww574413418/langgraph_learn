'''
定义请求和响应的数据格式。
'''
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field

class KnowledgeBaseCreate(BaseModel):
    '''
    KnowledgeBaseCreate 是用户创建知识库时允许传入的字段。
    不要让用户直接传 id/status/created_at，这些应该由系统生成。
    '''
    name:str = Field(min_length=1,max_length=100)
    description:str|None = None
    domain:str|None = None


class KnowledgeBaseRead(BaseModel):
    '''
    KnowledgeBaseRead 是接口返回给前端的数据格式。
    ConfigDict(from_attributes=True) 允许 Pydantic 从 SQLAlchemy 模型对象读取字段。
    '''
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    name:str
    description:str|None
    domain:str|None
    status:str
    default_chunk_strategy:str
    default_parent_chunk_size:int
    default_child_chunk_size:int
    default_chunk_overlap:int
    embedding_model:str|None
    retrieval_config:dict
    extra_metadata:dict
    created_at:datetime
    updated_at:datetime

class KnowledgeBaseUpdate(BaseModel):
    '''
    更新知识库所需字段
    '''
    name:str |None = Field(default=None,min_length=1,max_length=100)
    description:str|None = None
    domain:str|None = None