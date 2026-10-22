"""Contactos cruzados en Galicia Giamigli del 04/11/2024 (Sergio 22/10/2026, punto 3 aprobado).

Mov. Galicia 2198 ($250.000, "REEMBOLSO GASTOS") estaba en Sergio (375) y fue a Lucy: extracto Galicia de Lucy 04/11/24
"REEMBOLSO GASTOS 250.000 GIAMIGLI DE BOLIVAR"; Cuenta Lucy 04/11/2024 $250.000. Mov. 2199 ($90.000) estaba en Lucy (390) y
fue a Sergio: su extracto acredita $90.000 ese día; Cuenta Sergio 04/11/2024 $90.000. Se cruzan los contactos con log en
ReasignacionesContacto. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, cuenta 375 22/10/2026)'
CAMBIOS = [(2198, 250000, 375, 390, 'Albina Iglina'), (2199, 90000, 390, 375, 'Sergio Giamberardini')]


def main():
    _assert_target_is_wc()
    st = []
    for mov, imp, ant, nuevo, nombre in CAMBIOS:
        if fetch_all('SELECT 1 x FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=? AND IdContacto=? AND [Débitos]=?', (mov, ant, imp)):
            st += [('UPDATE dbo.[Movimientos Galicia] SET IdContacto=?, Contacto=? WHERE IdMovimiento=? AND IdContacto=?', (nuevo, nombre, mov, ant)),
                   ('INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) '
                    "VALUES ('Galicia',?,?,?,?,?,SYSDATETIME())",
                    (mov, ant, nuevo, 'Contactos cruzados 04/11/2024: según extractos de Sergio ($90.000) y Lucy ($250.000)', USUARIO))]
    if not st:
        print('ya aplicado'); return
    print(backup_verificado('sergio-lucy-galicia-20241104-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    for c in (375, 390):
        print(c, cargar_cuenta(c, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
