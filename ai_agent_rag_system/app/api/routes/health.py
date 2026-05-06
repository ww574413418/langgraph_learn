from fastapi import APIRouter
from app.db.redis import  check_redis_connection
from app.db.session import check_database_connection

router = APIRouter()

#get 结构,路径为空
@router.get("")
def health_check():
    '''
    请求路径为 /api/health
    :return:
    '''
    database_ok = check_database_connection()
    redis_ok = check_redis_connection()

    services = {
        "api":"ok",
        "database":"ok" if database_ok else "error",
        "redis":"ok" if redis_ok else "error",
    }

    status = "ok" if all (value == "ok" for value in services.values()) else "error"
    return {
        "status":status,
        "services":services
    }