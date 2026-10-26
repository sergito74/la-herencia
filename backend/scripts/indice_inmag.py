"""039: carga diaria de cotizaciones (INMAG y Dólar BNA) en WC (tarea programada "LaHerencia - Indice INMAG").

Uso: python -m scripts.indice_inmag [--desde AAAA-MM-DD] [--liquidar]
Sin --desde recupera los últimos 10 días (feriados, PC apagada). Re-corrible sin duplicar.
--liquidar: del día 1 al 10 de cada mes prepara (sin duplicar) los borradores de liquidación del mes vencido;
el margen cubre la PC apagada el día 1.
"""
import argparse
import json
from datetime import date, timedelta

from src.db.connection import _assert_target_is_wc
from src.features.pastaje import inmag


def actualizar_dolar(desde=None):
    from scripts.cotizaciones_dolar_novillo import dolar, fetch_all, execute_write_transaction
    ayer_fecha = date.today() - timedelta(days=1)
    ult = fetch_all('SELECT MAX(Fecha) f FROM dbo.[Dolar BNA]')[0]['f']
    d0 = desde or ((ult.date() if hasattr(ult, 'date') else ult) - timedelta(days=10))
    filas = dolar(d0, ayer_fecha)
    existentes = {(r['f'].date() if hasattr(r['f'], 'date') else r['f']): r for r in fetch_all('SELECT Fecha f, Prom_billete p FROM dbo.[Dolar BNA] WHERE Fecha>=?', (d0,))}
    nuevas = [x for x in filas if x[0] not in existentes and x[3]]
    if nuevas:
        execute_write_transaction([('INSERT INTO dbo.[Dolar BNA] (Fecha,Comp_billete,Vend_billete,Prom_billete,Comp_Divisa,Vend_Divisa,Prom_Divisa) VALUES (?,?,?,?,?,?,?)',
                                    (x[0].isoformat(),) + x[1:]) for x in nuevas])
    return len(nuevas)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", type=date.fromisoformat)
    p.add_argument("--liquidar", action="store_true")
    a = p.parse_args()
    _assert_target_is_wc()
    res = inmag.actualizar(a.desde)
    try:
        res["dolar_agregados"] = actualizar_dolar(a.desde)
    except Exception as e:
        res["dolar_error"] = str(e)

    if a.liquidar and date.today().day <= 10:
        from src.features.pastaje import service
        hoy = date.today()
        anterior = date(hoy.year - (hoy.month == 1), 12 if hoy.month == 1 else hoy.month - 1, 1)
        res["liquidaciones"] = service.generar_mes(anterior, "tarea programada")
    print(json.dumps(res, ensure_ascii=False, default=str))
