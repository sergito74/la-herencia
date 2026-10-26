"""Determinación anual SCT 2026. Inspección por defecto; --aplicar escribe WC.

No reproduce como pagos los créditos computados: requieren cruce con sus orígenes.
"""
import argparse
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path
import shutil

from src.db.connection import _reconciliation_connection, reconciliation_transaction
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado
from scripts.vincular_tres_pagos_condominio_036 import control

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'backups/arca-continuacion-20261025'
NAME = 'SCT-GANANCIAS-2026-DDJJ-movimientos-copia.pdf'
RULE = 'arca-ganancias-ddjj-2026-036'
AMOUNT = D('1353097.06')
USER = 'Codex036'


def existentes(cur):
    return cur.execute(
        "SELECT IdImpuesto FROM dbo.Impuestos WITH (UPDLOCK,HOLDLOCK) "
        "WHERE IdOrganismo=119 AND IdTipoImpuesto=3 "
        "AND ([Periodo liquidado] LIKE ? OR [Numero de documento]=?)",
        '%2026%', 'SCT-GANANCIAS-2026-DDJJ',
    ).fetchall()


def run(aplicar=False):
    applied = read("SELECT Parametros FROM dbo.AuditoriaCorrecciones WHERE Regla=? AND Estado='aplicada'", (RULE,))
    if applied:
        return {'estado': 'ya_aplicado_sin_escrituras', 'aplicacion': json.loads(applied[0]['Parametros'])}
    source = OUT / NAME
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    target = RAIZ / 'Ganancias' / '2026' / NAME
    result = {'estado': 'inspeccion', 'importe': AMOUNT, 'fecha': '2026-08-13',
              'periodo': '2026', 'fuente': str(source), 'sha256': sha,
              'destino': str(target), 'creditosNuevos': 0}
    if not aplicar:
        return result
    backup = backup_verificado('arca-ganancias-ddjj-2026-036')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
        raise ValueError('El destino tiene otra huella')
    if not target.exists():
        shutil.copy2(source, target)
    verificar_archivo(target, sha)
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        if cur.execute('SELECT DB_NAME()').fetchone()[0] != 'WC':
            raise ValueError('Solo WC')
        if cur.execute("SELECT 1 FROM dbo.AuditoriaCorrecciones WITH (UPDLOCK,HOLDLOCK) WHERE Regla=? AND Estado='aplicada'", RULE).fetchone():
            raise ValueError('La regla fue aplicada concurrentemente')
        if existentes(cur):
            raise ValueError('Ya hay una obligación Ganancias 2026; revisar antes de insertar')
        before = control(cur)
        ident = cur.execute(
            'INSERT INTO dbo.Impuestos (Fecha,IdOrganismo,IdTipoImpuesto,[Periodo liquidado],'
            '[Numero de documento],Importe,[Documento Original]) OUTPUT INSERTED.IdImpuesto '
            'VALUES (?,119,3,?,?,?,?)',
            '2026-08-13', '2026', 'SCT-GANANCIAS-2026-DDJJ', str(AMOUNT), str(target),
        ).fetchone()[0]
        cur.execute(
            'INSERT INTO dbo.ArcaDocumentos (Origen,IdOrigen,Tipo,Periodo,Numero,Ruta,Sha256,EsOriginal,Usuario) '
            "VALUES ('Impuestos',?,'SCT DDJJ movimientos (copia portal)','2026',?,?,?,?,?)",
            ident, 'SCT-GANANCIAS-2026-DDJJ', str(target), sha, 0, USER,
        )
        after = control(cur)
        expected = dict(before['cuentas'])
        expected[119] -= AMOUNT
        if dict(after['cuentas']) != expected or before['cajas'] != after['cajas'] or before['socios'] != after['socios']:
            raise ValueError('Efecto fuera de la obligación anual prevista')
        result.update(estado='aplicado', idImpuesto=ident, respaldo=backup,
                      saldoAntes=dict(before['cuentas'])[119], saldoDespues=dict(after['cuentas'])[119])
        cur.execute(
            'INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) '
            "VALUES (?,'aplicada',?,?,SYSDATETIME(),?,SYSDATETIME(),?,?)",
            RULE, json.dumps(result, default=str, ensure_ascii=False), USER, USER, backup,
            'Determinación anual Ganancias 2026 según SCT; copia PDF verificada. Créditos y anticipos pendientes de cruce, sin nuevos pagos.',
        )
    (OUT / 'ganancias-ddjj-2026-aplicado.json').write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), default=str, ensure_ascii=False, indent=2))
