"""Cuenta 375 (Sergio), movimientos de 2017 con comprobante BNA (Sergio 22/10/2026).

1. BNA 18421 (30/03/2017, $21.000, comprobante "RETIRO MARZO / RETIRO DEUDA"): no es sueldo. Sergio: recuperación de pagos de
   Giamigli hechos desde su cuenta particular o de aportes de efectivo → contacto socio 5670 + AsignacionGasto en su cuenta de
   socio ("Devolución por aporte pagos varios"), 100% US$ (anterior a 2020).
2. Marzo-2017 con la opción A: BNA 18422 (10/04/2017, $16.000, comprobante "SUELDO MARZO 2017") ↔ caja 254 ("Devolución Sueldo
   Sergio Marzo 2017", $17.735, 01/04/2017): el débito queda sin contacto (traspaso BNA → caja vía Sergio) y la liquidación de
   marzo ($17.735) se cancela como no cobrada. Los $1.735 devueltos de más = aporte en efectivo de Sergio (Devolución en socio).
3. BNA 18425 (14/06/2017, $30.000): retiros genuinos de GANANCIAS de los socios (Sergio): $10.000 de Sergio en su cuenta y $20.000
   llevados a la caja para "Retiro Ceci" y "Retiro Lucy" ($10.000 c/u, caja 313/314). No es sueldo ni compensación: sale del 375
   al contacto socio 5670 y NO se registra en las cuentas de socio (no es deuda ni crédito). Idempotente.
"""
import json
import os
from datetime import date

from scripts.socios_valuacion_036 import cot, cotizaciones
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, fetch_one, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, cuenta 375 2017, 22/10/2026)'


def _reasignar(st, io, motivo):
    ult = fetch_one("SELECT TOP 1 IdContactoNuevo AS n FROM dbo.ReasignacionesContacto WHERE Origen='Banco Nacion' AND IdOrigen=? ORDER BY IdReasignacion DESC", (io,))
    if not ult or ult['n'] != 5670:
        st.append(("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                   "VALUES ('Banco Nacion',?,375,5670,?,?,SYSDATETIME())", (io, motivo, USUARIO)))


def _socio(st, tipo, imp, f, motivo, io):
    if not fetch_all('SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Tipo=? AND Importe=? AND CONVERT(date,Fecha)=? AND Anulada=0', (tipo, imp, f.isoformat())):
        _, dol = cotizaciones()
        st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) "
                   "VALUES (1,?,?,?,0,?,'Banco Nacion',?,?,?,?,0)", (tipo, imp, round(imp / cot(dol, f), 4), f.isoformat(), io, 'BNA', motivo, USUARIO)))


def main():
    _assert_target_is_wc()
    resp = backup_verificado('sergio-2017-retiros-036')
    st = []
    # 1
    _reasignar(st, 18421, 'Retiro marzo 2017 ("retiro deuda"): recuperación de pagos de Giamigli desde la cuenta de Sergio o aportes, no sueldo')
    _socio(st, 'AsignacionGasto', 21000.0, date(2017, 3, 30),
           'Giamigli – Devolución por aporte pagos varios (transferencia "Retiro marzo / retiro deuda" 30/03/2017)', 18421)
    # 2
    f = fetch_one('SELECT * FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA=18422 AND IdContacto=375')
    if f:
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f.items() if k != 'SSMA_TimeStamp'}
        st += [("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                "VALUES ('traspaso-bna-caja-via-sergio','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                (json.dumps({'tabla': 'Movimientos BNA', 'fila': fila, 'caja': 254}, ensure_ascii=False), USUARIO, USUARIO, os.path.basename(resp),
                 'BNA 18422 (sueldo marzo 2017) ↔ caja 254 (devolución $17.735): sueldo no cobrado, opción A')),
               ('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL, Contacto=NULL WHERE IdMovimientoBNA=18422 AND IdContacto=375', ()),
               ("UPDATE dbo.MovimientosCajaEfectivo SET Detalle=? WHERE IdMovimiento=254 AND Detalle IS NULL",
                ('Traspaso desde BNA (mov. 18422, $16.000) vía la cuenta de Sergio; sueldo marzo 2017 no cobrado; $1.735 aporte de Sergio',))]
    mot = 'Sueldo Marzo 2017 no cobrado: cobrado y devuelto a caja, opción A (IdSalario 1829632605)'
    if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=375 AND Motivo=?', (mot,)):
        st.append(("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (375,'2017-04-01','Credito',17735,?,?)", (mot, USUARIO)))
    _socio(st, 'Devolucion', 1735.0, date(2017, 4, 1), 'Sergio Giamberardini – Aporte efectivo (devolvió $17.735 a caja por un sueldo de marzo 2017 pagado de $16.000)', 18422)
    # 3
    _reasignar(st, 18425, 'Retiro de GANANCIAS de los socios 14/06/2017: $10.000 Sergio + $20.000 a caja para Ceci y Lucy (no es sueldo ni compensación)')
    for mov, txt in ((312, 'Retiro de ganancias de socios: efectivo traído de la CA de Sergio (BNA 18425 $30.000; $10.000 quedó para Sergio)'),
                     (313, 'Retiro de ganancias (Ceci)'), (314, 'Retiro de ganancias (Lucy)')):
        st.append(("UPDATE dbo.MovimientosCajaEfectivo SET Detalle=? WHERE IdMovimiento=? AND Detalle IS NULL", (txt, mov)))
    print('antes 375', cargar_cuenta(375, refrescar=True)['saldoPesos'])
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print('375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
