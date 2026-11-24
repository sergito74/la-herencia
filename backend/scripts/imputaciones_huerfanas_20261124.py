"""Da de baja (Estado 'Reemplazada', quedan como historia) las imputaciones que apuntan a renglones de factura borrados
al editar la compra (24/11/2026): Autopistas del Sol 0840-00979484 (dos versiones anteriores de sus 4 renglones, costo
contado tres veces) y El Luchador 0011-00005428 (renglón viejo de $355.672,91; la compra es anterior a la imputación
automática y se costea por rubro/destino). Re-corrible. Uso (desde backend/): python -m scripts.imputaciones_huerfanas_20261124 [--aplicar]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.connection import execute_write, fetch_all  # noqa: E402
from scripts.aplicar_vinculos_remitos import BACKUPS  # noqa: E402

FILTRO = ("FROM dbo.ImputacionPropuestas p WHERE p.Origen <> 'Contratista' AND p.Estado <> 'Reemplazada' "
          "AND NOT EXISTS (SELECT 1 FROM dbo.Det_Compras d WHERE d.IdDetalleCompra = p.IdDetalleCompra)")


def main():
    filas = fetch_all(f"SELECT p.* {FILTRO}")
    print(f"Imputaciones de renglones borrados que todavía suman: {len(filas)} "
          f"(${sum(float(f['Importe'] or 0) for f in filas):,.2f})")
    if "--aplicar" not in sys.argv:
        print("Simulación (usar --aplicar)")
        return
    resp = BACKUPS / f"imputaciones-huerfanas-antes-{datetime.now():%Y%m%d-%H%M%S}.json"
    resp.write_text(json.dumps(filas, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    n = execute_write(f"UPDATE p SET p.Estado = 'Reemplazada' {FILTRO}")
    print(f"Dadas de baja: {n}. Respaldo: {resp}")


if __name__ == "__main__":
    main()
