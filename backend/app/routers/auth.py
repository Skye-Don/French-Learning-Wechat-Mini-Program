# 认证路由（PRD 8.1：POST /api/auth/wx-login 等）
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, UserPreference
from ..schemas import UserPublic, WxLoginRequest, WxLoginResponse
from ..security import create_token
from ..wx_api import WxLoginError, code_to_openid

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/wx-login", response_model=WxLoginResponse)
async def wx_login(body: WxLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    微信登录（PRD 5.1）：
    前端只传 code；openid 一律由服务端换取，绝不允许前端上报。
    幂等：同一 openid 多次登录不重复建用户（users.wx_openid UNIQUE）。
    """
    try:
        wx = await code_to_openid(body.code)
    except WxLoginError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录失败，请稍后重试") from e

    openid = wx["openid"]
    result = await db.execute(select(User).where(User.wx_openid == openid))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(wx_openid=openid, wx_unionid=wx.get("unionid"), role="learner")
        db.add(user)
        await db.flush()
        db.add(UserPreference(user_id=user.id))
    user.last_login_at = datetime.now(timezone.utc)

    token = create_token(user.id, user.role)
    return WxLoginResponse(
        token=token,
        user=UserPublic.model_validate(user),
        is_new_user=is_new,
    )


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return UserPublic.model_validate(user)
