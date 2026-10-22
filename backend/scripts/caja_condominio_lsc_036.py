r"""Caja de efectivo del Condominio LSC (Sergio 22/10/2026: "estamos construyendo la caja condominio también").

Fuente: Documents\Alquileres urbanos\Condominio LSC\Movimientos LSC desde Abr 2016.xlsm, hoja "Caja Efectivo" (1.235
movimientos 28/03/2016 → 11/09/2026, saldo corrido sin saltos, cierra en $0,23). Se refleja 1:1 en MovimientosCajaEfectivo
con Caja='CondominioLSC' y FilaPlanilla = fila de la hoja. No entra en las cuentas corrientes. Idempotente.
Antes de 2016 la caja del Condominio está en Movimientos LSC.xlsx (Movs, TIPO CAJA 'EF') — pendiente.
"""
import warnings

import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

FUENTE = r'C:\Users\Sergio\Documents\Alquileres urbanos\Condominio LSC\Movimientos LSC desde Abr 2016.xlsm'
USUARIO = 'Sergio (036, caja condominio 22/10/2026)'


def ampliar_check():
    import pyodbc
    from src.db.connection import CONNECTION_STRING
    c = pyodbc.connect(CONNECTION_STRING, autocommit=True)
    d = c.cursor().execute("SELECT definition FROM sys.check_constraints WHERE name='CK_MovimientosCajaEfectivo_Caja'").fetchone()
    if d and 'CondominioLSC' not in d[0]:
        c.cursor().execute("ALTER TABLE dbo.MovimientosCajaEfectivo DROP CONSTRAINT CK_MovimientosCajaEfectivo_Caja")
        c.cursor().execute("ALTER TABLE dbo.MovimientosCajaEfectivo ADD CONSTRAINT CK_MovimientosCajaEfectivo_Caja CHECK (Caja IN ('GiamigliSA','CampoChica','CondominioLSC'))")
    c.close()


def main():
    _assert_target_is_wc()
    warnings.filterwarnings('ignore')
    ya = {r['fp'] for r in fetch_all("SELECT FilaPlanilla fp FROM dbo.MovimientosCajaEfectivo WHERE Caja='CondominioLSC'")}
    wb = openpyxl.load_workbook(FUENTE, data_only=True, read_only=True)
    st = []
    for i, r in enumerate(wb['Caja Efectivo'].iter_rows(values_only=True), 1):
        if i == 1 or i in ya or not (r and hasattr(r[0], 'year')) or not isinstance(r[2], (int, float)) or r[2] == 0:
            continue
        st.append(("INSERT INTO dbo.MovimientosCajaEfectivo (Caja,Fecha,Concepto,Importe,Cuenta,Usuario,FilaPlanilla) VALUES ('CondominioLSC',?,?,?,'B',?,?)",
                   (r[0].date().isoformat(), str(r[1] or '')[:200], round(float(r[2]), 2), USUARIO, i)))
    if st:
        ampliar_check()
        print(backup_verificado('caja-condominio-lsc-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    print(len(st), 'nuevos |', fetch_all("SELECT COUNT(*) n, ROUND(SUM(Importe),2) s, MIN(CONVERT(date,Fecha)) a, MAX(CONVERT(date,Fecha)) b FROM dbo.MovimientosCajaEfectivo WHERE Caja='CondominioLSC'"))


if __name__ == '__main__': main()
