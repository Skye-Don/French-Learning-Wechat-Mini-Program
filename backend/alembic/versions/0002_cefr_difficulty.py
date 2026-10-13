"""flashcards.difficulty：数字难度 1-5 -> CEFR 等级 A1/A2/B1/B2

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13

背景：
- 原设计 difficulty 为 INTEGER 1-5，与小程序「A1 → B2」的等级体系（PRD 2.2）对不上，
  后台录入时运营也不知道该填几。统一改成 CEFR 等级字符串，与 levels.code 同一套口径。

数据迁移映射（旧 -> 新）：
    1 -> A1      2 -> A2      3 -> B1      4 / 5 / 其它 -> B2

兼容说明：
- 生产目标是 PostgreSQL，走 USING 表达式原地转换（不丢数据、无需重建表）。
- 非 PostgreSQL（如本地 SQLite 单测库）走 batch_alter_table 改类型声明；SQLite 本身是
  动态类型，实际存储值由应用层保证，这里只同步 DDL 声明。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 旧数字 -> CEFR 等级（PostgreSQL USING 子句）
_PG_USING = """
CASE difficulty
    WHEN 1 THEN 'A1'
    WHEN 2 THEN 'A2'
    WHEN 3 THEN 'B1'
    ELSE 'B2'
END
"""

# 反向映射（downgrade）
_PG_USING_DOWN = """
CASE difficulty
    WHEN 'A1' THEN 1
    WHEN 'A2' THEN 2
    WHEN 'B1' THEN 3
    ELSE 4
END
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            f"ALTER TABLE flashcards ALTER COLUMN difficulty TYPE VARCHAR(2) USING ({_PG_USING})"
        )
        op.execute("ALTER TABLE flashcards ALTER COLUMN difficulty SET DEFAULT 'A1'")
    else:
        with op.batch_alter_table("flashcards") as batch_op:
            batch_op.alter_column(
                "difficulty",
                existing_type=sa.Integer(),
                type_=sa.String(length=2),
                existing_nullable=False,
                server_default="A1",
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            f"ALTER TABLE flashcards ALTER COLUMN difficulty TYPE INTEGER USING ({_PG_USING_DOWN})"
        )
        op.execute("ALTER TABLE flashcards ALTER COLUMN difficulty SET DEFAULT 1")
    else:
        with op.batch_alter_table("flashcards") as batch_op:
            batch_op.alter_column(
                "difficulty",
                existing_type=sa.String(length=2),
                type_=sa.Integer(),
                existing_nullable=False,
                server_default="1",
            )
