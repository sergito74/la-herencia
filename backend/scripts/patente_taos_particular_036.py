"""Patente de la VW Taos AG-964-SV: gasto particular de Sergio pagado desde las cuentas de Giamigli (Sergio 21/10/2026).

En ARBA (12) cada cuota queda como Impuesto (tipo 26) cancelado por su débito bancario; la compensación va en la cuenta del
socio Sergio (IdSocio 1) como AsignacionGasto (deuda de Sergio con la empresa), vinculada al débito (Origen/IdOrigen), igual
que el seguro Allianz de la Taos. Fuente: hoja "Cuenta Sergio" de Cajas Giamigli.xlsx (13 filas "Patente Camioneta").
- Vincula las 11 AsignacionGasto migradas de la planilla (Origen NULL) con su débito.
- Agrega la cuota del 08/09/2026 (Galicia, $170.967,50), que no estaba migrada. La del 09/10/2026 ($174.161,30) es
  posterior al corte (extracto de octubre sin cargar): se agrega cuando se cargue el débito.
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

USUARIO = 'Sergio (036, revisión 21/10/2026)'


def debito(fecha, importe):
    g = fetch_all("SELECT IdMovimiento i FROM dbo.[Movimientos Galicia] WHERE IdContacto=12 AND [Débitos]=? AND ABS(DATEDIFF(day,Fecha,?))<=3", (importe, fecha))
    return ('Galicia', g[0]['i']) if len(g) == 1 else (None, None)


def main():
    _assert_target_is_wc()
    filas = fetch_all("SELECT IdMovimiento i,Fecha f,Importe m FROM dbo.MovimientosCuentaSocio WHERE IdSocio=1 AND Tipo='AsignacionGasto' "
                      "AND Motivo LIKE '%Patente Camioneta%' AND Anulada=0")
    st = []
    for x in filas:
        o, i = debito(x['f'], x['m'])
        if o and not fetch_all('SELECT 1 y FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=? AND Origen IS NOT NULL', (x['i'],)):
            st.append(("UPDATE dbo.MovimientosCuentaSocio SET Origen=?,IdOrigen=? WHERE IdMovimiento=? AND Origen IS NULL", (o, i, x['i'])))
        print(str(x['f'])[:10], x['m'], '->', o, i)
    if not any(abs(x['m'] - 170967.50) < 0.01 for x in filas):
        o, i = debito('2026-09-08', 170967.50)
        assert o, 'débito 08/09/2026 no encontrado'
        st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada,ImporteUSD,ImporteKgCarne) "
                   "VALUES (1,'AsignacionGasto',170967.50,'2026-09-08',?,?,'Banco Galicia',?,?,0,0,0)",
                   (o, i, 'Patente VW Taos AG964SV cuota 7/2026: gasto particular de Sergio pagado por Giamigli', USUARIO)))
    if st:
        print(backup_verificado('patente-taos-particular-036'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    print(len(st), 'cambios')


if __name__ == '__main__': main()
