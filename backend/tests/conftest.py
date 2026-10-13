# pytest 夹具：用内存/临时 SQLite 跑通全链路（无需真实 PostgreSQL/Redis）
# 目的：CI 与本地都能一键验证核心闭环（登录→选等级→学卡片→打卡→统计）
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 必须在 import app.* 之前设置，避免 config 读取真实 .env
os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("WX_APPID", "test-appid")
os.environ.setdefault("WX_SECRET", "test-secret")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "false")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

TEST_DB = "sqlite+aiosqlite:///./_test_french.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def prepare_db():
    """建表 + 依赖覆盖，整个 session 复用同一个文件库"""
    engine = create_async_engine(TEST_DB, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    yield
    await engine.dispose()
    # 注：不删除 _test_french.db（沙箱禁止删除文件），下次运行会 drop_all 重建
