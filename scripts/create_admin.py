# -*- coding: utf-8 -*-
"""
创建后台管理员账号（PRD 5.8）

用法（在 backend/ 目录下，已配好 .env）：
    python ../scripts/create_admin.py admin YourStrong@Pass123 --role super_admin
    python ../scripts/create_admin.py ops SomePass@123            # 默认 role=admin

说明：
- 密码 bcrypt cost=12 存储，脚本不会把密码写进任何日志
- username 重复时会提示，不会覆盖已有账号
"""
import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models import AdminAccount  # noqa: E402
from app.security import hash_password  # noqa: E402


async def create_admin(username: str, password: str, role: str) -> None:
    async with AsyncSessionLocal() as db:
        exist = (await db.execute(
            select(AdminAccount).where(AdminAccount.username == username)
        )).scalar_one_or_none()
        if exist:
            print(f"[跳过] 管理员已存在：{username}（id={exist.id}, role={exist.role}）")
            return
        admin = AdminAccount(username=username, password_hash=hash_password(password), role=role)
        db.add(admin)
        await db.commit()
        print(f"[完成] 已创建管理员：{username}（id={admin.id}, role={role}）")


def main() -> None:
    parser = argparse.ArgumentParser(description="创建后台管理员")
    parser.add_argument("username", help="登录用户名")
    parser.add_argument("password", nargs="?", help="登录密码（不传则交互输入，避免进 shell 历史）")
    parser.add_argument("--role", choices=["admin", "super_admin"], default="admin")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("请输入密码（输入不回显）：")
        confirm = getpass.getpass("再次输入确认：")
        if password != confirm:
            print("[失败] 两次输入不一致")
            sys.exit(1)
    if len(password) < 8:
        print("[失败] 密码至少 8 位")
        sys.exit(1)

    asyncio.run(create_admin(args.username, password, args.role))


if __name__ == "__main__":
    main()
