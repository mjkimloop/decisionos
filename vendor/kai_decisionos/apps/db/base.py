from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from packages.common.config import settings


class Base(DeclarativeBase):
    pass


_ENGINE = None
_SessionLocal = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        if not settings.db_url:
            raise RuntimeError("DB URL not configured (DOS_DB_URL)")
        _ENGINE = create_engine(settings.db_url, future=True)
    return _ENGINE


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


def get_session():
    return get_sessionmaker()()

