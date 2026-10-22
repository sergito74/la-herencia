"""Banco Galicia (518): revisión y cierre (Sergio 21/10/2026).

1. Inversiones (FIMA suscripción/rescate, plazos fijos; también el plazo fijo BNA 18632 de 2019): no son cuenta corriente con el
   banco -> sin contacto (movimientos de Tesorería entre la cuenta y la inversión; el rendimiento es ingreso financiero).
2. Préstamos: el banco es acreedor; faltaban los intereses como gasto -> comprobante interno "Intereses préstamo" por la
   diferencia entre cuotas pagadas y capital acreditado (préstamos 2022 y 2023-24), rubro Financiamiento.
3. Gastos bancarios (comisiones, IVA, percepciones, sellos, intereses por descubierto): el extracto hace de factura ->
   comprobante interno mensual "Gastos bancarios <mes>", rubro Gastos bancarios. Desde 07/2026 Galicia factura el servicio: en
   esos meses el comprobante interno es solo por lo que la factura no cubre (percepciones/impuestos).
4. Extracciones en cajero (09/10/2024, 2 x $400.000): retiro a caja -> sin contacto. Transf Inmed CP 02/10/2025 $1.500.000:
   traspaso interno con BNA 9432 (crédito a cuenta propia del mismo día).
5. Comisiones BNA 18629-18631 (02/10/2023) estaban en Galicia -> Banco Nación (369).
Centro 3 (Administración General), destino 1, campaña No Aplica. Uso: --simular (default) / --aplicar. Idempotente.
"""
import sys
from collections import defaultdict
from datetime import date, datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras

C, BNA_C = 518, 369
USUARIO = 'Sergio (036, revisión 21/10/2026)'
RUBRO_GASTOS, RUBRO_FINANC = 2047893509, 2047893443
INVERSION = ('FIMA', 'PLAZO')
PRESTAMOS = [  # (nro, fecha, capital acreditado, cuotas pagadas)
    ('INT518-2022', date(2022, 12, 1), 1467000.00 + 753999.55, 1647136.34 + 894900.37),
    ('INT518-2024', date(2024, 8, 26), 9880148.00, 8120149.87 + 17825670.98),
]
MESES_CON_FACTURA = {(2026, 7), (2026, 8), (2026, 9)}


def _desc(i):
    return (fetch_all('SELECT [Descripción] d FROM dbo.[Movimientos Galicia] WHERE IdMovimiento=?', (i,))[0]['d'] or '').upper()


def _doc(nro, fecha, importe, texto, rubro):
    f = datetime(fecha.year, fecha.month, fecha.day)
    cab = {'idContacto': C, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': nro, 'moneda': 'Pesos',
           'tipoDeCambio': 1, 'ajustaTipoCambio': False}
    lin = {'productoServicio': texto[:50], 'cantidad': 1, 'precioUnitario': round(importe, 2), 'iva': 0, 'ajusteFinanciero': False,
           'idCentroCosto': 3, 'idDestino': 1, 'idRubro': rubro, 'campaña': 'No Aplica', 'idCampania': 20}
    return [compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin), compras._vencimiento_insert_statement({'fechaVencimiento': f})]


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    filas = cargar_cuenta(C, refrescar=True)['filas']
    sin_contacto_g, sin_contacto_b, a_bna, gastos = [], [], [], defaultdict(float)
    for f in filas:
        m = f['creditoPesos'] - f['deudaPesos']
        if f['origenTipo'] == 'Banco Nacion':
            (sin_contacto_b if f['idOrigen'] == 18632 else a_bna).append(f['idOrigen'])
            continue
        if f['origenTipo'] != 'Galicia':
            continue
        d = _desc(f['idOrigen'])
        if any(x in d for x in INVERSION) or 'EXTRACCION EN AUTO' in d or f['idOrigen'] == 2813:
            sin_contacto_g.append(f['idOrigen'])
        elif 'PRESTAMO' not in d:
            gastos[(f['fecha'].year, f['fecha'].month)] += m
    facturas = {(r['f'].year, r['f'].month): float(r['g']) for r in fetch_all(
        "SELECT c.Fecha f, t.GranTotal g FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda "
        "WHERE c.IdContacto=? AND c.[Nro Documento] NOT LIKE 'GB518-%' AND c.[Nro Documento] NOT LIKE 'INT518-%'", (C,))}
    docs = []
    for (a, m), imp in sorted(gastos.items()):
        neto = round(imp - facturas.get((a, m), 0), 2)
        if abs(neto) >= 0.01:
            fin = date(a, m, 28)  # fin de mes (todos los meses tienen 28)
            docs.append((f'GB518-{a % 100:02d}{m:02d}', fin, neto, f'Gastos bancarios {m:02d}/{a} (extracto Galicia)', RUBRO_GASTOS))
    for nro, f, capital, cuotas in PRESTAMOS:
        docs.append((nro, f, round(cuotas - capital, 2), f'Intereses préstamo Galicia ({nro[-4:]})', RUBRO_FINANC))
    print(f'sin contacto: {len(sin_contacto_g)} Galicia + {len(sin_contacto_b)} BNA; a Banco Nación: {a_bna}; comprobantes: {len(docs)} por {sum(d[2] for d in docs):,.2f}')
    for d in docs[-6:]:
        print('  ', d[0], d[1], d[2])
    saldo_prev = sum(f['creditoPesos'] - f['deudaPesos'] for f in filas
                     if not (f['origenTipo'] == 'Galicia' and f['idOrigen'] in sin_contacto_g) and f['origenTipo'] != 'Banco Nacion')
    print('saldo previsto', round(saldo_prev - sum(d[2] for d in docs), 2))
    if not aplicar:
        return
    from src.features.vinculos.backup import backup_verificado
    print(backup_verificado('banco-galicia-cierre-036'))
    st = [('UPDATE dbo.[Movimientos Galicia] SET IdContacto=NULL WHERE IdMovimiento=? AND IdContacto=?', (i, C)) for i in sin_contacto_g]
    st += [('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL WHERE IdMovimientoBNA=? AND IdContacto=?', (i, C)) for i in sin_contacto_b]
    st += [('UPDATE dbo.[Movimientos BNA] SET IdContacto=? WHERE IdMovimientoBNA=? AND IdContacto=?', (BNA_C, i, C)) for i in a_bna]
    st += [('UPDATE dbo.[Movimientos BNA] SET IdContacto=NULL WHERE IdMovimientoBNA=9432 AND ISNULL(IdContacto,0)=0', ())]
    if not fetch_all("SELECT 1 x FROM dbo.TraspasosInternosTesoreria WHERE MedioA='galicia' AND IdMovimientoA=2813", ()):
        st.append(("INSERT INTO dbo.TraspasosInternosTesoreria (MedioA,IdMovimientoA,MedioB,IdMovimientoB,Accion,Usuario) VALUES ('galicia',2813,'bna',9432,'Vincular',?)", (USUARIO,)))
    with reconciliation_transaction():
        execute_write_transaction(st)
        for nro, f, imp, texto, rubro in docs:
            if not fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]=?', (C, nro)):
                execute_write_transaction(_doc(nro, f, imp, texto, rubro))
    invalidar()
    print('saldo', cargar_cuenta(C, refrescar=True)['saldoPesos'])


if __name__ == '__main__': main()
