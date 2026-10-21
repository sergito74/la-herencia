"""J y M de la Serna (47): cierre de la cuenta (Sergio 21/10/2026). Redondeo final de $0,10 (precio B a 4 decimales y
centavo del flete Gutiérrez) y ficha cerrada con los criterios de la aplicación. Idempotente.
Historia: complemento = cuenta B (jym_cuenta_b_036, jym_precio_b_036), residuo 2015-2020 por venta (jym_residuo_b_036),
Breccia fuera (breccia_fuera_jym_036, piccirilli_mantenimiento_036), Galicia Broker a Galicia Seguros
(galicia_seguros_reconocimiento_036), vacuna aftosa AJ 293 (jym_vacuna_aftosa_036).
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from datetime import date

from src.features.revision_cuentas import evidencia, fichas
from src.features.vinculos.backup import backup_verificado

C = 47
USUARIO = 'Sergio (036, revisión 21/10/2026)'
NOTA = ('Cerrada 21/10/2026 en $0: ventas = PDF de liquidaciones; parte B = Complemento = efectivo de la planilla; comisión sobre B '
        'fuera de sistema (ajuste por venta 2015-2020); AJ 293 vacuna aftosa oct-2025; resumen J y M 25/11/2025 conciliado.')


def main():
    _assert_target_is_wc()
    print(backup_verificado('jym-cierre-036'))
    saldo = round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2)
    if abs(saldo) >= 0.005 and abs(saldo) < 1 and not fetch_all("SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo LIKE 'J y M: redondeo%'", (C,)):
        with reconciliation_transaction():
            execute_write_transaction([('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) VALUES (?,?,?,?,?,?,SYSDATETIME())',
                                        (C, '2026-09-30', 'Deuda' if saldo > 0 else 'Credito', abs(saldo),
                                         'J y M: redondeo final (precio B a 4 decimales y centavo del flete Gutiérrez)', USUARIO))])
        invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'])
    fichas._asegurar_fila(C, USUARIO)
    if not fetch_all('SELECT 1 x FROM dbo.RevisionSaldosExternos WHERE IdContacto=? AND Anulado=0', (C,)):
        evidencia.crear_saldo_externo(C, date(2025, 11, 25), 5640000.00, 'Pesos', 'mail',
                                      'Resumen de Cuenta J y M 01/01/2025-30/06/2026 (mail 25/11/2025)',
                                      'Saldo a cobrar = 2da cuota FC 0003-16137 (vto 21/12/2025), cobrada 18/12/2025', USUARIO)
    fichas.confirmar_inventario(C, [
        {'tipo': 'estado-proveedor', 'disponible': True, 'detalle': 'Resúmenes de cuenta J y M: 2016-2017 (mail 17/05/2017) y 2025-2026 (mail 25/11/2025)'},
        {'tipo': 'dropbox', 'disponible': True, 'detalle': 'Liquidaciones PDF en Dropbox/Ventas (desde 2017) y mails (2015-2016)'},
        {'tipo': 'extracto', 'disponible': True, 'detalle': 'Cobros en BNA/Galicia; órdenes de pago J y M por mail; efectivo B en Cajas Giamigli.xlsx'},
    ], USUARIO)
    print(fichas.cambiar_estado(C, {'estado': 'cerrada', 'nota': NOTA}, USUARIO).get('estado'))


if __name__ == '__main__': main()
