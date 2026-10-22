"""P18: Galicia 1390 (05/09/2023, $30.000) — retiro adicional de Sergio por compensación de pagos de Giamigli (Sergio 22/10/2026).

No es sueldo (agosto 2023: recibo $300.000, pagado 31/08). Se reasigna del 375 al contacto socio 5670 y se registra en su
cuenta de socio como AsignacionGasto (Devolución por aporte pagos varios). Idempotente.
"""
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

F = date(2023, 9, 5)
USUARIO = 'Sergio (036, cuenta 375 22/10/2026)'


def main():
    _assert_target_is_wc()
    st = []
    ult = fetch_one("SELECT TOP 1 IdContactoNuevo AS n FROM dbo.ReasignacionesContacto WHERE Origen='Galicia' AND IdOrigen=1390 ORDER BY IdReasignacion DESC")
    if not ult or ult['n'] != 5670:
        st.append(("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                   "VALUES ('Galicia',1390,375,5670,?,?,SYSDATETIME())", ('P18: retiro adicional por compensación de pagos de Giamigli, no sueldo', USUARIO)))
    if not fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Importe=30000 AND CONVERT(date,Fecha)=? AND Anulada=0", (F.isoformat(),)):
        nov, dol = cotizaciones()
        st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) "
                   "VALUES (1,'AsignacionGasto',30000,?,?,?,'Galicia',1390,'Galicia',?,?,0)",
                   (round(30000 * 0.5 / cot(dol, F), 4), round(30000 * 0.5 / cot(nov, F), 4), F.isoformat(),
                    'Giamigli – Devolución por aporte pagos varios (retiro adicional por compensación de pagos de Giamigli)', USUARIO)))
    if not st:
        print('ya aplicado'); return
    print(backup_verificado('sergio-p18-retiro-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print('375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
