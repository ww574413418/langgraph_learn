'''
Base 是所有 SQLAlchemy 模型的共同基类。
如果没有统一的 Base，Alembic 就不知道项目里有哪些模型，也就不能自动生成迁移。
Alembic 是数据库迁移工具。模型变了，数据库表结构怎么同步？

'''
from app.db.base_class import Base
from app.models.knowledge_base import KnowledgeBase  # noqa: F401
from app.models.document import Document
from app.models.document_asset import DocumentAssets