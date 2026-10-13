# 审计日志查询（PRD 8.4：仅 super_admin）
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ...database import get_db
from ...dependencies import require_super_admin
from ...models import AdminAccount, AdminAuditLog

router = APIRouter(prefix="/api/admin", tags=["admin-audit"])


@router.get("/audit-logs")
async def list_audit_logs(
    action: str | None = Query(None, max_length=50),
    admin_id: int | None = Query(None),
    target_type: str | None = Query(None, max_length=50),
    target_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminAccount = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    operator = aliased(AdminAccount)
    q = (
        select(AdminAuditLog, operator.username.label("admin_name"))
        .join(operator, operator.id == AdminAuditLog.admin_id)
    )
    cnt_q = select(func.count(AdminAuditLog.id))
    if action:
        q = q.where(AdminAuditLog.action == action)
        cnt_q = cnt_q.where(AdminAuditLog.action == action)
    if admin_id is not None:
        q = q.where(AdminAuditLog.admin_id == admin_id)
        cnt_q = cnt_q.where(AdminAuditLog.admin_id == admin_id)
    if target_type:
        q = q.where(AdminAuditLog.target_type == target_type)
        cnt_q = cnt_q.where(AdminAuditLog.target_type == target_type)
    if target_id is not None:
        q = q.where(AdminAuditLog.target_id == target_id)
        cnt_q = cnt_q.where(AdminAuditLog.target_id == target_id)

    total = (await db.execute(cnt_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(AdminAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).all()

    return {"items": [
        {"id": log.id, "admin_id": log.admin_id, "admin_name": name, "action": log.action,
         "target_type": log.target_type, "target_id": log.target_id,
         "detail": log.detail or {}, "ip_address": log.ip_address,
         "created_at": log.created_at.isoformat() if log.created_at else None}
        for log, name in rows
    ], "total": total, "page": page, "page_size": page_size}
