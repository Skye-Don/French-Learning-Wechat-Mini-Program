# 后台闪卡管理（PRD 8.4：列表/创建/编辑/删除/批量导入）
# 每次写操作落 admin_audit_logs
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...dependencies import client_ip, get_current_admin, write_audit_log
from ...models import AdminAccount, Flashcard, Lesson
from ...schemas import AdminFlashcardBatch, AdminFlashcardCreate, AdminFlashcardUpdate

router = APIRouter(prefix="/api/admin", tags=["admin-flashcards"])


def _card_to_dict(c: Flashcard) -> dict:
    return {
        "id": c.id, "lesson_id": c.lesson_id, "front_text": c.front_text,
        "back_text": c.back_text, "example_sentence": c.example_sentence,
        "example_translation": c.example_translation, "tip": c.tip,
        "difficulty": c.difficulty, "tags": c.tags or [], "is_sensitive": c.is_sensitive,
        "status": c.status, "sort_order": c.sort_order,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("/flashcards")
async def list_cards(
    keyword: str = Query("", max_length=100),
    lesson_id: int | None = Query(None),
    status_: str | None = Query(None, alias="status",
                                pattern="^(draft|published|archived)$"),
    is_sensitive: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(Flashcard)
    cnt_q = select(func.count(Flashcard.id))
    if keyword:
        like = f"%{keyword}%"
        cond = or_(Flashcard.front_text.ilike(like), Flashcard.back_text.ilike(like),
                   Flashcard.tip.ilike(like), Flashcard.example_sentence.ilike(like))
        q, cnt_q = q.where(cond), cnt_q.where(cond)
    if lesson_id is not None:
        q, cnt_q = q.where(Flashcard.lesson_id == lesson_id), cnt_q.where(Flashcard.lesson_id == lesson_id)
    if status_:
        q, cnt_q = q.where(Flashcard.status == status_), cnt_q.where(Flashcard.status == status_)
    if is_sensitive is not None:
        q = q.where(Flashcard.is_sensitive.is_(is_sensitive))
        cnt_q = cnt_q.where(Flashcard.is_sensitive.is_(is_sensitive))

    total = (await db.execute(cnt_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(Flashcard.sort_order, Flashcard.id)
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return {"items": [_card_to_dict(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


@router.post("/flashcards", status_code=status.HTTP_201_CREATED)
async def create_card(
    body: AdminFlashcardCreate,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.lesson_id is not None:
        if not (await db.execute(select(Lesson).where(Lesson.id == body.lesson_id))).scalar_one_or_none():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "所属课时不存在")

    card = Flashcard(**body.model_dump())
    db.add(card)
    await db.flush()
    await write_audit_log(db, admin, "create_flashcard", "flashcard", card.id,
                          {"front_text": card.front_text}, client_ip(request))
    return _card_to_dict(card)


@router.post("/flashcards/batch", status_code=status.HTTP_201_CREATED)
async def batch_create_cards(
    body: AdminFlashcardBatch,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """批量导入：单事务，失败整体回滚（PRD 5.8）"""
    lesson_ids = {i.lesson_id for i in body.items if i.lesson_id is not None}
    if lesson_ids:
        exist = (await db.execute(
            select(Lesson.id).where(Lesson.id.in_(lesson_ids))
        )).scalars().all()
        missing = lesson_ids - set(exist)
        if missing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"课时不存在：{sorted(missing)}")

    cards = [Flashcard(**i.model_dump()) for i in body.items]
    db.add_all(cards)
    await db.flush()
    await write_audit_log(db, admin, "batch_create_flashcard", "flashcard", None,
                          {"count": len(cards)}, client_ip(request))
    return {"created": len(cards), "ids": [c.id for c in cards]}


@router.put("/flashcards/{card_id}")
async def update_card(
    card_id: int,
    body: AdminFlashcardUpdate,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    card = (await db.execute(select(Flashcard).where(Flashcard.id == card_id))).scalar_one_or_none()
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "闪卡不存在")

    changed = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if getattr(card, k) != v:
            changed[k] = v
            setattr(card, k, v)
    if changed:
        await write_audit_log(db, admin, "update_flashcard", "flashcard", card_id,
                              {"changed": changed}, client_ip(request))
    return _card_to_dict(card)


@router.delete("/flashcards/{card_id}")
async def delete_card(
    card_id: int,
    request: Request,
    admin: AdminAccount = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    card = (await db.execute(select(Flashcard).where(Flashcard.id == card_id))).scalar_one_or_none()
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "闪卡不存在")
    await db.delete(card)
    await db.flush()
    await write_audit_log(db, admin, "delete_flashcard", "flashcard", card_id,
                          {"front_text": card.front_text}, client_ip(request))
    return {"ok": True}
