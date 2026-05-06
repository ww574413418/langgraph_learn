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

# 缓存配置对象，避免每次导入都重新读取 .env。
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
