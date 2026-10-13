# 管理员登录（PRD 5.8 / 8.4）
# 安全：bcrypt cost=12；连续 5 次失败锁定 30 分钟；token 2 小时
# 红线：日志禁止输出密码明文
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ...database import get_db
from ...dependencies import client_ip, get_current_admin, write_audit_log
from ...models import (
    AdminAccount, Checkin, Flashcard, FlashcardProgress, LearningRecord, Lesson, User,
)
from ...schemas import AdminLoginRequest
from ...security import create_token, verify_password

router = APIRouter(prefix="/api/admin", tags=["admin-auth"])

MAX_FAIL = 5
LOCK_MINUTES = 30


@router.post("/auth/login")
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    admin = (await db.execute(
        select(AdminAccount).where(AdminAccount.username == body.username)
    )).scalar_one_or_none()

    # 用户不存在时不暴露细节，统一报错（防用户名枚举）
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    # 锁定检查（PRD：5 次失败锁 30 分钟）
    now = datetime.now(timezone.utc)
    if admin.locked_until and admin.locked_until > now:
        remain = int((admin.locked_until - now).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_423_LOCKED, f"账号已锁定，请 {remain} 分钟后重试")

    if not verify_password(body.password, admin.password_hash):
        admin.login_fail_count += 1
        if admin.login_fail_count >= MAX_FAIL:
            admin.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            admin.login_fail_count = 0
        await write_audit_log(db, admin, "admin_login_fail", "admin_account", admin.id,
                              {"username": admin.username}, client_ip(request))
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已停用")

    admin.login_fail_count = 0
    admin.locked_until = None
    admin.last_login_at = now
    await write_audit_log(db, admin, "admin_login", "admin_account", admin.id,
                          {"username": admin.username}, client_ip(request))

    token = create_token(admin.id, admin.role, admin=True)
    return {
        "token": token,
        "expires_in": 7200,  # 2 小时
        "admin": {"id": admin.id, "username": admin.username, "role": admin.role},
    }


@router.post("/auth/logout")
async def admin_logout(admin: AdminAccount = Depends(get_current_admin)):
    """JWT 无状态，服务端不维护黑名单；前端删除 token 即完成登出"""
    return {"ok": True}


@router.get("/auth/me")
async def admin_me(admin: AdminAccount = Depends(get_current_admin)):
    return {"id": admin.id, "username": admin.username, "role": admin.role,
            "last_login_at": admin.last_login_at.isoformat() if admin.last_login_at else None}


@router.get("/dashboard")
async def dashboard(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """仪表盘：用户数 / 今日活跃 / 内容统计（PRD 5.8）"""
    CST = timezone(timedelta(hours=8))
    today = datetime.now(CST).date()
    day_start = datetime.combine(today, time(0, 0, 0), tzinfo=CST).astimezone(timezone.utc)
    day_end = day_start + timedelta(days=1)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )).scalar() or 0
    today_checkin = (await db.execute(
        select(func.count(Checkin.id)).where(Checkin.checkin_date == today)
    )).scalar() or 0
    total_cards = (await db.execute(select(func.count(Flashcard.id)))).scalar() or 0
    published_cards = (await db.execute(
        select(func.count(Flashcard.id)).where(Flashcard.status == "published")
    )).scalar() or 0
    total_lessons = (await db.execute(select(func.count(Lesson.id)))).scalar() or 0
    published_lessons = (await db.execute(
        select(func.count(Lesson.id)).where(Lesson.status == "published")
    )).scalar() or 0
    today_records = (await db.execute(
        select(func.count(LearningRecord.id)).where(
            LearningRecord.created_at >= day_start, LearningRecord.created_at < day_end)
    )).scalar() or 0
    mastered = (await db.execute(
        select(func.count(FlashcardProgress.id)).where(FlashcardProgress.status == "mastered")
    )).scalar() or 0

    return {
        "users": {"total": total_users, "active": active_users, "today_checkin": today_checkin},
        "content": {
            "total_cards": total_cards, "published_cards": published_cards,
            "total_lessons": total_lessons, "published_lessons": published_lessons,
        },
        "learning": {"today_records": today_records, "mastered_cards": mastered},
    }
