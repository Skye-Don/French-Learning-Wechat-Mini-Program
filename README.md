# 法语学习小程序（V0）

学**最地道的法语**：真实口语表达 + 教科书不教的用法提示（tip），3D 翻卡 + 间隔重复复习 + 每日打卡。

> 本仓库是 V0 全量交付：**小程序源码 + 生产后端代码 + H5 预览版（可扫码试用）+ 极简内容后台**。

---

## 📱 立即试用

| 方式 | 说明 |
|---|---|
| **扫码体验（推荐）** | 扫 `docs/qrcode-preview.png`，手机直接体验完整 V0 流程 |
| **浏览器打开** | https://french-learning-miniapp.app.workbuddy.host/ （内置手机壳模拟器） |
| **内容后台** | https://french-learning-miniapp.app.workbuddy.host/admin （极简录入页） |

> ⚠️ 微信小程序本体**无法**通过 http 链接打开（微信限制），所以提供 1:1 复刻的 H5 预览版供扫码试用；
> 真正的小程序请用微信开发者工具导入 `miniprogram/` 目录运行（见下文）。

---

## 📁 目录结构

```
french-miniprogram/
├── miniprogram/        # 微信小程序源码（原生框架，10 个页面，可直接用微信开发者工具打开）
├── backend/            # 生产后端：FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis
│   ├── app/            # models / schemas / routers(auth, learning, admin) / security
│   ├── alembic/        # 异步迁移（0001 初始建表，对齐 PRD 4.2 DDL）
│   └── tests/          # 端到端冒烟测试（SQLite 跑，无需真实 PG/Redis）
├── demo/               # H5 预览版：纯标准库 server + SQLite，零依赖一键启动
├── docker/             # docker-compose（PG + Redis + API + Nginx）与 nginx.conf
├── docs/               # 二维码、部署说明
└── scripts/            # 建管理员 / 导种子 / Git 上传脚本
```

---

## 🚀 快速开始

### 1. 跑 H5 预览版（30 秒）
```bash
cd demo
python server.py          # 打开 http://127.0.0.1:8000
```

### 2. 跑生产后端
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # 填 WX_APPID / WX_SECRET / JWT_SECRET / DB_PASSWORD
python ../scripts/create_admin.py admin 'YourPass@123' --role super_admin
python ../scripts/import_seed.py        # 导入 41 张地道法语种子卡
uvicorn app.main:app --reload           # http://127.0.0.1:8000/docs
```
> 开发环境自动建表；生产环境用 `alembic upgrade head`（连接串从 `.env` 读取，不入库）。

### 3. 跑小程序
1. 微信开发者工具 → 导入 `miniprogram/` 目录，填入你的 AppID
2. 修改 `miniprogram/utils/config.js` 里的 `API_BASE_URL` 为你的后端 HTTPS 域名
3. 上线前在微信公众平台配置 request 合法域名（必须 HTTPS + 备案）

### 4. 跑测试
```bash
cd backend
pytest tests/ -v        # 登录→学习→敏感词过滤→打卡幂等→后台 CRUD→审计日志 全链路
```

---

## 🔐 安全红线（改代码前必读）

- `openid` 只能在**服务端**用 code 换（`backend/app/wx_api.py`），绝不接受前端上报
- `JWT_SECRET` / `WX_SECRET` / 数据库密码只存 `.env`，已被 `.gitignore` 排除
- 日志禁止输出 token / openid / 密码（后台登录失败只记用户名与 IP）
- 支付类需求上线前必须服务端签名，密钥不进前端

## ⚠️ 上线合规检查（缺一项可能被驳回，以微信官方最新规则为准）

- 类目与资质（教育类可能需要资质）
- 用户隐私保护指引 + 隐私弹窗（本项目收集 openid、学习记录，需声明）
- 服务器域名 HTTPS + ICP 备案
- 敏感词汇内容已做 opt-in 前置开关（默认关闭）
