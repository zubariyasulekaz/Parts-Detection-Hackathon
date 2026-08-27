"""Alembic environment configuration for the RigidHitch database.

A parallel counterpart to `partpilot/alembic/env.py`, pointed at a different
database entirely - RigidHitch's catalog lives in its own database, not
PartPilot's own (see `scripts/import_rigidhitch_catalog.py` for why). Reads
`RIGIDHITCH_DATABASE_URL` directly rather than `backend.config.settings`, so
it never touches PartPilot's own `DATABASE_URL`.

Migrations run over a synchronous psycopg2 connection, same as the main
environment - Alembic's migration runner is not async-aware.

Run from the `partpilot/` directory:
    alembic -c alembic_rigidhitch.ini upgrade head
"""

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic_rigidhitch.schema import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Loads partpilot/.env (if present) into os.environ - RIGIDHITCH_DATABASE_URL
# can then live there like every other setting, rather than needing a
# separate `$env:RIGIDHITCH_DATABASE_URL = ...` each session. Does not
# override a value already set in the real environment.
load_dotenv()

database_url = os.environ.get("RIGIDHITCH_DATABASE_URL")
if not database_url:
    raise SystemExit("RIGIDHITCH_DATABASE_URL is not set - export it before running alembic.")

sync_database_url = database_url.replace("postgresql+asyncpg", "postgresql").replace(
    "postgresql://", "postgresql+psycopg2://"
)
if not sync_database_url.startswith("postgresql+psycopg2://"):
    raise SystemExit(f"Unrecognized database URL scheme: {sync_database_url.split('://')[0]}://")

config.set_main_option("sqlalchemy.url", sync_database_url)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Emit migration SQL without a live DB connection (`--sql` mode)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
