"""Engine і сесія SQLModel. Параметри беруться з .env (див. env.example)."""

import os
from collections.abc import Iterator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()


def get_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url
    user = quote_plus(os.getenv("POSTGRES_USER", "reserveflow"))
    password = quote_plus(os.environ["POSTGRES_PASSWORD"])
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "reserveflow")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def make_engine(url: str, **kwargs) -> Engine:
    """PostgreSQL для застосунку; SQLite (зокрема in-memory) для тестів."""
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False})
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _record):  # SQLite за замовчуванням ігнорує FK
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return engine
    return create_engine(url, pool_pre_ping=True, **kwargs)


_engine: Engine | None = None


def get_engine() -> Engine:
    """Ліниво створює engine, щоб імпорт модуля не вимагав змінних оточення."""
    global _engine
    if _engine is None:
        _engine = make_engine(get_database_url())
    return _engine


def init_db(engine: Engine | None = None) -> None:
    import models  # noqa: F401  (реєструє таблиці в metadata)

    SQLModel.metadata.create_all(engine or get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI-залежність: одна сесія на запит.
    У тестах підміняється через app.dependency_overrides[get_session]."""
    with Session(get_engine()) as session:
        yield session
