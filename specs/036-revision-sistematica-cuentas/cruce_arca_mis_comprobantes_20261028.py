"""Cruce de Mis Comprobantes Recibidos (ARCA, CSV por año) contra Compras de WC. Solo lectura.

Uso (desde backend/): python claude_cruce_arca.py <carpeta zips> <salida.json>
"""
import csv
import glob
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, '.')
from src.db.connection import fetch_all  # noqa: E402

CARPETA, SALIDA = sys.argv[1], sys.argv[2]
NOTAS_CREDITO = {3, 8, 13, 53, 113, 203, 208, 213}  # NC A/B/C/M, tique NC, FCE NC


def num(s):
    return float(s.replace('.', '').replace(',', '.')) if s else 0.0


arca = {}
for z in sorted(glob.glob(os.path.join(CARPETA, '*.zip'))):
    zf = zipfile.ZipFile(z)
    texto = zf.read(zf.namelist()[0]).decode('utf-8', 'replace')
    for r in csv.reader(io.StringIO(texto), delimiter=';'):
        if not r or not re.match(r'\d{4}-\d{2}-\d{2}', r[0]):
            continue
        clave = (r[7], int(r[2]), int(r[3]), int(r[1]))  # CUIT emisor, PV, número, tipo
        arca[clave] = {'fecha': r[0], 'tipo': int(r[1]), 'pv': int(r[2]), 'nro': int(r[3]), 'cuit': r[7], 'emisor': r[8],
                       'moneda': r[12], 'tc': num(r[11]), 'total': num(r[29]) * (-1 if int(r[1]) in NOTAS_CREDITO else 1)}

cuit_ct = {r['i']: re.sub(r'\D', '', r['c'] or '') for r in fetch_all("SELECT IdContacto i, [CUIT/CUIL] c FROM dbo.Contactos", ())}
razon = {r['i']: r['r'] for r in fetch_all("SELECT IdContacto i, [Razon Social] r FROM dbo.Contactos", ())}
wc = defaultdict(list)
for w in fetch_all(
        "SELECT c.IdDeuda, c.IdContacto, c.Fecha, c.[Nro Documento] nro, c.[Tipo documento] td, c.Moneda, "
        "v.ImporteDocumento tot FROM dbo.Compras c JOIN dbo.vw_Compras_ImporteDocumento v ON v.IdDeuda = c.IdDeuda", ()):
    m = re.findall(r'\d+', w['nro'] or '')
    if len(m) >= 2:
        wc[(int(m[-2]), int(m[-1]))].append(w)

# CUIT -> contacto aprendido de los comprobantes que sí cruzan (muchos contactos no tienen CUIT cargado)
res, cuenta = [], Counter()
for k, a in sorted(arca.items(), key=lambda kv: kv[1]['fecha']):
    cands = wc.get((a['pv'], a['nro']), [])
    propios = [w for w in cands if cuit_ct.get(w['IdContacto']) == a['cuit']]
    elegido = propios[0] if len(propios) == 1 else (cands[0] if len(cands) == 1 else None)
    if not cands:
        cuenta['no_en_wc'] += 1
        res.append({'estado': 'NO_EN_WC', **a})
        continue
    if not elegido:
        cuenta['ambiguo'] += 1
        res.append({'estado': 'AMBIGUO', **a, 'candidatos': [[w['IdDeuda'], w['IdContacto'], razon.get(w['IdContacto'])] for w in cands]})
        continue
    obs = []
    if cuit_ct.get(elegido['IdContacto']) and cuit_ct[elegido['IdContacto']] != a['cuit']:
        obs.append('CUIT_DISTINTO')
    fw = elegido['Fecha'].date().isoformat()
    if fw != a['fecha']:
        obs.append('FECHA')
    tot_wc = float(elegido['tot'] or 0)
    tot_a = a['total'] if a['moneda'] in ('$', 'PES') or elegido['Moneda'] == 'Dolares' and False else a['total']
    if elegido['Moneda'] == 'Dolares' and a['moneda'] != '$':
        tot_a = a['total']
    elif a['moneda'] != '$':
        tot_a = a['total'] * a['tc']
    if abs(abs(tot_wc) - abs(tot_a)) > 1:
        obs.append('IMPORTE')
    cuenta['ok' if not obs else 'con_obs'] += 1
    if obs:
        res.append({'estado': ','.join(obs), **a, 'idDeuda': elegido['IdDeuda'], 'ct': elegido['IdContacto'],
                    'razon': razon.get(elegido['IdContacto']), 'fechaWc': fw, 'totWc': round(tot_wc, 2), 'nroWc': elegido['nro']})
json.dump(res, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print('ARCA', len(arca), dict(cuenta))
print(Counter(r['estado'] for r in res).most_common())
