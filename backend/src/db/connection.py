"""Read-only SQL Server access shared across feature modules.

Constitution principle II (Real Data Protection) and V (Contract-First,
Tested Integration): every connection opened here MUST be used only for
SELECT statements. No INSERT/UPDATE/DELETE/MERGE/TRUNCATE/ALTER/DROP may be
issued through this module.

Uses the pre-configured ODBC DSN ``SQL_LaHerencia`` (Trusted_Connection).
No credentials are hard-coded or logged.
"""

from __future__ import annotations

import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

import pyodbc

from src.db.params import as_sql_datetime

DSN = os.environ.get("LA_HERENCIA_DSN", "SQL_LaHerencia")
CONNECTION_STRING = f"DSN={DSN};Trusted_Connection=Yes;DATABASE=LaHerencia"

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


@contextmanager
def get_connection() -> Generator[pyodbc.Connection, None, None]:
    """Yield a new, independent, read-only pyodbc connection.

    Each request opens and closes its own connection (no shared server-side
    session state), so concurrent reads from multiple users never block one
    another (FR-014).
    """
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True, readonly=True)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Run a parameterized SELECT and return rows as a list of dicts."""
    _assert_read_only(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, _coerce_params(params))
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


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
        return dict(zip(columns, row, strict=True))
