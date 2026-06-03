'''
定义配置类,它会自动从.env中读取值
'''
from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env", #读取当前目录下的.env
        env_file_encoding="utf-8"
    )

    app_name:str = "AI Agent Knowledge Workspce"
    app_version:str = "0.1.0"
    environment:str = "local"
    debug: bool = True

    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent_workspace"
    redis_url: str = "redis://localhost:6379/0"

    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5

    frontend_dist_dir: str = "frontend/dist" # Vue build 输出目录
    static_dir:str = "app/static" # 后端静态资源目录，后面可放上传文件、图片资产等

    # ===== Chat model 配置 =====
    # 后面 LangChain / LangGraph 调 LLM 时使用。
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_chat_model: str | None = None

    # ===== Embedding model 配置 =====
    # RAG indexing / retrieval 使用。
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "deterministic-test-embedding"

    # 维度必须显式配置。
    # 当前项目固定为 1024 维，因为 pgvector 字段会迁移为 vector(1024)。
    # 如果未来更换为 1536 / 3072 维模型，必须同步做数据库迁移并重新生成 embedding。
    embedding_dimensions: int = 1024

    # 网络超时，避免第三方平台卡住导致索引任务无限等待。
    embedding_timeout_seconds: float = 30.0

    # 批量 embedding 的最大 batch size。
    # 不同平台限制不同，建议通过配置控制。
    embedding_batch_size: int = 64

# 缓存配置对象，避免每次导入都重新读取 .env。
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
