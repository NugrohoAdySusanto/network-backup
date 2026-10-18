from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def new_session():
    return SessionLocal(bind=get_engine())


def get_db():
    db = new_session()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = new_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
