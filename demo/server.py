# -*- coding: utf-8 -*-
"""
法语学习小程序 — H5 预览版服务端（V0 Demo）

定位
----
这是**给小程序做的可试用 H5 预览版**，不是生产后端。
生产后端在 backend/（FastAPI + PostgreSQL + Redis），小程序源码在 miniprogram/。

职责：
1. 用与 PRD 第 8 章完全一致的路径提供 API，让前端代码可以原样复用到小程序端；
2. 用 SQLite 代替 PostgreSQL，零外部依赖（仅 Python 标准库），保证任何环境一键启动；
3. 承载 H5 静态资源与一个极简后台录入页。

与生产后端的差异（明确标注，勿混用）：
- 存储 SQLite，非 PostgreSQL；无 Redis 缓存；无 Alembic 迁移
- 登录为"模拟 wx.login"：客户端传 device_id 当作 openid。
  真正的 wx.login 流程见 miniprogram/utils/auth.js + backend/app/services/auth_service.py
  —— 服务端用 code 调 jscode2session 换 openid，绝不能把 openid 交给前端传。

启动：
    python server.py            # 默认 8000
    PORT=8080 python server.py  # 自定义端口（部署环境注入 $PORT）
"""

import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
from seed_content import build_seed  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
DB_PATH = os.environ.get("DEMO_DB_PATH", os.path.join(HERE, "data", "demo.db"))

# 打卡与日期一律按北京时间 UTC+8 计算（PRD 5.6：以服务器时间的北京时间日期为准）
CST = timezone(timedelta(hours=8))


def today_cst():
    return datetime.now(CST).date()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 数据库
# ---------------------------------------------------------------------------
# 表结构与 PRD 4.2 DDL 一一对应（Postgres 类型换成 SQLite 兼容写法）
SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    lesson_type TEXT NOT NULL DEFAULT 'vocabulary',
    sort_order INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    content TEXT,
    metadata TEXT,
    created_by INTEGER,
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id INTEGER,
    front_text TEXT NOT NULL,
    back_text TEXT NOT NULL,
    front_audio_url TEXT,
    back_audio_url TEXT,
    example_sentence TEXT,
    example_translation TEXT,
    difficulty INTEGER NOT NULL DEFAULT 1,
    tags TEXT DEFAULT '[]',
    is_sensitive INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    tip TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wx_openid TEXT UNIQUE,
    wx_unionid TEXT,
    nickname TEXT,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'learner',
    phone TEXT,
    current_level TEXT,
    total_study_days INTEGER NOT NULL DEFAULT 0,
    total_cards_learned INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0,
    last_checkin_date TEXT,
    last_login_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    sensitive_opt_in INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reminder_enabled INTEGER NOT NULL DEFAULT 0,
    reminder_time TEXT,
    reminder_days TEXT DEFAULT '[1,2,3,4,5,6,7]',
    daily_goal INTEGER NOT NULL DEFAULT 20,
    sound_enabled INTEGER NOT NULL DEFAULT 1,
    theme TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    checkin_date TEXT NOT NULL,
    cards_reviewed INTEGER NOT NULL DEFAULT 0,
    new_cards_learned INTEGER NOT NULL DEFAULT 0,
    study_duration INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, checkin_date)
);

CREATE TABLE IF NOT EXISTS flashcard_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    flashcard_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    next_review_date TEXT,
    last_review_date TEXT,
    correct_count INTEGER NOT NULL DEFAULT 0,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, flashcard_id)
);

CREATE TABLE IF NOT EXISTS learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    reference_id INTEGER,
    reference_type TEXT,
    result TEXT,
    duration_seconds INTEGER DEFAULT 0,
    extra_data TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,
    login_fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    detail TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lessons_level ON lessons(level_id, status);
CREATE INDEX IF NOT EXISTS idx_flashcards_lesson ON flashcards(lesson_id, status);
CREATE INDEX IF NOT EXISTS idx_progress_user ON flashcard_progress(user_id, status);
CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, checkin_date);
CREATE INDEX IF NOT EXISTS idx_records_user_date ON learning_records(user_id, created_at);
"""

_db_lock = threading.Lock()


# demo token 形如 demo.<uid>.<openid>；用 search 而非 split，避免被网关注入的 JWT 干扰
DEMO_TOKEN_RE = re.compile(r"demo\.(\d+)(?:\.|$)")


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        # 种子只灌一次：levels / lessons / flashcards
        n = conn.execute("SELECT COUNT(*) c FROM flashcards").fetchone()["c"]
        if n == 0:
            levels, lessons, flashcards = build_seed()
            ts = now_iso()
            for lv in levels:
                conn.execute(
                    "INSERT INTO levels (id, code, name, description, sort_order, is_active, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (lv["id"], lv["code"], lv["name"], lv["description"], lv["sort_order"], 1, ts, ts),
                )
            for ls in lessons:
                conn.execute(
                    "INSERT INTO lessons (id, level_id, title, description, lesson_type, sort_order, status,"
                    " content, metadata, created_by, published_at, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        ls["id"], ls["level_id"], ls["title"], ls["description"], ls["lesson_type"],
                        ls["sort_order"], ls["status"], json.dumps(ls["content"], ensure_ascii=False),
                        json.dumps(ls["metadata"]), ls["created_by"],
                        ts if ls["status"] == "published" else None, ts, ts,
                    ),
                )
            for fc in flashcards:
                conn.execute(
                    "INSERT INTO flashcards (id, lesson_id, front_text, back_text, front_audio_url, back_audio_url,"
                    " example_sentence, example_translation, difficulty, tags, is_sensitive, sort_order, status, tip,"
                    " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        fc["id"], fc["lesson_id"], fc["front_text"], fc["back_text"], fc["front_audio_url"],
                        fc["back_audio_url"], fc["example_sentence"], fc["example_translation"], fc["difficulty"],
                        json.dumps(fc["tags"], ensure_ascii=False), 1 if fc["is_sensitive"] else 0,
                        fc["sort_order"], fc["status"], fc.get("tip"), ts, ts,
                    ),
                )
            # 默认管理员（V0 演示用；生产环境必须由运维在部署时改密，见 docs）
            conn.execute(
                "INSERT OR IGNORE INTO admin_accounts (username, password_hash, role, is_active, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?)",
                ("admin", "demo-not-real-bcrypt-hash", "super_admin", 1, ts, ts),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def row_to_dict(r):
    return {k: r[k] for k in r.keys()}


def jloads(s, default):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def public_flashcard(fc, include_tip=True):
    """按 PRD 8.5 的 items[] schema 输出闪卡。"""
    d = {
        "id": fc["id"],
        "lesson_id": fc["lesson_id"],
        "front_text": fc["front_text"],
        "back_text": fc["back_text"],
        "front_audio_url": fc["front_audio_url"],
        "example_sentence": fc["example_sentence"],
        "example_translation": fc["example_translation"],
        "difficulty": fc["difficulty"],
        "tags": jloads(fc["tags"], []),
        "is_sensitive": bool(fc["is_sensitive"]),
        "sort_order": fc["sort_order"],
        "status": fc["status"],
    }
    if include_tip:
        d["tip"] = fc["tip"] if "tip" in fc.keys() else None
    return d


def get_user_by_openid(conn, openid):
    return conn.execute("SELECT * FROM users WHERE wx_openid=?", (openid,)).fetchone()


def ensure_preferences(conn, user_id):
    r = conn.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
    if r:
        return r
    ts = now_iso()
    conn.execute(
        "INSERT INTO user_preferences (user_id, reminder_enabled, reminder_time, reminder_days, daily_goal,"
        " sound_enabled, theme, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (user_id, 0, "20:00", "[1,2,3,4,5,6,7]", 20, 1, "default", ts, ts),
    )
    conn.commit()
    return conn.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()


def user_public(u, prefs=None):
    return {
        "id": u["id"],
        "nickname": u["nickname"],
        "avatar_url": u["avatar_url"],
        "role": u["role"],
        "current_level": u["current_level"],
        "sensitive_opt_in": bool(u["sensitive_opt_in"]),
        "total_study_days": u["total_study_days"],
        "total_cards_learned": u["total_cards_learned"],
        "streak_days": u["streak_days"],
        "longest_streak": u["longest_streak"],
        "last_checkin_date": u["last_checkin_date"],
        "daily_goal": prefs["daily_goal"] if prefs else 20,
    }


def today_summary(conn, user_id):
    """PRD 8.2 GET /api/user/today-summary"""
    today = today_cst().isoformat()
    ck = conn.execute("SELECT * FROM checkins WHERE user_id=? AND checkin_date=?", (user_id, today)).fetchone()
    goal = ensure_preferences(conn, user_id)["daily_goal"]
    learned_today = conn.execute(
        "SELECT COUNT(*) c FROM learning_records WHERE user_id=? AND record_type='flashcard_review'"
        " AND date(created_at)=?", (user_id, today_cst().isoformat()),
    ).fetchone()["c"]
    # SQLite 存的是 UTC ISO，这里按北京时间折算：UTC 时间 +8h 落在同一天
    rows = conn.execute(
        "SELECT created_at FROM learning_records WHERE user_id=? AND record_type='flashcard_review'", (user_id,)
    ).fetchall()
    learned_today = 0
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["created_at"])
        except Exception:
            continue
        if (dt.astimezone(CST)).date().isoformat() == today:
            learned_today += 1
    due = conn.execute(
        "SELECT COUNT(*) c FROM flashcard_progress WHERE user_id=? AND status IN ('learning','review')"
        " AND (next_review_date IS NULL OR next_review_date<=?)", (user_id, today),
    ).fetchone()["c"]
    return {
        "date": today,
        "daily_goal": goal,
        "cards_learned_today": ck["cards_reviewed"] if ck else learned_today,
        "cards_reviewed": ck["cards_reviewed"] if ck else 0,
        "new_cards_learned": ck["new_cards_learned"] if ck else 0,
        "study_duration": ck["study_duration"] if ck else 0,
        "checked_in": bool(ck),
        "due_cards": due,
        "streak_days": conn.execute("SELECT streak_days s FROM users WHERE id=?", (user_id,)).fetchone()["s"],
    }


def _today_learned_count(conn, user_id, date_s):
    """按北京时间统计某用户当日 flashcard_review 记录数。"""
    rows = conn.execute(
        "SELECT created_at FROM learning_records WHERE user_id=? AND record_type='flashcard_review'", (user_id,)
    ).fetchall()
    n = 0
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["created_at"])
        except Exception:
            continue
        if dt.astimezone(CST).date().isoformat() == date_s:
            n += 1
    return n


def refresh_today_checkin(conn, user_id):
    """把今日学习量回填到 checkins（PRD 5.6 的 cards_reviewed / new_cards_learned）。"""
    date_s = today_cst().isoformat()
    reviewed = _today_learned_count(conn, user_id, date_s)
    new_cnt = conn.execute(
        "SELECT COUNT(*) c FROM flashcard_progress WHERE user_id=? AND last_review_date=? AND repetitions<=1",
        (user_id, date_s),
    ).fetchone()["c"]
    conn.execute(
        "UPDATE checkins SET cards_reviewed=?, new_cards_learned=? WHERE user_id=? AND checkin_date=?",
        (reviewed, new_cnt, user_id, date_s),
    )
    conn.commit()
    return conn.execute("SELECT * FROM checkins WHERE user_id=? AND checkin_date=?", (user_id, date_s)).fetchone()


# ---------------------------------------------------------------------------
# 业务：打卡（PRD 5.6）
# ---------------------------------------------------------------------------
def auto_checkin(conn, user_id):
    today = today_cst()
    today_s = today.isoformat()
    exist = conn.execute("SELECT * FROM checkins WHERE user_id=? AND checkin_date=?", (user_id, today_s)).fetchone()
    if exist:
        return row_to_dict(exist), False  # 幂等：同日重复调用直接返回已有记录

    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    yesterday = (today - timedelta(days=1)).isoformat()
    streak = 1
    if u["last_checkin_date"]:
        prev = conn.execute(
            "SELECT id FROM checkins WHERE user_id=? AND checkin_date=?", (user_id, yesterday)
        ).fetchone()
        if prev:
            streak = (u["streak_days"] or 0) + 1
        elif u["last_checkin_date"] == yesterday:
            streak = (u["streak_days"] or 0) + 1

    ts = now_iso()
    cur = conn.execute(
        "INSERT INTO checkins (user_id, checkin_date, cards_reviewed, new_cards_learned, study_duration, created_at)"
        " VALUES (?,?,?,?,?,?)", (user_id, today_s, 0, 0, 0, ts),
    )
    conn.execute(
        "UPDATE users SET streak_days=?, longest_streak=MAX(longest_streak, ?), last_checkin_date=?,"
        " total_study_days=total_study_days+1, updated_at=? WHERE id=?",
        (streak, streak, today_s, ts, user_id),
    )
    conn.execute(
        "INSERT INTO learning_records (user_id, record_type, reference_id, reference_type, result,"
        " duration_seconds, extra_data, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, "checkin", None, "checkin", "success", 0, None, ts),
    )
    conn.commit()
    ck = refresh_today_checkin(conn, user_id)
    return row_to_dict(ck), True


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "FrenchDemo/0.1"

    # ---- 基础 ----
    def log_message(self, fmt, *args):  # 简化日志
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body=b"", ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(code, json.dumps(data, ensure_ascii=False))

    def _err(self, code, msg, detail=None):
        # PRD 10.2：生产环境不暴露堆栈，这里同样只回业务错误
        self._json({"error": {"code": code, "message": msg, "detail": detail}}, code)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _static(self, rel):
        # 防目录穿越
        rel = rel.strip("/") or "index.html"
        safe = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not safe.startswith(STATIC_DIR) or not os.path.isfile(safe):
            self._send(404, b"Not Found", "text/plain; charset=utf-8")
            return
        ext = os.path.splitext(safe)[1].lower()
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
            ".json": "application/json; charset=utf-8",
        }.get(ext, "application/octet-stream")
        with open(safe, "rb") as f:
            self._send(200, f.read(), ctype)

    # ---- 路由 ----
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")

    def do_PUT(self):
        self._route("PUT")

    def do_DELETE(self):
        self._route("DELETE")

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain", {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        })

    def _route(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path, query = parsed.path, urllib.parse.parse_qs(parsed.query)
        try:
            self._dispatch(method, path, query)
        except Exception as e:  # 兜底，避免 demo 直接 500 白屏
            import traceback
            traceback.print_exc()
            self._err(500, "服务器内部错误", str(e))

    def _dispatch(self, method, path, query):
        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path == "/admin":
            return self._static("admin.html")
        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if path == "/health":
            return self._json({"status": "ok", "env": "demo", "time": now_iso()})

        if not path.startswith("/api/"):
            return self._send(404, b"Not Found", "text/plain; charset=utf-8")

        conn = get_db()
        try:
            with _db_lock:
                self._api(method, path, query, conn)
        finally:
            conn.close()

    # ---- API ----
    def _api(self, method, path, query, conn):
        body = self._body() if method in ("POST", "PUT", "DELETE") else {}

        # ========== 认证（PRD 8.1）==========
        if path == "/api/auth/wx-login" and method == "POST":
            # ⚠️ Demo 专用：H5 没有 wx.login，用 device_id 冒充 openid。
            # 真实实现必须：前端只传 code，服务端调 jscode2session 换 openid。
            openid = (body.get("code") or body.get("device_id") or "").strip()
            if not openid:
                return self._err(400, "缺少登录凭证")
            openid = "demo_" + openid[:48]
            u = get_user_by_openid(conn, openid)
            is_new = False
            ts = now_iso()
            if not u:
                cur = conn.execute(
                    "INSERT INTO users (wx_openid, nickname, avatar_url, role, is_active, sensitive_opt_in,"
                    " created_at, updated_at, last_login_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (openid, body.get("nickname") or "法语学习者", body.get("avatar_url"), "learner", 1, 0, ts, ts, ts),
                )
                conn.commit()
                u = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
                ensure_preferences(conn, u["id"])
                is_new = True
            else:
                conn.execute("UPDATE users SET last_login_at=?, updated_at=? WHERE id=?", (ts, ts, u["id"]))
                conn.commit()
            prefs = ensure_preferences(conn, u["id"])
            return self._json({
                "token": "demo.%d.%s" % (u["id"], openid),
                "user": user_public(u, prefs),
                "is_new_user": is_new,
            })

        # 诊断接口（仅 demo 用，不返回敏感值，只回显"有没有收到"）
        if path == "/api/_diag":
            return self._json({
                "path": self.path,
                "has_authorization": bool(self.headers.get("Authorization")),
                "has_x_auth_token": bool(self.headers.get("X-Auth-Token")),
                "has_cookie": bool(self.headers.get("Cookie")),
                "query": urllib.parse.urlparse(self.path).query,
                "header_names": sorted([k for k in self.headers.keys()]),
                "extracted_token": (self._extract_token() or "")[:8],
            })

        # 以下接口需要登录态，demo 用 Authorization: Bearer demo.<uid>.<openid>
        uid = self._current_user_id(conn)
        if uid is None:
            return self._err(401, "未登录或登录态已失效")
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not user:
            return self._err(401, "用户不存在")

        # ========== 用户（PRD 8.2）==========
        if path == "/api/auth/me":
            return self._json({"user": user_public(user, ensure_preferences(conn, uid))})

        if path == "/api/user/profile" and method == "GET":
            total_checkin = conn.execute("SELECT COUNT(*) c FROM checkins WHERE user_id=?", (uid,)).fetchone()["c"]
            mastered = conn.execute(
                "SELECT COUNT(*) c FROM flashcard_progress WHERE user_id=? AND status='mastered'", (uid,)
            ).fetchone()["c"]
            prefs = ensure_preferences(conn, uid)
            data = user_public(user, prefs)
            data.update({
                "total_checkin_days": total_checkin,
                "mastered_cards": mastered,
                "reminder_enabled": bool(prefs["reminder_enabled"]),
                "reminder_time": prefs["reminder_time"],
                "reminder_days": jloads(prefs["reminder_days"], [1, 2, 3, 4, 5, 6, 7]),
                "sound_enabled": bool(prefs["sound_enabled"]),
            })
            return self._json(data)

        if path == "/api/user/profile" and method == "PUT":
            nickname = body.get("nickname")
            level = body.get("current_level")
            if nickname:
                conn.execute("UPDATE users SET nickname=?, updated_at=? WHERE id=?", (nickname, now_iso(), uid))
            if level:
                conn.execute("UPDATE users SET current_level=?, updated_at=? WHERE id=?", (level, now_iso(), uid))
            conn.commit()
            return self._json({"ok": True})

        if path == "/api/user/preferences/sensitive-opt-in" and method == "POST":
            val = 1 if body.get("sensitive_opt_in") else 0
            conn.execute("UPDATE users SET sensitive_opt_in=?, updated_at=? WHERE id=?", (val, now_iso(), uid))
            conn.commit()
            return self._json({"sensitive_opt_in": bool(val)})

        if path == "/api/user/preferences/reminder" and method == "PUT":
            p = ensure_preferences(conn, uid)
            enabled = body.get("reminder_enabled", p["reminder_enabled"])
            rtime = body.get("reminder_time", p["reminder_time"])
            days = body.get("reminder_days", jloads(p["reminder_days"], [1, 2, 3, 4, 5, 6, 7]))
            goal = body.get("daily_goal", p["daily_goal"])
            conn.execute(
                "UPDATE user_preferences SET reminder_enabled=?, reminder_time=?, reminder_days=?, daily_goal=?,"
                " updated_at=? WHERE user_id=?",
                (1 if enabled else 0, rtime, json.dumps(days), goal, now_iso(), uid),
            )
            conn.commit()
            return self._json({"ok": True, "reminder_enabled": bool(enabled), "reminder_time": rtime,
                               "daily_goal": goal})

        if path == "/api/user/today-summary":
            return self._json(today_summary(conn, uid))

        # ========== 学习（PRD 8.3）==========
        if path == "/api/levels" and method == "GET":
            rows = conn.execute(
                "SELECT l.*, (SELECT COUNT(*) FROM lessons s WHERE s.level_id=l.id AND s.status='published') AS lesson_count"
                " FROM levels l WHERE l.is_active=1 ORDER BY l.sort_order"
            ).fetchall()
            return self._json([{"id": r["id"], "code": r["code"], "name": r["name"],
                                "description": r["description"], "sort_order": r["sort_order"],
                                "lesson_count": r["lesson_count"]} for r in rows])

        if path.startswith("/api/levels/") and path.endswith("/lessons") and method == "GET":
            level_id = int(path.split("/")[3])
            rows = conn.execute(
                "SELECT s.*, (SELECT COUNT(*) FROM flashcards f WHERE f.lesson_id=s.id AND f.status='published'"
                " AND (?=1 OR f.is_sensitive=0)) AS card_count FROM lessons s"
                " WHERE s.level_id=? AND s.status='published' ORDER BY s.sort_order",
                (1 if user["sensitive_opt_in"] else 0, level_id),
            ).fetchall()
            return self._json([{"id": r["id"], "level_id": r["level_id"], "title": r["title"],
                                "description": r["description"], "lesson_type": r["lesson_type"],
                                "sort_order": r["sort_order"], "card_count": r["card_count"]} for r in rows])

        if path.startswith("/api/lessons/") and method == "GET" and "/flashcards" not in path:
            lesson_id = int(path.split("/")[3])
            r = conn.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
            if not r:
                return self._err(404, "课时不存在")
            return self._json({"id": r["id"], "level_id": r["level_id"], "title": r["title"],
                               "description": r["description"], "lesson_type": r["lesson_type"],
                               "status": r["status"], "content": jloads(r["content"], {}),
                               "metadata": jloads(r["metadata"], {})})

        if path.startswith("/api/lessons/") and path.endswith("/flashcards") and method == "GET":
            lesson_id = int(path.split("/")[3])
            page = int((query.get("page") or ["1"])[0])
            size = min(int((query.get("page_size") or ["100"])[0]), 100)
            where = "lesson_id=? AND status='published'"
            args = [lesson_id]
            if not user["sensitive_opt_in"]:
                where += " AND is_sensitive=0"  # PRD 5.5：未 opt-in 则过滤敏感卡
            total = conn.execute("SELECT COUNT(*) c FROM flashcards WHERE " + where, args).fetchone()["c"]
            rows = conn.execute(
                "SELECT * FROM flashcards WHERE " + where + " ORDER BY sort_order LIMIT ? OFFSET ?",
                args + [size, (page - 1) * size],
            ).fetchall()
            return self._json({"items": [public_flashcard(r) for r in rows], "total": total,
                               "page": page, "page_size": size})

        if path == "/api/flashcard-progress" and method == "POST":
            fid = body.get("flashcard_id")
            result = body.get("result")
            if result not in ("correct", "wrong", "skip"):
                return self._err(422, "result 必须是 correct / wrong / skip")
            ts = now_iso()
            today = today_cst()
            row = conn.execute(
                "SELECT * FROM flashcard_progress WHERE user_id=? AND flashcard_id=?", (uid, fid)
            ).fetchone()
            correct_add = 1 if result == "correct" else 0
            wrong_add = 1 if result == "wrong" else 0
            if row:
                reps = row["repetitions"] + 1
                # V0 不做 SM-2（PRD 5.5）：这里只给一个"方便演示"的简单间隔，
                # 真正的间隔重复算法留到 V1 的 flashcard_service.py 实现。
                interval = min(2 ** max(1, row["correct_count"] + correct_add), 21) if result == "correct" else 1
                status = "mastered" if (row["correct_count"] + correct_add) >= 5 else (
                    "review" if result == "correct" else "learning")
                conn.execute(
                    "UPDATE flashcard_progress SET status=?, repetitions=?, interval_days=?,"
                    " next_review_date=?, last_review_date=?, correct_count=correct_count+?,"
                    " wrong_count=wrong_count+?, updated_at=? WHERE id=?",
                    (status, reps, interval, (today + timedelta(days=interval)).isoformat(),
                     today.isoformat(), correct_add, wrong_add, ts, row["id"]),
                )
            else:
                reps = 1
                interval = 2 if result == "correct" else 1
                status = "learning" if result != "correct" else "review"
                conn.execute(
                    "INSERT INTO flashcard_progress (user_id, flashcard_id, status, ease_factor, interval_days,"
                    " repetitions, next_review_date, last_review_date, correct_count, wrong_count, created_at,"
                    " updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, fid, status, 2.5, interval, reps, (today + timedelta(days=interval)).isoformat(),
                     today.isoformat(), correct_add, wrong_add, ts, ts),
                )
            conn.execute(
                "INSERT INTO learning_records (user_id, record_type, reference_id, reference_type, result,"
                " duration_seconds, extra_data, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (uid, "flashcard_review", fid, "flashcard", result,
                 int((body.get("response_time_ms") or 0) / 1000),
                 json.dumps({"lesson_id": body.get("lesson_id"),
                             "response_time_ms": body.get("response_time_ms")}), ts),
            )
            conn.execute("UPDATE users SET total_cards_learned=total_cards_learned+1 WHERE id=?", (uid,))
            conn.commit()
            ck, created = auto_checkin(conn, uid)  # PRD 5.6：首次学习自动打卡（内部已回填今日学习量）
            p = conn.execute("SELECT * FROM flashcard_progress WHERE user_id=? AND flashcard_id=?", (uid, fid)).fetchone()
            return self._json({
                "status": p["status"], "next_review_date": p["next_review_date"],
                "correct_count": p["correct_count"], "wrong_count": p["wrong_count"],
                "checkin": {"created": created, "streak_days": conn.execute(
                    "SELECT streak_days s FROM users WHERE id=?", (uid,)).fetchone()["s"]},
            })

        if path == "/api/flashcard-progress/review-today":
            today = today_cst().isoformat()
            rows = conn.execute(
                "SELECT f.* FROM flashcards f JOIN flashcard_progress p ON p.flashcard_id=f.id"
                " WHERE p.user_id=? AND p.status IN ('learning','review') AND (p.next_review_date IS NULL"
                " OR p.next_review_date<=?)" + ("" if user["sensitive_opt_in"] else " AND f.is_sensitive=0"),
                (uid, today),
            ).fetchall()
            return self._json({"items": [public_flashcard(r) for r in rows], "total": len(rows), "date": today})

        if path == "/api/checkins/auto" and method == "POST":
            ck, created = auto_checkin(conn, uid)
            u = conn.execute("SELECT streak_days s, longest_streak ls FROM users WHERE id=?", (uid,)).fetchone()
            return self._json({"checkin": ck, "created": created, "streak_days": u["s"],
                               "longest_streak": u["ls"]})

        if path == "/api/checkins/calendar":
            month = (query.get("month") or [today_cst().strftime("%Y-%m")])[0]
            rows = conn.execute(
                "SELECT checkin_date, cards_reviewed, new_cards_learned, study_duration FROM checkins"
                " WHERE user_id=? AND checkin_date LIKE ? ORDER BY checkin_date",
                (uid, month + "-%"),
            ).fetchall()
            return self._json({"month": month, "items": [row_to_dict(r) for r in rows]})

        # ========== 极简后台（PRD 8.4 子集，V0 只做闪卡/课时录入）==========
        if path == "/api/admin/flashcards" and method == "GET":
            rows = conn.execute("SELECT * FROM flashcards ORDER BY lesson_id, sort_order").fetchall()
            return self._json({"items": [public_flashcard(r) for r in rows], "total": len(rows)})

        if path == "/api/admin/flashcards" and method == "POST":
            ts = now_iso()
            cur = conn.execute(
                "INSERT INTO flashcards (lesson_id, front_text, back_text, example_sentence, example_translation,"
                " difficulty, tags, is_sensitive, sort_order, status, tip, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (body.get("lesson_id"), body["front_text"], body["back_text"],
                 body.get("example_sentence"), body.get("example_translation"),
                 int(body.get("difficulty") or 1), json.dumps(body.get("tags") or [], ensure_ascii=False),
                 1 if body.get("is_sensitive") else 0, int(body.get("sort_order") or 0),
                 body.get("status") or "published", body.get("tip"), ts, ts),
            )
            conn.commit()
            return self._json({"id": cur.lastrowid}, 201)

        if path.startswith("/api/admin/flashcards/") and method == "PUT":
            fid = int(path.rsplit("/", 1)[1])
            sets, args = [], []
            for col in ("front_text", "back_text", "example_sentence", "example_translation", "tip", "status"):
                if col in body:
                    sets.append(col + "=?")
                    args.append(body[col])
            if "difficulty" in body:
                sets.append("difficulty=?")
                args.append(int(body["difficulty"]))
            if "is_sensitive" in body:
                sets.append("is_sensitive=?")
                args.append(1 if body["is_sensitive"] else 0)
            if "tags" in body:
                sets.append("tags=?")
                args.append(json.dumps(body["tags"], ensure_ascii=False))
            if not sets:
                return self._err(400, "没有可更新字段")
            args += [now_iso(), fid]
            conn.execute("UPDATE flashcards SET " + ",".join(sets) + ", updated_at=? WHERE id=?", args)
            conn.commit()
            return self._json({"ok": True})

        if path.startswith("/api/admin/flashcards/") and method == "DELETE":
            fid = int(path.rsplit("/", 1)[1])
            conn.execute("DELETE FROM flashcards WHERE id=?", (fid,))
            conn.execute("DELETE FROM flashcard_progress WHERE flashcard_id=?", (fid,))
            conn.commit()
            return self._json({"ok": True})

        if path == "/api/admin/lessons" and method == "GET":
            rows = conn.execute("SELECT * FROM lessons ORDER BY level_id, sort_order").fetchall()
            return self._json({"items": [row_to_dict(r) for r in rows], "total": len(rows)})

        if path == "/api/admin/stats" and method == "GET":
            return self._json({
                "users": conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
                "flashcards": conn.execute("SELECT COUNT(*) c FROM flashcards").fetchone()["c"],
                "lessons": conn.execute("SELECT COUNT(*) c FROM lessons WHERE status='published'").fetchone()["c"],
                "checkins_today": conn.execute(
                    "SELECT COUNT(*) c FROM checkins WHERE checkin_date=?", (today_cst().isoformat(),)
                ).fetchone()["c"],
            })

        return self._err(404, "接口不存在: " + path)

    def _extract_token(self):
        """取 token，按优先级：X-Auth-Token > ?token= > Authorization。

        为什么不能直接信 Authorization：部分部署网关（如 CloudStudio/EO 网关）
        会**注入自己的 Authorization: Bearer <JWT>** 覆盖客户端传的，
        所以这里把自定义头与 query 排在前面，并用正则从候选串里找 demo.<uid>。
        生产环境（自建 Nginx / 标准网关）只用 Authorization 即可。
        """
        cands = []
        x = (self.headers.get("X-Auth-Token") or "").strip()
        if x:
            cands.append(x)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        t = (q.get("token") or [""])[0].strip()
        if t:
            cands.append(t)
        auth = (self.headers.get("Authorization") or "").strip()
        if auth:
            cands.append(auth[7:].strip() if auth.lower().startswith("bearer ") else auth)
        for c in cands:
            if DEMO_TOKEN_RE.search(c):
                return c
        return cands[0] if cands else ""

    def _current_user_id(self, conn):
        token = self._extract_token()
        if not token:
            return None
        m = DEMO_TOKEN_RE.search(token)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None


def main():
    init_db()
    port = int(os.environ.get("PORT") or os.environ.get("SERVER_PORT") or 8000)
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    sys.stderr.write("法语学习小程序 H5 预览版已启动: http://0.0.0.0:%d\n" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
