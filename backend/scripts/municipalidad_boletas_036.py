"""Municipalidad de Bolívar (72): boletas que no se descargaron (Sergio 21/10/2026: "generalas a partir del modelo de las
que sí fueron descargadas").

1. Tasa Vial (bimestral, cuenta I-5283200): Impuestos tipo 8, Periodo "<cuota> <año>" como 1166/1187. Importe = pago del
   banco (DEBIN Nuevo Banco de Santa Fe / transferencia); número y PDF cuando el PDF está en Dropbox/Compras.
2. Transferencias chicas "Varios Proveedores" a la Municipalidad (guías de traslado / marca, comprobantes en
   Cuentas a pagar/Transferencias/Municipalidad Bolivar): Compras "SIN COPIA" como 2143514703 (centro 2, destino 1,
   rubro guías 2047893445, campaña No Aplica).
Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

C = 72
DB = r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras'
# (fecha, cuota/año, importe, número, pdf)
TASA_VIAL = [
    ('2025-03-17', '02 2025', 918555.34, None, DB + r'\04 2024 - 03 2025\20250317_MunicipalidadDeBolivar.pdf'),
    ('2025-05-14', '03 2025', 669250.56, None, None),
    ('2025-07-15', '04 2025', 662630.05, '001/002000194233/0', DB + r'\04 2025 - 03 2026\20250715_MunicipalidadDeBolivar.pdf'),
    ('2025-09-25', '05 2025', 726960.69, '007/000000059062/2', DB + r'\04 2025 - 03 2026\20250925_MunicipalidadDeBolivar.pdf'),
    ('2025-11-17', '06 2025', 717489.82, None, None),
    ('2026-03-16', '02 2026', 959758.40, None, None),
    ('2026-05-14', '03 2026', 1043783.59, None, None),
]
GUIAS = [('2024-12-13', 54486.10), ('2025-01-28', 82741.20), ('2025-09-18', 130535.68), ('2025-09-23', 85547.00),
         ('2025-12-15', 106592.33)]


def main():
    _assert_target_is_wc()
    print(backup_verificado('municipalidad-boletas-036'))
    with reconciliation_transaction():
        for f, per, imp, nro, pdf in TASA_VIAL:
            if fetch_all('SELECT 1 x FROM dbo.Impuestos WHERE IdOrganismo=? AND IdTipoImpuesto=8 AND [Periodo liquidado]=?', (C, per)):
                continue
            execute_write_transaction([('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) '
                                        'VALUES (?,?,8,?,?,?,?)', (f, C, per, nro, imp, pdf and pdf + '#' + pdf + '#'))])
            print('tasa vial', per, imp)
        for f, imp in GUIAS:
            d = datetime.strptime(f, '%Y-%m-%d')
            if fetch_all("SELECT 1 x FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda WHERE c.IdContacto=? AND c.Fecha=? "
                         "AND c.[Nro Documento]='SIN COPIA' AND ABS(t.GranTotal-?)<0.01", (C, d, imp)):
                continue
            cab = {'idContacto': C, 'fecha': d, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': 'SIN COPIA', 'moneda': 'Pesos',
                   'tipoDeCambio': 1, 'ajustaTipoCambio': False}
            lin = {'productoServicio': 'Guias de traslado / marca', 'cantidad': 1, 'precioUnitario': imp, 'iva': 0, 'ajusteFinanciero': False,
                   'idCentroCosto': 2, 'idDestino': 1, 'idRubro': 2047893445, 'campaña': 'No Aplica', 'idCampania': 20}
            execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                       compras._vencimiento_insert_statement({'fechaVencimiento': d})])
            print('guías', f, imp)
    invalidar()
    print('saldo', round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
