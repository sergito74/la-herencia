"""Cuentas sin ficha de revisión (organismos, bancos, socios, personal): correcciones de la revisión del 21/10/2026.

- Ministerio de Desarrollo Agrario (447): la transferencia LINK BNA 18591 del 16/04/2021 ($6.000) es la renovación del
  boleto de marca de Giamigli ante el MDA de la PBA (expediente 705329, renovado hasta el 30/04/2031; mails con el
  Registro Ganadero 05-28/04/2021 y del 03/05/2021). Se carga el comprobante (tipo X, exento), clasificado como los
  permisos de marca: centro 2, destino 1, Gastos de Administración, No Aplica.
- SENASA (250): 9 débitos automáticos "SENASA ARANCELES" en Galicia (dic-2024 a may-2026) sin comprobante. Se carga
  uno por débito con el número de boleta de la leyenda del banco, como el de ago-2024 ("SIN COMPROBANTE"), en Gastos de
  Comercialización como los DT-e (centro 2, destino 1, No Aplica, exento).
- AgroNacion (administración anterior) (5662): 22 pagos 2010-2012 (21 BNA + 1 efectivo) del resumen de la tarjeta
  AgroNación de la sucesión (resumen nov-dic 2011 en Comprobantes/Sucesion/2011). Sergio 21/10/2026: "cerralo como pago de
  la empresa a la sucesión; es una continuación luego de una reestructuración societaria". Un comprobante por pago
  (tipo X, exento), Gastos de Administración, centro 2, destino 1, No Aplica.
Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

GASTOS_ADM, GASTOS_COM = 14, 2047893445
DOCS = [
    (447, datetime(2021, 4, 16), 'EXP-705329', 'Renovación boleto de marca (Exp. 705329)', 6000.0, GASTOS_ADM),
] + [(250, f, f'SEN-{b}', f'Aranceles SENASA boleta {b}', imp, GASTOS_COM) for f, b, imp in (
    (datetime(2024, 12, 18), '6267117', 18454.24), (datetime(2025, 3, 17), '6475178', 3646.33), (datetime(2025, 6, 11), '6704777', 20732.38),
    (datetime(2025, 10, 20), '7048774', 7063.54), (datetime(2025, 11, 19), '7124524', 988.50), (datetime(2025, 12, 16), '7192507', 608.81),
    (datetime(2026, 3, 12), '7401130', 1747.88), (datetime(2026, 5, 14), '7557353', 2127.57), (datetime(2026, 5, 22), '7584526', 33222.90))]


def sucesion():
    pagos = fetch_all("SELECT Fecha f,Origen o,IdOrigen i,Credito c FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=5662 AND Credito>0 ORDER BY Fecha")
    return [(5662, p['f'], f"SUC-{p['f']:%y%m%d}", 'Resumen AgroNación sucesión (pago de la empresa)', round(p['c'], 2), GASTOS_ADM) for p in pagos]


def main():
    DOCS.extend(sucesion())
    _assert_target_is_wc()
    pend = [d for d in DOCS if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (d[0], d[2]))]
    if not pend:
        print('Nada pendiente.'); return
    print(backup_verificado('cuentas-sin-ficha-036'))
    with reconciliation_transaction():
        for c, f, nro, prod, imp, rubro in pend:
            cab = {'idContacto': c, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': nro, 'moneda': 'Pesos', 'tipoDeCambio': 1}
            lin = {'productoServicio': prod, 'cantidad': 1, 'precioUnitario': imp, 'iva': 0, 'idCentroCosto': 2, 'idDestino': 1, 'idRubro': rubro,
                   'campaña': 'No Aplica', 'idCampania': compras.get_id_campania_por_nombre('No Aplica')}
            print(nro, execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                                  compras._vencimiento_insert_statement({'fechaVencimiento': f})])[0])


if __name__ == '__main__': main()
