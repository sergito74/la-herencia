"""042 — Clave maestra de la bóveda (research.md R1).

Uso (desde backend/):
    python -m scripts.boveda_clave generar                 # crea la clave si no existe (no la pisa)
    python -m scripts.boveda_clave exportar D:\\respaldo.lhkey
    python -m scripts.boveda_clave importar D:\\respaldo.lhkey

`exportar` envuelve la clave con una frase de recuperación (scrypt + AES-GCM)
que se pide por consola y no se muestra. El archivo no puede quedar dentro
del repositorio ni de Dropbox. Sin la clave ni el archivo, las contraseñas de
la bóveda se vuelven a cargar a mano; el resto de la bóveda no se pierde.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from base64 import b64decode, b64encode
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from src.features.boveda import cifrado

REPO = Path(__file__).resolve().parents[2]
_N, _R, _P = 2**17, 8, 1


def _derivar(frase: str, sal: bytes, n: int = _N) -> bytes:
    return Scrypt(salt=sal, length=32, n=n, r=_R, p=_P).derive(frase.encode("utf-8"))


def _ruta_permitida(ruta: Path) -> Path:
    ruta = ruta.resolve()
    for prohibida in (REPO, Path.home() / "Dropbox"):
        if ruta.is_relative_to(prohibida.resolve()):
            raise SystemExit(f"No se guarda la clave dentro de {prohibida}.")
    return ruta


def generar() -> None:
    try:
        cifrado.clave_maestra(crear=False)
        print("La clave maestra ya existe; no se modificó.")
    except cifrado.ClaveMaestraNoDisponible:
        cifrado.clave_maestra(crear=True)
        print("Clave maestra creada en el Administrador de credenciales de Windows.")


def exportar(destino: str) -> None:
    ruta = _ruta_permitida(Path(destino))
    if ruta.exists():
        raise SystemExit(f"{ruta} ya existe: elegir otro nombre (no se pisa un respaldo).")
    frase = getpass.getpass("Frase de recuperación: ")
    if len(frase) < 12 or frase != getpass.getpass("Repetir frase: "):
        raise SystemExit("La frase debe tener al menos 12 caracteres y coincidir.")
    sal, nonce = os.urandom(16), os.urandom(12)
    envuelta = AESGCM(_derivar(frase, sal)).encrypt(nonce, cifrado.clave_maestra(crear=False), b"lh-boveda")
    ruta.write_text(json.dumps({"v": 1, "n": _N, "sal": b64encode(sal).decode(), "nonce": b64encode(nonce).decode(),
                                "clave": b64encode(envuelta).decode()}), encoding="utf-8")
    print(f"Clave exportada a {ruta}. Guardar el archivo y la frase por separado.")


def importar(origen: str) -> None:
    datos = json.loads(Path(origen).read_text(encoding="utf-8"))
    frase = getpass.getpass("Frase de recuperación: ")
    clave = AESGCM(_derivar(frase, b64decode(datos["sal"]), datos.get("n", _N))).decrypt(
        b64decode(datos["nonce"]), b64decode(datos["clave"]), b"lh-boveda")
    try:
        if cifrado.clave_maestra(crear=False) != clave:
            raise SystemExit("Este equipo ya tiene otra clave maestra; no se reemplaza.")
        print("La clave ya estaba instalada.")
    except cifrado.ClaveMaestraNoDisponible:
        cifrado.guardar_clave_maestra(clave)
        print("Clave maestra instalada.")


def main(argv: list[str]) -> None:
    if argv[:1] == ["generar"]:
        generar()
    elif argv[:1] == ["exportar"] and len(argv) == 2:
        exportar(argv[1])
    elif argv[:1] == ["importar"] and len(argv) == 2:
        importar(argv[1])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
