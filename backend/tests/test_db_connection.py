"""Unit tests for the WC golden-rule guard in src/db/connection.py.

The most important safety property in this codebase: `execute_write`
MUST refuse outright if the target database is ever "LaHerencia" (the
protected original), regardless of how it got misconfigured.
"""

from __future__ import annotations

import pytest

from src.db import connection


def test_execute_write_refuses_target_laherencia(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "LaHerencia")
    with pytest.raises(RuntimeError, match="LaHerencia"):
        connection.execute_write("UPDATE dbo.Foo SET Bar = ? WHERE Id = ?", (1, 2))


def test_execute_write_refuses_target_laherencia_case_insensitive(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "LAHERENCIA")
    with pytest.raises(RuntimeError, match="LaHerencia"):
        connection.execute_write("UPDATE dbo.Foo SET Bar = ? WHERE Id = ?", (1, 2))


def test_execute_write_rejects_select(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="INSERT/UPDATE/DELETE"):
        connection.execute_write("SELECT * FROM dbo.Foo", ())


def test_execute_write_rejects_ddl_keywords(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="Forbidden keyword"):
        connection.execute_write("UPDATE dbo.Foo SET Bar = 1; DROP TABLE dbo.Foo", ())


def test_execute_write_rejects_multiple_statements(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="Multiple statements"):
        connection.execute_write("UPDATE dbo.Foo SET Bar = 1; UPDATE dbo.Foo SET Baz = 2", ())
