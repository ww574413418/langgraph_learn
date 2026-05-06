from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
import logging
from app.core.logging import configure_logging
from app.web.spa import mount_spa


configure_logging()
log = logging.getLogger(__name__)

app = FastAPI(
    title = settings.app_name,
    version = settings.app_version
)

# 所有请求都以 /api 开头
# 最终路径为 /api/health
app.include_router(api_router,prefix="/api")
mount_spa(app)

log.info("Application configured")

