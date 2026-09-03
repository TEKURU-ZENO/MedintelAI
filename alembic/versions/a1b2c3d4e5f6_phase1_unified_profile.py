"""phase1_unified_profile

Phase 1: Unified Profile System
- Adds: full_name, date_of_birth, pending_parent_link, preferred_learning_mode,
        preferred_language, level, xp_points to users table
- Renames: role → _legacy_role (safe rename, NOT dropped — will be removed in Phase 2)
- Creates: practice_sessions table (central fact table for learning engine)

Revision ID: a1b2c3d4e5f6
Revises: (initial migration — no parent)
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Check if 'users' table exists, if not, create it ─────────────────────
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'users' not in inspector.get_table_names():
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('email', sa.String(), unique=True, nullable=False, index=True),
            sa.Column('hashed_password', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False
            ),
        )

    # ── Check if 'submissions' table exists, if not, create it ───────────────
    if 'submissions' not in inspector.get_table_names():
        op.create_table(
            'submissions',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('input_type', sa.Enum('image', 'canvas', name='inputtype'), nullable=False),
            sa.Column('image_path', sa.String(), nullable=True),
            sa.Column('stroke_data', postgresql.JSONB(), nullable=True),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False
            ),
        )

    # ── Check if 'results' table exists, if not, create it ───────────────────
    if 'results' not in inspector.get_table_names():
        op.create_table(
            'results',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('submission_id', sa.Integer(), sa.ForeignKey('submissions.id'), nullable=True),
            sa.Column('features', postgresql.JSONB(), nullable=True),
            sa.Column('scores', postgresql.JSONB(), nullable=True),
            sa.Column('feedback', postgresql.JSONB(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('audio_path', sa.String(), nullable=True),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False
            ),
        )

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Rename 'role' → '_legacy_role' on users table (safe rename, not drop)
    #    Using batch mode for cross-dialect compatibility.
    # ──────────────────────────────────────────────────────────────────────────
    with op.batch_alter_table('users') as batch_op:
        # Rename the existing role column so it is preserved but clearly marked legacy
        try:
            batch_op.alter_column('role', new_column_name='_legacy_role')
        except Exception:
            # Column may not exist in fresh DBs (first-time setup)
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Add new V2 profile columns to users table
    # ──────────────────────────────────────────────────────────────────────────
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('full_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('date_of_birth', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column(
            'parent_id',
            sa.Integer(),
            sa.ForeignKey('users.id'),
            nullable=True
        ))
        batch_op.add_column(sa.Column(
            'pending_parent_link', sa.Boolean(), nullable=False, server_default='false'
        ))
        batch_op.add_column(sa.Column(
            'preferred_learning_mode', sa.String(), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'preferred_language', sa.String(), nullable=False, server_default='english'
        ))
        batch_op.add_column(sa.Column(
            'level', sa.Integer(), nullable=False, server_default='1'
        ))
        batch_op.add_column(sa.Column(
            'xp_points', sa.Integer(), nullable=False, server_default='0'
        ))
        batch_op.add_column(sa.Column(
            'user_streak', sa.Integer(), nullable=False, server_default='0'
        ))
        batch_op.add_column(sa.Column(
            'last_active_date', sa.Date(), nullable=True
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Create practice_sessions table
    #    This is the central fact table for the adaptive learning engine.
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('module_type', sa.String(), nullable=False),
        sa.Column('target_item', sa.String(), nullable=True),
        sa.Column('language', sa.String(), nullable=False, server_default='english'),
        sa.Column('difficulty', sa.String(), nullable=False, server_default='beginner'),
        sa.Column(
            'started_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('detailed_scores', postgresql.JSONB(), nullable=True),
        sa.Column('xp_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
    )


def downgrade() -> None:
    # ── Drop practice_sessions ────────────────────────────────────────────────
    op.drop_table('practice_sessions')

    # ── Remove V2 columns from users ─────────────────────────────────────────
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('xp_points')
        batch_op.drop_column('level')
        batch_op.drop_column('preferred_language')
        batch_op.drop_column('preferred_learning_mode')
        batch_op.drop_column('pending_parent_link')
        batch_op.drop_column('parent_id')
        batch_op.drop_column('date_of_birth')
        batch_op.drop_column('full_name')

    # ── Rename _legacy_role back to role ──────────────────────────────────────
    with op.batch_alter_table('users') as batch_op:
        try:
            batch_op.alter_column('_legacy_role', new_column_name='role')
        except Exception:
            pass
