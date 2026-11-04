"""Proceso aparte que sincroniza UN portal (04/11/2026).

El backend lo lanza con `python -m src.features.boveda.trabajador <idPortal> <idCorrida> <origen> [usuario]` y lo
vigila: si se cuelga (Playwright o Chrome sin responder) se mata el proceso entero con su navegador, sin dejar
trabado al sistema. El lock del portal lo tiene el backend; acá solo se corre y se cierra la corrida.
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    from src.features.boveda import servicio

    id_portal, id_corrida, origen = int(argv[0]), int(argv[1]), argv[2]
    usuario = argv[3] if len(argv) > 3 and argv[3] else None
    from src.features.boveda import conectores, repository

    conectores._informar = lambda texto: repository.avance(id_corrida, texto)
    servicio.ejecutar(id_portal, origen, usuario, None, id_corrida)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
