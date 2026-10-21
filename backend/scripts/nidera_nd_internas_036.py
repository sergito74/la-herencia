"""Nidera (303): diferencias de cambio sin nota (respuesta 15 de Sergio, 21/10/2026) -> notas internas en pesos.

La cuenta en dólares coincide con los estados de Nidera (scripts/nidera_036.py, 18/10/2026). Cada ciclo se pagó en pesos al
TC del día de pago y la factura está a su TC: la diferencia en pesos no tiene ND de Nidera en el sistema (la "sin copia" de
2018 se borró y la ND 7028-11189 quedó anulada por el DI 1820026177). Saldo en pesos de cada ciclo cerrado = la nota interna:
  2018-06-22  FC 4028-87684        $0,21          2019-07-23  FC 7028-3931   (11.625,22 x 27,325)
  2020-07-01  FC 7028-12491  (x 42,79)            2021-06-24  FC 0301-4242/4243 (x 73,16)
  2022-07-01  FC 0301-23328  (x 119,41)           2023-04-19  FC 0301-32216  (x 215,10)
Los importes se calculan con los saldos del sistema en cada cierre. Total $398.474,06. Idempotente.
"""
from datetime import date

from scripts.nd_interna_tc_036 import crear
from src.db.connection import _assert_target_is_wc, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 303
CICLOS = [(date(2018, 6, 22), '4028-00087684'), (date(2019, 7, 23), '7028-00003931'), (date(2020, 7, 1), '7028-00012491'),
          (date(2021, 6, 24), '0301-00004242'), (date(2022, 7, 1), '0301-00023328'), (date(2023, 4, 19), '0301-00032216')]


def pesos_doc(nro):
    x = fetch_all("SELECT c.Moneda m,c.[Tipo de Cambio] tc,t.GranTotal g FROM dbo.Compras c JOIN dbo.vw_Cns_Total_Compra t ON t.IdDeuda=c.IdDeuda "
                  "WHERE c.IdContacto=? AND c.[Nro Documento]=?", (C, nro))[0]
    return x['g'] * (x['tc'] if x['m'] == 'Dolares' else 1)


def main():
    _assert_target_is_wc()
    if fetch_all("SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento] LIKE 'N_I303-%'", (C,)):
        print('Nada pendiente.'); return
    filas = cargar_cuenta(C, refrescar=True)['filas']
    saldo = lambda d: [x for x in filas if x['fecha'] <= d][-1]['saldoPesos']
    abierta = {date(2019, 7, 23): pesos_doc('7028-00012491')}  # FC 12491 ya emitida y abierta en ese cierre
    ajustes, previo = [], 0.0
    for d, fc in CICLOS:
        s = round(saldo(d) + abierta.get(d, 0.0), 2)
        ajustes.append((d, round(s - previo, 2), fc, f'Dif. de cambio ciclo {d:%d/%m/%Y}'))
        previo = s
    print(ajustes, round(sum(a[1] for a in ajustes), 2))
    print(backup_verificado('nidera-nd-internas-036'))
    with reconciliation_transaction():
        print(crear(C, ajustes))
    invalidar()
    c = cargar_cuenta(C, refrescar=True)
    print(c['saldoPesos'], c['saldoDolares'])


if __name__ == '__main__': main()
