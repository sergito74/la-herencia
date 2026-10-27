"""043 T031 — Activa el conector de De Campo a Campo en su cuenta de la bóveda (portal 21), solo en `WC`.

Uso (desde backend/):
    python -m scripts.activar_decampoacampo_043 --verificar   # no escribe
    python -m scripts.activar_decampoacampo_043               # pone CodigoConector = 'decampoacampo'
    python -m scripts.activar_decampoacampo_043 --revertir    # lo vuelve a NULL
"""

from __future__ import annotations

import sys

from src.db.connection import execute_write, fetch_one

ID_PORTAL = 21


def main(argv: list[str]) -> None:
    fila = fetch_one("SELECT Nombre AS nombre, CodigoConector AS codigo FROM dbo.Portales WHERE IdPortal = ?", (ID_PORTAL,))
    if not fila or "Campo" not in fila["nombre"]:
        raise SystemExit(f"El portal {ID_PORTAL} no es De Campo a Campo: {fila}")
    print(f"Portal {ID_PORTAL} {fila['nombre']}: conector actual {fila['codigo']!r}")
    if "--verificar" in argv:
        return
    nuevo = None if "--revertir" in argv else "decampoacampo"
    execute_write("UPDATE dbo.Portales SET CodigoConector = ? WHERE IdPortal = ?", (nuevo, ID_PORTAL))
    print(f"Conector: {nuevo!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
