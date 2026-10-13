# ============================================================
# 应用配置（PRD 19.1）
# 所有敏感值从环境变量读取，禁止写入代码库
# ============================================================
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "french_miniprogram"
    DB_USER: str = "french_admin"
    DB_PASSWORD: str = "changeme"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT
    JWT_SECRET: str = "changeme-generate-a-random-64-char-string"
    JWT_EXPIRE_DAYS: int = 7
    JWT_ADMIN_EXPIRE_HOURS: int = 2

    # 微信小程序
    WX_APPID: str = "changeme"
    WX_SECRET: str = "changeme"

    # 应用
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_LOG_LEVEL: str = "DEBUG"

    UPLOAD_DIR: str = "/app/uploads"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
