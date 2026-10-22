"""039: carga diaria del índice INMAG en WC (tarea programada "LaHerencia - Indice INMAG").

Uso: python -m scripts.indice_inmag [--desde AAAA-MM-DD] [--liquidar]
Sin --desde recupera los últimos 10 días (feriados, PC apagada). Re-corrible sin duplicar.
--liquidar: del día 1 al 10 de cada mes prepara (sin duplicar) los borradores de liquidación del mes vencido;
el margen cubre la PC apagada el día 1.
"""
import argparse
import json
from datetime import date

from src.db.connection import _assert_target_is_wc
from src.features.pastaje import inmag

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", type=date.fromisoformat)
    p.add_argument("--liquidar", action="store_true")
    a = p.parse_args()
    _assert_target_is_wc()
    res = inmag.actualizar(a.desde)
    if a.liquidar and date.today().day <= 10:
        from src.features.pastaje import service
        hoy = date.today()
        anterior = date(hoy.year - (hoy.month == 1), 12 if hoy.month == 1 else hoy.month - 1, 1)
        res["liquidaciones"] = service.generar_mes(anterior, "tarea programada")
    print(json.dumps(res, ensure_ascii=False, default=str))
