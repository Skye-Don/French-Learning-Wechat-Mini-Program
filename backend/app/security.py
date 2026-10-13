# 安全工具：JWT + bcrypt（PRD 10.1 应用安全）
# 红线：JWT_SECRET/AppSecret 只存 .env，禁止入代码库；禁止在日志输出 token/openid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    # PRD 10.1：bcrypt cost=12
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int, role: str, admin: bool = False) -> str:
    """小程序 token 7 天；后台管理 token 2 小时（PRD 5.8）"""
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.JWT_ADMIN_EXPIRE_HOURS if admin else settings.JWT_EXPIRE_DAYS * 24
    )
    payload = {"sub": str(user_id), "role": role, "admin": admin, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
