"""
alembic/env.py — V2 configured environment

Wired to:
  - Read DATABASE_URL from app.core.config (which reads .env)
  - Import all SQLAlchemy models so autogenerate can detect schema changes
  - Support both offline (SQL script) and online (live DB) migration modes
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# ── Path setup ────────────────────────────────────────────────────────────────
# Ensure the project root is on sys.path so app.* imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import app settings & Base ────────────────────────────────────────────────
from app.core.config import settings
from app.core.database import Base

# ── Import ALL models so Alembic autogenerate can detect them ─────────────────
# Adding a new model? Import it here.
from app.models.user import User  # noqa: F401
from app.models.submission import Submission  # noqa: F401
from app.models.result import Result  # noqa: F401
from app.models.practice_session import PracticeSession  # noqa: F401
from app.models.free_writing_session import FreeWritingSession  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with value from .env (never hardcode in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Offline mode (generate SQL script without a live DB) ─────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (apply to live DB) ───────────────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
