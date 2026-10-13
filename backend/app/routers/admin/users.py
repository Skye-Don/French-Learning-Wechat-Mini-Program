# 后台用户管理（PRD 8.4：仅 super_admin）
# 红线：openid 属于敏感信息，列表接口只返回脱敏后缀
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...dependencies import client_ip, require_super_admin, write_audit_log
from ...models import AdminAccount, Checkin, User
from ...schemas import AdminUserStatusUpdate

router = APIRouter(prefix="/api/admin", tags=["admin-users"])


def _mask(openid: str | None) -> str | None:
    """脱敏：只保留后 4 位"""
    if not openid:
        return None
    return "***" + openid[-4:]


def _user_to_dict(u: User, checkin_days: int = 0) -> dict:
    return {
        "id": u.id, "nickname": u.nickname, "avatar_url": u.avatar_url,
        "role": u.role, "current_level": u.current_level,
        "wx_openid_masked": _mask(u.wx_openid),
        "sensitive_opt_in": u.sensitive_opt_in,
        "total_study_days": u.total_study_days,
        "total_cards_learned": u.total_cards_learned,
        "streak_days": u.streak_days, "longest_streak": u.longest_streak,
        "checkin_days": checkin_days,
        "is_active": u.is_active,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/users")
async def list_users(
    keyword: str = Query("", max_length=50),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(User)
    cnt_q = select(func.count(User.id))
    if keyword:
        like = f"%{keyword}%"
        cond = or_(User.nickname.ilike(like), User.current_level.ilike(like))
        q, cnt_q = q.where(cond), cnt_q.where(cond)
    if is_active is not None:
        q, cnt_q = q.where(User.is_active.is_(is_active)), cnt_q.where(User.is_active.is_(is_active))

    total = (await db.execute(cnt_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    out = []
    for u in rows:
        days = (await db.execute(
            select(func.count(Checkin.id)).where(Checkin.user_id == u.id)
        )).scalar() or 0
        out.append(_user_to_dict(u, days))
    return {"items": out, "total": total, "page": page, "page_size": page_size}


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    days = (await db.execute(
        select(func.count(Checkin.id)).where(Checkin.user_id == u.id)
    )).scalar() or 0
    return _user_to_dict(u, days)


@router.put("/users/{user_id}/status")
async def set_user_status(
    user_id: int,
    body: AdminUserStatusUpdate,
    request: Request,
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if u.role in ("admin", "super_admin") and not body.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能停用管理员账号")

    u.is_active = body.is_active
    await db.flush()
    await write_audit_log(db, admin, "set_user_status", "user", user_id,
                          {"is_active": body.is_active}, client_ip(request))
    return {"ok": True, "is_active": u.is_active}
