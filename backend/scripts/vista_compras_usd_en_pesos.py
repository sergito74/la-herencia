"""Vista de cuentas corrientes: las compras en US$ pasan a pesos al TC del comprobante (21/10/2026, pedido de Sergio).

`vw_MovimientosCuenta_Base` ponía el GranTotal de las compras en dólares (en US$) en las columnas Deuda/Credito, que son
de pesos: el saldo de la vista sumaba dólares con pesos (ASP, Don Mario, Nidera... "con saldo" estando en US$ 0). Todas las
compras en dólares tienen TC (> 1). La rama Compras pasa a GranTotal x [Tipo de Cambio] para Moneda = 'Dolares'.
La valuación bimonetaria (bimonetaria._vista_en_memoria) divide por el mismo TC para recuperar el importe original en US$,
así sus resultados (y los cierres 036) no cambian.

Uso: --simular (default) compara el saldo de todas las cuentas antes y después (vista y valuación) sin aplicar;
--aplicar guarda la definición anterior en scripts/vista_base_anterior_usd_20261021.sql y aplica (respaldo verificado).
"""
import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all

VIEJO_D = "    CASE WHEN tc.GranTotal > 0 THEN tc.GranTotal ELSE 0 END AS Deuda,\n    CASE WHEN tc.GranTotal < 0 THEN -tc.GranTotal ELSE 0 END AS Credito,\n    CAST('Compras' AS varchar(50)) AS Origen,"
FACTOR = "(CASE WHEN c.Moneda = 'Dolares' AND ISNULL(c.[Tipo de Cambio], 0) > 1 THEN c.[Tipo de Cambio] ELSE 1 END)"
NUEVO_D = (f"    CAST(CASE WHEN tc.GranTotal > 0 THEN tc.GranTotal * {FACTOR} ELSE 0 END AS money) AS Deuda,  -- US$ a pesos al TC del comprobante\n"
           f"    CAST(CASE WHEN tc.GranTotal < 0 THEN -tc.GranTotal * {FACTOR} ELSE 0 END AS money) AS Credito,\n"
           "    CAST('Compras' AS varchar(50)) AS Origen,")
SALDOS = "SELECT IdContacto i, MAX([Razon Social]) n, ROUND(SUM(Credito)-SUM(Deuda),2) s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto IS NOT NULL GROUP BY IdContacto"


def main():
    _assert_target_is_wc()
    d = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base')) d")[0]["d"]
    if VIEJO_D not in d:
        print("La vista ya está corregida (o cambió la rama Compras): nada que hacer.")
        return
    assert d.count(VIEJO_D) == 1
    nueva = d.replace(VIEJO_D, NUEVO_D).replace("CREATE VIEW", "ALTER VIEW", 1)
    aplicar = "--aplicar" in sys.argv
    antes = {r["i"]: (r["n"], r["s"]) for r in fetch_all(SALDOS)}
    if aplicar:
        from src.features.vinculos.backup import backup_verificado
        print(backup_verificado("vista-compras-usd-en-pesos"))
        Path(__file__).with_name("vista_base_anterior_usd_20261021.sql").write_text(d, encoding="utf-8")
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute(nueva)
        cur.execute(SALDOS)
        despues = {r[0]: float(r[2] or 0) for r in cur.fetchall()}
        cambian = [(i, antes[i][0], antes[i][1], despues.get(i)) for i in antes if abs((antes[i][1] or 0) - (despues.get(i) or 0)) >= 0.01]
        print(len(cambian), "cuentas cambian de saldo en la vista:")
        for i, n, a, b in sorted(cambian, key=lambda x: x[1] or ""):
            print(f"  {i:>5} {str(n)[:32]:<32} {a:>18,.2f} -> {b:>18,.2f}")
        conn.commit() if aplicar else conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__": main()
