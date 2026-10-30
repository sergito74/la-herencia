"""Cliente del simulador público RG 830 de ARCA (sin login). Requiere un GET previo por la cookie del firewall."""
import json
from datetime import date

import requests

BASE = 'https://servicioscf.afip.gob.ar/calc-rg830/'
_JSON = {'Content-Type': 'application/json; charset=utf-8'}
_cache: dict = {}


def _sesion() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': BASE})
    s.get(BASE, timeout=20)
    return s


def _post(s, metodo, cuerpo=''):
    r = s.post(BASE + 'default.aspx/' + metodo, data=cuerpo, headers=_JSON, timeout=30)
    r.raise_for_status()
    d = r.json().get('d')
    if d is None:
        raise ConnectionError('El simulador de ARCA no respondió. Probá de nuevo en unos minutos')
    return d


def conceptos() -> list[dict]:
    """Tabla vigente de ARCA (una lectura por día)."""
    if _cache.get('dia') != date.today():
        _cache.update(dia=date.today(), conceptos=_post(_sesion(), 'conceptosalcliente'))
    return _cache['conceptos']


def concepto(cod_regimen: int, inscripto: bool, persona: str) -> dict:
    sit = 'I' if inscripto else 'NI'
    for c in conceptos():
        if c['COD_REGIMEN'] == cod_regimen and c['SITUACION'] == sit and c['TIPO_PERSONA'] in ('', persona):
            return c
    raise LookupError(f'ARCA no tiene el régimen {cod_regimen} para esta situación del proveedor')


def calcular(id_alicuota: int, inscripto: bool, persona: str, base: float, pagos_ant: float, reten_ant: float) -> dict:
    cuerpo = {'vsituacion': inscripto, 'vtipo': persona, 'vimpo_a_pagar': round(base, 2), 'vid_alicuota': str(id_alicuota),
              'vexiste_pago_ant': pagos_ant > 0, 'vcantidadmeses': 1, 'vpago_ant': round(pagos_ant, 2),
              'vreten_ant': round(reten_ant, 2)}
    d = _post(_sesion(), 'CalcularRetencion', json.dumps(cuerpo))
    if d.get('success') != 1:
        raise ValueError('El simulador de ARCA rechazó el cálculo')
    return d
