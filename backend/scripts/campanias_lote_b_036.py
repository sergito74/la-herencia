"""Auditoría de campañas 036, lote B: 13 renglones migrados de Access con texto 2025/2026 o 2026
y IdCampaña 20 (No Aplica), destino productivo. Decisión de Sergio 20/10/2026: vincular según el texto.
Se pasa IdCampaña a la única coincidencia exacta del catálogo; texto, importes, cantidades,
destinos y rubros quedan iguales. Fuente: informe de `auditar_campanias_036` (tipo texto_vinculo_discordantes).

Uso (desde backend/): python -m scripts.campanias_lote_b_036 <informe.json>
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/auditoria-campanias'
CAMPOS = ('IdCompra', 'Producto/Servicio', 'Cantidad', 'Precio Unitario', 'IVA', 'IdDestino', 'IdRubro', 'IdCentroCostos', 'Campaña', 'Ajuste financiero')


def lineas(ids):
    marcas = ','.join('?' * len(ids))
    return {r['IdDetalleCompra']: r for r in fetch_all(f'SELECT * FROM dbo.Det_Compras WHERE IdDetalleCompra IN ({marcas})', tuple(ids))}


def main(informe):
    h = [x for x in json.load(open(informe, encoding='utf-8'))['hallazgos'] if x['tipo'] == 'texto_vinculo_discordantes']
    plan = {x['IdDetalleCompra']: x['candidatos'][0] for x in h if len(x['candidatos']) == 1}
    assert len(plan) == len(h) == 13, (len(plan), len(h))
    cat = {r['id']: r['c'].strip() for r in fetch_all('SELECT IdCampaña AS id, Campaña AS c FROM dbo.Campañas')}
    antes = lineas(list(plan))
    for i, c in plan.items():
        r = antes[i]
        assert r['IdCampaña'] == 20 and r['Campaña'].strip().lower() == cat[c].lower(), (i, r['Campaña'], cat[c])
    audit = {'autorizacion': 'Sergio 20/10/2026: auditoría de campañas por lotes', 'informe': informe, 'plan': plan,
             'antes': antes, 'backup': backup_verificado('campanias-lote-b-036')}
    path = ROOT / f'lote-b-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert lineas(list(plan)) == antes
        execute_write_transaction([('UPDATE dbo.Det_Compras SET IdCampaña=? WHERE IdDetalleCompra=? AND IdCampaña=20', (c, i))
                                   for i, c in plan.items()])
        despues = lineas(list(plan))
        for i, c in plan.items():
            assert despues[i]['IdCampaña'] == c
            assert all(despues[i][k] == antes[i][k] for k in CAMPOS)
    marcas = ','.join('?' * len(plan))
    en_costos = fetch_all(f'SELECT COUNT(DISTINCT IdDetalleCompra) n FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdDetalleCompra IN ({marcas}) AND IdCampaña IS NOT NULL', tuple(plan))
    audit['despues'] = despues
    audit['enVistaCostos'] = en_costos
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'actualizados': len(plan), 'enVistaCostos': en_costos, 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main(sys.argv[1])
