"""Giamigli de Bolívar (386): últimos movimientos que no son de cuenta corriente (Sergio 21/10/2026, "hay que buscar la historia").

1. "Retención Ganancias" (Pagos efectivo tipo 3, forma 16; en Access eran del contacto 269 "Directo"): son retenciones de
   Ganancias que nos hicieron compradores de hacienda, ya registradas en "Retenciones Ventas Hacienda" en la cuenta de cada
   comprador (cuentas cerradas): 1466 $8.587,60 (Río Bermejo, ret 5), 1679 $4.153,60 (13 de Abril, ret 3), 1899 $22.430,23
   (Agropecuaria Bienvenidos, ret 2), 1255 $1.700 (contacto 431, ret 6). 1719 $4.153,60 (18/06/2019) repite la de 13 de
   Abril, cuya cuenta cierra en $0 con una sola retención. Duplicados: se eliminan (AuditoriaCorrecciones).
2. BNA "COBRADO POR CAJA" 18505 ($1.000, 30/03/2012), 18506 ($22.000, 07/11/2017), 18507 ($215.000, 09/10/2019): retiros de la
   cuenta del BNA a la caja de efectivo (planilla: "Ingreso Efectivo por Retiro en CC BNA"; MovimientosCajaEfectivo 403 y
   697). Movimiento interno: sin contacto.
Idempotente.
"""
import json

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 21/10/2026)'
RETENCIONES = {1466: 5, 1679: 3, 1899: 2, 1255: 6, 1719: 3}
RETIROS = (18505, 18506, 18507)


def main():
    _assert_target_is_wc()
    resp = backup_verificado('giamigli-retenciones-retiros-036')
    st = []
    for f in fetch_all('SELECT * FROM dbo.[Pagos efectivo] WHERE IdContacto=386 AND IdPagoEfectivo IN (' + ','.join(map(str, RETENCIONES)) + ')'):
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f.items()}
        st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                   "VALUES ('eliminar-pago-duplicado','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                   (json.dumps({'tabla': 'Pagos efectivo', 'fila': fila}, ensure_ascii=False), USUARIO, USUARIO, resp.split('\\')[-1],
                    f"Retención de Ganancias de venta de hacienda ya registrada (Retenciones Ventas Hacienda {RETENCIONES[f['IdPagoEfectivo']]}); estaba en Giamigli de Bolívar")))
        st.append(('DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND IdContacto=386', (f['IdPagoEfectivo'],)))
    st += [('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL WHERE IdMovimientoBNA=? AND IdContacto=386', (i,)) for i in RETIROS]
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    c = cargar_cuenta(386, refrescar=True)
    print('saldo 386', c['saldoPesos'])
    for f in c['filas']:
        print(' ', f['fecha'], f['origenTipo'], f['idOrigen'], f['deudaPesos'], f['creditoPesos'])


if __name__ == '__main__': main()
