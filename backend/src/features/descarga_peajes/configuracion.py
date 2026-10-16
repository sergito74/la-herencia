"""Estado de la configuración de la descarga de peajes (037, FR-013/014/015).

Las credenciales viven en el Administrador de credenciales de Windows,
servicio `LaHerencia-Peajes`: por cada cuenta, la entrada `<cuenta>` (la
contraseña) y `<cuenta>-usuario`. Las carga el instalador
(`scripts/instalar_descarga_peajes.ps1`); la aplicación solo consulta si
existen y nunca devuelve sus valores. `credencial()` es el único lugar que
las lee, y solo la usa la descarga.
"""

from __future__ import annotations

import csv
import io
import subprocess
from datetime import datetime

SERVICIO = "LaHerencia-Peajes"
TAREA = "LaHerencia - Descarga peajes"

# Portal (como se muestra) → cuenta en el Administrador de credenciales.
CUENTAS = {"TelepeajePlus": "telepeajeplus", "TelePASE": "telepase", "CEAMSE": "ceamse", "AUBASA": "aubasa"}


class SinCredenciales(Exception):
    pass


def credencial(portal: str) -> tuple[str, str]:
    import keyring

    cuenta = CUENTAS[portal]
    usuario = keyring.get_password(SERVICIO, f"{cuenta}-usuario")
    clave = keyring.get_password(SERVICIO, cuenta)
    if not usuario or not clave:
        raise SinCredenciales(f"Faltan las credenciales de {portal}: hay que correr el instalador.")
    return usuario, clave


def credenciales_configuradas(portal: str) -> bool:
    try:
        credencial(portal)
        return True
    except SinCredenciales:
        return False
    except Exception:  # keyring no instalado o backend de credenciales caído
        return False


def estado_tarea() -> dict:
    """Lee la tarea programada en solo lectura. Nunca falla: si no existe o
    `schtasks` no responde, informa `instalada=False`."""
    vacio = {"instalada": False, "proximaCorrida": None, "ultimoResultado": None}
    try:
        salida = subprocess.run(
            ["schtasks", "/Query", "/TN", TAREA, "/FO", "CSV", "/V"],
            capture_output=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return vacio
    if salida.returncode != 0:
        return vacio
    texto = salida.stdout.decode("cp850", errors="replace")
    filas = list(csv.reader(io.StringIO(texto)))
    if len(filas) < 2:
        return vacio
    encabezado, valores = filas[0], filas[1]
    datos = dict(zip(encabezado, valores))

    def campo(*nombres: str) -> str | None:
        for n in nombres:
            for k, v in datos.items():
                if k.strip().lower() == n.lower():
                    return v.strip()
        return None

    proxima = campo("Next Run Time", "Hora próxima ejecución", "Próxima hora de ejecución")
    return {
        "instalada": True,
        "proximaCorrida": _fecha_iso(proxima),
        "ultimoResultado": campo("Last Result", "Último resultado"),
    }


def _fecha_iso(valor: str | None) -> str | None:
    if not valor:
        return None
    for formato in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(valor, formato).isoformat()
        except ValueError:
            continue
    return None
