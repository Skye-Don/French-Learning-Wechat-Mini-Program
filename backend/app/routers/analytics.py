# 用户行为埋点（V0 分析模块）
# 小程序端 utils/track.js 批量上报，这里负责落库与看板聚合。
# 事件类型白名单见 EVENT_TYPES；非白名单事件服务端直接丢弃，避免脏数据。
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user, require_admin_user
from ..models import Flashcard, LearningEvent, User
from ..schemas import AnalyticsDashboard, TrackBatch

# 允许上报的事件类型（其他一律拒绝）
EVENT_TYPES = (
    "app_launch", "lesson_open", "flashcard_study", "flashcard_review",
    "checkin", "level_select", "sensitive_opt_toggle",
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/track")
async def track_events(
    batch: TrackBatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """小程序端批量上报行为事件。单次最多 50 条（schema 拦截），按白名单落库。"""
    objs = []
    for e in batch.events:
        if e.event_type not in EVENT_TYPES:
            continue  # 非白名单跳过，不计入 accepted
        ref = None
        if e.payload and isinstance(e.payload, dict):
            raw = (e.payload.get("flashcard_id")
                   or e.payload.get("lesson_id")
                   or e.payload.get("reference_id"))
            ref = raw if isinstance(raw, int) and not isinstance(raw, bool) else None
        objs.append(LearningEvent(
            user_id=user.id, event_type=e.event_type, reference_id=ref, payload=e.payload,
        ))
    if objs:
        db.add_all(objs)
        await db.commit()
    return {"accepted": len(objs)}


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def analytics_dashboard(
    _admin: User = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """行为数据看板（仅管理员）：1日/7日活跃、事件量、热门卡片、等级分布。"""
    now = datetime.now(timezone.utc)
    d1 = now - timedelta(days=1)
    d7 = now - timedelta(days=7)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    active_1d = (await db.execute(
        select(func.count(func.distinct(LearningEvent.user_id))).where(LearningEvent.created_at >= d1)
    )).scalar() or 0
    active_7d = (await db.execute(
        select(func.count(func.distinct(LearningEvent.user_id))).where(LearningEvent.created_at >= d7)
    )).scalar() or 0
    events_1d = (await db.execute(
        select(func.count()).select_from(LearningEvent).where(LearningEvent.created_at >= d1)
    )).scalar() or 0
    events_7d = (await db.execute(
        select(func.count()).select_from(LearningEvent).where(LearningEvent.created_at >= d7)
    )).scalar() or 0

    top_rows = (await db.execute(
        select(LearningEvent.reference_id, func.count().label("c"))
        .where(LearningEvent.event_type.in_(["flashcard_study", "flashcard_review"]),
               LearningEvent.reference_id.isnot(None),
               LearningEvent.created_at >= d7)
        .group_by(LearningEvent.reference_id)
        .order_by(func.count().desc())
        .limit(10)
    )).all()
    top_ids = [r[0] for r in top_rows]
    fc_map = {}
    if top_ids:
        fcs = (await db.execute(
            select(Flashcard.id, Flashcard.front_text).where(Flashcard.id.in_(top_ids))
        )).all()
        fc_map = {r[0]: r[1] for r in fcs}
    top_cards_7d = [
        {"flashcard_id": r[0], "count": r[1], "front_text": fc_map.get(r[0])}
        for r in top_rows
    ]

    lvl_rows = (await db.execute(
        select(User.current_level, func.count().label("c")).group_by(User.current_level)
    )).all()
    level_distribution = [
        {"level": (r[0] or "未设置"), "count": r[1]} for r in lvl_rows
    ]

    return AnalyticsDashboard(
        total_users=total_users, active_users_1d=active_1d, active_users_7d=active_7d,
        events_1d=events_1d, events_7d=events_7d,
        top_cards_7d=top_cards_7d, level_distribution=level_distribution,
    )
