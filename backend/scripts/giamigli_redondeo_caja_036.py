"""Giamigli de Bolívar (386): Pagos efectivo 1362 (07/03/2023, caja La Herencia, cuenta B, egreso "Redondeo", −$57,29) se
elimina de la caja (Sergio 21/10/2026). Ajuste de caja heredado de Access sin documento ni respaldo en la planilla de cajas.
Se guarda la fila en AuditoriaCorrecciones. Idempotente.
"""
import json

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 21/10/2026)'


def main():
    _assert_target_is_wc()
    f = fetch_all('SELECT * FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=1362 AND IdContacto=386')
    if f:
        resp = backup_verificado('giamigli-redondeo-caja-036')
        fila = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in f[0].items()}
        with reconciliation_transaction():
            execute_write_transaction([
                ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
                 "VALUES ('eliminar-pago-duplicado','aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
                 (json.dumps({'tabla': 'Pagos efectivo', 'fila': fila}, ensure_ascii=False), USUARIO, USUARIO, resp.split('\')[-1],
                  'Redondeo de caja heredado de Access sin respaldo (07/03/2023, −$57,29); eliminado de la caja a pedido de Sergio')),
                ('DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=1362 AND IdContacto=386', ())])
        invalidar()
    c = cargar_cuenta(386, refrescar=True)
    print('386', c['saldoPesos'], len(c['filas']), 'movimientos')


if __name__ == '__main__': main()
