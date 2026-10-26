"""Importación documental SCT a WC; no genera movimientos financieros.

--aplicar requiere respaldo verificado e invariantes; inspección por defecto.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

from scripts.conciliar_sct_arca_036 import run as reconstruir, SOURCE
from scripts.vincular_tres_pagos_condominio_036 import control
from src.db.connection import reconciliation_transaction, _reconciliation_connection
from src.features.cajas_efectivo.operaciones import read
from src.features.cuentas_corrientes.arca_documentos import RAIZ, verificar_archivo
from src.features.vinculos.backup import backup_verificado

DDL = """IF OBJECT_ID('dbo.ArcaSctExtractos','U') IS NULL
CREATE TABLE dbo.ArcaSctExtractos (
 IdExtracto int IDENTITY PRIMARY KEY,
 Impuesto varchar(20) NOT NULL CHECK(Impuesto IN ('GANANCIAS','SICORE','IVA')),
 Periodo varchar(8) NOT NULL, FechaConsulta datetime2 NOT NULL,
 Fuente nvarchar(200) NOT NULL, TextoSha256 char(64) NOT NULL UNIQUE,
 Texto nvarchar(max) NOT NULL, Contenido nvarchar(max) NOT NULL CHECK(ISJSON(Contenido)=1),
 Incompleto bit NOT NULL, PdfRuta nvarchar(1000) NOT NULL, PdfSha256 char(64) NOT NULL,
 Usuario nvarchar(100) NOT NULL, FechaAlta datetime2 NOT NULL DEFAULT SYSDATETIME()
);"""


def run(apply=False):
    report = reconstruir()
    exists = read("SELECT OBJECT_ID('dbo.ArcaSctExtractos','U') id")[0]['id']
    imported = {r['sha'] for r in read('SELECT TextoSha256 sha FROM dbo.ArcaSctExtractos')} if exists else set()
    plan = []
    for extract in report['extractos']:
        if extract['sha256'] in imported:
            continue
        name = extract['archivo']
        text = (SOURCE / name).read_text(encoding='utf-8-sig')
        period = re.search(r'PERÍODO\s*\n(\d{8})', text)
        consulted = re.search(r'FECHA DE CONSULTA\s*\n(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})', text)
        if not period or not consulted:
            raise ValueError(f'Faltan metadatos SCT: {name}')
        pdf = SOURCE / name.replace('.txt', '-copia.pdf')
        pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        target = RAIZ / 'SCT' / pdf.name
        impuesto = name.split('-')[1]
        plan.append({'fuente': name, 'sha': extract['sha256'], 'texto': text, 'impuesto': impuesto,
                     'periodo': period[1], 'consulta': datetime.strptime(consulted[1], '%d/%m/%Y %H:%M:%S').isoformat(),
                     'conceptos': extract['conceptos'], 'incompleto': any(not s['verificado'] for s in extract['conceptos']),
                     'pdf': str(pdf), 'ruta': str(target), 'pdfSha': pdf_sha})
    result = {'estado': 'inspeccion', 'pendientes': len(plan), 'sinCambiosFinancieros': True}
    if not apply or not plan:
        return result
    backup = backup_verificado('arca-sct-fiscal-036')
    for p in plan:
        target = Path(p['ruta'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != p['pdfSha']:
            raise ValueError('Conflicto documental SCT')
        if not target.exists():
            shutil.copy2(p['pdf'], target)
        verificar_archivo(target, p['pdfSha'])
    with reconciliation_transaction():
        cur = _reconciliation_connection.get().cursor()
        before = control(cur)
        cur.execute(DDL)
        ids = []
        for p in plan:
            if cur.execute('SELECT 1 FROM dbo.ArcaSctExtractos WITH (UPDLOCK,HOLDLOCK) WHERE TextoSha256=?', p['sha']).fetchone():
                raise ValueError('Importación SCT concurrente; repetir inspección')
            ident = cur.execute('INSERT INTO dbo.ArcaSctExtractos (Impuesto,Periodo,FechaConsulta,Fuente,TextoSha256,Texto,Contenido,Incompleto,PdfRuta,PdfSha256,Usuario) OUTPUT INSERTED.IdExtracto VALUES (?,?,?,?,?,?,?,?,?,?,?)', p['impuesto'], p['periodo'], p['consulta'], p['fuente'], p['sha'], p['texto'], json.dumps(p['conceptos'], default=str, ensure_ascii=False), p['incompleto'], p['ruta'], p['pdfSha'], 'Codex036').fetchone()[0]
            ids.append(ident)
        if control(cur) != before:
            raise ValueError('La importación documental cambió saldos')
        result.update(estado='aplicado', ids=ids, respaldo=backup)
        cur.execute("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) VALUES ('arca-sct-fiscal-036','aplicada',?,'Codex036',SYSDATETIME(),'Codex036',SYSDATETIME(),?,?)", json.dumps(result, ensure_ascii=False), backup, f'{len(ids)} extractos SCT documentales. Sin efectos en el mayor, cajas ni socios.')
    (SOURCE / 'sct-importacion-aplicada.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    print(json.dumps(run(parser.parse_args().aplicar), ensure_ascii=False, indent=2))
