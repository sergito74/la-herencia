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
from collections.abc import Generator
from contextlib import contextmanager

import pyodbc

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


def _assert_read_only(sql: str) -> None:
    """Defensive guard: refuse to run anything that isn't a SELECT.

    This is a last line of defense, not a substitute for writing only
    SELECT statements in repository code.
    """
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        raise ValueError("Only SELECT statements are allowed through this connection")
    for keyword in _FORBIDDEN_KEYWORDS:
        if keyword in normalized:
            raise ValueError(f"Forbidden keyword '{keyword}' detected in query")


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
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a parameterized SELECT and return the first row as a dict, or None."""
    _assert_read_only(sql)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(zip(columns, row, strict=True))
