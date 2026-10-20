"""Cargill (258): últimos centavos contra el libro de Cargill.
- LPG 330118101789/101758 (partidas en IdVenta 136/139/149/150): Cargill acredita $1.794.090,36 netos, el sistema
  $1.794.090,35 -> +0,01 en IdVenta 136.
- LPG 330125575215 (IdVenta 193/221): Cargill $14.983.292,43 netos, sistema ,44 -> -0,01 en IdVenta 193.
- Tramo del sistema viejo: +0,01 tras redondear sus filas -> ND RED-20200728 $0,01.
- FC 1079-00001141: $4.753,33 como en el listado de Cargill 04/05/2018 (había quedado ,32 al redondear) y el ajuste
  RED-20171104 un centavo menos, para que el saldo al 04/11/2017 siga siendo -$243.087,85.
- LPG 2016 al listado de Cargill 13/05 y 04/07/2016: 330105739157 $59.049,35 (+0,01), 330105739173 $92.630,39 (-0,02),
  330106067367 $15.235,26 (+0,01).
Idempotente.
"""
from datetime import datetime

from scripts.cargill_tramo_viejo_centavos_036 import ajuste
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

CONCEPTO = 'Redondeo cuenta Cargill (036) centavo'


def main():
    _assert_target_is_wc()
    print(backup_verificado('cargill-ultimo-centavo-036'))
    if not fetch_all('SELECT 1 x FROM dbo.[Venta Granos_Ajustes] WHERE Concepto=?', (CONCEPTO,)):
        with reconciliation_transaction():
            execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)", (136, CONCEPTO, 0.01)),
                                       ("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)", (193, CONCEPTO, -0.01))])
            if not fetch_all("SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento]='RED-20200728'"):
                ajuste(datetime(2020, 7, 28), 0.01, 'RED-20200728', 'Redondeo cierre cuenta Cargill 2020')
    fc = fetch_all("SELECT c.IdDeuda i,c.[Tipo de Cambio] tc,t.GranTotal g,t.TotalDetalleCompra d FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t "
                   "ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=258 AND c.[Nro Documento]='1079-00001141'")[0]
    if abs(fc['g'] * fc['tc'] - 4753.33) >= 0.005:
        with reconciliation_transaction():
            execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?',
                                        ((4753.33 / fc['tc'] - (fc['g'] - fc['d'])) / fc['d'], fc['i'])),
                                       ("UPDATE d SET [Precio Unitario]=[Precio Unitario]-0.01 FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra "
                                        "WHERE c.IdContacto=258 AND c.[Nro Documento]='RED-20171104'", ())])
    if not fetch_all("SELECT 1 x FROM dbo.[Venta Granos_Ajustes] WHERE Concepto=? AND IdVenta=21", (CONCEPTO,)):
        with reconciliation_transaction():
            execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)", (i, CONCEPTO, v))
                                       for i, v in ((21, 0.01), (23, -0.02), (37, 0.01))])
    print('ok')


if __name__ == '__main__': main()
