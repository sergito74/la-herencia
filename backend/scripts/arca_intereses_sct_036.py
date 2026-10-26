"""Registra cuatro intereses explícitos del SCT, sin repetir pagos ni capital.

Inspección por defecto. --aplicar: respaldo, transacción, invariantes y auditoría.
"""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import shutil

from scripts.conciliar_sct_arca_036 import parse, SOURCE
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes import arca
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado

RULE = 'arca-intereses-sct-4-036'
ITEMS = [
    ('SICORE-2025-07', '2025-07-22', '471.21', 'sicore-ganancias'),
    ('SICORE-2025-10', '2025-10-22', '54.58', 'sicore-ganancias'),
    ('SICORE-2026-06', '2026-06-23', '610.69', 'sicore-ganancias'),
    ('GANANCIAS-2026-anticipo-8', '2026-04-14', '320.06', 'ganancias'),
]


def run(apply=False):
    applied = read("SELECT Parametros FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,))
    if applied:
        return {'estado': 'ya_aplicado_sin_escrituras', 'aplicacion': json.loads(applied[0]['Parametros'])}
    plan = []
    for key, date, amount, account in ITEMS:
        name = f'SCT-{key}-movimientos'
        section = next(s for s in parse(SOURCE / f'{name}.txt')['conceptos'] if s['concepto'] == 'INTERESES RESARCITORIOS')
        matches = [m for m in section['movimientos'] if m['fechaOperacion'][:10] == date and m['debe'] == D(amount) and m['detalle'] == 'Liquidación de Intereses Resarcitorios']
        if len(matches) != 1 or not section['verificado']:
            raise ValueError(f'Interés sin evidencia completa: {key}')
        pdf = SOURCE / f'{name}-copia.pdf'
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        target = RAIZ / 'Intereses' / pdf.name
        plan.append({'numero': f'SCT-INT-{key}', 'fecha': date, 'importe': D(amount), 'subcuenta': account,
                     'pdf': str(pdf), 'destino': str(target), 'sha256': sha, 'saldoFiscalInteres': section['saldoDeudorPublicado']})
    total = sum((p['importe'] for p in plan), D(0))
    result = {'estado': 'inspeccion', 'intereses': plan, 'importe': total}
    if not apply:
        return result
    backup = backup_verificado('arca-intereses-sct-4-036')
    for p in plan:
        target = Path(p['destino'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != p['sha256']:
            raise ValueError('Conflicto documental')
        if not target.exists():
            shutil.copy2(p['pdf'], target)
        verificar_archivo(target, p['sha256'])
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        if cur.execute("SELECT 1 FROM dbo.AuditoriaCorrecciones WITH (UPDLOCK,HOLDLOCK) WHERE Regla=? AND Estado='aplicada'", RULE).fetchone():
            raise ValueError('Aplicación concurrente')
        # Revisar todo el inventario de intereses para no duplicar un registro sin nuestro número.
        existing = read('SELECT * FROM dbo.Impuestos WITH (UPDLOCK,HOLDLOCK) WHERE IdOrganismo=119 AND IdTipoImpuesto=23')
        before = control(cur)
        for p in plan:
            if any(i['Numero de documento'] == p['numero'] or (str(i['Fecha'])[:10] == p['fecha'] and D(str(i['Importe'])) == p['importe']) for i in existing):
                raise ValueError(f"Interés ya existente: {p['numero']}")
            ident = cur.execute('INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto VALUES (?,119,23,?,?,?,?)', p['fecha'], p['numero'].replace('SCT-INT-', ''), p['numero'], str(p['importe']), p['destino']).fetchone()[0]
            p['idImpuesto'] = ident
            arca.guardar('Impuestos', ident, 0, [{'subcuenta': p['subcuenta'], 'deuda': p['importe'], 'credito': D(0)}], f"Interés resarcitorio según {p['numero']}; no es capital ni un pago nuevo.", 'Codex036')
            period = p['numero'].replace('SCT-INT-SICORE-', '') if p['subcuenta'] == 'sicore-ganancias' else '2026'
            cur.execute("INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) VALUES ('Impuestos',?,'SCT intereses (copia portal)',?,?,?,?,0,'Codex036')", ident, period, p['numero'], p['destino'], p['sha256'])
        after = control(cur)
        expected = dict(before['cuentas'])
        expected[119] -= total
        if dict(after['cuentas']) != expected or before['cajas'] != after['cajas'] or before['socios'] != after['socios']:
            raise ValueError('Efecto no previsto')
        result.update(estado='aplicado', respaldo=backup, saldoAntes=dict(before['cuentas'])[119], saldoDespues=dict(after['cuentas'])[119])
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES (?,'aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", RULE, json.dumps(result, default=str, ensure_ascii=False), backup, 'Tres intereses SICORE pendientes por 1136,48 y Ganancias anticipo8 pagado por 320,06. Sin pagos nuevos.')
    (SOURCE / 'intereses-sct-aplicados.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
