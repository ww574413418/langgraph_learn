# 学习笔记（一）：FastAPI 工程骨架与知识库 CRUD

记录日期：2026-05-07

项目名称：`AI Agent Knowledge Workspace`

这份笔记用于复习本项目第一阶段的核心内容。重点记录：为什么这样设计、每一层负责什么、关键代码怎么写、容易错在哪里。

## 1. 本篇学习范围

这个项目不是一个简单调用大模型 API 的 demo，而是一个具备工程落地结构的 AI Agent + RAG 系统。

当前确定的技术栈：

- 后端：FastAPI
- 前端：Vue 3 + Vite + TypeScript
- 数据库：PostgreSQL
- 向量扩展：pgvector
- 缓存和任务状态：Redis
- ORM：SQLAlchemy 2.x
- 数据库迁移：Alembic
- 测试：pytest + FastAPI TestClient
- 后续 AI 编排：LangChain + LangGraph

项目最终要支持：

- 企业知识库管理
- 文档上传、解析、切分、入库
- 普通 chunk 和父子 chunk
- Word / Markdown / PDF 中图片资产抽取
- 图片 URL 回填到文档正文
- 文本和图片联合召回
- 基于 RAG 的问答
- LangGraph Multi-Agent 工作流
- 类主流大模型的聊天前端

## 2. 项目结构

当前后端核心结构：

```text
app/
  main.py
  api/
    router.py
    routes/
      health.py
      knowledge_bases.py
  core/
    config.py
    logging.py
  db/
    base.py
    base_class.py
    redis.py
    session.py
  models/
    knowledge_base.py
  schemas/
    knowledge_base.py
  services/
    knowledge_base_service.py
  web/
    spa.py
```

当前测试结构：

```text
tests/
  test_health.py
  test_knowledge_bases.py
```

当前文档结构：

```text
docs/
  README.md
  development_plan.md
  frontend_design.md
  learning_record.md
  rag_design.md
  notes/
    01-fastapi-knowledge-base.md
    02-document-ingestion-assets.md
  superpowers/
    plans/
      2026-06-01-agent-rag-learning-roadmap.md
```

## 3. FastAPI 工程骨架

### 3.1 `main.py` 的职责

`app/main.py` 是程序入口。

它负责：

- 创建 FastAPI 应用对象
- 读取项目配置
- 初始化日志
- 注册总 API 路由
- 挂载 Vue SPA 静态资源

核心结构：

```python
from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.web.spa import mount_spa

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(api_router, prefix="/api")
mount_spa(app)
```

注意：

- `main.py` 不应该写具体业务逻辑。
- 所有业务 API 应该放到 `app/api/routes/`。
- 所有业务处理应该放到 `app/services/`。

### 3.2 `api/router.py` 的职责

`app/api/router.py` 是 API 总路由。

它负责把不同业务模块的 router 汇总起来：

```python
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    knowledge_bases.router,
    prefix="/knowledge-bases",
    tags=["knowledge-bases"],
)
```

最终路径由多层 prefix 拼接：

```text
app.include_router(api_router, prefix="/api")
knowledge_bases.router prefix="/knowledge-bases"
router.post("")

最终路径：POST /api/knowledge-bases
```

易错点：

- 不要把所有接口都写在 `main.py`。
- `@router` 是错的，应该写 `@router.get(...)`、`@router.post(...)`。
- 如果路由路径写错，浏览器会返回 `{"detail":"Not Found"}`。

## 4. 配置管理

配置文件：

```text
app/core/config.py
```

核心代码：

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "AI Agent Knowledge Workspce"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent_workspace"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    frontend_dist_dir: str = "frontend/dist"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

原理：

- `BaseSettings` 可以从 `.env` 读取配置。
- 代码里保留默认值，方便本地开发。
- 真实密码和 API Key 放 `.env`。
- 配置模板放 `.env.example`。
- `.env` 必须被 `.gitignore` 忽略。

易错点：

- `.env` 不应该提交。
- `.env.example` 应该提交。
- 曾经误写过 `.evn`，这种文件如果进了暂存区，需要用 `git restore --staged` 移除。
- 字段名拼错会导致运行时取不到配置，例如 `fronted_dist_dir` 和 `frontend_dist_dir`。

## 5. PostgreSQL 和 Redis 的职责

### 5.1 PostgreSQL

PostgreSQL 负责长期、可靠、可查询的数据。

在本项目中用于：

- 知识库
- 文档元数据
- 文档 chunk
- 图片资产
- 会话
- 消息
- Agent 任务和事件
- pgvector 向量字段

当前已经创建：

```text
数据库用户：agent
数据库名：agent_workspace
扩展：vector
```

验证命令：

```bash
docker exec postgres psql -U agent -d agent_workspace -c "SELECT current_user, current_database();"
docker exec postgres psql -U agent -d agent_workspace -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

### 5.2 Redis

Redis 负责短期、高频、临时状态。

在本项目中用于：

- 缓存
- 任务状态
- 停止生成标记
- 限流
- LangGraph checkpoint 或执行状态

Redis 不负责保存重要长期数据。

验证命令：

```bash
python -c "from app.db.redis import check_redis_connection; print(check_redis_connection())"
```

## 6. 数据库连接

文件：

```text
app/db/session.py
```

核心结构：

```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

原理：

- `engine` 管理底层数据库连接池。
- `SessionLocal` 是 session 工厂。
- `Session` 是一次数据库操作上下文。
- `get_db()` 用于 FastAPI 依赖注入。
- `pool_pre_ping=True` 可以减少连接池里拿到失效连接的问题。

易错点：

- 曾经把 `bind=engine` 写成 `bing=engine`。
- `check_database_connection()` 直接用 `engine.connect()`，所以它能通过不代表 `SessionLocal()` 一定没问题。
- 一旦 API route 使用 `Depends(get_db)`，`SessionLocal()` 的配置错误就会暴露。

## 7. 健康检查接口

接口：

```text
GET /api/health
```

职责：

- 检查 API 是否正常。
- 检查 PostgreSQL 是否可连接。
- 检查 Redis 是否可连接。

返回示例：

```json
{
  "status": "ok",
  "services": {
    "api": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

学习重点：

- 健康检查不是只返回 `ok`。
- 工程项目应该检查关键外部依赖。
- 这个测试依赖真实 PostgreSQL 和 Redis，所以更接近集成测试。

## 8. 日志系统

文件：

```text
app/core/logging.py
```

配置字段：

```python
log_level: str = "INFO"
log_to_file: bool = True
log_file_path: str = "logs/app.log"
log_max_bytes: int = 10 * 1024 * 1024
log_backup_count: int = 5
```

学习重点：

- `print` 适合临时调试。
- `logging` 适合工程项目。
- 日志应该能输出到控制台，也能本地保存。
- 日志文件属于运行产物，不应该提交 Git。

验证方式：

```bash
ls -la logs
cat logs/app.log
```

易错点：

- 日志太少时排查问题很困难。
- 日志配置应该放在 `config.py`，不要散落在业务代码里。

## 9. FastAPI 托管 Vue SPA

本篇笔记不记录 Vue 前端的具体组件实现，只记录后端如何托管 Vue 构建产物，以及为什么需要 SPA fallback。

前端使用 Vue Router 时，页面路径可能是：

```text
/
/chat
/knowledge-bases
/settings
```

这些路径不是 FastAPI 的 API 路径，而是前端页面路由。生产或演示环境中，如果用户直接访问 `/chat`，浏览器会向 FastAPI 请求 `/chat`。如果后端没有 fallback，就会返回：

```json
{"detail": "Not Found"}
```

所以 FastAPI 需要在 API 路由之外，把这些前端页面路径统一返回 `frontend/dist/index.html`，再交给 Vue Router 在浏览器里接管。

开发模式：

```text
前端：localhost:5173
后端：localhost:8000
```

Vite 负责把 `/api/*` 代理到 FastAPI。

构建后：

```bash
cd frontend
npm run build
```

会生成：

```text
frontend/dist/index.html
frontend/dist/assets/
```

### 9.1 配置构建产物目录

在 `app/core/config.py` 中配置：

```python
frontend_dist_dir: str = "frontend/dist"
static_dir: str = "app/static"
```

含义：

- `frontend_dist_dir`：Vue build 后的目录。
- `static_dir`：后端自己的静态资源目录，后续可放上传图片、头像、文档资产等。

### 9.2 在 `main.py` 中挂载 SPA

`app/main.py` 中：

```python
app.include_router(api_router, prefix="/api")
mount_spa(app)
```

注意顺序：

- 先注册 `/api` 路由。
- 再挂载 SPA fallback。

这样可以保证业务接口优先匹配，前端页面路由最后兜底。

### 9.3 `mount_spa` 的核心实现

文件：

```text
app/web/spa.py
```

核心逻辑：

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings


def mount_spa(app: FastAPI) -> None:
    static_dir = Path(settings.static_dir)
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    frontend_dist_dir = Path(settings.frontend_dist_dir)
    index_file = frontend_dist_dir / "index.html"
    assets_dir = frontend_dist_dir / "assets"

    if not index_file.exists():
        return

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(
                status_code=404,
                detail="API route should not be handled by SPA fallback",
            )

        return FileResponse(index_file)
```

### 9.4 这里的关键点

`app.mount("/assets", ...)`：

- 让 Vue build 后的 JS、CSS、图片可以通过 `/assets/...` 访问。
- 如果 `index.html` 里引用了 `/assets/index-xxx.js`，这个挂载必须存在。

`@app.get("/{full_path:path}")`：

- `{full_path:path}` 是 FastAPI 的路径转换器。
- 它可以捕获多层路径。
- 例如 `/chat/session/123` 会得到 `full_path = "chat/session/123"`。

`include_in_schema=False`：

- 不把 SPA fallback 显示在 Swagger 文档里。
- 因为它不是业务 API。

`if full_path.startswith("api/")`：

- 防止 `/api/...` 被 Vue fallback 接管。
- API 路径如果不存在，应该返回真正的 API 404。
- 不应该返回前端首页。

`return FileResponse(index_file)`：

- 对所有前端页面路由返回 Vue 的 `index.html`。
- 浏览器加载 `index.html` 后，Vue Router 再根据当前路径渲染正确页面。

易错点：

- `frontend/dist/` 是构建产物，不提交 Git。
- 开发环境访问前端应该访问 Vite 地址。
- FastAPI 托管 Vue 构建产物时，需要正确配置 SPA fallback。
- fallback 路由应使用 `/{full_path:path}`，不是 `/{full_path}:path`。
- 如果没有执行 `npm run build`，`frontend/dist/index.html` 不存在，`mount_spa` 会直接返回，不会挂载前端页面。
- 如果忘记挂载 `/assets`，页面可能能返回 HTML，但 JS/CSS 加载失败。
- 如果 fallback 没有排除 `/api/`，不存在的 API 可能会错误返回前端首页。

## 10. SQLAlchemy Base 和 Alembic

### 10.1 为什么要拆 `base_class.py` 和 `base.py`

当前设计：

```text
app/db/base_class.py
  只定义 Base

app/db/base.py
  导入 Base
  导入所有模型
  给 Alembic 收集 metadata

app/models/*.py
  从 app.db.base_class 导入 Base
```

原因：

- 如果模型从 `app.db.base` 导入 `Base`，而 `base.py` 又导入模型，会形成循环导入。
- 拆出 `base_class.py` 后，模型只依赖最基础的 Base 定义。
- `base.py` 变成 Alembic 专用的模型聚合入口。

正确关系：

```text
base_class.py -> 定义 Base
models/*.py -> 使用 Base
base.py -> 导入 Base 和所有 models
migrations/env.py -> 使用 Base.metadata
```

### 10.2 Alembic 配置

`migrations/env.py` 需要配置：

```python
from app.db.base import Base

target_metadata = Base.metadata
```

易错点：

- `target_metadata = None` 会导致自动迁移看不到模型。
- `target_metadata = Base` 是错的，会出现 `Base has no attribute sorted_tables`。
- 正确的是 `Base.metadata`。
- 如果误删 `migrations/`，重新 `alembic init migrations` 后要重新修改 `env.py`。

### 10.3 常用命令

生成迁移：

```bash
alembic revision --autogenerate -m "create knowledge bases"
```

执行迁移：

```bash
alembic upgrade head
```

查看当前版本：

```bash
alembic current
```

查看表：

```bash
docker exec postgres psql -U agent -d agent_workspace -c "\dt"
docker exec postgres psql -U agent -d agent_workspace -c "\d knowledge_bases"
```

## 11. `knowledge_bases` 表设计

当前模型：

```text
app/models/knowledge_base.py
```

核心字段：

```text
id
name
description
domain
status
default_chunk_strategy
default_parent_chunk_size
default_child_chunk_size
default_chunk_overlap
embedding_model
retrieval_config
metadata
created_at
updated_at
```

业务含义：

- `name`：知识库名称
- `description`：知识库说明
- `domain`：领域标签，后续 Agent Router 可以根据领域选择知识库
- `status`：知识库状态，例如 `active`、`disabled`、`indexing`、`failed`
- `default_chunk_strategy`：默认切分策略，例如 `parent_child`
- `default_parent_chunk_size`：父 chunk 默认大小
- `default_child_chunk_size`：子 chunk 默认大小
- `default_chunk_overlap`：chunk 重叠长度
- `embedding_model`：后续记录向量模型
- `retrieval_config`：检索配置，例如 `top_k`、`use_rerank`、`include_assets`
- `metadata`：扩展元数据
- `created_at` / `updated_at`：创建和更新时间

易错点：

- PostgreSQL 不支持 `DATETIME`，应使用 SQLAlchemy `DateTime`，最终生成 PostgreSQL `timestamp`。
- SQLAlchemy 内部已有 `metadata` 属性，所以 Python 模型属性不能直接叫 `metadata`。
- 当前做法是 Python 属性叫 `extra_metadata`，数据库列名仍叫 `metadata`：

```python
extra_metadata: Mapped[dict] = mapped_column(
    "metadata",
    JSONB,
    nullable=False,
    default=dict,
)
```

## 12. Schema、Service、API 三层

这是当前最重要的后端分层。

### 12.1 Model

文件：

```text
app/models/knowledge_base.py
```

职责：

- 描述数据库表结构。
- 定义字段类型、索引、默认值。
- 不处理 HTTP 请求。
- 不处理复杂业务流程。

### 12.2 Schema

文件：

```text
app/schemas/knowledge_base.py
```

职责：

- 定义请求数据格式。
- 定义响应数据格式。
- 做基础字段校验。
- 控制哪些字段允许前端传入，哪些字段返回给前端。

当前 schema：

```python
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    domain: str | None = None

class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    domain: str | None
    status: str
    created_at: datetime
    updated_at: datetime
```

学习重点：

- `KnowledgeBaseCreate` 是创建时允许用户传入的字段。
- 不要让用户传 `id`、`status`、`created_at`。
- `KnowledgeBaseRead` 是接口返回格式。
- `ConfigDict(from_attributes=True)` 允许 Pydantic 从 SQLAlchemy 对象读取属性。

部分更新需要单独的 schema：

```python
class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    domain: str | None = None
```

学习重点：

- `POST` 使用 `KnowledgeBaseCreate`。
- `PATCH` 使用 `KnowledgeBaseUpdate`。
- 创建时 `name` 必填。
- 更新时所有字段都可选。
- `name` 如果传了，仍然要满足长度校验。
- 不传的字段不应该覆盖数据库原值。

### 12.3 Service

文件：

```text
app/services/knowledge_base_service.py
```

职责：

- 处理业务逻辑。
- 执行数据库增删改查。
- 不关心 HTTP 状态码。
- 不直接处理请求头、路径参数等 HTTP 细节。

当前核心逻辑：

```python
def create_knowledge_base(db: Session, data: KnowledgeBaseCreate) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        name=data.name,
        description=data.description,
        domain=data.domain,
    )

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base
```

详情查询：

```python
def get_knowledge_base(
    db: Session,
    knowledge_base_id: UUID,
) -> KnowledgeBase | None:
    statement = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    result = db.execute(statement)
    return result.scalar_one_or_none()
```

部分更新：

```python
def update_knowledge_base(
    db: Session,
    knowledge_base: KnowledgeBase,
    data: KnowledgeBaseUpdate,
) -> KnowledgeBase:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(knowledge_base, field, value)

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base
```

软删除：

```python
def disable_knowledge_base(
    db: Session,
    knowledge_base: KnowledgeBase,
) -> KnowledgeBase:
    knowledge_base.status = "disabled"

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base
```

学习重点：

- `db.add()`：把对象加入当前 session。
- `db.commit()`：提交事务，真正写入数据库。
- `db.refresh()`：重新读取数据库生成的字段，例如 `id`、`created_at`。
- `select(KnowledgeBase)` 是 SQLAlchemy 2.x 推荐查询方式。
- `result.scalars().all()` 用于取模型对象列表。
- `scalar_one_or_none()` 用于按主键查询一条或没有结果。
- `data.model_dump(exclude_unset=True)` 只取用户真正传入的字段。
- `setattr()` 可以根据字段名动态更新模型对象。
- 对知识库更推荐软删除，把 `status` 改成 `disabled`，而不是直接物理删除记录。

易错点：

- 曾经把 `description` 拼成 `descripiton`，语法检查不会发现，但运行时会报 invalid keyword。
- 曾经把 `result.scalars().all()` 写成 `result.scalar().all()`。
- `scalar()` 取单个值，`scalars()` 取一组模型对象。
- `PATCH` 如果误用 `KnowledgeBaseCreate`，只更新 `description` 时会报缺少 `name`。
- `exclude_unset=True` 很重要，否则没传的字段可能被误覆盖成 `None`。

### 12.4 API Route

文件：

```text
app/api/routes/knowledge_bases.py
```

职责：

- 接收 HTTP 请求。
- 使用 `Depends(get_db)` 获取数据库 session。
- 调用 service。
- 用 `response_model` 控制响应格式。
- 设置 HTTP 状态码。

当前接口：

```text
POST /api/knowledge-bases
GET  /api/knowledge-bases
GET  /api/knowledge-bases/{knowledge_base_id}
PATCH /api/knowledge-bases/{knowledge_base_id}
DELETE /api/knowledge-bases/{knowledge_base_id}
```

核心结构：

```python
@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_api(
    data: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
):
    return create_knowledge_base(db, data)
```

详情接口：

```python
@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def get_knowledge_base_api(
    knowledge_base_id: UUID,
    db: Session = Depends(get_db),
):
    knowledge_base = get_knowledge_base(db, knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    return knowledge_base
```

部分更新接口：

```python
@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def update_knowledge_base_api(
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
):
    knowledge_base = get_knowledge_base(db, knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    return update_knowledge_base(db, knowledge_base, data)
```

软删除接口：

```python
@router.delete(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def delete_knowledge_base_api(
    knowledge_base_id: UUID,
    db: Session = Depends(get_db),
):
    knowledge_base = get_knowledge_base(db, knowledge_base_id)

    if knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    return disable_knowledge_base(db=db, knowledge_base=knowledge_base)
```

学习重点：

- API 层不应该写复杂数据库逻辑。
- `response_model` 会把 SQLAlchemy 对象转换成 schema 定义的 JSON。
- `Depends(get_db)` 是 FastAPI 依赖注入。
- `knowledge_base_id: UUID` 会让 FastAPI 自动校验路径参数。
- UUID 格式不合法时，FastAPI 返回 422。
- UUID 格式合法但数据库中不存在时，业务代码返回 404。
- 对外接口可以叫 DELETE，但 service 内部可以叫 `disable_knowledge_base`，表达真实业务动作。

## 13. 业务链路

创建知识库：

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{"name":"扫地机器人知识库","description":"扫地机器人相关资料","domain":"robot_cleaner"}'
```

返回示例：

```json
{
  "id": "c17c8b7d-0c5c-47bd-adfa-6f38dc1125f6",
  "name": "扫地机器人知识库",
  "description": "扫地机器人相关资料",
  "domain": "robot_cleaner",
  "status": "active",
  "default_chunk_strategy": "parent_child",
  "default_parent_chunk_size": 1500,
  "default_child_chunk_size": 400,
  "default_chunk_overlap": 80,
  "embedding_model": null,
  "retrieval_config": {},
  "extra_metadata": {},
  "created_at": "2026-05-06T15:11:09.857032",
  "updated_at": "2026-05-06T15:11:09.857036"
}
```

查询知识库：

```bash
curl http://127.0.0.1:8000/api/knowledge-bases
```

查询详情：

```bash
curl http://127.0.0.1:8000/api/knowledge-bases/c17c8b7d-0c5c-47bd-adfa-6f38dc1125f6
```

部分更新：

```bash
curl -X PATCH http://127.0.0.1:8000/api/knowledge-bases/c17c8b7d-0c5c-47bd-adfa-6f38dc1125f6 \
  -H "Content-Type: application/json" \
  -d '{"description":"这是更新后的扫地机器人知识库"}'
```

软删除：

```bash
curl -X DELETE http://127.0.0.1:8000/api/knowledge-bases/c17c8b7d-0c5c-47bd-adfa-6f38dc1125f6
```

完整链路：

```text
HTTP 请求
  -> API route
  -> Pydantic schema 校验
  -> Depends(get_db) 获取 Session
  -> service 层
  -> SQLAlchemy model
  -> PostgreSQL
  -> db.refresh 读取生成字段
  -> response_model 转 JSON
  -> HTTP 响应
```

## 14. 接口测试

文件：

```text
tests/test_knowledge_bases.py
```

测试目标：

- `POST /api/knowledge-bases` 能创建知识库。
- `GET /api/knowledge-bases` 能返回知识库列表。
- 创建后的知识库能在列表中查到。
- 按 ID 查询不存在的知识库返回 404。
- 非法 UUID 返回 422。
- PATCH 可以只更新部分字段。
- PATCH 不存在资源返回 404。
- DELETE 会把知识库状态改成 `disabled`。
- DELETE 不存在资源返回 404。

核心断言：

```python
items = list_response.json()
assert any(item["id"] == created["id"] for item in items)
```

部分更新断言重点：

```python
updated = update_response.json()

assert updated["id"] == created["id"]
assert updated["name"] == "待更新知识库"
assert updated["description"] == "新描述"
assert updated["domain"] == "old domain"
```

这个断言证明：只传 `description` 时，`name` 和 `domain` 没有被误覆盖。

软删除断言重点：

```python
deleted = delete_response.json()

assert deleted["id"] == created["id"]
assert deleted["status"] == "disabled"
```

学习重点：

- `TestClient(app)` 可以不启动 uvicorn，直接测试 FastAPI 应用。
- 这个测试会真的写入当前 PostgreSQL，所以属于集成测试。
- 手工 curl 通过不等于以后不会坏，测试可以固定住行为。
- 测试里如果后续依赖创建结果，要先断言创建成功。
- 否则真正错误会被后面的 `KeyError` 掩盖。

易错点：

曾经写成：

```python
assert any(items["id"] == created["id"] for item in items)
```

错误原因：

- `items` 是列表。
- `item` 才是列表中的单条字典。
- 列表不能用字符串 key 取值，所以报 `TypeError: list indices must be integers or slices, not str`。

正确写法：

```python
assert any(item["id"] == created["id"] for item in items)
```

另一个易错点是测试路径拼写：

```python
client.post("api/knowledge-base", ...)
```

问题：

- 少了开头的 `/`。
- `knowledge-base` 写成了单数。
- 当前真实路径是 `/api/knowledge-bases`。

推荐写法：

```python
create_response = client.post("/api/knowledge-bases", json=payload)
assert create_response.status_code == 201
```

运行测试：

```bash
pytest
```

## 15. 目前遇到过的重要错误

### 15.1 `ModuleNotFoundError: No module named 'api'`

原因：

```python
from api.router import api_router
```

项目是以 `app.main:app` 方式启动的，应使用完整包路径：

```python
from app.api.router import api_router
```

### 15.2 `Router.__call__() missing receive and send`

原因：

把 router 当装饰器用了：

```python
@router
```

正确写法：

```python
@router.get("")
def health_check():
    ...
```

### 15.3 浏览器返回 `{"detail":"Not Found"}`

常见原因：

- 访问了没有注册的路径。
- API prefix 拼错。
- Vue SPA fallback 没挂好。
- 访问 `/` 时后端没有根路径处理。

排查方式：

- 先访问 `/docs` 看 Swagger。
- 再确认接口是否出现在 Swagger。
- 再确认实际路径是不是 `/api/...`。

### 15.4 Alembic 生成空迁移

原因：

- `target_metadata = None`
- 或 `base.py` 没有导入模型
- 或模型没有继承同一个 `Base`

解决：

```python
from app.db.base import Base
target_metadata = Base.metadata
```

并确保 `app/db/base.py` 导入所有模型。

### 15.5 SQLAlchemy 循环导入

错误表现：

```text
ImportError: cannot import name 'Base' from partially initialized module
```

原因：

- `base.py` 导入模型
- 模型又从 `base.py` 导入 `Base`

解决：

- `base_class.py` 只定义 `Base`
- 模型从 `base_class.py` 导入 `Base`
- `base.py` 导入所有模型

### 15.6 `Base has no attribute sorted_tables`

原因：

Alembic 配置错了：

```python
target_metadata = Base
```

正确：

```python
target_metadata = Base.metadata
```

### 15.7 PostgreSQL 不支持 `DATETIME`

错误：

```text
type "datetime" does not exist
```

原因：

迁移里生成了：

```python
sa.DATETIME()
```

正确：

```python
sa.DateTime()
```

PostgreSQL 最终表结构中会显示：

```text
timestamp without time zone
```

### 15.8 `metadata` 是 SQLAlchemy 保留属性

不能在模型里直接使用：

```python
metadata = mapped_column(JSONB)
```

当前正确做法：

```python
extra_metadata = mapped_column("metadata", JSONB, nullable=False, default=dict)
```

### 15.9 `scalar()` 和 `scalars()` 混淆

错误：

```python
result.scalar().all()
```

正确：

```python
result.scalars().all()
```

区别：

- `scalar()`：取单个标量值。
- `scalars()`：从结果集中取模型对象序列。

### 15.10 测试中列表和字典混淆

错误：

```python
items["id"]
```

原因：

`items` 是列表。

正确：

```python
item["id"]
```

### 15.11 PATCH 误用 Create Schema

错误表现：

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required"
    }
  ]
}
```

原因：

PATCH 接口的参数仍然写成了：

```python
data: KnowledgeBaseCreate
```

所以即使只是更新 `description`，FastAPI 仍然要求请求体必须带 `name`。

正确：

```python
data: KnowledgeBaseUpdate
```

判断方法：

- 如果返回 422，并且 `loc` 指向 `body`，说明请求还没进入 service。
- 应先检查 API 函数参数类型和 schema。

### 15.12 测试没有先断言前置请求成功

错误表现：

```text
KeyError: 'id'
```

原因：

测试中先调用创建接口，但创建接口实际失败了。后续直接读取：

```python
created["id"]
```

错误响应里没有 `id`，所以报 `KeyError`。

正确做法：

```python
create_response = client.post("/api/knowledge-bases", json=payload)
assert create_response.status_code == 201

created = create_response.json()
```

这样能让错误停在真正失败的位置。

## 16. 核心理解

你现在已经理解并实践了：

- `main.py` 是应用入口，不写业务。
- `router.py` 聚合 API，不写复杂逻辑。
- `routes/*.py` 接收 HTTP 请求。
- `schemas/*.py` 定义请求和响应格式。
- `services/*.py` 写业务逻辑。
- `models/*.py` 定义数据库表结构。
- `db/session.py` 管理数据库连接和 session。
- `core/config.py` 管理配置。
- `core/logging.py` 管理日志。
- Alembic 管理数据库结构版本。
- pytest 固化接口行为。
- `POST`、`GET`、`PATCH`、`DELETE` 不只是 HTTP 方法不同，它们背后的业务语义也不同。
- 对知识库系统来说，删除通常应优先考虑软删除。

当前最重要的工程分层可以记成：

```text
API 层：处理 HTTP
Schema 层：定义数据边界
Service 层：处理业务
Model 层：映射数据库表
DB 层：管理连接和事务上下文
```

## 17. 复习检查题

可以用这些问题检查自己是否真正理解：

1. 为什么不要把所有接口都写在 `main.py`？
2. `api/router.py` 和 `api/routes/*.py` 有什么区别？
3. `schema` 和 `model` 有什么区别？
4. 为什么创建知识库时不允许前端传 `id`？
5. `db.add()`、`db.commit()`、`db.refresh()` 分别做什么？
6. `Depends(get_db)` 的作用是什么？
7. 为什么 `Base.metadata` 对 Alembic 很重要？
8. 为什么模型不能直接使用 `metadata` 作为属性名？
9. PostgreSQL 和 Redis 在本项目中的职责有什么不同？
10. 为什么当前知识库接口测试属于集成测试？
11. 为什么手工 curl 成功后还要写 pytest？
12. `scalar()` 和 `scalars()` 有什么区别？

这些问题如果都能讲清楚，说明当前阶段的工程骨架和知识库基础已经掌握得比较扎实。

补充复习题：

1. `POST` 和 `PATCH` 为什么不能共用同一个 schema？
2. `exclude_unset=True` 解决了什么问题？
3. 什么时候应该返回 422，什么时候应该返回 404？
4. 为什么知识库更适合软删除，而不是物理删除？
5. 测试里为什么要先断言 `create_response.status_code == 201`？
6. API 层的 `delete_knowledge_base_api` 和 service 层的 `disable_knowledge_base` 命名为什么可以不同？
