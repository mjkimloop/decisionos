from __future__ import annotations

from sqlalchemy import text

from .base import Base, get_engine
from . import models  # noqa: F401 - ensure models are imported


def init_db():
    """개발용: 테이블 자동 생성(create_all). 운영은 마이그레이션 권장."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))

