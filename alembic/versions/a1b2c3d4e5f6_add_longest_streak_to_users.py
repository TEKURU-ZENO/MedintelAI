"""add_longest_streak_to_users

Revision ID: a1b2c3d4e5f6
Revises: (previous migration)
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill: set longest_streak = user_streak for all existing users
    op.execute("UPDATE users SET longest_streak = user_streak WHERE longest_streak = 0 AND user_streak > 0")


def downgrade() -> None:
    op.drop_column("users", "longest_streak")
