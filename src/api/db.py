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
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    user = quote_plus(os.getenv("POSTGRES_USER", "reserveflow"))
    password = quote_plus(os.environ["POSTGRES_PASSWORD"])
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    name = os.getenv("POSTGRES_DB", "reserveflow")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


# Тайм-аути до PostgreSQL (Лаб 9, знахідки #2, #3): жоден виклик до БД не чекає необмежено.
# Значення в межах, які відчуває користувач: краще швидка 503, ніж «зависання» всього API.
DB_CONNECT_TIMEOUT_S = 5  # TCP-з'єднання з сервером БД
DB_POOL_TIMEOUT_S = 5  # очікування вільного з'єднання в пулі
DB_STATEMENT_TIMEOUT_MS = 5000  # максимальний час виконання одного SQL-запиту
DB_LOCK_TIMEOUT_MS = 3000  # очікування блокування рядка (SELECT ... FOR UPDATE)


def _postgres_timeouts() -> dict:
    """Параметри create_engine з тайм-аутами для psycopg / PostgreSQL."""
    return {
        "pool_timeout": DB_POOL_TIMEOUT_S,
        "connect_args": {
            "connect_timeout": DB_CONNECT_TIMEOUT_S,
            "options": (
                f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS} "
                f"-c lock_timeout={DB_LOCK_TIMEOUT_MS}"
            ),
        },
    }


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
    for key, value in _postgres_timeouts().items():
        kwargs.setdefault(key, value)
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


# Використання ШІ: для редагування файлу для публічного розгортання було використано ШІ Gemini,
# перевірено та затверджено командою.
