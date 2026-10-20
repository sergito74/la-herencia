"""Cargill (258): cada movimiento al centavo exacto, como lo registra Cargill (sin fracciones de centavo que se
acumulan entre cientos de filas).
- Comprobantes: precios de renglones escalados para que total en pesos = total redondeado a 2 decimales.
- Liquidaciones: ajuste "Redondeo cuenta Cargill (036)" sin IVA por la fracción.
Idempotente.
"""
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

EPS = 1e-6


def filas():
    docs = fetch_all("SELECT c.IdDeuda i,c.Moneda m,c.[Tipo de Cambio] tc,t.GranTotal g,t.TotalDetalleCompra d FROM dbo.Compras c "
                     "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=258")
    lpg = fetch_all("SELECT v.IdVenta i,b.Credito c FROM dbo.[Venta Granos] v JOIN dbo.vw_MovimientosCuenta_Base b ON b.Origen='Venta Granos' "
                    "AND b.IdOrigen=v.IdVenta WHERE v.IdConsignatario=258")
    docs = [x for x in docs if abs(x['g'] * (x['tc'] if x['m'] == 'Dolares' else 1) - round(x['g'] * (x['tc'] if x['m'] == 'Dolares' else 1), 2)) > EPS]
    lpg = [x for x in lpg if abs(x['c'] - round(x['c'], 2)) > EPS]
    return docs, lpg


def main():
    _assert_target_is_wc()
    docs, lpg = filas()
    if not docs and not lpg:
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-fracciones-036'))
    with reconciliation_transaction():
        for x in docs:
            k = x['tc'] if x['m'] == 'Dolares' else 1
            p = round(x['g'] * k, 2)
            if abs(x['d']) > EPS:
                execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', ((p / k - (x['g'] - x['d'])) / x['d'], x['i']))])
            else:
                execute_write_transaction([('UPDATE dbo.Compras SET PercepcionIVA=PercepcionIVA+? WHERE IdDeuda=?', (p / k - x['g'], x['i']))])
        if lpg:
            execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)",
                                        (x['i'], 'Redondeo cuenta Cargill (036)', round(x['c'], 2) - x['c'])) for x in lpg])
    d, l = filas()
    print(len(docs), 'comprobantes,', len(lpg), 'liquidaciones; quedan', len(d), len(l))


if __name__ == '__main__': main()
