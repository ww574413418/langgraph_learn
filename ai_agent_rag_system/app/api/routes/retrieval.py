from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.retrieval import RetrievalRequest,RetrievalResponse
from app.services.retrieval_service import run_retrieval


router = APIRouter()

@router.post(
    "",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK
)
def run_retrieval_api(data:RetrievalRequest,
                      db:Session=Depends(get_db)):
    try:
        return run_retrieval(db,data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
