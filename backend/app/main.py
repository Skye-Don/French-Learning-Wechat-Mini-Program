# FastAPI 应用入口（PRD 9 / 10）
# 安全：生产环境关闭 /docs 与 /openapi.json；CORS 白名单从 env 读取
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import engine
from .models import Base
from .routers import admin as admin_pkg
from .routers import auth as auth_router
from .routers import learning as learning_router
from .routers.admin import admin_auth_router

IS_PROD = settings.APP_ENV == "production"

logging.basicConfig(
    level=getattr(logging, settings.APP_LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("french")

app = FastAPI(
    title="法语学习小程序 API",
    version="0.1.0",
    # 生产环境关闭文档（PRD 10.1）
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# ---------- CORS：白名单来自环境变量，逗号分隔 ----------
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    max_age=86400,
)


# ---------- 请求日志（禁止输出 Authorization / token）----------
@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        logger.exception("unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "服务器内部错误"}, status_code=500)
    cost_ms = int((time.perf_counter() - start) * 1000)
    logger.info("%s %s -> %s (%dms)",
                request.method, request.url.path, response.status_code, cost_ms)
    response.headers["X-Response-Time"] = f"{cost_ms}ms"
    return response


# ---------- 路由注册 ----------
app.include_router(auth_router.router)
app.include_router(learning_router.router)
app.include_router(admin_auth_router)                      # /api/admin/auth/*
app.include_router(admin_pkg.admin_flashcards_router)      # /api/admin/flashcards/*
app.include_router(admin_pkg.admin_lessons_router)         # /api/admin/lessons/*、/levels/*
app.include_router(admin_pkg.admin_users_router)           # /api/admin/users/*
app.include_router(admin_pkg.admin_settings_router)        # /api/admin/settings/*
app.include_router(admin_pkg.audit_router)                 # /api/admin/audit-logs


@app.on_event("startup")
async def on_startup():
    """开发环境自动建表；生产环境请用 Alembic 迁移（见 alembic/）"""
    if not IS_PROD:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("dev mode: tables ensured via create_all")


@app.on_event("shutdown")
async def on_shutdown():
    await engine.dispose()


@app.get("/health")
async def health():
    """K8s/Docker 健康检查：不查库，避免 DB 抖动导致误判"""
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/health/db")
async def health_db():
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except Exception as e:  # noqa: BLE001
        logger.error("db health check failed: %s", type(e).__name__)
        return JSONResponse({"status": "degraded", "db": "down"}, status_code=503)
