"""Cuenta 375 (Sergio empleado): cierre (Sergio 22/10/2026: "Giamigli no le debe nada a Sergio (empleado). El saldo debe ser
$1.800.000 porque no está registrado el pago del sueldo de septiembre").

- 2011–2012 (liquidaciones hasta diciembre-2012, fechada 10/01/2013): sueldos no cobrados. Los pagos del bloque se aplican FIFO
  a las liquidaciones más viejas; el resto impago de cada período se cancela con un Ajuste Interno (Crédito) "no cobrado".
- Junio-2018 (con SAC, $33.208): $2.208 no cobrados (pagos de $21.000 + $10.000 del 28/10/2019).
- Redondeos 2020–2026 (+$2,48): Ajuste Interno (Deuda) por diferencia de redondeo.
Resultado esperado: 375 = −$1.800.000 (sueldo de septiembre-2026, se paga en octubre). Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, cierre cuenta 375 22/10/2026)'


def _aj(st, f, lado, imp, mot):
    if not fetch_all('SELECT 1 x FROM dbo.AjustesCuentaCorriente WHERE IdContacto=375 AND Motivo=?', (mot,)):
        st.append(('INSERT INTO dbo.AjustesCuentaCorriente (IdContacto,Fecha,Lado,Importe,Motivo,Usuario) VALUES (375,?,?,?,?,?)', (f, lado, round(imp, 2), mot, USUARIO)))


def main():
    _assert_target_is_wc()
    filas = fetch_all("SELECT Fecha f,Origen o,IdOrigen i,[Nro Documento] n,Deuda d,Credito c FROM dbo.vw_MovimientosCuenta_Base "
                      "WHERE IdContacto=375 AND Fecha<'2013-01-31' ORDER BY Fecha")
    sue = [[r, float(r['d'])] for r in filas if r['o'] == 'Remuneraciones']
    pago = sum(float(r['c']) - (float(r['d']) if r['o'] != 'Remuneraciones' else 0) for r in filas)
    for s in sue:                       # FIFO
        usa = min(pago, s[1]); s[1] -= usa; pago -= usa
    st = []
    for r, resto in sue:
        if resto > 0.005:
            f = r['f'].date().isoformat() if hasattr(r['f'], 'date') else str(r['f'])[:10]
            _aj(st, f, 'Credito', resto, f'Sueldo {r["n"]} no cobrado (2011-2012): Giamigli no le debe nada a Sergio empleado (IdSalario {r["i"]})')
    _aj(st, '2018-07-01', 'Credito', 2208.0, 'Sueldo Junio 2018 (con SAC $33.208): $2.208 no cobrados (IdSalario 1829632635)')
    print('2011-2012 no cobrado', round(sum(x[1] for x in sue), 2), '| pagos sin aplicar', round(pago, 2))
    print(backup_verificado('sergio-375-cierre-sueldos-036'))
    with reconciliation_transaction():
        st and execute_write_transaction(st)
    invalidar()
    saldo = cargar_cuenta(375, refrescar=True)['saldoPesos']
    dif = round(saldo + 1800000, 2)
    if abs(dif) > 0.004 and abs(dif) < 10:
        with reconciliation_transaction():
            st2 = []
            _aj(st2, '2026-09-30', 'Deuda' if dif > 0 else 'Credito', abs(dif), 'Diferencia de redondeo acumulada 2020-2026 (cierre cuenta 375)')
            st2 and execute_write_transaction(st2)
        invalidar()
        saldo = cargar_cuenta(375, refrescar=True)['saldoPesos']
    print('375', saldo)


if __name__ == '__main__': main()
