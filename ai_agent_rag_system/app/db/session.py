'''
postgres 连接测试
'''
from collections.abc import Generator
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker,Session
from app.core.config import settings

# 创建数据库拦截引擎 负责管理底层连接池。
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True, # 先检查链接池的连接是否还活着
)


# 创建数据库session工厂 每次请求可以创建一个 session
SessionLocal = sessionmaker(
    bind = engine,
    autoflush = False,
    autocommit = False,
)

# Session 一次数据库操作上下文，后面增删改查都通过它完成。
def get_db() -> Generator[Session,None,None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_database_connection() ->bool:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return result.scalar() == 1