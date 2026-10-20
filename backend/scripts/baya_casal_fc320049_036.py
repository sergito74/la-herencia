"""Corrige precio documentado y vínculos de campaña; ejecución única con respaldo."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts.baya_casal_nd134645_036 import state
from src.db.connection import fetch_all, execute_write_transaction, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado
from src.features.auditoria_cuentas.bimonetaria import invalidar

ID = 2143514033
ROOT = Path(__file__).resolve().parents[2] / 'backups/baya-conciliacion-20261019'


def main():
    before = state(ID)
    header = before['cabecera'][0]
    assert header['IdContacto'] == 226 and header['Nro Documento'].replace(' ', '') == '0020-00320049'
    rows = before['lineas']
    assert len(rows) == 9
    campaigns = fetch_all('SELECT [IdCampaña], [Campaña] FROM dbo.[Campañas]')
    mapping = {r['Campaña']: r['IdCampaña'] for r in campaigns}
    target = next(r for r in rows if r['IdDetalleCompra'] == 2141390016)
    assert target['Cantidad'] == 9488
    if target['Precio Unitario'] == .6218 and all(r['IdCampaña'] == mapping[r['Campaña']] for r in rows):
        print('Corrección ya aplicada; sin cambios.'); return
    assert target['Precio Unitario'] == .62 and all(r['IdCampaña'] is None for r in rows)
    pdf = Path(header['Documento Original'].replace('\\\\', '\\'))
    audit = {'antes': before, 'pdf': str(pdf), 'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
             'autorizacion': 'Sergio 20/10/2026: aplicar correcciones de FC320049',
             'backup': backup_verificado('baya-fc320049-036')}
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / f'fc320049-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        assert state(ID) == before
        assert fetch_all('SELECT [IdCampaña], [Campaña] FROM dbo.[Campañas]') == campaigns
        statements = [('UPDATE dbo.Det_Compras SET [IdCampaña]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                       (mapping[r['Campaña']], r['IdDetalleCompra'], ID)) for r in rows]
        statements.append(('UPDATE dbo.Det_Compras SET [Precio Unitario]=? WHERE IdDetalleCompra=? AND IdCompra=?',
                           (.6218, target['IdDetalleCompra'], ID)))
        execute_write_transaction(statements)
        after = state(ID)
        assert after['cabecera'] == before['cabecera'] and after['relaciones'] == before['relaciones']
        for old, new in zip(rows, after['lineas']):
            expected = dict(old, **{'IdCampaña': mapping[old['Campaña']]})
            if old['IdDetalleCompra'] == target['IdDetalleCompra']: expected['Precio Unitario'] = .6218
            for key in expected:
                if key != 'SSMA_TimeStamp': assert new[key] == expected[key], key
        total = fetch_all('SELECT ImporteDocumento FROM dbo.vw_Compras_ImporteDocumento WHERE IdDeuda=?', (ID,))[0]['ImporteDocumento']
        assert round(total, 2) == 19375.91
        costs = fetch_all('SELECT IdDetalleCompra,[IdCampaña],Pesos,Dolares FROM dbo.vw_ResultadosCultivo_CostosBase WHERE IdCompra=?', (ID,))
        assert len(costs) == 9 and all(r['IdCampaña'] is not None for r in costs)
        audit.update(despues=after, total=total, costos=costs)
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    invalidar()
    print(json.dumps({'total': total, 'lineasConCampaña': len(costs), 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
