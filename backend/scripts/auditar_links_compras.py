"""Relevamiento de los links "Documento Original" de Compras (21/10/2026, pedido de Sergio: "la mayoría están rotos").

Para cada compra con documento:
1. cómo lo resuelve hoy la aplicación (frontend/src/lib/documentoLocal.ts: primer tramo antes de '#'; relativa con '\' ->
   BASE_COMPRAS + ruta sin '..\' inicial) y si el archivo existe;
2. si no existe, busca la ubicación real: rutas de Access relativas a la carpeta de la base (Documents\\La Herencia\\<x>):
   '..\\Comprobantes\\...' -> Documents\\La Herencia\\Comprobantes, '..\\..\\..\\Dropbox\\...' -> C:\\Users\\Sergio\\Dropbox\\...;
   '%20' y similares decodificados; segundo tramo del hipervínculo; y por último el nombre de archivo en Dropbox\\...\\Compras y
   Documents\\La Herencia\\Comprobantes (solo si hay un único archivo con ese nombre).
Uso: python -m scripts.auditar_links_compras [--aplicar]  (--aplicar guarda la ruta completa encontrada, respaldo verificado).
Salida: resumen + CSV en backups/links-compras-<fecha>.csv. Idempotente.
"""
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction

HOME = Path(r'C:\Users\Sergio')
BASE_COMPRAS = HOME / 'Dropbox' / 'Giamigli de Bolivar SA' / 'Compras'
LA_HERENCIA = HOME / 'Documents' / 'La Herencia'
COMPROBANTES = LA_HERENCIA / 'Comprobantes'
RAICES = [BASE_COMPRAS, COMPROBANTES]


def ruta_app(v: str) -> str:
    """Réplica de normalizarDocumentoOriginal (frontend)."""
    v = v.strip().strip('"').split('#')[0]
    if len(v) > 2 and v[1] == ':' or v.startswith('\\\\') or '://' in v:
        return v
    if '\\' not in v:
        return v
    return str(BASE_COMPRAS) + '\\' + (v[3:] if v.startswith('..\\') else v)


def candidatos(valor: str):
    tramos = [t for t in valor.split('#') if t.strip()]
    for t in tramos:
        t = unquote(t.strip().strip('"')).replace('/', '\\')
        if t.lower().startswith('file:'):
            t = t[5:].lstrip('\\')
        if len(t) > 2 and t[1] == ':':
            yield Path(t)
            continue
        partes = t.split('\\')
        subidas = 0
        while partes and partes[0] == '..':
            partes.pop(0); subidas += 1
        resto = '\\'.join(partes)
        if subidas >= 3:
            yield HOME / resto                       # ..\..\..\Dropbox\... (base de Access en Documents\La Herencia\<x>\<y>)
        if subidas >= 1:
            yield LA_HERENCIA / resto                # ..\Comprobantes\...
        yield BASE_COMPRAS / resto                   # 04 2025 - 03 2026\x.pdf
        yield HOME / 'Dropbox' / 'Giamigli de Bolivar SA' / resto
        yield COMPROBANTES / resto


def indice_por_nombre():
    idx = defaultdict(list)
    for raiz in RAICES:
        for dirpath, _, files in os.walk(raiz):
            for f in files:
                idx[f.lower()].append(Path(dirpath) / f)
    return idx


def main():
    _assert_target_is_wc()
    aplicar = '--aplicar' in sys.argv
    filas = fetch_all("SELECT IdDeuda i, Fecha f, IdContacto c, [Nro Documento] n, [Documento Original] d FROM dbo.Compras "
                      "WHERE [Documento Original] IS NOT NULL AND LTRIM(RTRIM([Documento Original])) <> ''")
    idx = indice_por_nombre()
    estado, salida, arreglos = Counter(), [], []
    for r in filas:
        v = r['d']
        actual = ruta_app(v)
        if Path(actual).is_file():
            estado['ok'] += 1
            continue
        real = next((p for p in candidatos(v) if p.is_file()), None)
        como = 'ruta'
        if real is None:
            nombre = unquote(v.split('#')[0]).replace('/', '\\').split('\\')[-1].strip().lower()
            hits = idx.get(nombre, [])
            if len(hits) == 1:
                real, como = hits[0], 'nombre'
            elif len(hits) > 1:
                como = f'ambiguo ({len(hits)})'
        clave = 'roto-arreglable-' + como if real else ('roto-' + como if como.startswith('ambiguo') else 'roto-sin-archivo')
        estado[clave] += 1
        salida.append((r['i'], str(r['f'])[:10], r['c'], r['n'], v, actual, str(real or ''), clave))
        if real:
            arreglos.append((str(real), r['i']))
    print(len(filas), 'compras con documento:', dict(estado))
    out = Path(r'C:\dev\LaHerencia\backups') / f'links-compras-{date.today():%Y%m%d}.csv'
    with open(out, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['IdDeuda', 'Fecha', 'IdContacto', 'Nro', 'DocumentoOriginal', 'RutaQueAbreHoy', 'ArchivoEncontrado', 'Estado'])
        w.writerows(salida)
    print('detalle:', out)
    if aplicar and arreglos:
        from src.features.vinculos.backup import backup_verificado
        print(backup_verificado('links-compras'))
        with reconciliation_transaction():
            execute_write_transaction([('UPDATE dbo.Compras SET [Documento Original]=? WHERE IdDeuda=?', a) for a in arreglos])
        print(len(arreglos), 'links corregidos (ruta completa)')


if __name__ == '__main__': main()
