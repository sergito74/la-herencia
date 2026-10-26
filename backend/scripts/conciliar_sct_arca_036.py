"""Reconstruye extractos SCT descargados y cruza pagos con WC, sin escrituras SQL.

No transforma compensaciones ni pases entre conceptos en pagos bancarios.
"""
from collections import Counter
from datetime import datetime
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re

from src.features.cajas_efectivo.operaciones import read

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'backups/arca-continuacion-20261025'


def parse(path):
    sections, current = [], None
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    for line in lines:
        header = re.fullmatch(r'(.+) - SALDO: (\(?\$[\d,.]+\)?)', line.strip())
        if header:
            raw = header[2]
            current = {'concepto': header[1], 'saldoDeudorPublicado': D(raw.strip('()$').replace(',', '')) * (-1 if '(' in raw else 1), 'movimientos': [], 'incompleto': False}
            sections.append(current)
            continue
        if current is None:
            continue
        pagination = re.search(r'Mostrando registros del (\d+) al (\d+) de un total de (\d+)', line)
        if pagination and (int(pagination[1]) != 1 or int(pagination[2]) != int(pagination[3])):
            current['incompleto'] = True
        fields = line.split('\t')
        if len(fields) < 5 or not re.fullmatch(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}', fields[0]):
            continue
        def money(s):
            return D(s.strip().replace(',', '') or '0')
        current['movimientos'].append({'fechaOperacion': datetime.strptime(fields[0], '%d/%m/%Y %H:%M').isoformat(),
                                      'fechaRegistracion': datetime.strptime(fields[1], '%d/%m/%Y %H:%M').isoformat(),
                                      'detalle': fields[2], 'debe': money(fields[3]), 'haber': money(fields[4])})
    if not sections:
        raise ValueError(f'Extracto sin conceptos: {path.name}')
    for section in sections:
        section['saldoDeudorCalculado'] = sum((m['debe'] - m['haber'] for m in section['movimientos']), D(0))
        section['diferencia'] = section['saldoDeudorCalculado'] - section['saldoDeudorPublicado']
        section['verificado'] = not section['incompleto'] and section['diferencia'] == 0
    return {'archivo': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'conceptos': sections}


def run():
    extracts = [parse(p) for p in sorted(SOURCE.glob('SCT-*-movimientos.txt'))]
    bank = read("SELECT Fecha,Origen,IdOrigen,Deuda,Credito,[Nro Documento] numero FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto=119 AND Fecha>=? AND Fecha<? AND Origen IN ('Galicia','Banco Nacion') ORDER BY Fecha,Origen,IdOrigen", ('2024-01-01', '2026-10-01'))
    for extract in extracts:
        for section in extract['conceptos']:
            for mov in section['movimientos']:
                if mov['detalle'] not in ('Pago de Anticipo', 'Pago Efectuado'):
                    continue
                matches = [b for b in bank if str(b['Fecha'])[:10] == mov['fechaOperacion'][:10] and D(str(b['Credito'])) == mov['haber'] and not b['Deuda']]
                mov['candidatosBancoMismoDiaImporte'] = matches
                mov['criterio'] = 'Candidatos; confirmar VEP. Un débito puede agrupar capital/intereses u otros impuestos.'
    incomplete = [{'archivo': e['archivo'], 'concepto': s['concepto'], 'diferencia': s['diferencia'], 'paginadoIncompleto': s['incompleto']} for e in extracts for s in e['conceptos'] if not s['verificado']]
    result = {'soloLectura': True, 'corteFinanciero': '2026-09-30', 'consultaSCT': '2026-10-25',
              'advertencia': 'Las fechas de octubre son posteriores al corte. No sumar cuentas anuales, anticipos y sus pases internos como nuevos gastos/pagos.',
              'extractos': extracts, 'conceptosPorRevisar': incomplete,
              'resumen': {'extractos': len(extracts), 'conceptos': sum(len(e['conceptos']) for e in extracts), 'noVerificados': len(incomplete)}}
    (SOURCE / 'sct-reconstruccion-cruce-wc.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'resumen': result['resumen'], 'porRevisar': incomplete}, default=str, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    run()
