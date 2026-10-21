"""UATRE (315): revisión 21/10/2026 (cuentas sin ficha). Saldo previo +$751.410,18 a favor; los aportes mensuales
cierran uno a uno contra el débito del mes (DEBIN a Mercado Pago, CUIT 30703088534 -> "Pago de servicios UATRE").
Correcciones:
1. Galicia 2375 (31/01/2025, DEBIN $604.224,36 a CUIT 30707743987, Nuevo Banco de Santa Fe = recaudador municipal) es
   el pago de la boleta municipal 007/000000049787/8 del mismo día y monto -> Municipalidad (72).
2. Galicia 2754 (28/08/2025, DEBIN $130.000 a Mercado Pago) es una carga de saldo usada ese día en "Pago con QR RIPSA"
   ($125.553,71), no un pago a UATRE -> sin contacto y traspaso interno galicia 2754 <-> mercado-libre 48.
3. Pagos efectivo 395 (04/09/2024, forma 29, $17.083,32) duplica el pago real por Mercado Pago (ML 23, $17.185,82)
   de la boleta 08/2024 -> se borra.
4. Residuo (Mercado Pago pagó $102,50 más que la boleta 08/2024) < $300 -> AjustesCuentaCorriente.
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 315
USUARIO = 'Sergio (036, revisión 21/10/2026)'


def main():
    _assert_target_is_wc()
    st = []
    if fetch_all('SELECT 1 x FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=2375 AND IdContacto=?', (C,)):
        st += [("UPDATE dbo.[Movimientos Galicia] SET IdContacto=72 WHERE IdMovimiento=2375 AND IdContacto=? AND [Débitos]=604224.36", (C,)),
               ("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                "VALUES ('Galicia',2375,?,72,?,?,SYSDATETIME())",
                (C, 'DEBIN a Nuevo Banco de Santa Fe (recaudador municipal): boleta municipal 007/000000049787/8 del 31/01/2025', USUARIO))]
    if fetch_all('SELECT 1 x FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=2754 AND IdContacto=?', (C,)):
        st.append(("UPDATE dbo.[Movimientos Galicia] SET IdContacto=NULL WHERE IdMovimiento=2754 AND IdContacto=? AND [Débitos]=130000", (C,)))
    if not fetch_all("SELECT 1 x FROM dbo.TraspasosInternosTesoreria WHERE MedioA='galicia' AND IdMovimientoA=2754"):
        st.append(("INSERT INTO dbo.TraspasosInternosTesoreria (MedioA,IdMovimientoA,MedioB,IdMovimientoB,Accion,Usuario) "
                   "VALUES ('galicia',2754,'mercado-libre',48,'Vincular',?)", (USUARIO,)))
    st.append(('DELETE FROM dbo.[Pagos efectivo] WHERE IdPagoEfectivo=395 AND IdContacto=? AND [Importe imputado]=17083.32', (C,)))
    print(backup_verificado('uatre-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    saldo = round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2)
    print('saldo tras correcciones', saldo)
    if abs(saldo) >= 0.005 and abs(saldo) < 300 and not fetch_all("SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=? AND Motivo LIKE 'UATRE:%'", (C,)):
        with reconciliation_transaction():
            execute_write_transaction([("INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario,FechaAlta) VALUES (?,?,?,?,?,?,SYSDATETIME())",
                                        (C, '2024-09-04', 'Credito' if saldo < 0 else 'Deuda', abs(saldo),
                                         'UATRE: Mercado Pago cobró $102,50 más que la boleta 08/2024 (redondeo < $300)', USUARIO))])
        invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'], '| Municipalidad', round(cargar_cuenta(72, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
