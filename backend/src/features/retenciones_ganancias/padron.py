"""Padrón público de condición tributaria de ARCA (sin login ni captcha), filtrado a los CUIT de los contactos.

Registro de ancho fijo: CUIT 1-11, denominación 12-41, Ganancias 42-43, IVA 44-45, monotributo 46-47, empleador 49.
"""
import io
import re
import tempfile
import zipfile
from datetime import date

import requests

from src.db.connection import execute_write_transaction, fetch_all

URL = 'https://www.afip.gob.ar/genericos/cInscripcion/archivos/apellidoNombreDenominacion.zip'


def cuits_contactos() -> set[str]:
    rows = fetch_all('SELECT [CUIT/CUIL] c FROM dbo.Contactos WHERE [CUIT/CUIL] IS NOT NULL', ())
    return {d for d in (re.sub(r'\D', '', str(r['c'])) for r in rows) if len(d) == 11}


def leer(lineas, buscados: set[str]) -> list[tuple]:
    out = []
    for linea in lineas:
        cuit = linea[:11]
        if cuit in buscados:
            g = lambda a, b: linea[a:b].strip() or None
            out.append((cuit, g(11, 41), g(41, 43), g(43, 45), g(45, 47), g(48, 49)))
    return out


def actualizar() -> dict:
    buscados = cuits_contactos()
    with tempfile.TemporaryFile() as tmp:
        with requests.get(URL, stream=True, timeout=120, headers={'User-Agent': 'Mozilla/5.0'}) as r:
            r.raise_for_status()
            for chunk in r.iter_content(1 << 20):
                tmp.write(chunk)
        tmp.seek(0)
        with zipfile.ZipFile(tmp) as z:
            nombre = max(z.namelist(), key=lambda n: z.getinfo(n).file_size)
            with z.open(nombre) as f:
                filas = leer(io.TextIOWrapper(f, encoding='latin-1'), buscados)
    hoy = date.today()
    marcas = ','.join('?' * len(buscados))
    stmts = [(f'DELETE FROM dbo.RetencionesGanancias_Padron WHERE CUIT IN ({marcas})', tuple(buscados))] if buscados else []
    stmts += [('INSERT INTO dbo.RetencionesGanancias_Padron (CUIT,Denominacion,Ganancias,IVA,Monotributo,Empleador,Actualizado) '
               'VALUES (?,?,?,?,?,?,?)', (*fila, hoy)) for fila in filas]
    if stmts:
        execute_write_transaction(stmts)
    return {'contactosConCuit': len(buscados), 'encontrados': len(filas), 'actualizado': hoy}
