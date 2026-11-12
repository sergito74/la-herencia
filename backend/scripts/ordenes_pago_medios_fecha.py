"""Fecha de cada medio de pago de una orden (12/11/2026): la orden sale por el total de la factura con un medio por
cuota (transferencia del adelanto, eCheqs a 30/60...). Agrega OrdenesPago_Medios.Fecha (NULL = la fecha de pago). Solo WC."""
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_one


def main():
    _assert_target_is_wc()
    if fetch_one("SELECT 1 AS x FROM sys.columns WHERE object_id = OBJECT_ID('dbo.OrdenesPago_Medios') AND name = 'Fecha'"):
        print("ya estaba"); return
    with pyodbc.connect(CONNECTION_STRING, autocommit=True) as conn:
        conn.cursor().execute("ALTER TABLE dbo.OrdenesPago_Medios ADD Fecha date NULL")
    print("ok")


if __name__ == "__main__":
    main()
