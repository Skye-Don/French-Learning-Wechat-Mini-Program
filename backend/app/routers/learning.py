# 用户/学习路由（PRD 8.2 / 8.3）
# - 北京时间（UTC+8）计算打卡日期（PRD 5.6）
# - 闪卡按 sensitive_opt_in 过滤（PRD 5.5）
# - flashcard_progress 走 UPSERT，天然幂等（PRD 5.5）
# - 打卡计数按当日 learning_records 实时回填，保证 summary/日历口径一致
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models import (
    Checkin, Flashcard, FlashcardProgress, LearningRecord, Lesson, Level, User, UserPreference,
)
from ..redis_client import CACHE_TTL_LEVELS, cache_get, cache_set
from ..schemas import (
    FlashcardOut, FlashcardPage, FlashcardProgressIn, FlashcardProgressOut,
    ReminderUpdateRequest, SensitiveOptInRequest,
)

router = APIRouter(prefix="/api", tags=["user & learning"])

CST = timezone(timedelta(hours=8))  # 北京时间


def today_cst() -> date:
    return datetime.now(CST).date()


def cst_day_utc_range(day: date) -> tuple[datetime, datetime]:
    """把北京时间某一天的 [00:00, 次日00:00) 换算成 UTC 区间。

    坑（PRD 12 时区陷阱）：created_at 存的是 UTC，而打卡日期按 UTC+8 算，
    直接 date(created_at)=today 会在 16:00-24:00 UTC 段漏统计。
    """
    start = datetime.combine(day, time(0, 0, 0), tzinfo=CST)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


async def _today_learned_count(db: AsyncSession, user_id: int, today: date) -> tuple[int, int, int]:
    """统计当日学习量：总张数 / 新学张数 / 总耗时秒"""
    start_utc, end_utc = cst_day_utc_range(today)
    rows = (await db.execute(
        select(LearningRecord.result, LearningRecord.duration_seconds,
               LearningRecord.reference_id)
        .where(LearningRecord.user_id == user_id,
               LearningRecord.record_type == "flashcard_review",
               LearningRecord.created_at >= start_utc,
               LearningRecord.created_at < end_utc)
    )).all()

    reviewed = len(rows)
    seconds = sum(r.duration_seconds or 0 for r in rows)
    # 新学 = 首次学到（该卡首次记录时间落在今天）
    first_seen = set()
    if rows:
        ids = [r.reference_id for r in rows if r.reference_id]
        if ids:
            first_rows = (await db.execute(
                select(LearningRecord.reference_id,
                       func.min(LearningRecord.created_at).label("first_at"))
                .where(LearningRecord.user_id == user_id,
                       LearningRecord.record_type == "flashcard_review",
                       LearningRecord.reference_id.in_(ids))
                .group_by(LearningRecord.reference_id)
            )).all()
            first_seen = {r.reference_id for r in first_rows
                          if r.first_at and r.first_at.astimezone(CST).date() == today}
    return reviewed, len(first_seen), seconds


async def refresh_today_checkin(db: AsyncSession, user: User, today: date) -> None:
    """把当日学习量回填进 checkins 行（幂等，可重复调用）"""
    ck = (await db.execute(
        select(Checkin).where(Checkin.user_id == user.id, Checkin.checkin_date == today)
    )).scalar_one_or_none()
    if not ck:
        return
    reviewed, new_learned, seconds = await _today_learned_count(db, user.id, today)
    ck.cards_reviewed = reviewed
    ck.new_cards_learned = new_learned
    ck.study_duration = seconds


# ---------------- 用户偏好 ----------------
@router.post("/user/preferences/sensitive-opt-in")
async def set_sensitive_opt_in(
    body: SensitiveOptInRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """敏感词汇 opt-in（PRD 5.2）。关闭后所有列表接口即时过滤"""
    user.sensitive_opt_in = body.sensitive_opt_in
    await db.flush()
    return {"sensitive_opt_in": body.sensitive_opt_in}


@router.put("/user/preferences/reminder")
async def update_reminder(
    body: ReminderUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pref = (await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )).scalar_one_or_none()
    if not pref:
        pref = UserPreference(user_id=user.id)
        db.add(pref)
    if body.reminder_enabled is not None:
        pref.reminder_enabled = body.reminder_enabled
    if body.reminder_time:
        try:
            hh, mm = body.reminder_time.split(":")[:2]
            pref.reminder_time = datetime.strptime(f"{hh.zfill(2)}:{mm.zfill(2)}", "%H:%M").time()
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "提醒时间格式应为 HH:MM")
    if body.reminder_days is not None:
        if not all(isinstance(d, int) and 1 <= d <= 7 for d in body.reminder_days):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "提醒星期取值应为 1-7")
        pref.reminder_days = body.reminder_days
    if body.daily_goal is not None:
        pref.daily_goal = body.daily_goal
    await db.flush()
    return {"ok": True, "reminder_enabled": pref.reminder_enabled,
            "reminder_time": pref.reminder_time.strftime("%H:%M") if pref.reminder_time else None,
            "reminder_days": pref.reminder_days, "daily_goal": pref.daily_goal}


@router.get("/user/today-summary")
async def today_summary(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    today = today_cst()
    pref = (await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )).scalar_one_or_none()
    goal = pref.daily_goal if pref else 20

    ck = (await db.execute(
        select(Checkin).where(Checkin.user_id == user.id, Checkin.checkin_date == today)
    )).scalar_one_or_none()
    if ck:
        await refresh_today_checkin(db, user, today)

    review_cnt = (await db.execute(
        select(func.count(FlashcardProgress.id)).where(
            FlashcardProgress.user_id == user.id,
            FlashcardProgress.status.in_(["learning", "review"]),
            (FlashcardProgress.next_review_date.is_(None))
            | (FlashcardProgress.next_review_date <= today),
        )
    )).scalar() or 0

    return {
        "date": today.isoformat(),
        "daily_goal": goal,
        "cards_learned_today": ck.cards_reviewed if ck else 0,
        "checked_in": bool(ck),
        "streak_days": user.streak_days,
        "review_count": review_cnt,
    }


# ---------------- 学习内容 ----------------
@router.get("/levels")
async def list_levels(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    cached = await cache_get("levels:active")
    if cached is not None:
        return cached

    lesson_count = (
        select(func.count(Lesson.id))
        .where(Lesson.level_id == Level.id, Lesson.status == "published")
        .correlate(Level)
        .scalar_subquery()
    )
    rows = (await db.execute(
        select(Level, lesson_count.label("lesson_count"))
        .where(Level.is_active.is_(True))
        .order_by(Level.sort_order)
    )).all()
    data = [
        {"id": lv.id, "code": lv.code, "name": lv.name, "description": lv.description,
         "sort_order": lv.sort_order, "lesson_count": cnt or 0}
        for lv, cnt in rows
    ]
    await cache_set("levels:active", data, CACHE_TTL_LEVELS)
    return data


@router.get("/levels/{level_id}/lessons")
async def list_lessons(
    level_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Lesson).where(Lesson.level_id == level_id, Lesson.status == "published")
        .order_by(Lesson.sort_order)
    )).scalars().all()

    out = []
    for ls in rows:
        q = select(func.count(Flashcard.id)).where(
            Flashcard.lesson_id == ls.id, Flashcard.status == "published")
        if not user.sensitive_opt_in:
            q = q.where(Flashcard.is_sensitive.is_(False))
        cnt = (await db.execute(q)).scalar() or 0
        out.append({"id": ls.id, "level_id": ls.level_id, "title": ls.title,
                    "description": ls.description, "lesson_type": ls.lesson_type,
                    "sort_order": ls.sort_order, "card_count": cnt})
    return out


@router.get("/lessons/{lesson_id}")
async def lesson_detail(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ls = (await db.execute(select(Lesson).where(Lesson.id == lesson_id))).scalar_one_or_none()
    if not ls:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课时不存在")
    return {"id": ls.id, "level_id": ls.level_id, "title": ls.title,
            "description": ls.description, "lesson_type": ls.lesson_type,
            "status": ls.status, "content": ls.content or {}, "metadata": ls.metadata_ or {}}


@router.get("/lessons/{lesson_id}/flashcards", response_model=FlashcardPage)
async def lesson_flashcards(
    lesson_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = [Flashcard.lesson_id == lesson_id, Flashcard.status == "published"]
    if not user.sensitive_opt_in:  # PRD 5.5：未 opt-in 过滤敏感卡
        base.append(Flashcard.is_sensitive.is_(False))

    total = (await db.execute(select(func.count(Flashcard.id)).where(*base))).scalar() or 0
    rows = (await db.execute(
        select(Flashcard).where(*base)
        .order_by(Flashcard.sort_order, Flashcard.id)
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return FlashcardPage(
        items=[FlashcardOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
    )


# ---------------- 学习进度 ----------------
@router.post("/flashcard-progress", response_model=FlashcardProgressOut)
async def record_progress(
    body: FlashcardProgressIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录学习结果 + 自动打卡（PRD 5.5 / 5.6）。幂等：UNIQUE(user_id, flashcard_id) UPSERT"""
    card = (await db.execute(
        select(Flashcard).where(Flashcard.id == body.flashcard_id)
    )).scalar_one_or_none()
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "闪卡不存在")
    if card.is_sensitive and not user.sensitive_opt_in:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "未开启敏感词汇学习")

    prog = (await db.execute(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user.id,
            FlashcardProgress.flashcard_id == card.id)
    )).scalar_one_or_none()

    today = today_cst()
    correct_add = 1 if body.result == "correct" else 0
    wrong_add = 1 if body.result == "wrong" else 0
    is_new_card = prog is None

    if prog:
        prog.repetitions += 1
        prog.correct_count += correct_add
        prog.wrong_count += wrong_add
        prog.last_review_date = today
        # V0 简化间隔（PRD 5.5 说明 V0 不实现完整 SM-2），V1 在 service 层替换为 SM-2
        prog.interval_days = min(2 ** max(1, prog.correct_count), 21) \
            if body.result == "correct" else 1
        prog.next_review_date = today + timedelta(days=prog.interval_days)
        prog.status = ("mastered" if prog.correct_count >= 5
                       else "review" if body.result == "correct" else "learning")
    else:
        prog = FlashcardProgress(
            user_id=user.id, flashcard_id=card.id,
            status="learning" if body.result != "correct" else "review",
            interval_days=2 if body.result == "correct" else 1,
            repetitions=1, last_review_date=today,
            next_review_date=today + timedelta(days=2 if body.result == "correct" else 1),
            correct_count=correct_add, wrong_count=wrong_add,
        )
        db.add(prog)

    db.add(LearningRecord(
        user_id=user.id, record_type="flashcard_review", reference_id=card.id,
        reference_type="flashcard", result=body.result,
        duration_seconds=(body.response_time_ms or 0) // 1000,
        extra_data={"lesson_id": body.lesson_id, "response_time_ms": body.response_time_ms,
                    "is_new": is_new_card},
    ))
    user.total_cards_learned += 1

    await auto_checkin(db, user)
    await db.flush()
    await refresh_today_checkin(db, user, today)

    return FlashcardProgressOut(
        status=prog.status,
        next_review_date=prog.next_review_date.isoformat() if prog.next_review_date else None,
        correct_count=prog.correct_count, wrong_count=prog.wrong_count,
    )


@router.get("/flashcard-progress/review-today")
async def review_today(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    today = today_cst()
    q = (
        select(Flashcard)
        .join(FlashcardProgress, FlashcardProgress.flashcard_id == Flashcard.id)
        .where(
            FlashcardProgress.user_id == user.id,
            FlashcardProgress.status.in_(["learning", "review"]),
            (FlashcardProgress.next_review_date.is_(None))
            | (FlashcardProgress.next_review_date <= today),
            Flashcard.status == "published",
        )
    )
    if not user.sensitive_opt_in:
        q = q.where(Flashcard.is_sensitive.is_(False))
    rows = (await db.execute(q)).scalars().all()
    return {"date": today.isoformat(), "total": len(rows),
            "items": [
                {"id": r.id, "front_text": r.front_text, "back_text": r.back_text,
                 "example_sentence": r.example_sentence, "example_translation": r.example_translation,
                 "difficulty": r.difficulty, "tags": r.tags or [], "is_sensitive": r.is_sensitive,
                 "lesson_id": r.lesson_id, "tip": r.tip, "front_audio_url": r.front_audio_url}
                for r in rows
            ]}


# ---------------- 打卡（PRD 5.6）----------------
async def auto_checkin(db: AsyncSession, user: User) -> Checkin:
    """同日幂等：UNIQUE(user_id, checkin_date)；昨天打过则 streak+1 否则归 1"""
    today = today_cst()
    exist = (await db.execute(
        select(Checkin).where(Checkin.user_id == user.id, Checkin.checkin_date == today)
    )).scalar_one_or_none()
    if exist:
        return exist

    yesterday = today - timedelta(days=1)
    streak = 1
    if user.last_checkin_date == yesterday:
        streak = (user.streak_days or 0) + 1
    elif user.last_checkin_date == today:
        streak = user.streak_days or 1

    checkin = Checkin(user_id=user.id, checkin_date=today)
    db.add(checkin)
    user.streak_days = streak
    user.longest_streak = max(user.longest_streak or 0, streak)
    user.last_checkin_date = today
    user.total_study_days += 1
    db.add(LearningRecord(user_id=user.id, record_type="checkin", result="success"))
    return checkin


@router.post("/checkins/auto")
async def checkin_auto(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    today = today_cst()
    existed = (await db.execute(
        select(Checkin).where(Checkin.user_id == user.id, Checkin.checkin_date == today)
    )).scalar_one_or_none() is not None
    ck = await auto_checkin(db, user)
    await db.flush()
    await refresh_today_checkin(db, user, today)
    return {"already_checked_in": existed, "checkin_date": ck.checkin_date.isoformat(),
            "streak_days": user.streak_days, "longest_streak": user.longest_streak,
            "cards_reviewed": ck.cards_reviewed, "new_cards_learned": ck.new_cards_learned}


@router.get("/checkins/calendar")
async def checkin_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Checkin)
        .where(Checkin.user_id == user.id, Checkin.checkin_date.like(month + "-%"))
        .order_by(Checkin.checkin_date)
    )).scalars().all()
    return {"month": month, "items": [
        {"checkin_date": r.checkin_date.isoformat(), "cards_reviewed": r.cards_reviewed,
         "new_cards_learned": r.new_cards_learned, "study_duration": r.study_duration}
        for r in rows
    ]}


# ---------------- 个人中心 ----------------
@router.get("/user/profile")
async def get_profile(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pref = (await db.execute(
        select(UserPreference).where(UserPreference.user_id == user.id)
    )).scalar_one_or_none()
    total_checkin = (await db.execute(
        select(func.count(Checkin.id)).where(Checkin.user_id == user.id)
    )).scalar() or 0
    mastered = (await db.execute(
        select(func.count(FlashcardProgress.id)).where(
            FlashcardProgress.user_id == user.id, FlashcardProgress.status == "mastered")
    )).scalar() or 0

    return {
        "id": user.id, "nickname": user.nickname, "avatar_url": user.avatar_url,
        "role": user.role, "current_level": user.current_level,
        "sensitive_opt_in": user.sensitive_opt_in,
        "total_study_days": user.total_study_days,
        "total_cards_learned": user.total_cards_learned,
        "streak_days": user.streak_days, "longest_streak": user.longest_streak,
        "total_checkin_days": total_checkin, "mastered_cards": mastered,
        "reminder_enabled": bool(pref and pref.reminder_enabled),
        "reminder_time": pref.reminder_time.strftime("%H:%M")
        if pref and pref.reminder_time else "20:00",
        "reminder_days": (pref.reminder_days if pref else None) or [1, 2, 3, 4, 5, 6, 7],
        "sound_enabled": bool(pref.sound_enabled) if pref else True,
        "daily_goal": pref.daily_goal if pref else 20,
    }
