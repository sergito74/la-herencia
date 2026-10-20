"""Cargill (258): retenciones de IVA e IIBB de las liquidaciones de granos según certificados (desde 04/2020).

Pedido de Sergio 20/10/2026. En las liquidaciones de Cargill la columna [Retencion IVA] tenía el IVA completo
(IVA RG 2300/2007, que Cargill paga aparte): no es retención. Cargill retiene un % del IVA (certificado RETIVA,
ARCA lo devuelve ~90 días después) y retiene IIBB (certificado RETIIBB). Por liquidación:
  [Retencion IVA]   = suma de certificados RETIVA
  [Otra Retenciones]= suma de certificados RETIIBB
y en Retenciones IVA Granos una fila por certificado de IVA (número, importe, agente, PDF archivado).
Los PDF se copian a Dropbox/Ventas/Retenciones <ejercicio>. Certificados 2021-01-00000094 (retención) y
2021-01-00001075 (su reversión) se compensan y no se registran. Idempotente.
"""
import json
import re
import shutil
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

ROOT = Path(__file__).resolve().parents[2] / 'backups/cargill-conciliacion-20261020'
VENTAS = Path(r'C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Ventas')
COMPENSADAS = {'20210100000094', '20210100001075'}
DESDE = datetime(2020, 4, 1)


def ejercicio(d):
    y = d.year if d.month >= 4 else d.year - 1
    return f'Retenciones 04 {y} - 03 {y + 1}'


def nro_iva(k):
    m = re.fullmatch(r'0?9601(\d{4})(\d{6})', k)
    return f'09601-{m.group(1)}-{m.group(2)}' if m else k


def archivar(c, k):
    d = datetime.strptime(c['fecha'], '%d/%m/%Y')
    carpeta = VENTAS / ejercicio(d)
    carpeta.mkdir(exist_ok=True)
    existente = [p for p in carpeta.glob('*.pdf') if k.lstrip('0') in re.sub(r'\D', '', p.name)]
    if existente:
        return str(existente[0])
    destino = carpeta / f"30712114602_RET{'IVA' if c['tipo'] == 'IVA' else 'IIBB'}_{k}.pdf"
    origen = Path(c['archivos'][0])
    if not origen.is_absolute():
        origen = ROOT.parents[1] / origen
    shutil.copy2(origen, destino)
    return str(destino)


def main():
    _assert_target_is_wc()
    certs = {k: c for k, c in json.load(open(ROOT / 'certificados.json', encoding='utf-8')).items() if k not in COMPENSADAS}
    ventas = {r['Nro Documento']: r for r in fetch_all('SELECT * FROM dbo.[Venta Granos] WHERE IdConsignatario=258 AND Fecha>=?', (DESDE,))}
    por_lpg = defaultdict(list)
    sin_lpg = []
    for k, c in certs.items():
        if c.get('lpg') in ventas:
            por_lpg[c['lpg']].append((k, c))
        else:
            sin_lpg.append((k, c))
    ids = [v['IdVenta'] for v in ventas.values()]
    m = ','.join(map(str, ids))
    rig_antes = fetch_all(f'SELECT * FROM dbo.[Retenciones IVA Granos] WHERE IdLiquidacion IN ({m})')
    devol = {re.sub(r'\D', '', r['Nro Certificado'] or ''): r['Importe Devolucion'] for r in rig_antes if r['Importe Devolucion']}
    plan, filas = [], []
    for nro, v in ventas.items():
        cs = por_lpg.get(nro, [])
        iva = round(sum(c['importe'] for _, c in cs if c['tipo'] == 'IVA'), 2)
        iibb = round(sum(c['importe'] for _, c in cs if c['tipo'] == 'IIBB'), 2)
        plan.append({'IdVenta': v['IdVenta'], 'lpg': nro, 'antes': {'iva': v['Retencion IVA'], 'otras': v['Otra Retenciones']}, 'iva': iva, 'iibb': iibb})
        for k, c in cs:
            if c['tipo'] == 'IVA':
                filas.append((v['IdVenta'], nro_iva(k), c['importe'], devol.get(k.lstrip('0'), devol.get(k, 0)) or 0, archivar(c, k)))
            else:
                archivar(c, k)
    audit = {'autorizacion': 'Sergio 20/10/2026: registrar retenciones faltantes y archivar comprobantes', 'plan': plan,
             'rigAntes': rig_antes, 'rigNuevas': filas, 'certificadosSinLiquidacion': sin_lpg,
             'backup': backup_verificado('cargill-retenciones-036')}
    path = ROOT / f'retenciones-{datetime.now():%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(audit, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    with reconciliation_transaction():
        stmts = [('UPDATE dbo.[Venta Granos] SET [Retencion IVA]=?,[Otra Retenciones]=? WHERE IdVenta=? AND IdConsignatario=258', (p['iva'], p['iibb'], p['IdVenta'])) for p in plan]
        stmts.append((f'DELETE FROM dbo.[Retenciones IVA Granos] WHERE IdLiquidacion IN ({m})', ()))
        base = fetch_all('SELECT ISNULL(MAX(IdRetencion),0) AS n FROM dbo.[Retenciones IVA Granos]')[0]['n']
        stmts += [('INSERT INTO dbo.[Retenciones IVA Granos] (IdRetencion,IdLiquidacion,[Nro Certificado],[Agente Retencion],[Importe Retenido],[Importe Devolucion],Imagen) VALUES (?,?,?,?,?,?,?)',
                   (base + j + 1, i, n, 258, imp, dv, img)) for j, (i, n, imp, dv, img) in enumerate(filas)]
        execute_write_transaction(stmts)
    print(json.dumps({'liquidaciones': len(plan), 'certIVA': len(filas), 'conIIBB': sum(1 for p in plan if p['iibb']),
                      'certSinLiquidacion': [(k, c['lpg'], c['importe']) for k, c in sin_lpg], 'backup': audit['backup']}, default=str))


if __name__ == '__main__': main()
