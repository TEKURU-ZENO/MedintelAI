"""add_recommendation_feedback_table

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a1"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "recommendation_feedback",
        sa.Column("id",         sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id",    sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("item",       sa.String(),  nullable=False),
        sa.Column("module_type", sa.String(), nullable=False),
        sa.Column("focus_mode", sa.String(),  nullable=True),
        sa.Column("source",     sa.String(),  nullable=True),
        sa.Column("action",     sa.String(),  nullable=False),
        sa.Column("outcome_accuracy",   sa.Float(),   nullable=True),
        sa.Column("rule_prediction",    sa.String(),  nullable=True),
        sa.Column("ml_prediction",      sa.String(),  nullable=True),
        sa.Column("ml_confidence",      sa.Float(),   nullable=True),
        sa.Column("predictions_agreed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("recommendation_feedback")
