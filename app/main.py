"""FastAPI应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import os

from app.config import settings
from app.db import close_db, init_db
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[{settings.APP_NAME}] starting in {settings.APP_ENV} mode")
    await init_db()
    logger.info("database initialized")
    # 自动初始化角色数据
    from app.seed import seed
    await seed()
    yield
    await close_db()
    logger.info("database connection closed")


app = FastAPI(
    title=settings.APP_NAME,
    description="自适应自演化生活智能Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")

# 静态资源（前端）
_static_dir = os.path.join(os.path.dirname(__file__), "static")
_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
async def root():
    """前端主页"""
    return FileResponse(os.path.join(_templates_dir, "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
