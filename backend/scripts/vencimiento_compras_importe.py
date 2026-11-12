"""Importe por fecha de vencimiento de compras (12/11/2026): agrega [Vencimiento Compras].Importe (NULL = sin monto,
como las cargas anteriores). Idempotente; solo contra WC."""
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_one


def main():
    _assert_target_is_wc()
    if fetch_one("SELECT 1 AS x FROM sys.columns WHERE object_id = OBJECT_ID('dbo.[Vencimiento Compras]') AND name = 'Importe'"):
        print("ya estaba"); return
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        conn.cursor().execute("ALTER TABLE dbo.[Vencimiento Compras] ADD Importe decimal(18, 2) NULL")
    print("ok")


if __name__ == "__main__":
    main()
