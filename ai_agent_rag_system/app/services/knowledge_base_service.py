'''
service 层的职责是：处理业务逻辑，不处理 HTTP 请求细节。
'''

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate

def create_knowledge_base(db:Session,data:KnowledgeBaseCreate) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        name=data.name,
        description=data.description,
        domain=data.domain
    )
    # 把对象放入当前数据库对象
    db.add(knowledge_base)
    db.commit()

    # 把数据库生成的字段重新读回来，比如 id、created_at。
    db.refresh(knowledge_base)

    return knowledge_base

def list_knowledge_bases(db:Session) -> list[KnowledgeBase]:
    statement = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    result = db.execute(statement)
    # 从查询结果中取出模型对象列表。
    return list(result.scalars().all())