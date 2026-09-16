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

import pyodbc

from src.db.params import as_sql_datetime

DSN = os.environ.get("LA_HERENCIA_DSN", "SQL_LaHerencia")
DATABASE = os.environ.get("LA_HERENCIA_DATABASE", "WC")
CONNECTION_STRING = f"DSN={DSN};Trusted_Connection=Yes;DATABASE={DATABASE}"

_FORBIDDEN_DATABASE = "LaHerencia"

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
    """Hard stop: writes may only ever target `WC`, never `LaHerencia`.

    This is the code-level enforcement of the golden rule — even a
    misconfigured `LA_HERENCIA_DATABASE` env var cannot make a write hit
    the original database.
    """
    if DATABASE.strip().lower() == _FORBIDDEN_DATABASE.lower():
        raise RuntimeError(
            f"Refusing to write: LA_HERENCIA_DATABASE is set to "
            f"'{_FORBIDDEN_DATABASE}' (the protected original), not 'WC'."
        )


@contextmanager
def get_connection(*, readonly: bool = True) -> Generator[pyodbc.Connection, None, None]:
    """Yield a new, independent pyodbc connection.

    Each request opens and closes its own connection (no shared server-side
    session state), so concurrent reads from multiple users never block one
    another (FR-014).
    """
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=True, readonly=readonly)
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
