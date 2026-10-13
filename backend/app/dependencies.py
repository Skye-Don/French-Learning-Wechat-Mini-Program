# FastAPI 依赖：当前用户 / 管理员 / 角色权限（PRD 3.1 权限矩阵）
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import AdminAccount, User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------- 小程序端用户 ----------------
async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Bearer Token 解出用户；401 由前端触发静默重登"""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    payload = decode_token(cred.credentials)
    if not payload or payload.get("admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录态无效或已过期")

    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已禁用")
    return user


async def require_admin_user(user: User = Depends(get_current_user)) -> User:
    """learner 不可访问管理接口（PRD 13.3 权限测试）"""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权限访问")
    return user


# ---------------- 后台管理员（PRD 5.8）----------------
async def get_current_admin(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminAccount:
    """后台 token：payload.admin=True，2 小时过期"""
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    payload = decode_token(cred.credentials)
    if not payload or not payload.get("admin"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "后台登录态无效或已过期")

    admin = (await db.execute(
        select(AdminAccount).where(AdminAccount.id == int(payload["sub"]))
    )).scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "管理员不存在或已停用")
    return admin


async def require_super_admin(admin: AdminAccount = Depends(get_current_admin)) -> AdminAccount:
    """仅 super_admin 可见：用户管理 / 审计日志 / 系统配置"""
    if admin.role != "super_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅超级管理员可访问")
    return admin


def client_ip(request: Request) -> str:
    """审计日志取 IP：优先 Nginx 透传头"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


async def write_audit_log(
    db: AsyncSession,
    admin: AdminAccount,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """所有后台写操作落审计日志（PRD 5.8 / 表 admin_audit_logs）"""
    from .models import AdminAuditLog  # 局部导入避免循环依赖

    db.add(AdminAuditLog(
        admin_id=admin.id, action=action, target_type=target_type,
        target_id=target_id, detail=detail, ip_address=ip,
        created_at=datetime.now(timezone.utc),
    ))
