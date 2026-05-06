# AI Agent Knowledge Workspace

一个用于学习和实践的 AI Agent RAG 系统。项目目标是通过一套具备工程落地能力的系统，串联 FastAPI、Vue、PostgreSQL、Redis、LangChain、LangGraph、RAG、父子 chunk、图片资产召回和 Multi-Agent 工作流。

## 当前阶段

当前处于 Phase 0：工程骨架。

已完成：

- FastAPI 后端入口和 API 路由分层。
- `/api/health` 综合健康检查。
- 配置模块和 `.env.example`。
- PostgreSQL 项目库连接。
- Redis 连接。
- pgvector 扩展验证。
- pytest 基础测试。
- 基础日志系统，支持终端和本地滚动日志文件。
- Vue + Vite 前端工作台骨架。
- FastAPI 托管 Vue 构建产物的 SPA fallback 设计。

未完成：

- Phase 1 数据库业务模型。
- 知识库、文档、chunk、图片资产表。
- RAG 入库和检索。
- LangGraph Multi-Agent 工作流。
- 前端真实接口接入。

## 技术栈

后端：

- Python 3.11+
- FastAPI
- Pydantic Settings
- SQLAlchemy
- Alembic
- PostgreSQL + pgvector
- Redis
- pytest
- logging

前端：

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Element Plus
- markdown-it
- highlight.js

AI 应用层：

- LangChain
- LangGraph

## 本地服务

当前复用本地 Docker 容器：

```text
PostgreSQL: localhost:5432
Redis:      localhost:6379
```

PostgreSQL 项目配置：

```text
user:     agent
password: agent
database: agent_workspace
```

Redis 配置：

```text
redis://localhost:6379/0
```

## 环境配置

本地真实配置放在 `.env`，不要提交到 Git。

配置模板放在 `.env.example`，应该提交到 Git。

常用配置：

```env
APP_NAME="AI Agent Knowledge Workspace"
APP_VERSION="0.1.0"
ENVIRONMENT="local"
DEBUG=true

DATABASE_URL="postgresql+psycopg://agent:agent@localhost:5432/agent_workspace"
REDIS_URL="redis://localhost:6379/0"

LOG_LEVEL="INFO"
LOG_TO_FILE=true
LOG_FILE_PATH="logs/app.log"
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

## 后端启动

进入项目目录：

```bash
cd ai_agent_rag_system
```

安装依赖：

```bash
python -m pip install -e ".[dev]"
```

启动后端：

```bash
uvicorn app.main:app --reload
```

访问：

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/health
```

健康检查预期：

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

## 前端启动

进入前端目录：

```bash
cd ai_agent_rag_system/frontend
```

安装依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

访问：

```text
http://localhost:5173/
```

开发模式下，Vite 会把 `/api/*` 转发到：

```text
http://localhost:8000
```

## 前端构建和 FastAPI 托管

构建 Vue：

```bash
cd ai_agent_rag_system/frontend
npm run build
```

构建产物：

```text
frontend/dist/
```

启动 FastAPI 后，预期可以通过后端访问：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/chat
```

API 仍然走：

```text
http://127.0.0.1:8000/api/health
```

## 测试

运行后端测试：

```bash
cd ai_agent_rag_system
pytest
```

当前预期：

```text
1 passed
```

运行前端构建检查：

```bash
cd ai_agent_rag_system/frontend
npm run build
```

## 日志

日志默认同时输出到终端和本地文件：

```text
logs/app.log
```

日志文件由 `.gitignore` 忽略，不应该提交。

## 目录结构

```text
ai_agent_rag_system/
  app/
    api/          # API 路由
    core/         # 配置、日志、错误处理
    db/           # PostgreSQL / Redis 连接
    models/       # SQLAlchemy 模型
    schemas/      # Pydantic 请求和响应模型
    services/     # 业务逻辑
    rag/          # RAG 入库、检索、rerank、图片召回
    agents/       # LangGraph Multi-Agent
    web/          # Vue SPA 托管
  data/           # RAG 原始资料
  docs/           # 开发文档、学习记录、教案
  frontend/       # Vue 前端
  scripts/        # 一次性脚本
  tests/          # 自动化测试
```

## 下一步

Phase 0 收尾：

- 确认 FastAPI 托管 Vue SPA 的 `/` 和 `/chat` 路由正常。
- 完善 README 中的实际启动细节。

Phase 1：

- 建立 SQLAlchemy Base。
- 配置 Alembic。
- 设计知识库、文档、chunk、图片资产、会话、消息、Agent 任务模型。
- 创建第一版数据库迁移。
