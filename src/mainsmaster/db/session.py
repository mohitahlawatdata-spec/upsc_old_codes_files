"""Lazy database connection and transaction scope."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mainsmaster.settings import get_settings


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is missing; copy .env.example to .env and set it")
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
