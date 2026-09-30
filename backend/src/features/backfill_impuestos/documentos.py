"""Inventario local de solo lectura; no altera archivos ni usa OCR."""
from pathlib import Path
from datetime import date
import hashlib, os, re, time, unicodedata
from .diagnostico import digest

# Comprobantes de impuestos cuyo nombre de archivo no menciona al
# organismo sino al impuesto (convención real de las carpetas, 2026-09-30).
ALIAS_EXTRA = {'arba': ['iibb'], 'municipalidaddebolivar': ['tasavial']}


def normal(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))


def compacto(text):
    """Sin espacios ni separadores: "MunicipalidadDeBolivar" y "Municipalidad de Bolívar" coinciden."""
    return re.sub(r'[^a-z0-9]', '', normal(text))


def raices():
    configured = os.environ.get('LA_HERENCIA_BACKFILL_DOCUMENTOS')
    if configured:
        return [Path(p.strip()).resolve() for p in configured.split(';') if p.strip()]
    base = Path.home() / 'Dropbox' / 'Giamigli de Bolivar SA'
    return [base / 'Impuestos', base / 'Compras']


def ruta_guardada(valor, base_relativa):
    """`[Documento Original]` viene en el formato roto heredado de Access
    ("04 2026 - 03 2027\\a.pdf#04 2026 - 03 2027\\a.pdf#", relativo a la
    carpeta de Compras) o como ruta completa entre comillas — mismo criterio
    que `normalizarDocumentoOriginal` del frontend."""
    v = (valor or '').strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1]
    v = v.split('#', 1)[0].strip()
    if not v:
        return None
    p = Path(v)
    if not p.is_absolute():
        if v.startswith('..\\'):
            p = base_relativa.parent / v[3:]
        else:
            p = base_relativa / v
    return os.path.normcase(str(p.resolve()))


def filehash(p, deadline=None):
    h = hashlib.sha256()
    with p.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            if deadline and time.monotonic() > deadline:
                raise TimeoutError('Recorrido incompleto')
            h.update(chunk)
    return h.hexdigest()


def _alias(organismos):
    aliases = {}
    for o in organismos:
        clave = compacto(o['organismo'])
        aliases[o['idOrganismo']] = [clave] + ALIAS_EXTRA.get(clave, [])
    return aliases


def _organismos_del_nombre(nombre, aliases):
    c = compacto(Path(nombre).stem)
    return [i for i, names in aliases.items() if any(a and a in c for a in names)]


def inventario(organismos, usados, roots=None, base_relativa=None):
    roots = raices() if roots is None else roots
    base_relativa = base_relativa or (roots[-1] if roots else Path.cwd())
    end = time.monotonic() + 60
    errors = []
    found = []
    aliases = _alias(organismos)

    paths = {r for r in (ruta_guardada(u, base_relativa) for u in usados) if r}
    # Solo los adjuntos de impuestos (nombre con un organismo) pueden ser
    # copias de un comprobante candidato; hashear los ~6.000 adjuntos de
    # Compras cortaba el recorrido por tiempo.
    used_hashes = set()
    for p in paths:
        if not _organismos_del_nombre(p, aliases):
            continue
        try:
            if Path(p).is_file():
                used_hashes.add(filehash(Path(p), end))
        except OSError:
            errors.append('No se pudo verificar un adjunto existente')

    seen = set()
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            errors.append('Carpeta documental no disponible')
            continue

        def onerror(exc):
            errors.append('Carpeta documental ilegible')

        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
            for name in sorted(files):
                if Path(name).suffix.lower() not in ('.pdf', '.jpg', '.jpeg', '.png'):
                    continue
                matches = _organismos_del_nombre(name, aliases)
                if not matches:
                    continue
                if time.monotonic() > end:
                    errors.append('Límite del recorrido: búsqueda incompleta')
                    break
                path = (Path(folder) / name).resolve()
                key = os.path.normcase(str(path))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    sha = filehash(path, end)
                except (OSError, TimeoutError):
                    errors.append('Archivo ilegible o recorrido incompleto')
                    continue
                match = re.search(r'(?<![0-9])(20[0-9]{2}|19[0-9]{2})[-_ .]?([01][0-9])[-_ .]?([0-3][0-9])(?![0-9])', name)
                fecha = None
                if match:
                    try:
                        fecha = date(*map(int, match.groups())).isoformat()
                    except ValueError:
                        pass
                found.append(dict(archivoId=digest([key, sha]), nombre=name, ruta=str(path), hash=sha,
                                  idOrganismo=matches[0] if len(matches) == 1 else None, fecha=fecha,
                                  usado=key in paths or sha in used_hashes))
            if time.monotonic() > end:
                break

    # Copias físicas de un archivo son una sola evidencia, incluso con nombres distintos.
    by_hash = {}
    for f in found:
        if f['hash'] in by_hash:
            previous = by_hash[f['hash']]
            previous['usado'] = previous['usado'] or f['usado']
            if (previous['idOrganismo'], previous['fecha']) != (f['idOrganismo'], f['fecha']):
                previous['idOrganismo'] = None
        else:
            by_hash[f['hash']] = f
    return dict(items=list(by_hash.values()), completo=not errors, advertencias=sorted(set(errors)))
