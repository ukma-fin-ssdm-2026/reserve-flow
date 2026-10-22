import os
from unittest.mock import patch
from sqlmodel import Session
from db import get_database_url, make_engine, get_engine, init_db, get_session


def test_get_database_url_explicit(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/db")
    assert get_database_url() == "postgresql+psycopg://test:test@localhost/db"


def test_get_database_url_env_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "maindb")
    
    url = get_database_url()
    assert "admin:secret@dbhost:5432/maindb" in url


def test_make_engine_sqlite_branches():
    engine_memory = make_engine("sqlite:///:memory:")
    assert engine_memory is not None
    
    raw_conn = engine_memory.raw_connection()
    raw_conn.close()

    engine_file = make_engine("sqlite:///test.db")
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