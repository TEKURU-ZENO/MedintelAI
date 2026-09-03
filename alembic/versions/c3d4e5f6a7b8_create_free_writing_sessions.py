"""create_free_writing_sessions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "free_writing_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("session_intent", sa.String(length=50), nullable=True, server_default="practice"),
        sa.Column("soft_goal", sa.String(length=100), nullable=True),
        sa.Column("stroke_data", postgresql.JSONB(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("stroke_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("canvas_width", sa.Integer(), nullable=True, server_default="400"),
        sa.Column("canvas_height", sa.Integer(), nullable=True, server_default="400"),
        sa.Column("quality_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("quality_band", sa.String(length=20), nullable=True),
        sa.Column("primary_strength", sa.String(length=50), nullable=True),
        sa.Column("primary_focus_area", sa.String(length=50), nullable=True),
        sa.Column("emotional_state_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("free_writing_sessions")
