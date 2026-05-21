"""Слой БД: движок/сессии. Продакшн — Postgres (settings.database_url); тесты — sqlite in-memory."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# важно: импортируем модели, чтобы они зарегистрировались в SQLModel.metadata
from figaro.domain import models  # noqa: F401


def make_engine(url: str, echo: bool = False):
    return create_engine(url, echo=echo)


def make_test_engine():
    """In-memory sqlite с единым соединением (StaticPool) — для тестов/BDD."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def session_scope(engine) -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
