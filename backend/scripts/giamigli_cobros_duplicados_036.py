"""Giamigli de Bolívar (386): cobros en efectivo de ventas de hacienda (parte B) registrados dos veces (Sergio 21/10/2026).

Las ventas existen y su cobro en efectivo ya está en la cuenta de cada comprador (cuentas cerradas en $0):
  Senosiain (445) venta 85: 554 = 1256 ($138.400, 09/04/2021)
  Gregec (485) venta 99: 494 = 1257 ($105.130, 04/04/2022; en la planilla figura "Adrián Sosa")
  Transcom (502) venta 106 (terneros Tapalqué): 586 = 1326 ($438.100) + 1327 "pago proveedor" $48.684 (30/01/2023)
  Pavón Arriba (508) venta 101 (vacas descarte Tapalqué): 495 $111.370 = 1360 $100.250 + 1361 $11.120 (05/08/2023)
Las filas de 386 son duplicados: se eliminan dejando la fila en AuditoriaCorrecciones (regla eliminar-pago-duplicado).
Idempotente.
"""
import json

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 21/10/2026)'
DUPLICADOS = {1256: 554, 1257: 494, 1326: 586, 1327: 586, 1360: 495, 1361: 495}


def main():
    _assert_target_is_wc()
    filas = fetch_all('SELECT * FROM dbo.[Pagos efectivo] WHERE IdContacto=386 AND IdPagoEfectivo IN (' + ','.join(map(str, DUPLICADOS)) + ')')
    if not filas:
        print('nada que hacer'); return
    resp = backup_verificado('giamigli-cobros-duplicados-036')
    st = []
    for f in filas:
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f.items()}
        st.append(("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                   "VALUES ('eliminar-pago-duplicado','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                   (json.dumps({'tabla': 'Pagos efectivo', 'fila': fila}, ensure_ascii=False), USUARIO, USUARIO, resp.split('\\')[-1],
                    f"Duplicado del cobro {DUPLICADOS[f['IdPagoEfectivo']]} en la cuenta del comprador (venta de hacienda parte B); estaba en Giamigli de Bolívar")))
        st.append(('DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=? AND IdContacto=386', (f['IdPagoEfectivo'],)))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print(len(filas), 'eliminados; saldo 386', cargar_cuenta(386, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
