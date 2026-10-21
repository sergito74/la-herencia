"""J y M de la Serna (47): precio B x cantidad = Complemento, sin duplicar (Sergio 21/10/2026).

1. Ventas de J y M con Complemento: el renglón B lleva precio B = Complemento / cantidad (mar-2025 15132/15103, oct-2025 16182,
   mar-2026 16822); la 16178 (anulada por la NC 16181) y la NC quedan sin B ni complemento.
2. Vista vw_MovimientosCuenta_Base, rama Venta Hacienda: cuando Complemento = precio B x cantidad (hoy solo J y M) la parte B
   se cuenta una vez (no se suma el Complemento además de TotalB) y la comisión registrada va solo sobre A (la comisión sobre B
   se paga pero no se registra; el efectivo B cobrado = Complemento). Para las demás ventas la fórmula no cambia.
Uso: --simular muestra qué cuentas cambiarían de saldo; sin argumentos aplica (definición anterior en
scripts/vista_base_anterior_jym_b_20261021.sql). Idempotente.
"""
import sys
from pathlib import Path

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

C = 47
# IdVenta -> efectivo B cobrado (Complemento original); precio B = efectivo / cantidad a 4 decimales, Complemento = precio x cantidad
B_RENGLON = {135: 262599.06, 136: 719400.94, 143: 403000.00, 147: 1137200.00}
IGUAL = "ABS(ISNULL(v.Complemento, 0) - ISNULL(subtotal.TotalB, 0)) < 0.01 AND ISNULL(v.Complemento, 0) <> 0"
VIEJO = """            - ((ISNULL(subtotal.TotalA, 0) + ISNULL(subtotal.TotalB, 0)) * ISNULL(v.[Porc Comision], 0) / 100.0)"""
NUEVO = f"""            - ((ISNULL(subtotal.TotalA, 0) + CASE WHEN {IGUAL} THEN 0 ELSE ISNULL(subtotal.TotalB, 0) END) * ISNULL(v.[Porc Comision], 0) / 100.0)"""
VIEJO2 = """        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + ISNULL(v.Complemento, 0)
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen"""
NUEVO2 = f"""        - ISNULL(v.[Retencion IVA], 0) - ISNULL(v.[Ingresos Brutos], 0) + CASE WHEN {IGUAL} THEN 0 ELSE ISNULL(v.Complemento, 0) END
    AS money) AS Credito,
    CAST('Venta Hacienda' AS varchar(50)) AS Origen"""
SALDOS = "SELECT IdContacto, ROUND(SUM(Credito) - SUM(Deuda), 2) s FROM dbo.vw_MovimientosCuenta_Base GROUP BY IdContacto"


def main():
    _assert_target_is_wc()
    d = fetch_all("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base')) d")[0]['d']
    cambia_vista = VIEJO in d
    if cambia_vista:
        assert d.count(VIEJO) == 1 and d.count(VIEJO2) == 1
        nueva = d.replace(VIEJO, NUEVO).replace(VIEJO2, NUEVO2).replace('CREATE VIEW', 'ALTER VIEW', 1)
    antes = {r['IdContacto']: r['s'] for r in fetch_all(SALDOS)}
    if '--simular' not in sys.argv:
        print(backup_verificado('jym-precio-b-036'))
        if cambia_vista:
            Path(__file__).with_name('vista_base_anterior_jym_b_20261021.sql').write_text(d, encoding='utf-8')
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        for v, comp in B_RENGLON.items():
            cur.execute("SELECT TOP 1 d.IdDetalleVenta, d.Cantidad FROM dbo.[Det_Ventas Hacienda] d JOIN dbo.[Venta Hacienda] h ON h.IdVenta=d.IdVenta "
                        "WHERE d.IdVenta=? AND h.IdConsignatario=? ORDER BY CASE WHEN d.IdVenta=147 AND d.Cantidad=1065 THEN 0 ELSE 1 END, d.IdDetalleVenta", v, C)
            i, cant = cur.fetchone()
            precio = round(comp / cant, 4)  # la columna guarda 4 decimales
            cur.execute("UPDATE dbo.[Det_Ventas Hacienda] SET [Precio unitario (B)]=? WHERE IdDetalleVenta=?", precio, i)
            # Complemento = precio B x cantidad tal como lo multiplica la base (la columna es real de precisión simple)
            cur.execute("UPDATE dbo.[Venta Hacienda] SET Complemento=ROUND((SELECT SUM(d.Cantidad*ISNULL(d.[Precio unitario (B)],0)) "
                        "FROM dbo.[Det_Ventas Hacienda] d WHERE d.IdVenta=?),2) WHERE IdVenta=?", v, v)
            cur.execute("SELECT Complemento FROM dbo.[Venta Hacienda] WHERE IdVenta=?", v)
            print(v, 'precio B', precio, 'x', cant, '= complemento', cur.fetchone()[0], '(efectivo', comp, ')')
        if cambia_vista:
            cur.execute(nueva)
        cur.execute(SALDOS)
        despues = {r[0]: round(r[1], 2) for r in cur.fetchall()}
        cambios = {c: (antes.get(c), s) for c, s in despues.items() if abs((antes.get(c) or 0) - (s or 0)) >= 0.01}
        print('cuentas que cambian:', cambios)
        assert set(cambios) <= {C}, 'cambia otra cuenta: no se aplica'
        if '--simular' in sys.argv:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__': main()
