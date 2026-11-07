"""Alembic environment for the clean app."""

from alembic import context
from sqlalchemy import create_engine, pool

from mainsmaster.db.models import Base
from mainsmaster.settings import get_settings

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
