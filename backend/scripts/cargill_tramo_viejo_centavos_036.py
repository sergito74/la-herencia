"""Cargill (258): tramo del sistema viejo de Cargill (2016 - 07/2020) al centavo.

1. Ventana del listado "Cuenta Corriente en Pesos al 04-05-2018" (04/11/2017 - 03/05/2018): cada comprobante y
   liquidación al importe exacto que figura en el listado (renglones escalados / ajuste "Redondeo cuenta Cargill (036)").
2. Lo que no tiene detalle de Cargill se cierra con un ajuste de redondeo (ND/NC tipo X, Financiamiento, sin IVA):
   - RED-20171104: diferencia al saldo inicial del listado (-$243.087,85 al 04/11/2017).
   - RED-20200728: diferencia al cierre del sistema viejo (saldo 0 tras la transferencia del 28/07/2020 + AJ 2).
Idempotente.
"""
import sys
from datetime import date, datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

DOCS = {'1126-00004959': -866.12}  # pesos del listado de Cargill (el resto ya coincide)
LPG = {'330110364220': 174306.09, '330110375148': 189384.51, '330110399498': 162745.86, '330110399611': 113039.52, '330110399367': 120294.92}
SALDO_20171104 = -243087.85
VIEJOS = ('1125-00000608', '1125-00001548', '1125-00001549', '1126-00014654', '1126-00014865', '1125-00003153', 'AJ 2', '1079-00003180')
BANCOS_VIEJOS = {('Banco Nacion', 16482), ('Banco Nacion', 16483), ('Banco Nacion', 16484), ('Banco Nacion', 16485), ('Pagos efectivo', 1895), ('Venta Granos', 119)}


def movimientos():
    return fetch_all("SELECT v.Fecha f,v.Origen o,v.IdOrigen i,c.[Nro Documento] n,(ISNULL(v.Credito,0)-ISNULL(v.Deuda,0))*ISNULL(CASE WHEN c.Moneda='Dolares' "
                     "THEN c.[Tipo de Cambio] END,1) s FROM dbo.vw_MovimientosCuenta_Base v LEFT JOIN dbo.Compras c ON v.Origen='Compras' AND c.IdDeuda=v.IdOrigen "
                     "WHERE v.IdContacto=258")


def ajuste(fecha, importe, nro, texto):
    cab = {'idContacto': 258, 'fecha': fecha, 'tipoDocumento': 'Nota de Débito' if importe > 0 else 'Nota de Crédito', 'tipo': 'X',
           'numeroDocumento': nro, 'moneda': 'Pesos', 'tipoDeCambio': 1}
    linea = {'productoServicio': texto, 'cantidad': 1, 'precioUnitario': importe, 'iva': 0, 'idCentroCosto': 3, 'idDestino': 1,
             'idRubro': 2047893443, 'campaña': 'No Aplica', 'idCampania': compras.get_id_campania_por_nombre('No Aplica')}
    execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(linea),
                               compras._vencimiento_insert_statement({'fechaVencimiento': fecha})])


def main():
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.Compras WHERE IdContacto=258 AND [Nro Documento] IN ('RED-20171104','RED-20200728')"):
        print('Nada pendiente.'); return
    print(backup_verificado('cargill-tramo-viejo-036'))
    with reconciliation_transaction():
        for n, p in DOCS.items():
            x = fetch_all("SELECT c.IdDeuda i,c.Moneda m,c.[Tipo de Cambio] tc,t.GranTotal g,t.TotalDetalleCompra d FROM dbo.Compras c "
                          "JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=258 AND c.[Nro Documento]=?", (n,))[0]
            k = x['tc'] if x['m'] == 'Dolares' else 1
            execute_write_transaction([('UPDATE dbo.Det_Compras SET [Precio Unitario]=[Precio Unitario]*? WHERE IdCompra=?', ((p / k - (x['g'] - x['d'])) / x['d'], x['i']))])
        for n, p in LPG.items():
            x = fetch_all("SELECT v.IdVenta i,b.Credito c FROM dbo.[Venta Granos] v JOIN dbo.vw_MovimientosCuenta_Base b ON b.Origen='Venta Granos' AND b.IdOrigen=v.IdVenta "
                          "WHERE v.IdConsignatario=258 AND v.[Nro Documento]=?", (n,))[0]
            execute_write_transaction([("INSERT INTO dbo.[Venta Granos_Ajustes] (IdVenta,Concepto,Importe,AlicuotaIVA) VALUES (?,?,?,0)",
                                        (x['i'], 'Redondeo cuenta Cargill (036)', round(p - x['c'], 4)))])
        M = movimientos()
        a = round(SALDO_20171104 - sum(x['s'] for x in M if x['f'].date() <= date(2017, 11, 4)), 2)
        if a:
            ajuste(datetime(2017, 11, 4), -a, 'RED-20171104', 'Ajuste al saldo Cargill 04/11/2017')
        M = movimientos()
        viejo = [x for x in M if x['f'].date() < date(2020, 6, 4) or x['n'] in VIEJOS or (x['o'], x['i']) in BANCOS_VIEJOS]
        b = round(sum(x['s'] for x in viejo), 2)
        if b:
            ajuste(datetime(2020, 7, 28), b, 'RED-20200728', 'Redondeo cierre cuenta Cargill 2020')
        M = movimientos()
        print('al 04/11/2017', round(sum(x['s'] for x in M if x['f'].date() <= date(2017, 11, 4)), 2), 'al 04/05/2018',
              round(sum(x['s'] for x in M if x['f'].date() <= date(2018, 5, 4)), 2), 'ajustes', a, b, 'total', round(sum(x['s'] for x in M), 2))


if __name__ == '__main__': main()
