"""phase2_session_upgrades

Phase 2: Learning Module System — session table upgrades
- Adds: attempt_number, stroke_data, module_version, status enum,
        total_strokes, total_points to practice_sessions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b2c3d4e5f6a7'
down_revision = 'b2c3d4e5f6a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the session_status_enum type in PostgreSQL
    session_status_enum = postgresql.ENUM(
        'started', 'in_progress', 'completed', 'abandoned',
        name='session_status_enum',
    )
    session_status_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table('practice_sessions') as batch_op:
        batch_op.add_column(sa.Column(
            'attempt_number', sa.Integer(), nullable=False, server_default='1'
        ))
        batch_op.add_column(sa.Column(
            'module_version', sa.String(), nullable=False, server_default='v1'
        ))
        batch_op.add_column(sa.Column(
            'status',
            sa.Enum('started', 'in_progress', 'completed', 'abandoned',
                    name='session_status_enum'),
            nullable=False,
            server_default='started',
        ))
        batch_op.add_column(sa.Column(
            'stroke_data', postgresql.JSONB(), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'total_strokes', sa.Integer(), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'total_points', sa.Integer(), nullable=True
        ))


def downgrade() -> None:
    with op.batch_alter_table('practice_sessions') as batch_op:
        batch_op.drop_column('total_points')
        batch_op.drop_column('total_strokes')
        batch_op.drop_column('stroke_data')
        batch_op.drop_column('status')
        batch_op.drop_column('module_version')
        batch_op.drop_column('attempt_number')

    # Drop the enum type
    postgresql.ENUM(name='session_status_enum').drop(op.get_bind(), checkfirst=True)
