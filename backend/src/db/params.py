"""Shared SQL parameter coercions for pyodbc quirks.

Binding a plain `datetime.date` against a SQL Server `datetime` column
(as opposed to a `date` column) raises pyodbc.Error 'HYC00 - Caracteristica
opcional no implementada (SQLBindParameter)' with this environment's ODBC
driver. Binding a `datetime.datetime` instead works. Every date/datetime
column in this schema turned out to be `datetime` (confirmed against
INFORMATION_SCHEMA), so any `date` query parameter MUST go through this
helper before being passed to fetch_all/fetch_one.
"""

from __future__ import annotations

from datetime import date, datetime


def as_sql_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day)
