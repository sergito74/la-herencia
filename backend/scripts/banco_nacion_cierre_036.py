"""Banco Nación (369): revisión (Sergio 21/10/2026), mismo tratamiento que Banco Galicia (banco_galicia_cierre_036).

1. Plazos fijos (constitución "DEB.P.FIJO" y acreditación "PLAZO FIJO") y extracción en red Link: sin contacto.
2. Gastos bancarios (comisiones, IVA, retenciones/percepciones, alquiler caja de seguridad, "Débito Nación", débito indebido
   Mastercard 18020 decidido como pérdida/gasto 06/10/2026, pares que se anulan): comprobante interno mensual GB369-aamm,
   rubro Gastos bancarios. Las facturas del BNA de 2026 cubren el total de julio (FC 14/08 $74.400), agosto y septiembre
   ($85.560 c/u): esos meses sin comprobante interno.
3. Queda en la cuenta: préstamos (acreditaciones y cuotas; hay préstamos vigentes, falta el cronograma de capital e intereses).
4. BNA 16987 "DEPOSITO DE TER-SUC 1190" 07/02/2011 $3.285: es el depósito del cobro de Agropecuaria Las Heras (venta
   0001-1789), ya registrado en su cuenta como Pagos efectivo 108 + 109 ($235,43 + $3.049,57, forma "Depósito en cuenta",
   mismo día): sin contacto (no es del banco).
Centro 3, destino 1. Uso: --simular (default) / --aplicar. Idempotente.
"""
import sys
from collections import defaultdict
from datetime import date, datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras

C = 369
RUBRO_GASTOS = 2047893509
FACTURADOS = {(2026, 7), (2026, 8), (2026, 9)}
QUEDAN = ()


def _doc(nro, fecha, importe, texto):
    f = datetime(fecha.year, fecha.month, fecha.day)
    cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': nro, 'moneda': 'Pesos',
           'tipoDeCambio': 1, 'ajustaTipoCambio': False}
    lin = {'productoServicio': texto[:50], 'cantidad': 1, 'precioUnitario': round(importe, 2), 'iva': 0, 'ajusteFinanciero': False,
           'idCentroCosto': 3, 'idDestino': 1, 'idRubro': RUBRO_GASTOS, 'campaña': 'No Aplica', 'idCampania': 20}
    return [compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin), compras._vencimiento_insert_statement({'fechaVencimiento': f})]


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    conceptos = {r['i']: (r['c'] or '').upper() for r in fetch_all('SELECT IdMovimientoBNA i, Concepto c FROM dbo.[Movimientos BNA]')}
    filas = cargar_cuenta(C, refrescar=True)['filas']
    sin_contacto, gastos, prestamos = [], defaultdict(float), 0.0
    for f in filas:
        if f['origenTipo'] != 'Banco Nacion' or f['idOrigen'] in QUEDAN:
            continue
        d, m = conceptos.get(f['idOrigen'], ''), f['creditoPesos'] - f['deudaPesos']
        if 'PLAZO FIJO' in d or 'P.FIJO' in d or 'EXTR.RED LINK' in d or f['idOrigen'] == 16987:
            sin_contacto.append(f['idOrigen'])
        elif 'PRESTAMO' in d:
            prestamos += m
        else:
            gastos[(f['fecha'].year, f['fecha'].month)] += m
    docs = [(f'GB369-{a % 100:02d}{m:02d}', date(a, m, 28), round(v, 2), f'Gastos bancarios {m:02d}/{a} (extracto BNA)')
            for (a, m), v in sorted(gastos.items()) if (a, m) not in FACTURADOS and abs(v) >= 0.01]
    resto = sum(f['creditoPesos'] - f['deudaPesos'] for f in filas if not (f['origenTipo'] == 'Banco Nacion' and f['idOrigen'] in sin_contacto))
    print(f'sin contacto {len(sin_contacto)}; comprobantes {len(docs)} por {sum(d[2] for d in docs):,.2f}; préstamos neto {prestamos:,.2f}')
    print('saldo previsto', round(resto - sum(d[2] for d in docs), 2))
    if not aplicar:
        return
    from src.features.vinculos.backup import backup_verificado
    print(backup_verificado('banco-nacion-cierre-036'))
    with reconciliation_transaction():
        execute_write_transaction([('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL WHERE IdMovimientoBNA=? AND IdContacto=?', (i, C)) for i in sin_contacto])
        for nro, f, imp, texto in docs:
            if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, nro)):
                execute_write_transaction(_doc(nro, f, imp, texto))
    invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
