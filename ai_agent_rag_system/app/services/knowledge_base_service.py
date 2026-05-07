'''
service 层的职责是：处理业务逻辑，不处理 HTTP 请求细节。
'''
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate,KnowledgeBaseUpdate
from uuid import UUID

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

def get_knowledge_base(db:Session,knowledge_base_id:UUID) -> KnowledgeBase:
    statement = select(KnowledgeBase).where(KnowledgeBase.id==knowledge_base_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()


def update_knowledge_base(
        db:Session,
        knowledge_base:KnowledgeBase,
        data:KnowledgeBaseUpdate
) -> KnowledgeBase:
    # 只取用户传入的字段
    update_data = data.model_dump(exclude_unset=True)

    for field,value in update_data.items():
        setattr(knowledge_base,field,value)

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base


def disable_knowledge_base(db:Session,knowledge_base:KnowledgeBase) -> KnowledgeBase:
    '''
    软删除数据库
    :param db:
    :param knowledge_base:
    :return:
    '''
    knowledge_base.status = "disabled"

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base