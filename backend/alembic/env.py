"""
alembic/env.py — Alembic migration environment (async)
─────────────────────────────────────────────────────────────────────────────
Wired to asyncpg via run_async_migrations() so migrations run in the same
async engine used by the app.  All models are imported via app.db.models so
Alembic detects every table in the `autogenerate` diff.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Load app config ───────────────────────────────────────────────────────────
# Import settings BEFORE models so DATABASE_URL is available
from app.core.config import settings

# Import ALL models so Base.metadata is fully populated
import app.db.models  # noqa: F401  — side-effect: registers all ORM classes
from app.db.models import Base

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url with the value from our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ─────────────────────────────────────────────────────────────────────────────
# Offline mode  (generate SQL script without connecting)
# ─────────────────────────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
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


# ─────────────────────────────────────────────────────────────────────────────
# Online mode  (connect and run migrations)
# ─────────────────────────────────────────────────────────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Render the PostgreSQL partial index for PIN uniqueness
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()