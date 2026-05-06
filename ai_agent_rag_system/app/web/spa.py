'''
专门负责挂载 Vue SPA
'''
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings


def mount_spa(app:FastAPI) ->None:
    # /static/ 访问后段自己的静态文件
    # /assests/访问vue打包后的js/css/图片资源
    static_dir = Path(settings.static_dir)
    static_dir.mkdir(parents=True,exist_ok=True)
    # 将目录挂载到/static
    # 如果有 static/avatar.png,可以通过http://localhost:8000/static/avatar.png访问到
    app.mount("/static",StaticFiles(directory=static_dir),name="static")

    # 找到vue打包后目录
    frontend_dist_dir = Path(settings.frontend_dist_dir)
    index_file = frontend_dist_dir / "index.html"
    assets_dir = frontend_dist_dir / "assets"

    # 如果没有index.html就不挂载,dist/index.html
    if not index_file.exists():
        return

    # 挂载 assest目录,如果存在dist/assest 就挂载到 /assets
    if assets_dir.exists():
        app.mount("/assets",StaticFiles(directory=assets_dir),name="assets")

    #  fallback 路由 {full_path:path} 表示捕获任意层级路径。
    # /chat/session/123 则 full_path = "chat/session/123"
    @app.get("/{full_path:path}",include_in_schema=False)
    def spa_fallback(full_path:str) -> FileResponse:
        # /api/...路径不应该被vue fallback接管
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404,detail="API route should not be handled by SPA fallback")
        # 返回vue首页index.html
        return FileResponse(index_file)
