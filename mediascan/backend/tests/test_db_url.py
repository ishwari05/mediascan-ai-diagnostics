"""
Tests for DATABASE_URL resolution logic introduced in the Supabase migration.
These tests are pure-unit — no database connection is needed.
"""

import pytest
from app import _resolve_database_url


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
