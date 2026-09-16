"""Regression test for the pyodbc date-binding quirk (see src/db/params.py).

Binding a plain `datetime.date` against this schema's `datetime` columns
raised `pyodbc.Error: HYC00 - SQLBindParameter` in this environment
(discovered 2026-09-15 while validating 003-tesoreria against real data;
it also silently affected 002-compras' `fechaDesde`/`fechaHasta` filters,
which had never been exercised against the real DB before).
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.params import as_sql_datetime


def test_date_is_converted_to_midnight_datetime():
    assert as_sql_datetime(date(2026, 7, 30)) == datetime(2026, 7, 30, 0, 0, 0)


def test_datetime_passes_through_unchanged():
    dt = datetime(2026, 7, 30, 10, 15, 0)
    assert as_sql_datetime(dt) is dt


def test_none_passes_through():
    assert as_sql_datetime(None) is None
