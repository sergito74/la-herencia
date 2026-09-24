"""SQL Server access shared across feature modules.

**Regla de oro (2026-09-17, decisión explícita del usuario)**: la
aplicación trabaja exclusivamente contra `WC` ("Working Copy"), una
réplica completa de `LaHerencia` restaurada vía BACKUP/RESTORE el
2026-09-17. `LaHerencia` (la base original) NUNCA se escribe desde este
código — `fetch_all`/`fetch_one` siguen siendo de solo lectura (para
`WC` también, salvo que se use `execute_write` explícitamente), y
`execute_write` se niega en tiempo de ejecución a operar contra
cualquier base que no sea `WC` (ver `_assert_target_is_wc`). Esto
convierte la regla de negocio en una barrera de código, no solo en una
convención.

Uses the pre-configured ODBC DSN ``SQL_LaHerencia`` (Trusted_Connection).
No credentials are hard-coded or logged.
"""

from __future__ import annotations

import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pyodbc

from src.db.params import as_sql_datetime

DSN = os.environ.get("LA_HERENCIA_DSN", "SQL_LaHerencia")
DATABASE = os.environ.get("LA_HERENCIA_DATABASE", "WC")
CONNECTION_STRING = f"DSN={DSN};Trusted_Connection=Yes;DATABASE={DATABASE}"

_DEVELOPMENT_DATABASE = "WC"

_FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "TRUNCATE",
    "ALTER",
    "DROP",
    "EXEC",
    "EXECUTE",
)

# `SELECT ... INTO new_table` creates a table — a write disguised as a
# SELECT. `\bINTO\b` alone would also match legitimate `INSERT INTO`, but
# that's already rejected by the INSERT keyword check above, so any
# remaining bare INTO is the SELECT INTO form.
_SELECT_INTO_RE = re.compile(r"\bINTO\b")


def _assert_read_only(sql: str) -> None:
    """Defensive guard: refuse to run anything that isn't a SELECT.

    This is a last line of defense, not a substitute for writing only
    SELECT statements in repository code. The real enforcement is the
    read-only role of the SQL Server login behind this DSN.
    """
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        raise ValueError("Only SELECT statements are allowed through this connection")
    for keyword in _FORBIDDEN_KEYWORDS:
        if keyword in normalized:
            raise ValueError(f"Forbidden keyword '{keyword}' detected in query")
    if _SELECT_INTO_RE.search(normalized):
        raise ValueError("SELECT INTO is not allowed through this connection")
    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed through this connection")


def _coerce_params(params: tuple) -> tuple:
    """Convert plain `date` params to `datetime` before binding.

    pyodbc raises 'HYC00 SQLBindParameter' when binding a `datetime.date`
    against this schema's `datetime` columns (every date/time column here
    is `datetime`, confirmed against INFORMATION_SCHEMA) — see
    src/db/params.py for the original discovery. Centralized here so no
    caller can forget the conversion.
    """
    return tuple(as_sql_datetime(p) if isinstance(p, date) else p for p in params)


def _assert_target_is_wc() -> None:
    """Hard stop: application connections must target development database `WC`.

    Checking only that the configured database is not `LaHerencia` leaves
    typos and unexpected database names writable. Restricting the target to
    the explicitly designated working copy protects the official database
    and prevents writes to any other database by mistake.
    """
    if DATABASE.strip().lower() != _DEVELOPMENT_DATABASE.lower():
        raise RuntimeError(
            "Refusing database access: LA_HERENCIA_DATABASE is set to "
            f"'{DATABASE}', but development must use '{_DEVELOPMENT_DATABASE}'."
        )


@contextmanager
def get_connection(*, readonly: bool = True) -> Generator[pyodbc.Connection, None, None]:
    """Yield a new, independent pyodbc connection.

    Each request opens and closes its own connection (no shared server-side
    session state), so concurrent reads from multiple users never block one
    another (FR-014).
    """
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True, readonly=readonly)
    try:
        yield conn
    finally:
        conn.close()


def _coerce_row(row_dict: dict) -> dict:
    """`money`/`decimal` llegan de pyodbc como `Decimal`. Los endpoints que
    devuelven estas filas directamente (sin pasar por un schema Pydantic)
    no los convierten solos: FastAPI los serializa como *string* en el JSON
    ("5000934.0000"), y el frontend, que espera number, termina concatenando
    texto en vez de sumar (bug real de UI, 2026-09-24). Un solo punto de
    conversión acá cubre todos los endpoints, no solo los que usan
    response_model."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row_dict.items()}


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Run a parameterized SELECT and return rows as a list of dicts."""
    _assert_read_only(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, _coerce_params(params))
        columns = [column[0] for column in cursor.description]
        return [_coerce_row(dict(zip(columns, row, strict=True))) for row in cursor.fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a parameterized SELECT and return the first row as a dict, or None."""
    _assert_read_only(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, _coerce_params(params))
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if row is None:
            return None
        return _coerce_row(dict(zip(columns, row, strict=True)))


def execute_write(sql: str, params: tuple = ()) -> int:
    """Run a single parameterized INSERT/UPDATE/DELETE against `WC` only.

    Refuses outright (`_assert_target_is_wc`) if this process is somehow
    configured to point at `LaHerencia` — the golden rule (2026-09-17):
    only `WC` may ever be written to. Returns the affected row count.
    """
    _assert_target_is_wc()
    normalized = sql.strip().upper()
    if not any(normalized.startswith(verb) for verb in ("INSERT", "UPDATE", "DELETE")):
        raise ValueError("execute_write only accepts INSERT/UPDATE/DELETE statements")
    if any(kw in normalized for kw in ("DROP", "TRUNCATE", "ALTER", "EXEC", "EXECUTE")):
        raise ValueError("Forbidden keyword detected in write statement")
    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed through this connection")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, _coerce_params(params))
        return cursor.rowcount


def execute_insert_returning_id(sql: str, params: tuple = ()) -> int:
    """Run an INSERT with an `OUTPUT INSERTED.<col>` clause against `WC`.

    Same guards as `execute_write`, but returns the single scalar value
    produced by the OUTPUT clause (e.g. the new identity id) instead of
    the affected row count.
    """
    _assert_target_is_wc()
    normalized = sql.strip().upper()
    if not normalized.startswith("INSERT"):
        raise ValueError("execute_insert_returning_id only accepts INSERT statements")
    if "OUTPUT" not in normalized:
        raise ValueError("execute_insert_returning_id requires an OUTPUT clause")
    if any(kw in normalized for kw in ("DROP", "TRUNCATE", "ALTER", "EXEC", "EXECUTE")):
        raise ValueError("Forbidden keyword detected in write statement")
    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed through this connection")

    with get_connection(readonly=False) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, _coerce_params(params))
        row = cursor.fetchone()
        return row[0]


def _validate_write_statement(sql: str) -> str:
    """Shared guard for a single statement inside a transaction (see `execute_write`)."""
    normalized = sql.strip().upper()
    if not any(normalized.startswith(verb) for verb in ("INSERT", "UPDATE", "DELETE")):
        raise ValueError("execute_write_transaction only accepts INSERT/UPDATE/DELETE statements")
    if any(kw in normalized for kw in ("DROP", "TRUNCATE", "ALTER", "EXEC", "EXECUTE")):
        raise ValueError("Forbidden keyword detected in write statement")
    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Multiple statements are not allowed through this connection")
    return normalized


def execute_write_transaction(statements: list) -> list:
    """Run several parameterized INSERT/UPDATE/DELETE statements as one transaction against `WC`.

    All-or-nothing: opens a single connection with `autocommit=False`,
    executes every statement in order, commits only if all succeed, and
    rolls back the whole batch on any failure — needed because a Compra's
    cabecera/líneas/vencimientos have no real foreign keys in SQL Server
    (confirmed via `sys.foreign_keys`), so a partial write would leave an
    orphaned, inconsistent Compra (see research.md §1).

    Each item in `statements` is either a static `(sql, params)` tuple, or
    a callable `(results_so_far: list) -> (sql, params)` for statements
    that need a value produced by an earlier statement in the same
    transaction (e.g. the `IdCompra` from an `OUTPUT INSERTED.IdDeuda`
    insert, needed by the line/vencimiento inserts that follow it) —
    building that dependent SQL ahead of time, before the id exists, is
    not possible with a plain list of tuples.

    Each resolved statement is validated exactly like `execute_write`
    (only INSERT/UPDATE/DELETE, no DDL, no multi-statement strings). A
    statement with an `OUTPUT` clause returns its scalar value (like
    `execute_insert_returning_id`); otherwise the statement's rowcount is
    returned. Returns a list with one entry per input statement, in order.
    """
    _assert_target_is_wc()
    if not statements:
        raise ValueError("execute_write_transaction requires at least one statement")

    # Validate every statement we can check without executing anything yet
    # (static tuples) before opening a connection, same as `execute_write`.
    for item in statements:
        if not callable(item):
            _validate_write_statement(item[0])

    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False, readonly=False)
    try:
        cursor = conn.cursor()
        results: list = []
        for item in statements:
            sql, params = item(results) if callable(item) else item
            normalized = _validate_write_statement(sql)
            cursor.execute(sql, _coerce_params(params))
            if "OUTPUT" in normalized:
                results.append(cursor.fetchone()[0])
            else:
                results.append(cursor.rowcount)
        conn.commit()
        return results
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
