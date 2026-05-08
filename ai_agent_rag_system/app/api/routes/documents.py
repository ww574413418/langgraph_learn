from fastapi import APIRouter,Depends,HTTPException,Query,status
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.document import DocumentRead,DocumentCreate
from app.services.document_service import (get_document,list_documents,create_document)

router = APIRouter()

@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED
)
def create_document_api(data:DocumentCreate,db:Session=Depends(get_db)):
    try:
        return create_document(db,data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=str(e)) from e

@router.get(
    "",
    response_model=list[DocumentRead]
)
#  Query(default=None) 表示 是查询参数：
def list_documents_api(knowledge_base_id:UUID|None = Query(default=None),
                       db:Session = Depends(get_db)):
    # Query(default=None) 它表示这是查询参数
    # GET /api/documents?knowledge_base_id=xxx,如果不传就查询全部文档
    return list_documents(db,knowledge_base_id)

@router.get(
    "/{document_id}",
    response_model=DocumentRead
)
def get_document_api(document_id:UUID,db:Session=Depends(get_db)):
    document = get_document(db,document_id)

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Document not found")
    return document


