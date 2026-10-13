# 后台课时 / 等级管理（PRD 8.4）
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...dependencies import client_ip, get_current_admin, write_audit_log
from ...models import AdminAccount, Flashcard, Lesson, Level
from ...schemas import AdminLessonCreate, AdminLessonUpdate, AdminLevelUpdate

router = APIRouter(prefix="/api/admin", tags=["admin-lessons"])


def _lesson_to_dict(ls: Lesson, card_count: int = 0) -> dict:
    return {
        "id": ls.id, "level_id": ls.level_id, "title": ls.title,
        "description": ls.description, "lesson_type": ls.lesson_type,
        "sort_order": ls.sort_order, "status": ls.status,
        "content": ls.content or {}, "metadata": ls.metadata_ or {},
        "card_count": card_count,
        "published_at": ls.published_at.isoformat() if ls.published_at else None,
        "created_at": ls.created_at.isoformat() if ls.created_at else None,
    }


@router.get("/lessons")
async def list_lessons(
    level_id: int | None = Query(None),
    status_: str | None = Query(None, alias="status",
                                pattern="^(draft|published|archived)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(Lesson)
    cnt_q = select(func.count(Lesson.id))
    if level_id is not None:
        q, cnt_q = q.where(Lesson.level_id == level_id), cnt_q.where(Lesson.level_id == level_id)
    if status_:
        q, cnt_q = q.where(Lesson.status == status_), cnt_q.where(Lesson.status == status_)

    total = (await db.execute(cnt_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(Lesson.sort_order, Lesson.id).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    out = []
    for ls in rows:
        cnt = (await db.execute(
            select(func.count(Flashcard.id)).where(Flashcard.lesson_id == ls.id)
        )).scalar() or 0
        out.append(_lesson_to_dict(ls, cnt))
    return {"items": out, "total": total, "page": page, "page_size": page_size}


@router.post("/lessons", status_code=status.HTTP_201_CREATED)
async def create_lesson(
    body: AdminLessonCreate,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if not (await db.execute(select(Level).where(Level.id == body.level_id))).scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "所属等级不存在")

    data = body.model_dump()
    data["metadata_"] = data.pop("metadata", None)
    data["created_by"] = admin.user_id
    if data.get("status") == "published":
        data["published_at"] = datetime.now(timezone.utc)
    ls = Lesson(**data)
    db.add(ls)
    await db.flush()
    await write_audit_log(db, admin, "create_lesson", "lesson", ls.id,
                          {"title": ls.title}, client_ip(request))
    return _lesson_to_dict(ls)


@router.put("/lessons/{lesson_id}")
async def update_lesson(
    lesson_id: int,
    body: AdminLessonUpdate,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ls = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
    if not ls:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课时不存在")

    data = body.model_dump(exclude_unset=True)
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    changed = {}
    for k, v in data.items():
        if getattr(ls, k) != v:
            changed[k] = v
            setattr(ls, k, v)
    if changed:
        await write_audit_log(db, admin, "update_lesson", "lesson", lesson_id,
                              {"changed": changed}, client_ip(request))
    return _lesson_to_dict(ls)


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ls = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
    if not ls:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课时不存在")
    # 闪卡 lesson_id 为 ON DELETE SET NULL，不会被级联删除
    await db.execute(
        Flashcard.__table__.update().where(Flashcard.lesson_id == lesson_id)
        .values(lesson_id=None)
    )
    await db.delete(ls)
    await db.flush()
    await write_audit_log(db, admin, "delete_lesson", "lesson", lesson_id,
                          {"title": ls.title}, client_ip(request))
    return {"ok": True}


@router.post("/lessons/{lesson_id}/publish")
async def publish_lesson(
    lesson_id: int,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """发布课时：要求至少 1 张 published 闪卡"""
    ls = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
    if not ls:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课时不存在")

    cnt = (await db.execute(
        select(func.count(Flashcard.id)).where(
            Flashcard.lesson_id == lesson_id, Flashcard.status == "published")
    )).scalar() or 0
    if cnt == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该课时没有已发布的闪卡，无法发布")

    ls.status = "published"
    ls.published_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(db, admin, "publish_lesson", "lesson", lesson_id,
                          {"title": ls.title}, client_ip(request))
    return {"ok": True, "status": ls.status, "card_count": cnt}


@router.get("/levels")
async def admin_list_levels(
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(select(Level).order_by(Level.sort_order))).scalars().all()
    out = []
    for lv in rows:
        lesson_cnt = (await db.execute(
            select(func.count(Lesson.id)).where(Lesson.level_id == lv.id)
        )).scalar() or 0
        card_cnt = (await db.execute(
            select(func.count(Flashcard.id)).join(Lesson, Lesson.id == Flashcard.lesson_id)
            .where(Lesson.level_id == lv.id)
        )).scalar() or 0
        out.append({"id": lv.id, "code": lv.code, "name": lv.name,
                    "description": lv.description, "sort_order": lv.sort_order,
                    "is_active": lv.is_active, "lesson_count": lesson_cnt,
                    "card_count": card_cnt})
    return out


@router.put("/levels/{level_id}")
async def update_level(
    level_id: int,
    body: AdminLevelUpdate,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    lv = (await db.execute(select(Level).where(Level.id == level_id))).scalar_one_or_none()
    if not lv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "等级不存在")
    changed = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if getattr(lv, k) != v:
            changed[k] = v
            setattr(lv, k, v)
    if changed:
        await write_audit_log(db, admin, "update_level", "level", level_id,
                              {"changed": changed}, client_ip(request))
    return {"id": lv.id, "code": lv.code, "name": lv.name, "is_active": lv.is_active}
