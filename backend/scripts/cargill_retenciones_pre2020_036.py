"""Cargill (258): tramo 2016 - 06/2020, retenciones sufridas y liquidaciones contra la cuenta corriente de Cargill.

- Las retenciones que Cargill practicó al pagar (Ganancias/IVA/IIBB, 114 filas de Pagos efectivo tipo Egreso) estaban
  con importe positivo, es decir como pagos nuestros a Cargill. La convención de los demás compradores (Elordi, Genta,
  Nidera, Ferias del Centro) es importe negativo: reducen lo que el comprador nos debe ("CE RET..." en el listado de
  cuenta corriente de Cargill 13/05/2016 y 04/07/2016, "Comprob.Egreso" en el de 04/05/2018). Se invierte el signo.
  Las devoluciones de IIBB (2019-09, 2020-01, 2020-04, negativas) quedan positivas, como crédito a nuestro favor.
- LPG 330105739111/739173/106067148/106067367 (IdVenta 22, 23, 36, 37) tenían [Retencion IVA] restando: el PDF y la cuenta
  de Cargill las acreditan por el neto sin retenciones (las retenciones van en el comprobante de egreso). Se pone 0.
Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
VENTAS = (22, 23, 36, 37)
FILTRO = 'IdContacto=258 AND IdTipoMovimiento=3 AND IdFormaPago IN (16,24,27)'


def main():
    _assert_target_is_wc()
    filas = fetch_all(f'SELECT * FROM dbo.[Pagos efectivo] WHERE {FILTRO}')
    assert len(filas) == 114
    ventas = fetch_all(f"SELECT IdVenta,[Retencion IVA] FROM dbo.[Venta Granos] WHERE IdConsignatario=258 AND IdVenta IN ({','.join(map(str, VENTAS))})")
    hecho = fetch_all(f'SELECT SUM([Importe imputado]) s FROM dbo.[Pagos efectivo] WHERE {FILTRO}')[0]['s'] < 0
    if hecho and all(not v['Retencion IVA'] for v in ventas):
        print('Nada pendiente.'); return
    audit = {'autorizacion': 'Sergio 20/10/2026: reconstruir Cargill desde el inicio hasta 2020', 'pagosEfectivo': filas, 'ventas': ventas,
             'backup': backup_verificado('cargill-retenciones-pre2020-036')}
    (ROOT / f'retenciones-pre2020-{datetime.now():%Y%m%d_%H%M%S}.json').write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=1), encoding='utf-8')
    st = [(f"UPDATE dbo.[Venta Granos] SET [Retencion IVA]=0 WHERE IdConsignatario=258 AND IdVenta IN ({','.join(map(str, VENTAS))})", ())]
    if not hecho:
        st.append((f'UPDATE dbo.[Pagos efectivo] SET [Importe imputado]=-[Importe imputado] WHERE {FILTRO}', ()))
    with reconciliation_transaction():
        execute_write_transaction(st)
    print('ok', audit['backup'])


if __name__ == '__main__': main()
