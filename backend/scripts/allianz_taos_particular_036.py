"""Allianz (515): seguro de la VW Taos con la regla de compras particulares (Sergio 22/10/2026: "SIEMPRE debe ser así").

El 01/10/2026 se reasignaron al contacto de Sergio (375) los 20 débitos de Allianz de la Taos (Galicia 02/2025–09/2026,
$2.487.318,43). Regla de compras particulares: el pago queda en la cuenta del proveedor; se compensa con un asiento
"Particular S" (Pagos efectivo, negativo) y la deuda va a la cuenta de socio de Sergio (ya cargada desde la planilla,
1 por débito; mayo 2026 = factura $134.724,39 − NC $105). Las facturas de Allianz ya tienen la línea negativa "Gasto/Seguro
particular". Se reasignan los 20 débitos de vuelta a Allianz y se agrega el asiento Particular S de cada uno. Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, regla compras particulares 22/10/2026)'


def main():
    _assert_target_is_wc()
    movs = fetch_all("SELECT g.IdMovimiento i, CONVERT(date,g.Fecha) f, g.[Débitos] m FROM dbo.[Movimientos Galicia] g "
                     "CROSS APPLY (SELECT TOP 1 r.IdContactoNuevo n FROM dbo.ReasignacionesContacto r WHERE r.Origen='Galicia' "
                     "AND r.IdOrigen=g.IdMovimiento ORDER BY r.IdReasignacion DESC) ult "
                     "WHERE ult.n=375 AND EXISTS (SELECT 1 FROM dbo.ReasignacionesContacto r WHERE r.Origen='Galicia' "
                     "AND r.IdOrigen=g.IdMovimiento AND r.IdContactoAnterior=515 AND r.IdContactoNuevo=375)")
    if not movs:
        print('ya aplicado'); return
    print('antes 515', cargar_cuenta(515, refrescar=True)['saldoPesos'], '| 375', cargar_cuenta(375)['saldoPesos'])
    st = []
    for m in movs:
        st.append(("INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
                   "VALUES ('Galicia',?,375,515,?,?,SYSDATETIME())",
                   (m['i'], 'Seguro VW Taos: vuelve a Allianz (regla compras particulares: pago en el proveedor + asiento Particular S)', USUARIO)))
        st.append(("INSERT INTO dbo.[Pagos efectivo] (IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,[Importe imputado]) "
                   "VALUES (515,2,30,?,'Blue','Particular S',?)", (m['f'].isoformat() if hasattr(m['f'], 'isoformat') else m['f'], -float(m['m']))))
    print(backup_verificado('allianz-taos-particular-036'))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print(len(movs), 'débitos devueltos | 515', cargar_cuenta(515, refrescar=True)['saldoPesos'], '| 375', cargar_cuenta(375, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
