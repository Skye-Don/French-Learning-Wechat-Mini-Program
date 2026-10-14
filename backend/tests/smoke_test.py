# 端到端冒烟测试：覆盖 V0 核心闭环（PRD 13 测试要点）
# 运行：cd backend && pytest tests/ -v
# 说明：用 SQLite + 依赖覆盖，不需要真实 PostgreSQL / Redis
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import (
    AdminAccount, Flashcard, FlashcardProgress, Lesson, Level, User, UserPreference,
)
from app.security import create_token, hash_password
from sqlalchemy import select


async def _seed_content(session_factory):
    """灌入最小可用内容：1 等级 / 1 课时 / 3 张闪卡（含 1 张敏感卡）。幂等，可重复调用"""
    async with session_factory() as db:
        exist = (await db.execute(select(Level).where(Level.code == "A1"))).scalar_one_or_none()
        if exist:
            ls = (await db.execute(
                select(Lesson).where(Lesson.level_id == exist.id))).scalars().first()
            cards = (await db.execute(
                select(Flashcard.id).where(Flashcard.lesson_id == ls.id)
                .order_by(Flashcard.sort_order))).scalars().all()
            return exist.id, ls.id, list(cards)

        lv = Level(code="A1", name="A1 - 入门级", description="零基础日常法语", sort_order=1)
        db.add(lv)
        await db.flush()

        ls = Lesson(level_id=lv.id, title="日常打招呼", lesson_type="phrase",
                    status="published", sort_order=1)
        db.add(ls)
        await db.flush()

        cards = [
            Flashcard(lesson_id=ls.id, front_text="Salut", back_text="你好／嗨（熟人之间）",
                      example_sentence="Salut, ça va ?", example_translation="嗨，最近怎么样？",
                      tip="白天晚上都能用，但只用于朋友和同龄人，对老板要说 Bonjour",
                      difficulty="A1", tags=["日常"], status="published", sort_order=1),
            Flashcard(lesson_id=ls.id, front_text="Ça marche", back_text="行／没问题",
                      example_sentence="On se voit à 20h ? — Ça marche.",
                      example_translation="晚上8点见？——没问题。",
                      tip="教科书只教 D'accord，法国人口语高频用 Ça marche",
                      difficulty="A2", tags=["口语"], status="published", sort_order=2),
            Flashcard(lesson_id=ls.id, front_text="Merde", back_text="该死／糟了（脏话）",
                      tip="法国最常用的宣泄词，正式场合绝对不要说",
                      difficulty="B1", tags=["脏话"], is_sensitive=True,
                      status="published", sort_order=3),
        ]
        db.add_all(cards)
        await db.commit()
        return lv.id, ls.id, [c.id for c in cards]


async def _mk_admin(session_factory, username="admin", role="super_admin"):
    async with session_factory() as db:
        admin = AdminAccount(username=username, password_hash=hash_password("Admin@12345"),
                             role=role)
        db.add(admin)
        await db.commit()
        return admin.id


def _session_factory():
    """从 app.dependency_overrides 里取出测试用 sessionmaker"""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    engine = create_async_engine("sqlite+aiosqlite:///./_test_french.db", future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_full_learning_loop():
    """核心闭环：登录 → 等级 → 课时 → 闪卡 → 敏感过滤 → 学习 → 打卡 → 统计"""
    from app.database import get_db
    import app.main as main_mod

    sf = _session_factory()
    level_id, lesson_id, card_ids = await _seed_content(sf)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) 未带 token 访问受保护接口 → 401
        r = await client.get("/api/levels")
        assert r.status_code == 401, r.text

        # 2) 造一个测试用户并直接签发 token（真实环境走 wx.login + code 换取）
        async with sf() as db:
            user = User(wx_openid="test-openid-0001", nickname="测试用户", role="learner")
            db.add(user)
            await db.flush()
            db.add(UserPreference(user_id=user.id))
            await db.commit()
            uid = user.id
        token = create_token(uid, "learner")
        h = {"Authorization": f"Bearer {token}"}

        # 3) 等级列表
        r = await client.get("/api/levels", headers=h)
        assert r.status_code == 200 and len(r.json()) == 1
        assert r.json()[0]["lesson_count"] == 1

        # 4) 敏感词未 opt-in → 只返回 2 张
        r = await client.get(f"/api/lessons/{lesson_id}/flashcards", headers=h)
        assert r.status_code == 200
        assert r.json()["total"] == 2, "未 opt-in 时必须过滤敏感卡"
        assert all(not c["is_sensitive"] for c in r.json()["items"])

        # 5) 直接学敏感卡 → 403
        r = await client.post("/api/flashcard-progress", headers=h,
                              json={"flashcard_id": card_ids[2], "result": "correct"})
        assert r.status_code == 403

        # 6) opt-in 后 → 3 张
        r = await client.post("/api/user/preferences/sensitive-opt-in", headers=h,
                              json={"sensitive_opt_in": True})
        assert r.json()["sensitive_opt_in"] is True
        r = await client.get(f"/api/lessons/{lesson_id}/flashcards", headers=h)
        assert r.json()["total"] == 3

        # 7) 连续学两张（触发自动打卡）
        for cid in card_ids[:2]:
            r = await client.post("/api/flashcard-progress", headers=h,
                                  json={"flashcard_id": cid, "result": "correct",
                                        "lesson_id": lesson_id, "response_time_ms": 3200})
            assert r.status_code == 200, r.text
            assert r.json()["correct_count"] >= 1

        # 8) 今日汇总：打卡已生成且学习量已回填
        r = await client.get("/api/user/today-summary", headers=h)
        s = r.json()
        assert s["checked_in"] is True
        assert s["cards_learned_today"] == 2, f"学习量回填错误：{s}"
        assert s["streak_days"] == 1

        # 9) 重复打卡幂等：streak 不重复 +1
        r = await client.post("/api/checkins/auto", headers=h)
        assert r.json()["already_checked_in"] is True
        assert r.json()["streak_days"] == 1

        # 10) 复习队列：答对的卡间隔 2 天，今天不应再进复习
        r = await client.get("/api/flashcard-progress/review-today", headers=h)
        assert r.status_code == 200
        assert r.json()["total"] == 0, "答对后应间隔 2 天才进复习队列"

        # 11) 打卡日历
        today = date.today().isoformat()
        r = await client.get(f"/api/checkins/calendar?month={today[:7]}", headers=h)
        assert r.status_code == 200 and len(r.json()["items"]) == 1

        # 12) 个人中心
        r = await client.get("/api/user/profile", headers=h)
        p = r.json()
        assert p["total_cards_learned"] == 2
        assert p["total_checkin_days"] == 1
        assert p["sensitive_opt_in"] is True


@pytest.mark.asyncio
async def test_admin_flow_and_permissions():
    """后台：登录 → 建卡 → 审计日志；普通用户不可访问"""
    sf = _session_factory()
    await _mk_admin(sf)
    _, lesson_id, card_ids = await _seed_content(sf)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) 错误密码 → 401
        r = await client.post("/api/admin/auth/login",
                              json={"username": "admin", "password": "wrong-password"})
        assert r.status_code == 401

        # 2) 正确密码 → token
        r = await client.post("/api/admin/auth/login",
                              json={"username": "admin", "password": "Admin@12345"})
        assert r.status_code == 200, r.text
        ah = {"Authorization": f"Bearer {r.json()['token']}"}

        # 3) 仪表盘
        r = await client.get("/api/admin/dashboard", headers=ah)
        assert r.status_code == 200 and "users" in r.json()

        # 4) 建卡
        r = await client.post("/api/admin/flashcards", headers=ah,
                              json={"lesson_id": lesson_id, "front_text": "Grave",
                                    "back_text": "非常／超（口语）",
                                    "tip": "C'est grave bien = 超棒，口语里不是'严重的'",
                                    "difficulty": "A2", "tags": ["口语"], "status": "published"})
        assert r.status_code == 201, r.text
        new_id = r.json()["id"]

        # 5) 改卡
        r = await client.put(f"/api/admin/flashcards/{new_id}", headers=ah,
                             json={"back_text": "非常／超（年轻人高频口语）"})
        assert r.json()["back_text"].endswith("口语）")

        # 6) 批量导入
        r = await client.post("/api/admin/flashcards/batch", headers=ah, json={"items": [
            {"lesson_id": lesson_id, "front_text": "Bof", "back_text": "嗯…一般般",
             "tip": "配合耸肩，表示不以为然", "status": "published"},
            {"lesson_id": lesson_id, "front_text": "Du coup", "back_text": "所以／于是",
             "tip": "口语连接词，法国人一分钟能说好几次", "status": "published"},
        ]})
        assert r.json()["created"] == 2

        # 7) 列表搜索
        r = await client.get("/api/admin/flashcards?keyword=Grave", headers=ah)
        assert r.json()["total"] == 1

        # 8) 删卡
        r = await client.delete(f"/api/admin/flashcards/{new_id}", headers=ah)
        assert r.json()["ok"] is True

        # 9) 审计日志有记录
        r = await client.get("/api/admin/audit-logs", headers=ah)
        assert r.json()["total"] >= 5
        actions = {i["action"] for i in r.json()["items"]}
        assert "create_flashcard" in actions

        # 10) 小程序端 token 访问后台 → 401（admin 分支校验）
        async with sf() as db:
            u = (await db.execute(select(User).where(User.wx_openid == "test-openid-0001"))
                 ).scalar_one_or_none()
            if u is None:
                u = User(wx_openid="test-openid-0001", role="learner")
                db.add(u)
                await db.commit()
        learner_h = {"Authorization": f"Bearer {create_token(u.id, 'learner')}"}
        r = await client.get("/api/admin/flashcards", headers=learner_h)
        assert r.status_code == 401

        # 11) 无 token → 401
        r = await client.get("/api/admin/dashboard")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_cefr_difficulty_levels():
    """难度等级必须是 A1/A2/B1/B2：合法值放行，越界值（含旧的数字 1-5）一律 422。

    对应需求变更：后台难度由 1-5 数字改为 CEFR 等级。
    """
    sf = _session_factory()
    level_id, lesson_id, _ = await _seed_content(sf)
    await _mk_admin(sf, username="cefr-admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/admin/auth/login",
                              json={"username": "cefr-admin", "password": "Admin@12345"})
        assert r.status_code == 200, r.text
        h = {"Authorization": f"Bearer {r.json()['token']}"}

        base = {"lesson_id": lesson_id, "front_text": "Ça marche",
                "back_text": "行／没问题", "status": "published"}

        # 1) 四个合法等级都能建
        for lvl in ("A1", "A2", "B1", "B2"):
            r = await client.post("/api/admin/flashcards", headers=h,
                                  json={**base, "front_text": base["front_text"] + lvl,
                                        "difficulty": lvl})
            assert r.status_code == 201, f"{lvl} 应当放行，实际 {r.status_code}: {r.text}"

        # 2) 越界等级（C1 / 数字 / 空）全部 422
        for bad in ("C1", 3, 1, 9, "a1x", ""):
            r = await client.post("/api/admin/flashcards", headers=h,
                                  json={**base, "difficulty": bad})
            assert r.status_code == 422, f"{bad!r} 应当被拒，实际 {r.status_code}"

        # 3) 默认值 = A1
        r = await client.post("/api/admin/flashcards", headers=h, json=base)
        assert r.status_code == 201
        r = await client.get("/api/admin/flashcards?keyword=Ça marche", headers=h)
        assert any(c["difficulty"] == "A1" for c in r.json()["items"])

        # 4) 按等级筛选
        r = await client.get("/api/admin/flashcards?level=B2", headers=h)
        assert r.status_code == 200
        assert all(c["difficulty"] == "B2" for c in r.json()["items"])

        # 5) 非法筛选值 → 422
        r = await client.get("/api/admin/flashcards?level=C2", headers=h)
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_analytics_track_and_dashboard():
    """V0 行为埋点：小程序上报 → 看板聚合。

    对应需求：用户行为数据分析（埋点选 A 方案）。
    """
    sf = _session_factory()
    _, lesson_id, card_ids = await _seed_content(sf)
    await _mk_admin(sf, username="analytics-admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1) 未登录上报 → 401
        r = await client.post("/api/analytics/track", json={"events": [
            {"event_type": "app_launch", "payload": {}},
        ]})
        assert r.status_code == 401

        # 2) 造用户 + token
        async with sf() as db:
            u = User(wx_openid="test-openid-analytics", nickname="埋点用户", role="learner")
            db.add(u)
            await db.flush()
            db.add(UserPreference(user_id=u.id))
            await db.commit()
            uid = u.id
        h = {"Authorization": f"Bearer {create_token(uid, 'learner')}"}

        # 3) 上报：合法 + 非法事件混合，非法应被丢弃
        r = await client.post("/api/analytics/track", headers=h, json={"events": [
            {"event_type": "app_launch", "payload": {"channel": "weapp"}},
            {"event_type": "flashcard_study", "payload": {"flashcard_id": card_ids[0]}},
            {"event_type": "not_a_real_event", "payload": {}},  # 非白名单 → 丢弃
            {"event_type": "level_select", "payload": {"level_id": 1}},
        ]})
        assert r.status_code == 200
        assert r.json()["accepted"] == 3, "非白名单事件应被丢弃"

        # 4) 空数组 / 超长 → 422（schema 校验）
        r = await client.post("/api/analytics/track", headers=h, json={"events": []})
        assert r.status_code == 422

        # 5) 看板：仅管理员可访问 → learner 401
        r = await client.get("/api/analytics/dashboard", headers=h)
        assert r.status_code == 401

        # 6) 管理员看板：能拿到聚合数据
        r = await client.post("/api/admin/auth/login",
                              json={"username": "analytics-admin", "password": "Admin@12345"})
        ah = {"Authorization": f"Bearer {r.json()['token']}"}
        r = await client.get("/api/analytics/dashboard", headers=ah)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_users"] >= 1
        assert d["events_7d"] >= 3
        assert any(c["flashcard_id"] == card_ids[0] for c in d["top_cards_7d"]), "热门卡片应包含已学习的卡"
