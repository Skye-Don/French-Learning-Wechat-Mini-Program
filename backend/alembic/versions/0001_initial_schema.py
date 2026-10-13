"""initial schema（对齐 PRD 4.2 DDL）

Revision ID: 0001
Revises: None
Create Date: 2026-10-13

说明：
- 与 PRD 4.2 完全一致，额外新增 flashcards.tip（地道用法提示，V0 内容字段）
- 时间统一 TIMESTAMPTZ；枚举全小写；主键 SERIAL
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_levels_active", "levels", ["is_active"])

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lesson_type", sa.String(30), server_default="vocabulary", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_lessons_level", "lessons", ["level_id"])
    op.create_index("idx_lessons_status", "lessons", ["status"])
    op.create_index("idx_lessons_type", "lessons", ["lesson_type"])
    op.create_index("idx_lessons_sort", "lessons", ["level_id", "sort_order"])

    op.create_table(
        "flashcards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=True),
        sa.Column("front_text", sa.Text(), nullable=False),
        sa.Column("back_text", sa.Text(), nullable=False),
        sa.Column("front_audio_url", sa.String(500), nullable=True),
        sa.Column("back_audio_url", sa.String(500), nullable=True),
        sa.Column("example_sentence", sa.Text(), nullable=True),
        sa.Column("example_translation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tags", postgresql.JSONB(), server_default="'[]'::jsonb", nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("tip", sa.Text(), nullable=True),  # V0 扩展：地道用法提示
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_flashcards_lesson", "flashcards", ["lesson_id"])
    op.create_index("idx_flashcards_status", "flashcards", ["status"])
    op.create_index("idx_flashcards_difficulty", "flashcards", ["difficulty"])
    op.create_index("idx_flashcards_sensitive", "flashcards", ["is_sensitive"])
    op.create_index("idx_flashcards_tags", "flashcards", ["tags"], postgresql_using="gin")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("wx_openid", sa.String(128), nullable=True),
        sa.Column("wx_unionid", sa.String(128), nullable=True),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("role", sa.String(20), server_default="learner", nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("current_level", sa.String(10), nullable=True),
        sa.Column("total_study_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_cards_learned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("streak_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_checkin_date", sa.Date(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sensitive_opt_in", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_active", "users", ["is_active"])
    op.create_index("idx_users_level", "users", ["current_level"])
    op.create_index("idx_users_streak", "users", [sa.text("streak_days DESC")])
    # 注：PRD 另有部分唯一索引 idx_users_wx_openid（WHERE wx_openid IS NOT NULL），
    # 与下面的 UNIQUE 约束等价（PG 中 NULL 互不相等），此处只保留约束，避免重复索引
    op.create_unique_constraint("uq_users_openid", "users", ["wx_openid"])
    op.create_unique_constraint("uq_users_unionid", "users", ["wx_unionid"])

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=True),
        sa.Column("reminder_days", postgresql.JSONB(),
                  server_default="'[1,2,3,4,5,6,7]'::jsonb", nullable=False),
        sa.Column("daily_goal", sa.Integer(), server_default="20", nullable=False),
        sa.Column("sound_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("theme", sa.String(20), server_default="default", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_pref_user"),
    )

    op.create_table(
        "checkins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("cards_reviewed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("new_cards_learned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("study_duration", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),
    )
    op.create_index("idx_checkins_user_date", "checkins", ["user_id", sa.text("checkin_date DESC")])
    op.create_index("idx_checkins_date", "checkins", ["checkin_date"])

    op.create_table(
        "flashcard_progress",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("flashcard_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("ease_factor", sa.Float(), server_default="2.5", nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("repetitions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("last_review_date", sa.Date(), nullable=True),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wrong_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["flashcard_id"], ["flashcards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "flashcard_id", name="uq_progress_user_card"),
    )
    op.create_index("idx_progress_user_status", "flashcard_progress", ["user_id", "status"])
    op.create_index("idx_progress_next_review", "flashcard_progress", ["user_id", "next_review_date"])

    op.create_table(
        "learning_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(30), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), server_default="0", nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_records_user_type", "learning_records", ["user_id", "record_type"])
    op.create_index("idx_records_user_date", "learning_records", ["user_id", sa.text("created_at DESC")])

    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="admin", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("login_fail_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_admin", "admin_audit_logs", ["admin_id"])
    op.create_index("idx_audit_action", "admin_audit_logs", ["action"])
    op.create_index("idx_audit_date", "admin_audit_logs", [sa.text("created_at DESC")])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("setting_key", sa.String(100), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_index("idx_audit_date", table_name="admin_audit_logs")
    op.drop_index("idx_audit_action", table_name="admin_audit_logs")
    op.drop_index("idx_audit_admin", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_table("admin_accounts")
    op.drop_index("idx_records_user_date", table_name="learning_records")
    op.drop_index("idx_records_user_type", table_name="learning_records")
    op.drop_table("learning_records")
    op.drop_index("idx_progress_next_review", table_name="flashcard_progress")
    op.drop_index("idx_progress_user_status", table_name="flashcard_progress")
    op.drop_table("flashcard_progress")
    op.drop_index("idx_checkins_date", table_name="checkins")
    op.drop_index("idx_checkins_user_date", table_name="checkins")
    op.drop_table("checkins")
    op.drop_table("user_preferences")
    op.drop_constraint("uq_users_unionid", "users", type_="unique")
    op.drop_constraint("uq_users_openid", "users", type_="unique")
    op.drop_index("idx_users_streak", table_name="users")
    op.drop_index("idx_users_level", table_name="users")
    op.drop_index("idx_users_active", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_table("users")
    op.drop_index("idx_flashcards_tags", table_name="flashcards")
    op.drop_index("idx_flashcards_sensitive", table_name="flashcards")
    op.drop_index("idx_flashcards_difficulty", table_name="flashcards")
    op.drop_index("idx_flashcards_status", table_name="flashcards")
    op.drop_index("idx_flashcards_lesson", table_name="flashcards")
    op.drop_table("flashcards")
    op.drop_index("idx_lessons_sort", table_name="lessons")
    op.drop_index("idx_lessons_type", table_name="lessons")
    op.drop_index("idx_lessons_status", table_name="lessons")
    op.drop_index("idx_lessons_level", table_name="lessons")
    op.drop_table("lessons")
    op.drop_index("idx_levels_active", table_name="levels")
    op.drop_table("levels")
