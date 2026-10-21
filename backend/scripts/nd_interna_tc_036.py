"""Nota de débito/crédito INTERNA por ajuste de tipo de cambio (respuesta 15 de Sergio, 21/10/2026).

En una cuenta con documentos en dólares, si un pago en pesos no coincide con los dólares de la factura a su tipo de cambio
y el proveedor no emitió la ND/NC de diferencia de cambio, se registra una nota interna en pesos por la diferencia:
  * tipo X, número "NDI<contacto>-<aammdd>" (o NCI si es a favor; el campo admite 15 caracteres), "Ajusta Tipo Cambio" (no mueve dólares);
  * renglones con el reparto (centro, destino, rubro, campaña) de la factura que ajusta, en proporción a su neto;
  * vinculada a esa factura (CompraDocumentosRelacionados).
Uso: importado desde un script de cuenta con la lista de ajustes: crear(contacto, [(fecha, importe, nro_factura, motivo), ...]).
Importe > 0 = ND (más deuda), < 0 = NC. Idempotente por número.
"""
from datetime import datetime

from src.db.connection import execute_write_transaction, fetch_all
from src.features.compras import repository as compras


def _renglones(contacto, nro_factura, importe, texto):
    src = fetch_all("SELECT d.* FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda=d.IdCompra WHERE c.IdContacto=? AND c.[Nro Documento]=?",
                    (contacto, nro_factura))
    assert src, (contacto, nro_factura)
    pesos = [abs((r['Cantidad'] or 0) * (r['Precio Unitario'] or 0)) or 1.0 for r in src]
    total = sum(pesos)
    cent = int(round(importe * 100))
    partes = [int(cent * w / total) for w in pesos]
    partes[0] += cent - sum(partes)
    return [{'productoServicio': texto[:50], 'cantidad': 1, 'precioUnitario': c / 100, 'iva': 0, 'ajusteFinanciero': False,
             'idCentroCosto': r['IdCentroCostos'], 'idDestino': r['IdDestino'], 'idRubro': r['IdRubro'], 'campaña': r['Campaña'],
             'idCampania': r['IdCampaña']} for c, r in zip(partes, src) if c]


def crear(contacto, ajustes, prefijos=('NDI', 'NCI'), texto='Dif. TC interna', ajusta=True):
    """Crea las notas internas que falten. Devuelve {numero: IdDeuda}. Debe llamarse dentro de reconciliation_transaction().
    Con prefijos=('RDD','RDC'), texto='Redondeo' y ajusta=False sirve para redondeos de cuentas en pesos."""
    creadas = {}
    for fecha, importe, nro_factura, motivo in ajustes:
        f = fecha if isinstance(fecha, datetime) else datetime(fecha.year, fecha.month, fecha.day)
        nro = f"{prefijos[0] if importe > 0 else prefijos[1]}{contacto}-{f:%y%m%d}"
        if fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (contacto, nro)):
            continue
        ref = fetch_all('SELECT IdDeuda i FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (contacto, nro_factura))[0]['i']
        cab = {'idContacto': contacto, 'fecha': f, 'tipoDocumento': 'Nota de Débito' if importe > 0 else 'Nota de Crédito', 'tipo': 'X',
               'numeroDocumento': nro, 'moneda': 'Pesos', 'tipoDeCambio': 1, 'ajustaTipoCambio': ajusta}
        lineas = _renglones(contacto, nro_factura, importe, f'{texto} {nro_factura}')
        i = execute_write_transaction([compras._cabecera_insert_statement(cab)] + [compras._linea_insert_statement(l) for l in lineas] +
                                      [compras._vencimiento_insert_statement({'fechaVencimiento': f})])[0]
        g = fetch_all('SELECT GranTotal g FROM dbo.vw_Cns_Total_Compra WHERE IdDeuda=?', (i,))[0]['g']
        assert abs(g - importe) < 0.01, (nro, g, importe)
        execute_write_transaction([('INSERT INTO dbo.CompraDocumentosRelacionados (IdCompra,IdCompraRelacionada,CreatedAt) VALUES (?,?,SYSDATETIME())', (i, ref))])
        creadas[nro] = (i, motivo)
    return creadas
