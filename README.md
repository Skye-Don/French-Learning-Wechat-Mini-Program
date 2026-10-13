# French Learning Mini Program (V0)

**Learn French the way French people actually speak it** — authentic colloquial expressions, usage tips that no textbook teaches, 3D flip cards, spaced repetition, and a daily check-in streak.

> This repository is the complete V0 delivery: **WeChat Mini Program source + production backend + a scannable H5 preview + a minimal content admin panel**.

---

## Table of contents

- [Try it now](#try-it-now)
- [What V0 covers](#what-v0-covers)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Difficulty model: CEFR A1–B2](#difficulty-model-cefr-a1b2)
- [Data model](#data-model)
- [API surface](#api-surface)
- [Deploying the Mini Program](#deploying-the-mini-program)
- [Security red lines](#security-red-lines)
- [Compliance checklist before review](#compliance-checklist-before-review)
- [Known limitations](#known-limitations)

---

## Try it now

| How | Where |
|---|---|
| **Scan the QR code (recommended)** | `docs/qrcode-preview.png` — open it on your phone and run the whole V0 flow |
| **Browser** | https://french-learning-miniapp.app.workbuddy.host/ — ships with a phone-shell simulator |
| **Content admin** | https://french-learning-miniapp.app.workbuddy.host/admin — minimal card entry panel |

> A WeChat Mini Program **cannot** be opened through a plain HTTP link (platform restriction). The H5 preview above is a 1:1 replica built for evaluation. To run the real Mini Program, import the `miniprogram/` directory in WeChat DevTools — see [Deploying the Mini Program](#deploying-the-mini-program).

---

## What V0 covers

| Area | Delivered |
|---|---|
| Onboarding | Silent login (`wx.login` → server exchanges `code` for `openid` → JWT) |
| Learning path | Levels → lessons → flashcards, 10 pages total |
| Flashcards | 3D flip, know / don't know, usage tip (`tip`) panel |
| Spaced repetition | Per-card scheduling based on correctness, `next_review_date` driven |
| Sensitive vocabulary | **Opt-in by default off**: sensitive cards are filtered out until the user explicitly enables them |
| Daily check-in | Beijing-time (UTC+8) day boundary, idempotent, streak tracking, month calendar |
| Reminders | Per-user reminder time / days / daily goal |
| Content admin | Card + lesson CRUD, batch import, publish guard, audit log, role gating |
| Seed content | 41 authentic French expressions across greetings, ordering, shopping and spoken connectors |

Not in V0: speech scoring / ASR, subscription payments, AI conversation correction, the full Vue 3 admin panel.

---

## Repository layout

```
french-miniprogram/
├── miniprogram/        # WeChat Mini Program source (native framework, 10 pages)
│   ├── pages/          # home, learn, profile, level, lesson, study, summary, calendar, reminder, sensitive
│   ├── utils/          # config / request / auth / util
│   └── project.config.json   # AppID is already filled in
├── backend/            # Production backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis
│   ├── app/            # models / schemas / routers (auth, learning, admin) / security / dependencies
│   ├── alembic/        # Async migrations (0001 initial schema, 0002 CEFR difficulty)
│   └── tests/          # End-to-end smoke tests (run on SQLite, no real PG/Redis needed)
├── demo/               # H5 preview: standard-library-only HTTP server + SQLite, zero dependencies
├── docker/             # docker-compose (Postgres + Redis + API + Nginx) and nginx.conf
├── docs/               # QR codes, Mini Program upload & release guide
└── scripts/            # create admin, import seed content, git push helpers
```

---

## Quick start

### 1. H5 preview — 30 seconds

```bash
cd demo
python server.py          # http://127.0.0.1:8000
```

### 2. Production backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # fill in WX_APPID / WX_SECRET / JWT_SECRET / DB_PASSWORD
alembic upgrade head      # create schema (connection string is read from .env, never committed)
python ../scripts/create_admin.py admin 'YourPass@123' --role super_admin
python ../scripts/import_seed.py        # import the 41 seed cards
uvicorn app.main:app --reload           # http://127.0.0.1:8000/docs
```

In `APP_ENV=development` tables are auto-created on startup. In production **always** use `alembic upgrade head`.

### 3. Mini Program

1. WeChat DevTools → **Import project** → select `miniprogram/` → AppID `wx290524b33830af1f` is picked up automatically from `project.config.json`
2. Set `PROD_BASE_URL` in `miniprogram/utils/config.js` to your backend HTTPS domain
3. Before release, add that domain to **request 合法域名** (allow-listed request domains) in the WeChat admin console

### 4. Tests

```bash
cd backend
pytest tests/ -v
# login → levels → lessons → cards → sensitive filtering → study → idempotent check-in
# → admin CRUD → audit log → permission isolation → CEFR difficulty validation
```

---

## Difficulty model: CEFR A1–B2

Every flashcard carries a CEFR level instead of an opaque 1–5 integer:

| Level | Meaning |
|---|---|
| `A1` | Beginner — the shortest, most frequent everyday expressions |
| `A2` | Elementary — complete sentences for everyday situations |
| `B1` | Intermediate — includes conjugation and register differences |
| `B2` | Upper intermediate — slang, euphemisms, cultural context |

Implementation notes:

- Database column `flashcards.difficulty` is `VARCHAR(2)`, default `A1`
- Pydantic enforces `Literal["A1","A2","B1","B2"]`; anything else (including legacy integers) is rejected with `422`
- Migration `backend/alembic/versions/0002_cefr_difficulty.py` converts existing rows: `1→A1, 2→A2, 3→B1, 4/5→B2`
- The admin list renders a colour-coded badge and supports filtering by level (`GET /api/admin/flashcards?level=B2`)

---

## Data model

Core tables (see `backend/app/models.py` and migration `0001`):

| Table | Purpose |
|---|---|
| `levels` | A1–B2 levels |
| `lessons` | Lessons belonging to a level; publishing requires ≥ 1 published card |
| `flashcards` | Front (French) / back (Chinese) / example / tip / `difficulty` / tags / `is_sensitive` |
| `users` | `wx_openid` (± `unionid`), streak counters, `sensitive_opt_in` |
| `user_preferences` | Reminder time/days, daily goal |
| `flashcard_progress` | Per-card correct/wrong counts and `next_review_date`; unique per `(user_id, flashcard_id)` |
| `checkins` | One row per user per day, unique `(user_id, checkin_date)` |
| `admin_accounts`, `admin_audit_logs`, `system_settings` | Backend admin, audit trail, runtime settings |

Two conventions worth knowing:

- **All timestamps are stored as UTC** (`TIMESTAMPTZ`), but the check-in day boundary is **Beijing time (UTC+8)**. Comparing `date(created_at)` directly loses records between 00:00 and 08:00 Beijing time — the code converts the CST day into a UTC range instead (`cst_day_utc_range`).
- **Sensitive cards are filtered server-side** whenever `users.sensitive_opt_in = false`; requesting a sensitive card directly returns `403`.

---

## API surface

All paths match the PRD chapter 8 contract so the Mini Program and the H5 preview share the same client code.

### Learner

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/auth/wx-login` | Body carries only `code`; the server calls `jscode2session` |
| `GET` | `/api/auth/me` | |
| `GET` | `/api/levels` | Cached in Redis with jittered TTL |
| `GET` | `/api/levels/{id}/lessons` | |
| `GET` | `/api/lessons/{id}/flashcards` | Sensitive cards filtered unless opt-in |
| `POST` | `/api/flashcard-progress` | Body: `flashcard_id`, `result` (`correct` / `wrong` / `skip`), `lesson_id`, `response_time_ms` |
| `GET` | `/api/flashcard-progress/review-today` | Cards due today |
| `POST` | `/api/checkins/auto` | Idempotent |
| `GET` | `/api/checkins/calendar?month=YYYY-MM` | |
| `GET`/`PUT` | `/api/user/profile` | |
| `PUT` | `/api/user/preferences/reminder` | Reminder time / days / daily goal |
| `POST` | `/api/user/preferences/sensitive-opt-in` | Toggles sensitive content |
| `GET` | `/api/user/today-summary` | Today's goal progress |

### Admin (JWT with `admin` claim)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/admin/auth/login` | bcrypt verify, 5 failures → 30 min lock, 2 h token |
| `GET` | `/api/admin/dashboard` | |
| `GET`/`POST` | `/api/admin/flashcards` | List supports `keyword`, `lesson_id`, `status`, `is_sensitive`, `level` |
| `PUT`/`DELETE` | `/api/admin/flashcards/{id}` | |
| `POST` | `/api/admin/flashcards/batch` | Up to 200 items in one transaction |
| `GET`/`POST`/`PUT`/`DELETE` | `/api/admin/lessons` | |
| `POST` | `/api/admin/lessons/{id}/publish` | Validates ≥ 1 published card |
| `GET`/`PUT` | `/api/admin/levels` | |
| `GET` | `/api/admin/audit-logs` | `super_admin` only |
| `GET` | `/api/admin/users` | `super_admin` only; `openid` is masked |
| `GET`/`PUT` | `/api/admin/settings` | `super_admin` only |
| `POST` | `/api/admin/auth/logout`, `GET` `/api/admin/me` | Token lifecycle |

---

## Deploying the Mini Program

The AppID `wx290524b33830af1f` is already written into `miniprogram/project.config.json`. The remaining steps require **you**, because uploading code to a Mini Program needs a scan confirmation from a developer account bound to that AppID — no third party (and no CLI without your upload key) can do it.

1. WeChat DevTools → **Import project** → choose the `miniprogram/` directory
2. Verify the AppID under **Details → Basic info**
3. Set `PROD_BASE_URL` in `miniprogram/utils/config.js`
4. Add your domain under **mp.weixin.qq.com → Development → Development Settings → Server Domains**
5. Click **Upload**, set a version number and notes, scan to confirm
6. In **Version management**, promote to 体验版 (beta), let testers verify, then **Submit for review**

Full walkthrough, review self-check and troubleshooting: [`docs/小程序上传发布指南.md`](docs/小程序上传发布指南.md).

For unattended releases, the official [`miniprogram-ci`](https://developers.weixin.qq.com/miniprogram/dev/devtools/ci.html) can be wired into CI using an upload key you generate in the admin console.

---

## Security red lines

- `openid` is obtained **server-side only** by exchanging the `code` from `wx.login`; the client never sends an `openid`
- `JWT_SECRET`, `WX_SECRET` and database passwords live only in `.env`, which is git-ignored
- Logs must never contain tokens, `openid`s or passwords — failed admin logins record username and IP only
- Payment signing belongs on the server; keys never ship in client code
- The admin panel in `demo/` is guarded by an `X-Admin-Key` header. It is a **preview-only** gate (the key is visible in front-end code) — production must use the JWT + `AdminAccount` + audit-log path in `backend/`

---

## Compliance checklist before review

Always verify against the **latest official WeChat rules**; this list is a starting point, not legal advice.

- [ ] Correct category selected; confirm whether the education category requires a qualification in your case
- [ ] User privacy protection guide configured and published in the admin console (`wx.login` collects user data and must be declared)
- [ ] Server domain uses HTTPS and is ICP-registered
- [ ] User agreement available in-app
- [ ] Submit a test account / note: V0 has no signup — "open and use"
- [ ] The 2 profanity cards in the seed set are hidden behind `sensitive_opt_in`; state this in the review notes
- [ ] No outbound links, no incentivised sharing, no forced follow

---

## Known limitations

- The production backend has not been integration-tested against real PostgreSQL/Redis in this environment; tests run on SQLite. Run `alembic upgrade head` against a real database before release.
- The H5 preview host is a temporary evaluation environment with no availability guarantee.
- `demo/` stores an SQLite file and uses a simplified auth flow; it is **not** the production backend.
- The full Vue 3 + Element Plus admin panel is planned for the next iteration.

---

## Tech stack

| Layer | Choice |
|---|---|
| Mini Program | Native WeChat framework (WXML / WXSS / JS), base library 3.x |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, PyJWT, bcrypt |
| Storage | PostgreSQL 16, Redis 7 |
| Preview | Python standard library `http.server` + SQLite |
| Ops | Docker Compose, Nginx, Gunicorn/Uvicorn |

Brand palette: primary `#5B7FA5`, accent `#D4837A`, background `#F8F6F3`, success `#7CB69D`, warning `#E8B86D`.
