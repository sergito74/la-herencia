"""Pasada diaria de la imputación progresiva (050 T026).

1. Vínculo automático remito↔factura de las compras en alcance con insumos.
2. Recálculo de cada renglón en alcance (insumos: usos + stock; una sola vez: directo). Solo guarda una
   corrida nueva si cambió algo.
3. Los posibles duplicados (capa de factura + remito sin vincular del mismo proveedor y producto) quedan
   Pendientes en la cola, nunca se aprueban solos.

Sin renglones en alcance (criterio sin activar) no hace nada. Solo WC.
Uso (desde backend/):  python -m scripts.imputacion_diaria_050
"""

from __future__ import annotations

import logging
from collections import Counter

from src.db.connection import _assert_target_is_wc
from src.features.imputacion import progresivo
from src.features.remitos import vinculo_auto

logging.basicConfig(filename="logs/imputacion_diaria_050.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("imputacion_diaria_050")


def main() -> Counter:
    _assert_target_is_wc()
    renglones = progresivo.renglones_en_alcance()
    resumen: Counter = Counter()
    for id_compra in sorted({r["idCompra"] for r in renglones if r["destino"] == "CultivoStock"}):
        try:
            v = vinculo_auto.vincular_por_compra(id_compra)
            resumen["vinculados"] += v["vinculados"]
            resumen["vinculoARevisar"] += v["revisar"]
        except Exception:  # noqa: BLE001
            _log.exception("Vínculo de la compra %s", id_compra)
            resumen["errores"] += 1
    for r in renglones:
        try:
            resumen[progresivo.imputar_renglon(r["id"])["accion"]] += 1
        except Exception:  # noqa: BLE001
            _log.exception("Imputación del renglón %s", r["id"])
            resumen["errores"] += 1
    _log.info("Pasada diaria: %s renglones · %s", len(renglones), dict(resumen))
    return resumen


if __name__ == "__main__":
    print(dict(main()))
