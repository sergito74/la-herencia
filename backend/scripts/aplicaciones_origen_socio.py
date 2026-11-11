"""Pagos de socios imputados a comprobantes (11/11/2026): agrega 'socio' a CK_AplicacionesPago_Origen. Idempotente."""
import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_one

ORIGENES = ("comp-venta-hacienda", "comp-venta-granos", "comp-compra", "ret-ventas-hacienda", "ret-iva-granos", "retenciones",
            "tarjetas", "valores-propios", "valores-recibidos", "efectivo", "galicia", "bna", "socio")
# Boletas de impuestos y recibos de sueldo pagados por un socio (11/11/2026).
TIPOS = ("Alquiler", "VentaGranos", "VentaHacienda", "CompraDeuda", "Pastaje", "Impuesto", "Remuneracion")


def main():
    _assert_target_is_wc()
    d = fetch_one("SELECT definition d FROM sys.check_constraints WHERE name='CK_AplicacionesPago_Origen'")
    t = fetch_one("SELECT definition d FROM sys.check_constraints WHERE name='CK_AplicacionesPago_TipoDocumento'")
    if d and "'socio'" in d["d"] and t and "'Remuneracion'" in t["d"]:
        print("ya estaba"); return
    with pyodbc.connect(CONNECTION_STRING, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute("ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_Origen")
        cur.execute("ALTER TABLE dbo.AplicacionesPago WITH CHECK ADD CONSTRAINT CK_AplicacionesPago_Origen CHECK (OrigenMovimiento IN ("
                    + ",".join(f"'{o}'" for o in ORIGENES) + "))")
        cur.execute("ALTER TABLE dbo.AplicacionesPago DROP CONSTRAINT CK_AplicacionesPago_TipoDocumento")
        cur.execute("ALTER TABLE dbo.AplicacionesPago WITH CHECK ADD CONSTRAINT CK_AplicacionesPago_TipoDocumento CHECK (TipoDocumento IN ("
                    + ",".join(f"'{t}'" for t in TIPOS) + "))")
        conn.commit()
    print("ok")


if __name__ == "__main__":
    main()
