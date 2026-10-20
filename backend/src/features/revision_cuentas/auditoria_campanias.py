"""Clasificación de inconsistencias de campaña, sin inferir ni corregir datos."""
from collections import defaultdict


def normalizar(value):
    return str(value or '').strip().casefold()


def clasificar(texto, identificador, catalogo):
    por_id = {r['IdCampaña']: r['Campaña'] for r in catalogo}
    por_texto = defaultdict(list)
    for r in catalogo:
        por_texto[normalizar(r['Campaña'])].append(r['IdCampaña'])
    nombre = normalizar(texto)
    candidatos = por_texto.get(nombre, []) if nombre else []
    if identificador is not None and identificador not in por_id:
        return 'identificador_inexistente', candidatos
    if not nombre:
        return ('sin_texto' if identificador is not None else 'sin_asignacion'), []
    if not candidatos:
        return 'texto_desconocido', []
    if len(candidatos) > 1:
        return 'texto_ambiguo', candidatos
    if identificador is None:
        return ('no_aplica_sin_vinculo' if nombre == 'no aplica' else 'falta_vinculo'), candidatos
    if identificador != candidatos[0]:
        return 'texto_vinculo_discordantes', candidatos
    return None, candidatos
