# 学习记录

记录日期：2026-04-30

学习项目：`AI Agent Knowledge Workspace`

学习目标：通过一个具备工程落地能力的项目，串联 FastAPI、Vue、PostgreSQL、Redis、LangChain、LangGraph、Multi-Agent、RAG、父子 chunk、图片召回、流式输出和 Agent 工作流。

## 1. 当前学习状态

你已经完成或正在形成的基础：

- 已经有 LangGraph 学习笔记和实验代码。
- 已经学习过 LangGraph 的串行、分支、循环、持久化、短期记忆、人机交互、工具调用、流式输出等内容。
- 已经把旧的 LangGraph 学习资料整理到 `langgraph_learning/`。
- 已经明确不想再按零散知识点逐个学习，而是希望通过项目贯穿知识体系。

当前项目方向已经确定：

- 项目类型：AI Agent + RAG + 企业知识库 + 智能分析系统。
- 后端：FastAPI。
- 前端：Vue 3。
- 数据库：PostgreSQL。
- 缓存和任务状态：Redis。
- AI 编排：LangChain + LangGraph。
- RAG 增强：普通 chunk、父子 chunk、图片资产召回。
- 产品形态：类主流大模型聊天界面。

## 2. 已完成文档

项目文档：

- `development_plan.md`：系统开发总文档。
- `rag_design.md`：RAG 详细设计，包含父子 chunk 和图片资产召回。
- `frontend_design.md`：Vue 前端设计，包含历史会话、流式输出、停止生成、编辑消息、引用来源和图片预览。
- `learning_record.md`：当前学习记录。
- `teaching_plan.md`：后续教学教案。

## 3. 已明确的关键需求

### 3.1 后端能力

- FastAPI 工程结构。
- RESTful API。
- PostgreSQL 数据建模。
- Redis 缓存、任务状态和停止生成控制。
- 文档上传。
- 会话和消息管理。
- Agent 任务管理。

### 3.2 RAG 能力

- 支持普通 chunk。
- 支持父子 chunk。
- 支持 Word 文档图片抽取。
- 图片保存到资产表。
- 文档正文中图片替换为 URL 占位符。
- 检索时可以召回相关图片 URL。
- 回答结果中返回文本引用和图片资产。

### 3.3 Agent 能力

- 使用 LangGraph 实现状态机式 Multi-Agent。
- 初始 Agent 节点包括：
  - Router Agent。
  - Retriever Agent。
  - Analyzer Agent。
  - Planner Agent。
  - Reviewer Agent。
- 支持 Agent 执行轨迹记录。
- 支持思考过程在前端展示。

### 3.4 前端能力

- Vue 3 + Vite + TypeScript。
- 左侧历史会话。
- 主聊天窗口。
- 流式输出。
- 停止生成。
- 编辑用户消息。
- 重新生成 AI 回复。
- 展示 Agent 思考过程。
- 展示引用来源。
- 展示 RAG 召回图片。
- 知识库和文档管理页面。

## 4. 当前理解程度记录

| 模块 | 当前状态 | 后续目标 |
| --- | --- | --- |
| FastAPI | 已完成 Phase 0 基础实践 | 继续掌握依赖注入、错误处理、业务路由拆分 |
| PostgreSQL | 已完成容器检查、项目库创建和连接验证 | 能设计知识库、文档、chunk、会话、消息、任务表 |
| Redis | 已完成容器检查和连接验证 | 能用于任务状态、停止生成、缓存和限流 |
| LangChain | 待项目实践 | 能封装模型、prompt、retriever、tool |
| LangGraph | 已有学习基础 | 能实现真实 Multi-Agent 工作流 |
| RAG | 已明确设计方向 | 能实现普通 chunk、父子 chunk、图片召回 |
| Vue | 待项目实践 | 能实现类大模型产品的聊天工作台 |
| 工程化 | 已完成配置、依赖、测试、日志的基础实践 | 能用 Docker、测试、日志、配置完成可维护项目 |

## 5. 学习方式

本项目不采用“先学完全部理论再写项目”的方式，而采用：

1. 先提出真实工程需求。
2. 再拆成可实现的模块。
3. 每次只学当前模块所需知识。
4. 学完马上写代码。
5. 写完马上验证。
6. 最后总结为简历和面试表达。

## 6. 每日学习记录模板

后续每次学习可以按这个格式追加。

### 日期：YYYY-MM-DD

学习主题：

- 待记录

今天完成：

- 待记录

今天写了哪些代码：

- 待记录

今天理解的关键概念：

- 待记录

遇到的问题：

- 待记录

解决方式：

- 待记录

还不理解的地方：

- 待记录

下次继续：

- 待记录

### 日期：2026-04-30

学习主题：

- FastAPI 工程骨架、健康检查接口和配置模块。

今天完成：

- 创建后端基础目录中的第一批入口文件。
- 跑通 `GET /api/health` 健康检查接口。
- 确认 FastAPI Swagger 文档页面可以展示 `GET /api/health`。
- 初步接入 `app/core/config.py`，让应用名称和版本从配置读取。

今天写了哪些代码：

- `app/main.py`：FastAPI 应用入口，注册 API 总路由。
- `app/api/router.py`：聚合 API 路由。
- `app/api/routes/health.py`：定义健康检查接口。
- `app/core/config.py`：定义基础配置对象。

今天理解的关键概念：

- `main.py` 负责应用组装，不负责具体业务接口。
- `api/router.py` 负责汇总路由，不直接处理复杂业务。
- `routes/*.py` 负责具体 HTTP 接口。
- 路径由多层 prefix 拼接得到，例如 `/api` + `/health` + `""` = `/api/health`。
- `BaseSettings` 可以把配置从代码中抽离出来，后续支持 `.env` 和环境变量覆盖。

遇到的问题：

- `from api.router import api_router` 导致 `ModuleNotFoundError: No module named 'api'`。
- `@router` 写法错误导致 `TypeError: Router.__call__() missing receive and send`。
- 浏览器访问未注册路径时返回 `{"detail":"Not Found"}`。

解决方式：

- 在 `app/main.py` 中使用完整包路径：`from app.api.router import api_router`。
- 在健康检查接口中使用 `@router.get("")`，而不是 `@router`。
- 明确当前只注册了 `/api/health`，访问 `/` 或其他未注册路径会返回 404。

还不理解的地方：

- 后续需要继续理解 `.env`、`.env.example`、环境变量覆盖优先级。
- 后续需要继续理解配置模块如何服务数据库、Redis 和 LLM API Key。

下次继续：

- 学习 `.env` 和 `.env.example` 的区别。
- 创建本地配置模板。
- 检查 `.gitignore` 是否正确忽略本地敏感配置。

### 日期：2026-04-30

学习主题：

- 项目规划、文档体系和学习协作原则。

今天完成：

- 明确项目不再按零散知识点学习，而是通过一个完整项目串联知识。
- 确定项目方向为 AI Agent 企业知识库与智能分析系统。
- 创建 `development_plan.md`，作为系统开发总文档。
- 创建 `rag_design.md`，补充普通 chunk、父子 chunk、图片资产召回设计。
- 创建 `frontend_design.md`，明确 Vue 前端工作台设计。
- 创建 `learning_record.md`，用于持续记录学习过程。
- 创建 `teaching_plan.md`，用于约束后续教学节奏。
- 明确教学原则：没有明确要求代写代码时，AI 只教学和检查，不自动写代码。

今天写了哪些文档：

- `docs/development_plan.md`
- `docs/rag_design.md`
- `docs/frontend_design.md`
- `docs/learning_record.md`
- `docs/teaching_plan.md`

今天理解的关键概念：

- 这个项目的目标不是做最小 demo，而是做具备工程落地能力的系统。
- RAG 部分需要同时支持普通 chunk 和父子 chunk。
- Word 文档中的图片需要作为资产保存，并能通过上下文召回。
- 前端采用 Vue，但当前阶段不做前后端分离部署。
- 学习目标优先于开发速度，必须理解每一步为什么这样设计。

遇到的问题：

- 需要避免学习过程变成 AI 直接代写代码。

解决方式：

- 将“默认教学，不默认代写”的原则写入开发文档和教学教案。

下次继续：

- 从 Phase 0 工程骨架开始学习和实现。

### 日期：2026-04-30

学习主题：

- 本地配置管理：`.env`、`.env.example`、`.gitignore`。

今天完成：

- 确认 `.env` 是本地真实配置，不应该提交。
- 确认 `.env.example` 是配置模板，应该提交。
- 检查 `.gitignore` 中已经忽略 `.env`。
- 发现并清理误加入暂存区的 `.evn`。
- 创建 `.env.example`。
- 确认 Git 当前只追踪 `.env.example`，不追踪 `.env`。

今天写了哪些代码或配置：

- `ai_agent_rag_system/.env.example`

今天理解的关键概念：

- `.env` 保存真实配置，可能包含数据库密码和 API Key。
- `.env.example` 只保存模板，不能包含真实密钥。
- `.gitignore` 用来防止本地敏感文件进入 Git。
- Git 的 `AD` 状态表示文件曾经 add 进暂存区，但工作区中已经删除。

遇到的问题：

- Git 暂存区中出现了误拼写的 `ai_agent_rag_system/.evn`。

解决方式：

- 使用 `git restore --staged ai_agent_rag_system/.evn` 移除暂存区残留。

下次继续：

- 学习 `pyproject.toml` 和 Python 项目依赖管理。

### 日期：2026-04-30

学习主题：

- `pyproject.toml` 和 Python 项目依赖管理。

今天完成：

- 创建 `pyproject.toml`。
- 声明 FastAPI、Uvicorn、Pydantic Settings、SQLAlchemy、Alembic、psycopg、Redis、LangChain、LangGraph 等核心依赖。
- 声明 pytest、httpx、ruff 等开发依赖。
- 验证 `fastapi`、`sqlalchemy`、`redis`、`langgraph` 可以正常导入。

今天写了哪些代码或配置：

- `pyproject.toml`

今天理解的关键概念：

- `pyproject.toml` 是 Python 项目的工程配置文件。
- `dependencies` 是运行依赖。
- `optional-dependencies.dev` 是开发依赖。
- `build-system` 告诉 pip 如何构建项目。
- `tool.setuptools.packages.find` 用来限制只打包 Python 后端包，避免误打包 `data/`、`docs/`、`frontend/`。
- ruff 和 pytest 可以在 `pyproject.toml` 中集中配置。

遇到的问题：

- 暂无。

解决方式：

- 暂无。

下次继续：

- 学习 pytest 和 FastAPI TestClient。

### 日期：2026-04-30

学习主题：

- pytest 和 FastAPI TestClient。

今天完成：

- 创建 `tests/` 目录。
- 创建 `tests/test_health.py`。
- 使用 `TestClient` 测试 `/api/health`。
- 第一次运行 pytest 时发现没有收集到测试。
- 补齐测试文件后，pytest 通过，结果为 `1 passed`。

今天写了哪些代码：

- `tests/__init__.py`
- `tests/test_health.py`

今天理解的关键概念：

- pytest 会自动发现 `tests/` 下的 `test_*.py` 文件。
- `TestClient` 可以不启动 uvicorn，直接测试 FastAPI app。
- 自动化测试可以替代重复的手动 curl 验证。
- `pyproject.toml` 中的 `testpaths = ["tests"]` 指定测试目录。

遇到的问题：

- 第一次运行 pytest 时出现 `collected 0 items`，因为 `tests/` 目录不存在或测试文件未创建。

解决方式：

- 创建 `tests/__init__.py` 和 `tests/test_health.py`。

下次继续：

- 检查已有 Docker PostgreSQL / Redis 是否可以复用。

### 日期：2026-05-06

学习主题：

- 复用 Docker PostgreSQL / Redis，并创建项目专用数据库。

今天完成：

- 检查已有 Docker 容器。
- 确认 Redis 容器运行在 `localhost:6379`。
- 确认 PostgreSQL 容器运行在 `localhost:5432`，镜像为 `pgvector/pgvector:pg18`。
- 验证 Redis `PING` 返回 `PONG`。
- 验证 PostgreSQL 18.3 可用。
- 验证 pgvector 扩展可用。
- 创建 PostgreSQL 项目用户 `agent`。
- 创建项目数据库 `agent_workspace`。
- 在 `agent_workspace` 中启用 `vector` 扩展。
- 验证 `agent` 用户可以连接 `agent_workspace`。

今天写了哪些代码或配置：

- 无代码改动，主要是 Docker/PostgreSQL 环境验证和数据库初始化。

今天理解的关键概念：

- 不一定需要为项目新开 PostgreSQL / Redis 容器，可以复用已有服务。
- 复用已有 PostgreSQL 时，最好创建项目专用用户和项目专用数据库。
- PostgreSQL 存长期业务数据和 RAG chunk。
- Redis 存短期状态、缓存和停止生成标记。
- pgvector 是 PostgreSQL 的向量检索扩展，后续 RAG 向量字段依赖它。

遇到的问题：

- 创建数据库时遇到 `template1 collation version mismatch`。
- 因为 `agent_workspace` 尚未创建，第一次启用 vector 扩展失败。

解决方式：

- 刷新 `template1` 和 `postgres` 的 collation version。
- 重新创建 `agent_workspace`。
- 在 `agent_workspace` 中启用 `vector` 扩展。

下次继续：

- 学习 SQLAlchemy 数据库连接。

### 日期：2026-05-06

学习主题：

- SQLAlchemy 数据库连接。

今天完成：

- 创建 `app/db/session.py`。
- 使用 `settings.database_url` 创建 SQLAlchemy engine。
- 创建 `SessionLocal`。
- 创建 `get_db` 依赖函数。
- 创建 `check_database_connection` 验证函数。
- 成功连接 PostgreSQL `agent_workspace`，验证结果为 `True`。

今天写了哪些代码：

- `app/db/session.py`

今天理解的关键概念：

- `engine` 是数据库连接引擎，负责管理底层连接池。
- `SessionLocal` 是数据库会话工厂。
- `Session` 是一次数据库操作上下文。
- `get_db` 用于 FastAPI 依赖注入。
- 数据库地址从 `.env` 读取，不应该写死在业务代码里。
- `pool_pre_ping=True` 可以在连接池取连接时检查连接是否可用。

遇到的问题：

- 暂无。

解决方式：

- 暂无。

下次继续：

- 学习 Redis 连接。

### 日期：2026-05-06

学习主题：

- Redis 连接。

今天完成：

- 创建 `app/db/redis.py`。
- 使用 `settings.redis_url` 创建 Redis 客户端。
- 使用 `ping` 验证 Redis 连接。
- 成功连接 Docker Redis 容器，验证结果为 `True`。

今天写了哪些代码：

- `app/db/redis.py`

今天理解的关键概念：

- Redis 用于短期状态、缓存、限流和停止生成标记。
- Redis 不替代 PostgreSQL。
- `decode_responses=True` 可以让 Redis 返回字符串而不是 bytes。
- `Redis.from_url` 可以从配置统一创建客户端。

遇到的问题：

- 暂无。

解决方式：

- 暂无。

下次继续：

- 扩展健康检查接口，让 `/api/health` 同时检查 API、PostgreSQL、Redis。

### 日期：2026-05-06

学习主题：

- 扩展健康检查接口。

今天完成：

- 将 `/api/health` 从简单 API 检查升级为综合健康检查。
- 接入 PostgreSQL 连接检查。
- 接入 Redis 连接检查。
- 更新 `tests/test_health.py`。
- 使用 curl 验证综合健康检查通过。
- 使用 pytest 验证测试通过，结果为 `1 passed`。

今天写了哪些代码：

- `app/api/routes/health.py`
- `tests/test_health.py`

今天理解的关键概念：

- 健康检查不只是检查 API 是否启动。
- 工程项目需要检查核心依赖服务是否可用。
- PostgreSQL 和 Redis 属于外部依赖。
- 综合健康检查测试现在属于偏集成测试，因为它依赖外部服务。

遇到的问题：

- 暂无。

解决方式：

- 暂无。

下次继续：

- 学习日志系统。

### 日期：2026-05-06

学习主题：

- 日志系统。

今天完成：

- 创建 `app/core/logging.py`。
- 实现 `configure_logging()`。
- 在 `app/main.py` 中初始化日志。
- 使用 `logger.info("Application configured")` 验证日志输出。
- 使用 pytest 验证现有测试仍然通过。

今天写了哪些代码：

- `app/core/logging.py`
- `app/main.py`

今天理解的关键概念：

- `print` 适合临时调试，`logging` 适合工程项目。
- logging 支持日志级别：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。
- logger 名称通常来自 `__name__`。
- 日志格式可以包含时间、级别、模块名和消息。
- 日志系统是工程可维护性的基础。

遇到的问题：

- 暂无。

解决方式：

- 暂无。

下次继续：

- Phase 0 后端基础回顾。
- 补齐 README 或进入 Vue + Vite 前端骨架。

### 日期：2026-05-06

学习主题：

- Vue + Vite 前端骨架和 README。

今天完成：

- 创建 Vue 3 + Vite + TypeScript 前端工程。
- 接入 Pinia、Vue Router、Element Plus。
- 创建聊天工作台基础页面。
- 创建历史会话、消息列表、输入框、思考过程、引用来源、图片资产等前端组件。
- 使用本地 mock 数据验证聊天工作台交互。
- 执行 `npm install` 安装前端依赖。
- 执行 `npm run build` 完成前端构建检查。
- 创建项目 `README.md`，记录当前启动方式、技术栈、测试方式和下一步计划。
- 更新 `.gitignore`，忽略 `node_modules/`、`frontend/dist/`、`logs/`、`*.egg-info/` 等生成产物。

今天写了哪些代码或文档：

- `frontend/`
- `README.md`
- `.gitignore`

今天理解的关键概念：

- 开发模式下前端运行在 `localhost:5173`，后端运行在 `localhost:8000`。
- Vite 可以把 `/api/*` 代理到 FastAPI。
- 前端工作台先做骨架和 mock 交互，后续再接真实后端接口。
- `frontend/dist/` 是构建产物，不应该提交到 Git。
- README 是项目启动手册，需要记录环境、启动、测试和当前阶段。

遇到的问题：

- 第一次 `npm install` 无输出且疑似卡住。
- Vite dev server 在沙箱内直接监听 `0.0.0.0:5173` 遇到权限问题。
- FastAPI SPA fallback 一开始返回 404。

解决方式：

- 使用 npm 镜像 registry 完成依赖安装。
- 使用提升权限启动 Vite dev server。
- 检查 `frontend/dist/index.html`、`settings.frontend_dist_dir`、`mount_spa(app)` 和 fallback 路由写法。
- 修正 fallback 路由语法为 `/{full_path:path}`，并建议单独处理 `/` 根路径。

下次继续：

- Phase 1：数据库建模。
- 学习 SQLAlchemy Base、Alembic 和第一张业务表 `knowledge_bases`。

### 日期：2026-05-06

学习主题：

- SQLAlchemy Base、Alembic 和 `knowledge_bases` 表。

今天完成：

- 创建 `app/db/base_class.py`。
- 梳理 `base_class.py`、`base.py`、`models/*.py`、`migrations/env.py` 的职责。
- 创建 `KnowledgeBase` 模型。
- 配置 Alembic `target_metadata`。
- 生成 `knowledge_bases` 迁移文件。
- 检查迁移文件内容。
- 修复 DateTime 类型问题。
- 执行 `alembic upgrade head`。
- 验证 PostgreSQL 中 `knowledge_bases` 表创建成功。
- 验证 Alembic 当前版本为 `52e5ab4ad04f (head)`。

今天写了哪些代码：

- `app/db/base_class.py`
- `app/db/base.py`
- `app/models/knowledge_base.py`
- `migrations/env.py`
- `migrations/versions/52e5ab4ad04f_create_knowledge_bases.py`

今天理解的关键概念：

- `Base` 是所有 SQLAlchemy 模型的共同基类。
- `Base.metadata` 是 Alembic 自动生成迁移的依据。
- `base_class.py` 只定义 `Base`。
- `base.py` 导入 `Base` 和所有模型，供 Alembic 收集 metadata。
- 模型文件应该从 `base_class.py` 导入 `Base`，避免循环导入。
- `migrations/env.py` 应该使用 `target_metadata = Base.metadata`。
- Alembic revision 是数据库结构变更记录。
- `alembic upgrade head` 会把数据库升级到最新迁移版本。
- PostgreSQL 使用 `timestamp`，不支持 `DATETIME` 类型。
- `metadata` 是 SQLAlchemy 内部保留属性，模型中应使用 `extra_metadata` 映射数据库列名 `metadata`。

遇到的问题：

- `base.py` 和 `knowledge_base.py` 出现循环导入。
- Alembic 第一次生成空迁移。
- 误删了整个 `migrations/` 目录，导致 Alembic 找不到迁移目录。
- 重新初始化 Alembic 后，`migrations/env.py` 恢复成默认模板，`target_metadata = None`。
- `target_metadata` 曾错误配置为 `Base`，导致 `sorted_tables` 报错。
- 使用 `DATETIME` 导致 PostgreSQL 报 `type "datetime" does not exist`。

解决方式：

- 拆分 `app/db/base_class.py` 和 `app/db/base.py`。
- 让模型从 `app.db.base_class` 导入 `Base`。
- 让 `app/db/base.py` 导入所有模型，供 Alembic 收集 metadata。
- 重新配置 `migrations/env.py`：`target_metadata = Base.metadata`。
- 使用 SQLAlchemy 的 `DateTime`，而不是 `DATETIME`。
- 修改迁移文件中的 `sa.DATETIME()` 为 `sa.DateTime()` 后重新执行迁移。

下次继续：

- 创建 `KnowledgeBase` schema。
- 创建 `KnowledgeBaseService`。
- 实现 `POST /api/knowledge-bases` 和 `GET /api/knowledge-bases`。

### 日期：2026-05-07

学习主题：

- 知识库 CRUD、部分更新、软删除和接口测试。

今天完成：

- 实现 `KnowledgeBaseCreate`、`KnowledgeBaseRead`、`KnowledgeBaseUpdate`。
- 实现知识库创建、列表、详情、部分更新、软删除接口。
- 理解 `POST` 和 `PATCH` 使用不同 schema 的原因。
- 使用 `exclude_unset=True` 实现部分更新，避免未传字段被覆盖。
- 理解知识库系统为什么优先使用软删除。
- 补充知识库接口测试，覆盖创建、列表、详情、更新、删除、404 和非法 UUID。
- 新增第一份学习笔记 `study_notes.md`，整理 FastAPI 工程骨架和知识库 CRUD。

今天写了哪些代码或文档：

- `app/schemas/knowledge_base.py`
- `app/services/knowledge_base_service.py`
- `app/api/routes/knowledge_bases.py`
- `tests/test_knowledge_bases.py`
- `docs/study_notes.md`

今天理解的关键概念：

- API 层负责 HTTP 语义，service 层负责业务逻辑。
- 422 表示请求参数格式或请求体校验失败。
- 404 表示请求格式正确，但业务资源不存在。
- `KnowledgeBaseUpdate` 的字段应该都是可选。
- 软删除本质是把 `status` 改为 `disabled`，保留可追溯数据。
- 测试中如果后续依赖创建结果，应先断言创建请求成功。

遇到的问题：

- PATCH 接口误用了 `KnowledgeBaseCreate`，导致只更新 `description` 时仍要求 `name`。
- 测试路径写成 `api/knowledge-base`，导致创建失败后读取 `created["id"]` 报错。

解决方式：

- 将 PATCH 请求体类型改为 `KnowledgeBaseUpdate`。
- 统一使用正确路径 `/api/knowledge-bases`。
- 在测试中先断言 `create_response.status_code == 201`。

下次继续：

- 进入文档入库基础，设计 `documents` 表。

### 日期：2026-05-08

学习主题：

- `documents` 表、Alembic 迁移处理、Document API 和本地资料入库脚本准备。

今天完成：

- 设计 `Document` 模型，用于登记知识库下的文档元数据。
- 理解 `documents` 表不直接保存完整文件内容的原因。
- 理解文档处理状态 `uploaded`、`parsing`、`parsed`、`chunking`、`indexed`、`failed` 的作用。
- 生成并执行 `documents` 表迁移。
- 发现并删除重复生成的空迁移。
- 为 `file_hash` 补充索引迁移。
- 验证 `documents` 表、外键、`status` 索引、`knowledge_base_id` 索引、`file_hash` 索引。
- 实现 `DocumentCreate`、`DocumentRead`。
- 实现 Document 创建、列表、按知识库过滤、详情接口。
- 通过 curl 验证 Document 接口可用。
- 创建第二份学习笔记 `study_notes2.md`，用于后续文档入库和 RAG 数据基础记录。

今天写了哪些代码或文档：

- `app/models/document.py`
- `app/db/base.py`
- `app/schemas/document.py`
- `app/services/document_service.py`
- `app/api/routes/documents.py`
- `app/api/router.py`
- `migrations/versions/32bfadf5771c_create_documents.py`
- `migrations/versions/42abb46cdedc_add_document_file_hash_index.py`
- `docs/study_notes2.md`

今天理解的关键概念：

- `documents` 表保存文件元数据，不保存完整原始文件内容。
- `file_path` 指向文件位置，`file_hash` 用于判断文件内容是否重复或变化。
- 新增模型后必须在 `app/db/base.py` 导入，否则 Alembic 可能看不到模型。
- 已执行过的迁移不要随便修改，缺少的变更应通过新迁移补齐。
- 空迁移如果还没有执行，可以删除后重新生成正确迁移。
- `response_model` 字段必须和 ORM 模型属性对齐，否则数据库写入成功后仍可能响应序列化失败。

遇到的问题：

- Alembic 生成了重复的空迁移。
- `file_hash` 初始迁移中缺少索引。
- `DocumentRead` 中 `extra_metadata` 拼写错误，导致 `POST /api/documents` 返回 500。
- `list_documents` 初始实现中没有正确处理 `knowledge_base_id is None`，也没有加 where 过滤。

解决方式：

- 删除未执行的空迁移。
- 新增 `add document file hash index` 迁移。
- 将 `extra_metadate` 修正为 `extra_metadata`。
- 在 `list_documents` 中先定义基础 `select(Document)`，再根据可选查询参数追加 `.where(...)`。

下次继续：

- 学习本地资料入库脚本，扫描 `data/` 目录并自动登记文档。

### 日期：2026-05-09

学习主题：

- 本地资料入库脚本。

今天完成：

- 创建 `scripts/register_local_documents.py`。
- 实现文件类型识别函数 `detect_file_type`。
- 实现文件内容 hash 计算函数 `calculate_file_hash`。
- 实现 `data/` 目录递归扫描函数 `iter_files`。
- 实现通过 `file_hash` 判断文档是否已登记的函数 `document_exists`。
- 实现本地文档登记函数 `register_documents`。
- 将临时 `python -c` 调用升级为正式 CLI 参数调用。
- 使用 `--knowledge-base-id` 和 `--data-dir` 运行脚本。
- 验证脚本第一次运行可登记 6 个资料文件。
- 验证脚本第二次运行可以识别重复文件并跳过，具备幂等性。

今天写了哪些代码：

- `scripts/register_local_documents.py`

今天理解的关键概念：

- `scripts/` 适合放本地批处理、数据初始化和维护脚本。
- `app/api/routes/` 适合放对外 HTTP 请求入口。
- `file_hash` 是基于文件内容计算的指纹，比文件名更适合判断重复。
- 同名文件内容可能不同，不同名文件内容也可能相同。
- 幂等性表示同一个脚本重复执行，不会重复产生错误数据。
- `python -c` 适合临时验证，正式脚本应使用命令行参数。

遇到的问题：

- 脚本输出中只打印 hash，没有打印文件名，不利于排查。

解决方式：

- 后续建议将输出调整为同时包含文件路径和 hash，例如 `SKIP existing: {file_path} {file_hash}`。

下次继续：

- 学习文档解析入口：根据 `documents.file_path` 读取文件内容，为后续 chunk 切分做准备。

### 日期：2026-05-11

学习主题：

- 文档解析入口、Markdown 图片资产解析、`document_assets` 表和解析脚本。

今天完成：

- 创建 `app/rag/loaders.py`。
- 定义统一解析结果 `ParsedDocument`。
- 定义图片资产结构 `ParsedAsset`。
- 实现 txt 文本文件读取。
- 实现 Markdown 图片语法解析，将 `![](...)` 替换为 `[IMAGE:asset_xxx]` 占位符。
- 验证 `data/md/数组.md` 可以识别 6 张图片。
- 设计并创建 `document_assets` 表。
- 建立 `document_assets.document_id -> documents.id` 外键。
- 为 `document_id`、`asset_type`、`placeholder` 创建索引。
- 实现 `DocumentAssetCreate`、`DocumentAssetRead`。
- 实现 `DocumentAsset` service，包括创建、按文档列出、按 placeholder 查询。
- 实现 `save_parsed_assets`，把 Markdown 图片复制到 `app/static/assets/{document_id}/` 并写入 `document_assets`。
- 增加重复解析保护：同一文档下相同 placeholder 的 asset 不重复写入。
- 解析成功后将 `documents.status` 更新为 `parsed`。
- 解析失败时将 `documents.status` 更新为 `failed` 并记录 `error_message`。
- 创建正式解析脚本 `scripts/parse_registered_documents.py`。
- 验证解析脚本可以处理 `uploaded` 文档，并跳过暂未支持的 PDF 类型。
- 设计 `document_chunks` 表，支持普通 chunk 和父子 chunk。
- 讨论并确认 chunk 切分策略不采用简单硬切分，而是使用 LangChain 成熟 splitter。
- 明确采用 `MarkdownHeaderTextSplitter` 保留 Markdown 标题结构。
- 明确采用 `RecursiveCharacterTextSplitter` 做长度控制和 overlap。
- 明确借鉴 LangChain `ParentDocumentRetriever` 的父子 chunk 思路，但仍由本项目自己落库到 PostgreSQL。
- 对比 agent harness / learn-claude-code 类项目，理解 chunking 是底层索引，后续 Agent 还需要检索工具化和可追溯读取能力。

今天写了哪些代码：

- `app/rag/loaders.py`
- `app/models/document_asset.py`
- `app/schemas/document_asset.py`
- `app/services/document_asset_service.py`
- `app/services/document_parse_service.py`
- `scripts/parse_registered_documents.py`
- `migrations/versions/e349934e4513_create_document_assets.py`
- `app/models/document_chunk.py`
- `app/schemas/document_chunk.py`
- `app/services/document_chunk_service.py`
- `migrations/versions/e01cb6c9aa11_create_document_chunks.py`

今天理解的关键概念：

- 图片不应该直接塞进正文文本，而应该用 placeholder 保留位置，并把图片信息单独保存为 asset。
- Markdown 图片和 docx 图片来源不同，但后续都应该归一成 `ParsedAsset`。
- `storage_path` 给后端文件系统使用，`url` 给前端展示使用。
- `placeholder` 是稳定逻辑标识，URL 是可变化的展示地址。
- `document_assets` 独立成表，比塞进 `documents.metadata` 更适合查询、关联、维护和召回。
- 解析脚本应按 `status` 选择待处理文档。
- 暂未支持的文件类型不应该轻易标为 `failed`，可以先跳过等待后续 loader。
- 生产级 RAG 不应该只用固定字符数硬切文本。
- LangChain 的 splitter 可以承担底层切分能力，但业务系统仍需要自己维护 metadata、图片 placeholder、父子关系和数据库结构。
- 父子 chunk 的核心是 child 精准召回，parent 提供完整上下文。
- `start_char` 和 `end_char` 是溯源字段，不是保证语义完整的字段。

遇到的问题：

- 在 dataclass 中误用了 Pydantic 的 `Field`，导致初始化错误。
- Markdown loader 一开始没有生效，因为 `load_document` 先命中了通用 `SUPPORTED_FILE_TYPES` 分支。
- `alt_text` 初始迁移生成了 `nullable=False`，但 Markdown 图片 alt 文本可以为空。
- 直接 `python -c` 操作 ORM 时只导入了 `Document`，导致 SQLAlchemy metadata 中缺少 `knowledge_bases`，提交时出现外键解析错误。
- 解析脚本最初错误导入 `from models.document import Document`，导致 `ModuleNotFoundError`。
- PDF 暂未实现 loader，被解析脚本标记成 `failed`。
- 初始讨论中考虑过自研 splitter，但进一步分析后确认应优先使用 LangChain 成熟组件并封装业务层。
- `DocumentChunk` 模型中曾把 `embedding_model` 和 `metadata` 混在一起，需要拆成 `embedding_model` 和 `extra_metadata` 两个字段。

解决方式：

- dataclass 默认列表使用 `dataclasses.field(default_factory=list)`。
- `load_document` 按具体文件类型分支，`md` 单独走 `load_markdown_file`。
- 将 `alt_text` 改为 nullable。
- 在脚本入口导入 `from app.db import base`，触发所有模型注册。
- 所有项目内导入使用完整包路径 `app...`。
- 解析脚本查询条件先限制为当前支持的 `txt`、`text`、`md`，PDF 保持待处理状态。
- chunk 底层切分优先采用 `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter`。
- 父子 chunk 借鉴 `ParentDocumentRetriever` 思路，但将 parent/child 写入自有 `document_chunks` 表。
- `embedding_model` 用于记录向量模型名称，后续真正的向量字段再使用 `embedding`。

下次继续：

- 封装基于 LangChain splitter 的 normal / parent_child 切分服务，并将 chunk 写入 `document_chunks` 表。

### 日期：2026-05-13

学习主题：

- RAG 普通 chunk 切分策略、Markdown heading metadata、小块合并和 chunk 入库链路。

今天完成：

- 明确普通 chunk 不应该使用临时的字符硬切分，而应该基于成熟 splitter 进行工程封装。
- 对比并选择了 LangChain 的 `MarkdownTextSplitter` 和 `RecursiveCharacterTextSplitter`。
- 验证 `MarkdownTextSplitter` 能保留 Markdown 代码块格式，不会像 `MarkdownHeaderTextSplitter` 那样改写缩进。
- 在 Markdown 切分结果中补充 heading metadata，例如 `heading_1`、`heading_2`、`heading_3`。
- 实现普通 chunk 的小块合并策略，避免生成只有 ``` 或极短内容的无效 chunk。
- 将 `data/md/数组.md` 验证为 10 个更合理的 normal chunks。
- 初步跑通 `document_indexing_service`，把文档切分结果写入 `document_chunks` 表。

今天写了哪些代码：

- `app/rag/splitters.py`：封装 normal chunk 切分、Markdown heading 提取、小块合并。
- `app/models/document_chunk.py`：定义 `document_chunks` ORM 模型。
- `app/schemas/document_chunk.py`：定义 chunk 创建和读取 schema。
- `app/services/document_chunk_service.py`：封装 chunk 写入、查询和存在性判断。
- `app/services/document_indexing_service.py`：封装文档解析、切分、chunk 入库和文档状态更新。
- `migrations/versions/e01cb6c9aa11_create_document_chunks.py`：创建 `document_chunks` 表。

今天理解的关键概念：

- chunk 不是简单切字符串，而是要尽量保留语义边界、代码块、标题层级和图片占位符。
- Markdown 文档的 heading metadata 很重要，后续召回时可以帮助模型知道 chunk 属于哪个章节。
- 图片不要直接塞进文本内容，而是用 `[IMAGE:asset_001]` 这类占位符和 `document_assets` 表建立稳定映射。
- `content_hash` 可以用于判断内容重复，但 chunk 去重不能只看 `content_hash`，还要结合 `document_id`、`chunk_type`、`chunk_index`。
- 小块合并属于工程质量问题，可以减少低价值 chunk，提高召回上下文质量。
- 普通 chunk 和父子 chunk 应该共用 `document_chunks` 表，通过 `chunk_type` 和 `parent_id` 区分。

遇到的问题：

- 最初手写字符切分效果太粗糙，不符合生产可用要求。
- `MarkdownHeaderTextSplitter` 会改变 Markdown 内容格式，尤其是代码缩进。
- 只按 `content_hash` 判断 chunk 是否存在，会导致不同位置但内容相同的 chunk 被误跳过。
- 小块合并逻辑一开始缩进有问题，导致只返回了一个 chunk。
- 切分后的某些 chunk 会因为 overlap 以 ``` 开头，需要接受这是重叠上下文带来的结果，后续可继续优化。

解决方式：

- Markdown 文档使用 `MarkdownTextSplitter`，普通文本使用 `RecursiveCharacterTextSplitter`。
- 手动扫描 Markdown 标题，并根据 chunk 的 `start_char` / `end_char` 补充 heading metadata。
- 增加 `merge_small_chunks`，把过短 chunk 合并到前一个 chunk，并重新编号。
- chunk 存在性判断改为结合文档、类型、序号和内容 hash。
- 使用 `document_indexing_service` 承担“解析文档 -> 切分 -> 写 chunk -> 更新状态”的流程编排，`document_chunk_service` 只负责 chunk 数据库操作。

还不理解的地方：

- 父子 chunk 的 parent 和 child 应该如何选择不同大小，并在召回时如何返回 parent。
- 后续 embedding 字段应该如何和 pgvector 结合。
- 图片资产如何参与召回排序，以及图片 chunk 是否需要单独向量化。

下次继续：

- 用小块合并后的 splitter 重新清空并重建 `数组.md` 的 normal chunks。
- 封装批量 indexing 脚本，处理所有已经 parsed 的文档。
- 开始实现父子 chunk 切分与入库。

## 7. 里程碑记录

### Milestone 0：项目规划

状态：已完成 Phase 0 主要目标，后续继续完善细节。

已完成：

- 明确项目方向。
- 明确技术栈。
- 明确 RAG 增强需求。
- 明确 Vue 前端需求。
- 建立开发文档。
- 建立 RAG 设计文档。
- 建立前端设计文档。
- 跑通 FastAPI 健康检查接口。
- 初步接入配置模块。
- 创建 `.env.example`。
- 创建 `pyproject.toml`。
- 创建 pytest 基础测试。
- 验证 PostgreSQL、Redis、pgvector。
- 创建 PostgreSQL 项目用户和项目数据库。
- 接入 SQLAlchemy 数据库连接。
- 接入 Redis 连接。
- 扩展综合健康检查接口。
- 接入基础日志系统。
- 初始化 Vue + Vite 前端工程。
- 完成前端工作台骨架。
- 创建 README 基础说明。

待完成：

- 继续完善 FastAPI 静态文件挂载和 SPA fallback 细节。

### Milestone 1：工程骨架

状态：基本完成

目标：

- FastAPI 能启动。
- Vue 能启动。
- PostgreSQL 和 Redis 能连通。
- 健康检查接口可用。
- README 记录本地启动方式。

已完成：

- FastAPI 能启动。
- Vue 能启动。
- PostgreSQL 和 Redis 能连通。
- 健康检查接口可用。
- pytest 基础测试通过。
- 日志系统初步可用。
- README 已创建。

待完成：

- FastAPI 挂载前端静态资源。

### Milestone 2：会话和知识库基础

状态：知识库基础已完成，会话和消息待开始

目标：

- 支持知识库 CRUD。
- 支持会话和消息 CRUD。
- 前端能展示历史会话。

已完成：

- 创建 `knowledge_bases` 表。
- 建立 Alembic 迁移链路。
- 实现知识库 schema。
- 实现知识库 service。
- 实现知识库创建、列表、详情、部分更新和软删除接口。
- 补充知识库接口测试。

待完成：

- 实现会话和消息模型。

### Milestone 3：RAG 入库

状态：已开始

目标：

- 文档上传。
- 普通 chunk。
- 父子 chunk。
- Word 图片抽取。
- 图片 URL 替换。
- embedding 和 pgvector 入库。

已完成：

- 创建 `documents` 表。
- 建立 `documents` 与 `knowledge_bases` 的外键关系。
- 为 `knowledge_base_id`、`status`、`file_hash` 建立索引。
- 实现文档登记、列表、按知识库过滤和详情接口。
- 实现本地资料入库脚本。
- 支持扫描 `data/` 目录并登记文档。
- 支持通过 `file_hash` 跳过重复文件。
- 实现 txt / md 文档解析入口。
- 实现 Markdown 图片占位符解析。
- 创建 `document_assets` 表。
- 实现 Markdown 图片复制、URL 生成和资产入库。
- 实现解析脚本并更新文档状态。
- 创建 `document_chunks` 表。
- 实现普通 chunk 的 ORM、schema 和 service。
- 基于 LangChain splitter 封装 normal chunk 切分。
- 支持 Markdown heading metadata。
- 支持过短 chunk 合并。
- 初步跑通文档 normal chunk 入库链路。

待完成：

- 用小块合并后的策略重建并验证已入库 chunks。
- 批量 chunk indexing 脚本。
- 父子 chunk 切分与入库。
- docx 图片抽取与登记。
- PDF 解析。
- embedding 和 pgvector 入库。

### Milestone 4：RAG 问答

状态：未开始

目标：

- 文本问答。
- 引用来源。
- 图片资产召回。
- 流式输出。
- 停止生成。

### Milestone 5：Multi-Agent

状态：未开始

目标：

- LangGraph 工作流。
- Router / Retriever / Analyzer / Planner / Reviewer。
- Agent 执行轨迹。
- 前端展示思考过程。

### Milestone 6：工程化和展示

状态：未开始

目标：

- Docker Compose。
- 测试。
- 日志。
- README。
- 演示数据。
- 简历项目描述。
