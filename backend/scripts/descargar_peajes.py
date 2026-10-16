"""Descarga y carga automática de comprobantes de peajes — entrada por línea de
comandos (037). La lógica vive en `src/features/descarga_peajes/`; esta es la
misma ejecución que el botón "Descargar ahora" de Compras › Descarga de peajes.

Portales (solo lectura/descarga, autorizado por Sergio el 2026-10-16):
TelepeajePlus, TelePASE, CEAMSE y AUBASA. Credenciales en el Administrador de
credenciales de Windows (servicio "LaHerencia-Peajes"), cargadas por
`scripts/instalar_descarga_peajes.ps1`, que también programa esta ejecución
semanal.

Uso (desde backend/, con el Python de .venv):
    python -m scripts.descargar_peajes                    # origen semanal
    python -m scripts.descargar_peajes --origen manual
    python -m scripts.descargar_peajes --dry-run          # informa, no escribe nada

Código de salida: 0 terminó (completa o con errores registrados), 2 salteada
(había otra en curso), 1 error general.
"""

from __future__ import annotations

import argparse
import sys

from src.features.descarga_peajes import servicio


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Descarga de comprobantes de peajes")
    parser.add_argument("--origen", choices=("manual", "semanal"), default="semanal")
    parser.add_argument("--dry-run", action="store_true", help="solo informa; no escribe en la base ni en disco")
    args = parser.parse_args(argv)

    resultado = servicio.ejecutar(origen=args.origen, usuario=None, dry_run=args.dry_run)
    for portal, r in resultado["portales"].items():
        print(f"{portal}: {r['estado']} · nuevos {r['nuevos']} · existentes {r['existentes']} · "
              f"cargados {r['cargados']} · pendientes {r['pendientes']}" + (f" · {r['error']}" if r["error"] else ""))
    for item in resultado.get("informe", []):
        print(f"  [simulación] {item['portal']} {item['detalle']} -> {item['archivo']}: {item['estadoCarga']}"
              + (f" ({item['motivo']})" if item.get("motivo") else ""))
    print(f"Ejecución {resultado['idEjecucion'] or '-'}: {resultado['estado']}")
    return resultado["codigo"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
