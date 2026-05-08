'''
负责管理注册各个业务的router
'''

from fastapi import APIRouter
from app.api.routes import health,knowledge_bases,documents

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health", # health.py 里的所有接口挂到 /health 下。
    tags=["health"]
)

api_router.include_router(
    knowledge_bases.router,
    prefix="/knowledge-bases",
    tags=["knowledge-bases"]
)
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)