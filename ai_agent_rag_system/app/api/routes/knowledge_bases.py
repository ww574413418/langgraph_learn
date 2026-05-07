'''
接收 HTTP 请求。
做依赖注入，比如拿到数据库 session。
调用 service，把结果返回给前端。
'''

from fastapi import APIRouter,Depends,status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.knowledge_base import KnowledgeBaseCreate,KnowledgeBaseRead,KnowledgeBaseUpdate
from app.services.knowledge_base_service import (create_knowledge_base,list_knowledge_bases,
                                                 get_knowledge_base,update_knowledge_base,
                                                 disable_knowledge_base)
from uuid import UUID
from fastapi import HTTPException

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

@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead
)
def get_knowledge_base_api(knowledge_base_id:UUID,db:Session=Depends(get_db)):
    knowledge_base = get_knowledge_base(db,knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Knowledge base not found")
    return knowledge_base

@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead
)
def update_knowledge_base_api(knowledge_base_id:UUID,
                              data:KnowledgeBaseUpdate,
                              db:Session=Depends(get_db)):
    knowledge_base = get_knowledge_base(db,knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Knowledge base not found")

    return update_knowledge_base(db,knowledge_base,data)


@router.delete(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead
)
def delete_knowledge_base_api(knowledge_base_id:UUID,db:Session=Depends(get_db)):
    knowledge_base = get_knowledge_base(db,knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Knowledge base not found")

    return disable_knowledge_base(db=db,knowledge_base=knowledge_base)