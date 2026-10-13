# -*- coding: utf-8 -*-
"""
把 demo/data/seed_content.py 的 41 张地道法语种子卡导入生产 PostgreSQL。

用法（在 backend/ 目录下配好 .env 后）：
    python ../scripts/import_seed.py            # 幂等：已存在同 front_text 的卡会跳过
    python ../scripts/import_seed.py --reset    # 危险：清空 levels/lessons/flashcards 后重建

说明：
- 只写内容三表（levels / lessons / flashcards），不动用户数据表
- 幂等判断：levels.code 唯一、lessons(level_id,title) 去重、flashcards.front_text 去重
- 上线前请人工审核每张卡的释义与 tip（PRD 7.2 内容质量要求）
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo" / "data"))

from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models import Flashcard, Lesson, Level  # noqa: E402
from seed_content import build_seed  # noqa: E402


async def do_import(reset: bool) -> None:
    levels, lessons, cards = build_seed()
    async with AsyncSessionLocal() as db:
        if reset:
            print("[警告] --reset：清空 flashcards / lessons / levels ...")
            await db.execute(Flashcard.__table__.delete())
            await db.execute(Lesson.__table__.delete())
            await db.execute(Level.__table__.delete())

        # 等级：按 code 幂等
        exist_codes = {c for (c,) in (await db.execute(select(Level.code))).all()}
        lv_map: dict[str, int] = {}
        for lv in levels:
            if lv["code"] in exist_codes:
                row = (await db.execute(
                    select(Level).where(Level.code == lv["code"]))).scalar_one()
                lv_map[lv["code"]] = row.id
                print(f"[跳过] 等级 {lv['code']} 已存在 (id={row.id})")
                continue
            row = Level(code=lv["code"], name=lv["name"], description=lv.get("description"),
                        sort_order=lv.get("sort_order", 0), is_active=True)
            db.add(row)
            await db.flush()
            lv_map[lv["code"]] = row.id
            print(f"[新增] 等级 {lv['code']} (id={row.id})")

        # 课时：按 (level_id, title) 幂等
        exist_titles = set((await db.execute(select(Lesson.level_id, Lesson.title))).all())
        lesson_ids: list[int] = []
        for ls in lessons:
            key = (lv_map[ls["level_code"]], ls["title"])
            if key in exist_titles:
                row = (await db.execute(
                    select(Lesson).where(Lesson.level_id == key[0], Lesson.title == key[1])
                )).scalar_one()
                lesson_ids.append(row.id)
                print(f"[跳过] 课时「{ls['title']}」已存在 (id={row.id})")
                continue
            row = Lesson(level_id=key[0], title=ls["title"],
                         description=ls.get("description"),
                         lesson_type=ls.get("lesson_type", "vocabulary"),
                         sort_order=ls.get("sort_order", 0), status="published")
            db.add(row)
            await db.flush()
            lesson_ids.append(row.id)
            print(f"[新增] 课时「{ls['title']}」(id={row.id})")

        # 闪卡：按 front_text 幂等
        exist_fronts = {f for (f,) in (await db.execute(select(Flashcard.front_text))).all()}
        added = skipped = 0
        for i, c in enumerate(cards):
            if c["front_text"] in exist_fronts:
                skipped += 1
                continue
            db.add(Flashcard(
                lesson_id=lesson_ids[min(i, len(lesson_ids) - 1)] if lesson_ids else None,
                front_text=c["front_text"], back_text=c["back_text"],
                example_sentence=c.get("example_sentence"),
                example_translation=c.get("example_translation"),
                tip=c.get("tip"), difficulty=c.get("difficulty", 1),
                tags=c.get("tags", []), is_sensitive=bool(c.get("is_sensitive")),
                sort_order=c.get("sort_order", i), status="published",
            ))
            exist_fronts.add(c["front_text"])
            added += 1

        await db.commit()
        print(f"[完成] 闪卡新增 {added} 张，跳过 {skipped} 张（共 {len(cards)} 张种子）")


def main() -> None:
    parser = argparse.ArgumentParser(description="导入种子内容到生产库")
    parser.add_argument("--reset", action="store_true",
                        help="危险：先清空内容三表再导入（不会动用户数据）")
    args = parser.parse_args()
    if args.reset:
        confirm = input("确认清空 levels/lessons/flashcards？输入 YES 继续：").strip()
        if confirm != "YES":
            print("已取消")
            return
    asyncio.run(do_import(args.reset))


if __name__ == "__main__":
    main()
