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


def test_execute_insert_returning_id_refuses_target_laherencia(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "LaHerencia")
    with pytest.raises(RuntimeError, match="LaHerencia"):
        connection.execute_insert_returning_id(
            "INSERT INTO dbo.Foo (Bar) OUTPUT INSERTED.Id VALUES (?)", (1,)
        )


def test_execute_insert_returning_id_rejects_non_insert(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="INSERT"):
        connection.execute_insert_returning_id("UPDATE dbo.Foo SET Bar = 1", ())


def test_execute_insert_returning_id_requires_output_clause(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="OUTPUT"):
        connection.execute_insert_returning_id("INSERT INTO dbo.Foo (Bar) VALUES (?)", (1,))


def test_execute_write_transaction_refuses_target_laherencia(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "LaHerencia")
    with pytest.raises(RuntimeError, match="LaHerencia"):
        connection.execute_write_transaction([("INSERT INTO dbo.Foo (Bar) VALUES (?)", (1,))])


def test_execute_write_transaction_rejects_non_write_statement(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="INSERT/UPDATE/DELETE"):
        connection.execute_write_transaction([("SELECT * FROM dbo.Foo", ())])


def test_execute_write_transaction_rejects_ddl_keywords(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="Forbidden keyword"):
        connection.execute_write_transaction(
            [
                ("UPDATE dbo.Foo SET Bar = 1", ()),
                ("UPDATE dbo.Foo SET Bar = 1; DROP TABLE dbo.Foo", ()),
            ]
        )


def test_execute_write_transaction_rejects_multiple_statements(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="Multiple statements"):
        connection.execute_write_transaction(
            [("UPDATE dbo.Foo SET Bar = 1; UPDATE dbo.Foo SET Baz = 2", ())]
        )


def test_execute_write_transaction_requires_at_least_one_statement(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    with pytest.raises(ValueError, match="at least one statement"):
        connection.execute_write_transaction([])


class _FakeCursor:
    """Fakes a pyodbc cursor. `fail_on_call` (1-indexed) raises on that execute()."""

    def __init__(self, fail_on_call: int | None = None):
        self.calls = 0
        self.executed = []
        self.fail_on_call = fail_on_call

    def execute(self, sql, params):
        self.calls += 1
        self.executed.append((sql, params))
        if self.fail_on_call is not None and self.calls == self.fail_on_call:
            raise RuntimeError("simulated failure on 2nd statement")

    def fetchone(self):
        return (42,)

    @property
    def rowcount(self):
        return 1


class _FakeConnection:
    def __init__(self, fail_on_call: int | None = None):
        self.cursor_obj = _FakeCursor(fail_on_call=fail_on_call)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_execute_write_transaction_rolls_back_all_on_mid_batch_failure(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    fake_conn = _FakeConnection(fail_on_call=2)
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **kw: fake_conn)

    statements = [
        ("INSERT INTO dbo.Compras (Fecha) VALUES (?)", (1,)),
        ("INSERT INTO dbo.Det_Compras (IdCompra) VALUES (?)", (1,)),
    ]
    with pytest.raises(RuntimeError, match="simulated failure"):
        connection.execute_write_transaction(statements)

    assert fake_conn.cursor_obj.calls == 2
    assert fake_conn.rolled_back is True
    assert fake_conn.committed is False
    assert fake_conn.closed is True


def test_execute_write_transaction_commits_once_when_all_succeed(monkeypatch):
    monkeypatch.setattr(connection, "DATABASE", "WC")
    fake_conn = _FakeConnection()
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **kw: fake_conn)

    statements = [
        ("INSERT INTO dbo.Compras (Fecha) OUTPUT INSERTED.IdDeuda VALUES (?)", (1,)),
        ("INSERT INTO dbo.Det_Compras (IdCompra) VALUES (?)", (1,)),
    ]
    results = connection.execute_write_transaction(statements)

    assert results == [42, 1]
    assert fake_conn.committed is True
    assert fake_conn.rolled_back is False


def test_execute_write_transaction_supports_callable_statements_using_prior_results(monkeypatch):
    """A callable item builds its (sql, params) from results already produced in this transaction."""
    monkeypatch.setattr(connection, "DATABASE", "WC")
    fake_conn = _FakeConnection()
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **kw: fake_conn)

    statements = [
        ("INSERT INTO dbo.Compras (Fecha) OUTPUT INSERTED.IdDeuda VALUES (?)", (1,)),
        lambda results: (
            "INSERT INTO dbo.Det_Compras (IdCompra) VALUES (?)",
            (results[0],),
        ),
    ]
    results = connection.execute_write_transaction(statements)

    assert results == [42, 1]
    assert fake_conn.cursor_obj.executed[1] == (
        "INSERT INTO dbo.Det_Compras (IdCompra) VALUES (?)",
        connection._coerce_params((42,)),
    )
    assert fake_conn.committed is True
