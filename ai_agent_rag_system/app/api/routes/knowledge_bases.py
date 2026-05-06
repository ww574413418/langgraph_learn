'''
接收 HTTP 请求。
做依赖注入，比如拿到数据库 session。
调用 service，把结果返回给前端。
'''

from fastapi import APIRouter,Depends,status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.knowledge_base import KnowledgeBaseCreate,KnowledgeBaseRead
from app.services.knowledge_base_service import (create_knowledge_base,list_knowledge_bases)

router = APIRouter()

@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED
)
def create_knowledge_api(data:KnowledgeBaseCreate,db:Session=Depends(get_db)):
    return create_knowledge_base(db,data)

@router.get(
    "",
    response_model=list[KnowledgeBaseRead]
)
def list_knowledge_api(db:Session=Depends(get_db)):
    return list_knowledge_bases(db=db)