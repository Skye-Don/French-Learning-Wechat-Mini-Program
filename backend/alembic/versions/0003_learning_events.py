"""learning_events 行为埋点表

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL 用 JSONB；其他库（如 SQLite 单测）回退到 JSON
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    payload_type = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()

    op.create_table(
        "learning_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("payload", payload_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_events_user_created", "learning_events", ["user_id", "created_at"])
    op.create_index("ix_learning_events_type_created", "learning_events", ["event_type", "created_at"])


def downgrade():
    op.drop_index("ix_learning_events_type_created", table_name="learning_events")
    op.drop_index("ix_learning_events_user_created", table_name="learning_events")
    op.drop_table("learning_events")
