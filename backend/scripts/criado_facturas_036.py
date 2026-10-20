"""Criado: facturas subidas por Sergio a Dropbox (20/10/2026).

- Ricardo Marcos Criado (210): recibo electrónico A 00003-00004511 del 25/09/2026, honorarios y
  certificación balance 25-26 (01/04/2025-31/03/2026): neto $4.254.483,72 + IVA 21% = $5.147.925,30.
- Estudio Criado / Nicolás Criado (115): factura C 00003-00000881 del 08/10/2026, $1.172.619
  (posterior al corte; misma clasificación que la mensual 00003-00000874).
Idempotente.
"""
from datetime import date
from src.db.connection import _assert_target_is_wc, fetch_all
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

DROP = r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras\04 2026 - 03 2027'


def existe(contacto, numero):
    return fetch_all('SELECT IdDeuda FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (contacto, numero))


def main():
    _assert_target_is_wc()
    print(backup_verificado('criado-facturas-036'))
    if not existe(210, '00003-00004511'):
        i = compras.create_compra(
            {'idContacto': 210, 'fecha': date(2026, 9, 25), 'tipoDocumento': 'Factura', 'tipo': 'A',
             'numeroDocumento': '00003-00004511', 'moneda': 'Pesos', 'documentoOriginal': DROP + r'\20260925_RicardoCriado.pdf'},
            [{'productoServicio': 'Honorarios y certif. balance 25-26', 'cantidad': 1, 'precioUnitario': 4254483.72, 'iva': 21,
              'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 2047893459, 'campaña': 'No Aplica'}],
            [{'fechaVencimiento': date(2026, 9, 25)}])
        print('Ricardo 4511 ->', i)
    if not existe(115, '00003-00000881'):
        base = fetch_all("SELECT TOP 1 d.* FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra WHERE c.IdContacto=115 AND c.[Nro Documento]='00003-00000874'")[0]
        cab = fetch_all("SELECT Tipo FROM dbo.Compras WHERE IdContacto=115 AND [Nro Documento]='00003-00000874'")[0]
        i = compras.create_compra(
            {'idContacto': 115, 'fecha': date(2026, 10, 8), 'tipoDocumento': 'Factura', 'tipo': cab['Tipo'],
             'numeroDocumento': '00003-00000881', 'moneda': 'Pesos', 'documentoOriginal': DROP + r'\20261008_NicolasCriado.pdf'},
            [{'productoServicio': base['Producto/Servicio'], 'cantidad': 1, 'precioUnitario': 1172619.00, 'iva': base['IVA'],
              'idCentroCosto': base['IdCentroCostos'], 'idDestino': base['IdDestino'], 'idRubro': base['IdRubro'], 'campaña': base['Campaña']}],
            [{'fechaVencimiento': date(2026, 10, 8)}])
        print('Nicolas 881 ->', i)
    for c, n in ((210, '00003-00004511'), (115, '00003-00000881')):
        print(n, fetch_all('SELECT v.GranTotal FROM dbo.vw_Cns_Total_Compra v JOIN dbo.Compras c ON c.IdDeuda=v.IdDeuda WHERE c.IdContacto=? AND c.[Nro Documento]=?', (c, n)))


if __name__ == '__main__': main()
