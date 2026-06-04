"""Alembic environment.

We don't use SQLAlchemy ORM models in this project; migrations are written
as raw SQL via `op.execute()`. `target_metadata` is therefore None and
autogeneration is not supported (intentional — we write migrations by hand).

The Config is built programmatically by `dequorum.db.migrate`, so there's
no alembic.ini file. We read `sqlalchemy.url` from the main options.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    assert url, "sqlalchemy.url must be set by dequorum.db.migrate"
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
