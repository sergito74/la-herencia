"""Municipalidad de Bolívar (72): cierre (Sergio 21/10/2026, "adelante").

1. Galicia 4 (31/05/2021, $35.864,32, TRANSFERENCIA A TERCEROS a ALBINA LUCILA IGLINA, CUIT 27048620944) no es un pago a la
   Municipalidad: es el reintegro a Lucy de la tasa vial 03/2021 que ella pagó el 04/05/2021 desde Supervielle (cuenta de
   socia: Devolucion 2455 vinculada a la Municipalidad + AsignacionGasto 2459 del reintegro). Pasa al contacto de Lucy (390),
   donde están las demás transferencias a ella.
2. Residuo histórico 2011-2022 (diferencias chicas entre boletas y pagos): ajuste "diferencia histórica".
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C, LUCY = 72, 390
USUARIO = 'Sergio (036, revisión 21/10/2026)'
MOTIVO = 'Municipalidad: diferencia histórica 2011-2022 entre boletas y pagos'


def main():
    _assert_target_is_wc()
    print(backup_verificado('municipalidad-cierre-036'))
    with reconciliation_transaction():
        if fetch_all('SELECT 1 x FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=4 AND IdContacto=?', (C,)):
            execute_write_transaction([
                ('UPDATE dbo.[Movimientos Galicia] SET IdContacto=? WHERE IdMovimiento=4 AND IdContacto=? AND [Débitos]=35864.32', (LUCY, C)),
                ("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                 "VALUES ('Galicia',4,?,?,?,?,SYSDATETIME())",
                 (C, LUCY, 'Reintegro a Lucy de la tasa vial 03/2021 que pagó ella (Supervielle 04/05/2021); no es pago a la Municipalidad', USUARIO))])
    invalidar()
    saldo = round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2)
    print('saldo tras reasignar', saldo)
    if abs(saldo) >= 0.01 and not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo=?', (C, MOTIVO)):
        with reconciliation_transaction():
            execute_write_transaction([('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) '
                                        'VALUES (?,?,?,?,?,?,SYSDATETIME())', (C, '2022-12-31', 'Deuda' if saldo > 0 else 'Credito', abs(saldo), MOTIVO, USUARIO))])
        invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
