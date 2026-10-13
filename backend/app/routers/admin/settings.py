# 系统配置（PRD 8.4：仅 super_admin）
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...dependencies import client_ip, require_super_admin, write_audit_log
from ...models import AdminAccount, SystemSetting
from ...schemas import AdminSettingUpdate

router = APIRouter(prefix="/api/admin", tags=["admin-settings"])

# 首次启动时写入的默认配置（PRD 5.9 预留开关）
DEFAULT_SETTINGS = {
    "daily_goal_default": ("20", "新用户默认每日目标卡片数"),
    "sensitive_words_enabled": ("true", "是否启用敏感词汇 opt-in 机制"),
    "reminder_enabled": ("false", "全局订阅消息推送开关（V0 预留，不实际推送）"),
    "maintenance_mode": ("false", "维护模式：开启后小程序端提示维护中"),
}


async def ensure_defaults(db: AsyncSession) -> None:
    for key, (val, desc) in DEFAULT_SETTINGS.items():
        exist = (await db.execute(
            select(SystemSetting).where(SystemSetting.setting_key == key)
        )).scalar_one_or_none()
        if not exist:
            db.add(SystemSetting(setting_key=key, setting_value=val, description=desc))
    await db.flush()


@router.get("/settings")
async def list_settings(
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    await ensure_defaults(db)
    rows = (await db.execute(select(SystemSetting).order_by(SystemSetting.id))).scalars().all()
    return {"items": [
        {"setting_key": r.setting_key, "setting_value": r.setting_value,
         "description": r.description}
        for r in rows
    ]}


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    body: AdminSettingUpdate,
    request: Request,
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(SystemSetting).where(SystemSetting.setting_key == key)
    )).scalar_one_or_none()
    if not row:
        row = SystemSetting(setting_key=key, setting_value=body.value)
        db.add(row)
        await db.flush()

    old = row.setting_value
    row.setting_value = body.value
    await db.flush()
    await write_audit_log(db, admin, "update_setting", "system_setting", row.id,
                          {"key": key, "from": old, "to": body.value}, client_ip(request))
    return {"ok": True, "setting_key": key, "setting_value": row.setting_value}
