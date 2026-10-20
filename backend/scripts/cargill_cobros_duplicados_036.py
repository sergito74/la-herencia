"""Cargill (258): cobros de granos registrados dos veces (decisión de Sergio 20/10/2026: anular el movimiento de caja).

Access registraba cada cobro como Pagos efectivo tipo 2 (Cobro/Retiro) forma 7 (Depósito en cuenta), caja La Herencia;
WC importó además el ingreso del Banco Nación/Galicia asignado a Cargill. Se conserva el banco y se eliminan los 67
movimientos de caja con ingreso bancario equivalente (±3 días, mismo importe); sus aplicaciones se anulan.
Fila completa de cada uno en la auditoría (restituible). Idempotente.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'


def candidatos():
    out = []
    for p in fetch_all("SELECT * FROM dbo.[Pagos efectivo] WHERE IdContacto=258 AND IdTipoMovimiento=2 AND IdFormaPago=7 AND [Importe imputado]<0"):
        bn = fetch_all("SELECT IdMovimientoBNA id FROM dbo.[Movimientos BNA] WHERE IdContacto=258 AND ABS(Importe+?)<0.01 AND ABS(DATEDIFF(day,[Fecha / Hora Mov#],?))<=3", (p['Importe imputado'], p['Fecha']))
        gl = fetch_all("SELECT IdMovimiento id FROM dbo.[Movimientos Galicia] WHERE IdContacto=258 AND ABS([Créditos]+?)<0.01 AND ABS(DATEDIFF(day,Fecha,?))<=3", (p['Importe imputado'], p['Fecha']))
        if bn or gl:
            out.append({'pago': p, 'banco': {'bna': [b['id'] for b in bn], 'galicia': [g['id'] for g in gl]}})
    return out


def main():
    _assert_target_is_wc()
    cand = candidatos()
    if not cand:
        print('Nada para anular.'); return
    ids = [c['pago']['IdPagoEfectivo'] for c in cand]
    m = ','.join(map(str, ids))
    apps = fetch_all(f"SELECT * FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' AND IdMovimientoOrigen IN ({m}) AND Anulada=0")
    audit = {'autorizacion': 'Sergio 20/10/2026: anular el movimiento de caja duplicado', 'pagos': cand, 'aplicaciones': apps,
             'backup': backup_verificado('cargill-cobros-duplicados-036')}
    path = ROOT / f'cobros-duplicados-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        execute_write_transaction(
            [("UPDATE dbo.AplicacionesPago SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion='sergio',FechaAnulacion=SYSDATETIME() WHERE IdAplicacion=? AND Anulada=0",
              ('Cobro Cargill duplicado: se conserva el ingreso bancario (036)', a['IdAplicacion'])) for a in apps] +
            [(f"DELETE FROM dbo.[Pagos efectivo] WHERE IdContacto=258 AND IdPagoEfectivo IN ({m})", ())])
    print(json.dumps({'pagosEliminados': len(ids), 'suma': round(sum(c['pago']['Importe imputado'] for c in cand), 2),
                      'aplicacionesAnuladas': len(apps), 'auditoria': str(path), 'backup': audit['backup']}))


if __name__ == '__main__': main()
