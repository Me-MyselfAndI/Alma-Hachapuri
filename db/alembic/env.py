"""Alembic environment.

Wires Alembic to the application's settings and ORM metadata:

* `sqlalchemy.url` is taken from `src.core.config.settings.database_url` so
  Alembic and the running API talk to the same database without duplicating
  config.
* `target_metadata = Base.metadata` after importing ``src.domains`` so every
  ORM model is registered — this is what makes ``--autogenerate`` see all
  tables in one pass.

Run from the ``db/`` directory (where ``alembic.ini`` lives):

    cd db
    alembic upgrade head
    alembic revision --autogenerate -m "..."
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `src` importable when alembic runs from db/.
# db/alembic/env.py -> parents[2] is the repo root; api/ sits next to db/.
REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC_PARENT = REPO_ROOT / "api"
if str(API_SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(API_SRC_PARENT))

from src.core.config import settings  # noqa: E402
from src.core.database import Base  # noqa: E402
import src.domains  # noqa: E402,F401  -- side-effect: register all models


config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a DBAPI connection (emits SQL to stdout)."""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
