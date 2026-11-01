import pytest
from sqlmodel import Session
from db import get_database_url, make_engine, get_engine, init_db, get_session

pytestmark = pytest.mark.no_req(
    "інфраструктура: підключення до БД і сесії (db.py), не поведінка системи"
)

# Вигадана адреса тестової БД, не справжні облікові дані
TEST_DB_URL = "postgresql+psycopg://test:test@localhost/db"  # pragma: allowlist secret


def test_get_database_url_explicit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    assert get_database_url() == TEST_DB_URL


@pytest.mark.parametrize(
    "raw_url",
    [
        "postgres://test:test@localhost:5432/db",  # pragma: allowlist secret
        "postgresql://test:test@localhost:5432/db",  # pragma: allowlist secret
    ],
)
def test_get_database_url_normalizes_paas_schemes(monkeypatch, raw_url):
    monkeypatch.setenv("DATABASE_URL", raw_url)
    expected = "postgresql+psycopg://test:test@localhost:5432/db"  # pragma: allowlist secret
    assert get_database_url() == expected


def test_get_database_url_env_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "maindb")

    url = get_database_url()
    assert "admin:secret@dbhost:5432/maindb" in url


def test_make_engine_sqlite_branches(tmp_path):
    engine_memory = make_engine("sqlite:///:memory:")
    assert engine_memory is not None

    raw_conn = engine_memory.raw_connection()
    raw_conn.close()

    # файлова БД — у тимчасовій папці pytest, а не в корені репо
    engine_file = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    assert engine_file is not None
    raw_file_conn = engine_file.raw_connection()
    raw_file_conn.close()


def test_get_engine_lazy_init(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    import db

    db._engine = None

    eng1 = get_engine()
    eng2 = get_engine()
    assert eng1 is eng2


def test_init_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    import db

    db._engine = None

    init_db()


def test_get_session_generator(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    import db

    db._engine = None

    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)
    try:
        next(gen)
    except StopIteration:
        pass


# Використання ШІ: створено за допомогою ШІ Gemini на основі ідей команди, перевірено та затверджено
# командою.
