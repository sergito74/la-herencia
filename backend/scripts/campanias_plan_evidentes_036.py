"""Auditoría de campañas 036 contra el plan agrícola: correcciones evidentes aprobadas por Sergio (20/10/2026).

Renglones con destino/campaña fuera del plan donde el documento indica la combinación correcta:
- Girasol SYN 3970 (PENDIENTE 56078 Bayá): destino General -> Girasol (semilla 2026/27, como el trigo del mismo pedido).
- Pulverización maíz diferido Pérez 03/01/2025: No Aplica -> 2024/2025.
- Semilla sorgo Sudol 18/12/2025: No Aplica -> 2025/2026.
- Seguro granizo soja segunda Nación Seguros 63288 (mayo 2023): No Aplica -> 2022/2023.
- Avena con campaña de verano 2020/2021: jun-2020 -> 2020; dic-2020 y may-2021 -> 2021.
Solo cambian IdDestino/Campaña/IdCampaña; importes y cantidades iguales.
"""
import json
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.compras.repository import campanias_validas_por_destino

ROOT = Path(__file__).resolve().parents[2] / 'backups/auditoria-campanias'
# IdDetalleCompra: (IdDestino nuevo o None, campaña nueva)
PLAN = {2141382043: (9, '2026/2027'), 2141377233: (None, '2024/2025'), 2141378500: (None, '2025/2026'),
        2141374988: (None, '2022/2023'), 2141374989: (None, '2022/2023'), 2141389806: (None, '2022/2023'),
        2141370653: (None, '2020'), 2141371485: (None, '2021'), 2141371947: (None, '2021')}
FIJOS = ('IdCompra', 'Producto/Servicio', 'Cantidad', 'Precio Unitario', 'IVA', 'IdRubro', 'IdCentroCostos', 'Ajuste financiero')


def lineas():
    m = ','.join('?' * len(PLAN))
    return {r['IdDetalleCompra']: r for r in fetch_all(f'SELECT * FROM dbo.Det_Compras WHERE IdDetalleCompra IN ({m})', tuple(PLAN))}


def main():
    cat = {r['c'].strip(): r['id'] for r in fetch_all('SELECT IdCampaña AS id, Campaña AS c FROM dbo.Campañas')}
    validas = campanias_validas_por_destino()
    antes = lineas()
    assert len(antes) == len(PLAN)
    for i, (dest, camp) in PLAN.items():
        assert cat[camp] in validas[dest or antes[i]['IdDestino']], (i, camp)
    audit = {'autorizacion': 'Sergio 20/10/2026: aplicar correcciones evidentes contra el plan', 'plan': PLAN, 'antes': antes,
             'backup': backup_verificado('campanias-plan-evidentes-036')}
    path = ROOT / f'plan-evidentes-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert lineas() == antes
        execute_write_transaction([('UPDATE dbo.Det_Compras SET IdDestino=COALESCE(?,IdDestino), Campaña=?, IdCampaña=? WHERE IdDetalleCompra=?',
                                    (dest, camp, cat[camp], i)) for i, (dest, camp) in PLAN.items()])
        despues = lineas()
        for i in PLAN:
            assert all(despues[i][k] == antes[i][k] for k in FIJOS)
    audit['despues'] = despues
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'actualizados': len(PLAN), 'backup': audit['backup']}))


if __name__ == '__main__': main()
