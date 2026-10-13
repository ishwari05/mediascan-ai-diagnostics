"""
Tests for DATABASE_URL resolution logic and engine options configuration.
"""

import os
import pytest
from app import _resolve_database_url, create_app


class TestResolveDatabaseUrl:
    def test_sqlite_url_unchanged(self):
        url, is_postgres = _resolve_database_url("sqlite:///mediascan.db")
        assert url == "sqlite:///mediascan.db"
        assert is_postgres is False

    def test_sqlite_memory_unchanged(self):
        url, is_postgres = _resolve_database_url("sqlite:///:memory:")
        assert url == "sqlite:///:memory:"
        assert is_postgres is False

    def test_postgresql_url_unchanged(self):
        raw = "postgresql://user:pass@host:5432/db"
        url, is_postgres = _resolve_database_url(raw)
        assert url == raw
        assert is_postgres is True

    def test_legacy_postgres_scheme_rewritten(self):
        raw = "postgres://user:pass@host:5432/db"
        url, is_postgres = _resolve_database_url(raw)
        assert url == "postgresql://user:pass@host:5432/db"
        assert is_postgres is True

    def test_legacy_scheme_with_sslmode(self):
        raw = "postgres://user:pass@host:5432/db?sslmode=require"
        url, is_postgres = _resolve_database_url(raw)
        assert url.startswith("postgresql://")
        assert "sslmode=require" in url
        assert is_postgres is True

    def test_supabase_pooler_url(self):
        """Supabase transaction-pooler URLs use the legacy scheme."""
        raw = "postgres://postgres.xyzxyz:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        url, is_postgres = _resolve_database_url(raw)
        assert url.startswith("postgresql://")
        assert "pooler.supabase.com" in url
        assert is_postgres is True

    def test_empty_string_does_not_crash(self):
        """Edge-case: empty string should not raise, just flag non-postgres."""
        url, is_postgres = _resolve_database_url("")
        assert url == ""
        assert is_postgres is False


class TestAppEngineOptions:
    def test_sqlite_does_not_set_postgres_engine_options(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
        app = create_app()

        assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
        engine_opts = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
        assert "connect_args" not in engine_opts
        assert "pool_recycle" not in engine_opts
        assert "pool_pre_ping" not in engine_opts

    def test_postgres_sets_engine_options(self, monkeypatch):
        raw_pg = "postgres://postgres.ref:secret@db.supabase.co:6543/postgres"
        monkeypatch.setenv("DATABASE_URL", raw_pg)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
        
        # Prevent create_app from attempting network calls on mock Postgres URI
        monkeypatch.setattr("database.init_db", lambda app: None)
        monkeypatch.setattr("models.ai_models.model_manager.load_models", lambda path: None)

        app = create_app()

        assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql://")
        assert "SQLALCHEMY_ENGINE_OPTIONS" in app.config
        opts = app.config["SQLALCHEMY_ENGINE_OPTIONS"]
        assert opts["pool_pre_ping"] is True
        assert opts["pool_recycle"] == 300
        assert opts["pool_size"] == 5
        assert opts["max_overflow"] == 5
        assert opts["connect_args"] == {"sslmode": "require"}
