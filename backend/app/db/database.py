"""Database configuration and SQLAlchemy session management."""

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(RuntimeError):
    """Raised when persistence has not been configured."""


class DatabaseUnavailableError(RuntimeError):
    """Raised when a configured database cannot be reached."""


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL ayarı bulunamadı. Kalıcı analiz depolaması için "
            "PostgreSQL bağlantı adresi tanımlanmalıdır."
        )
    return database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    try:
        return create_engine(url, pool_pre_ping=True)
    except Exception as exc:
        raise DatabaseConfigurationError(
            f"DATABASE_URL ile veritabanı motoru oluşturulamadı: {exc}"
        ) from exc


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def assert_database_available(engine: Engine) -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise DatabaseUnavailableError(
            f"PostgreSQL bağlantısı kurulamadı: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def get_default_engine() -> Engine:
    return create_database_engine()
