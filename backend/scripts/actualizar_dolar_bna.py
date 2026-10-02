"""Completa dbo.[Dolar BNA] con las cotizaciones BNA publicadas por Errepar.

Fuente (indicada por Sergio, 2026-10-01): https://www.errepar.com/cotizacion-dolar,
que consulta el servicio público
https://api.errepar.com/syserrepar/apidolar/api/CotizacionesBNAII/byDates.
Se validó contra la tabla: los 23 días superpuestos de abril de 2026
coinciden exactamente en billete y en divisa.

Carga los días posteriores a la última fecha de la tabla, hasta ayer. No
carga hoy, porque la cotización del día es provisoria. La tabla guarda
todos los días, incluidos los fines de semana, y la fuente también.
Promedio = (compra + venta) / 2.

Es idempotente: solo inserta las fechas que no existen. Opera sobre WC
mediante la conexión central del backend.

Uso:  .venv/Scripts/python.exe -m scripts.actualizar_dolar_bna [--dry-run]
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date, timedelta

from src.db.connection import execute_write_transaction, fetch_all

API = "https://api.errepar.com/syserrepar/apidolar/api/CotizacionesBNAII/byDates"


def _descargar(desde: date, hasta: date) -> list[dict]:
    url = f"{API}?fechaInicial={desde.isoformat()}&fechaFinal={hasta.isoformat()}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        cuerpo = json.load(resp)
    if not cuerpo.get("isSuccess"):
        raise RuntimeError(f"La fuente respondió sin éxito: {cuerpo}")
    return cuerpo["data"]


def main(dry_run: bool = False) -> None:
    ultima = fetch_all("SELECT MAX(Fecha) AS f FROM dbo.[Dolar BNA]")[0]["f"].date()
    hasta = date.today() - timedelta(days=1)
    if ultima >= hasta:
        print(f"Nada para cargar: la tabla llega al {ultima:%d/%m/%Y}.")
        return
    filas = {}
    for r in _descargar(ultima + timedelta(days=1), hasta):
        dia = date.fromisoformat(r["fecha"][:10])
        if ultima < dia <= hasta:
            cb, vb = float(r["billeteCompra"]), float(r["billeteVenta"])
            cd, vd = float(r["divisaCompra"]), float(r["divisaVenta"])
            if min(cb, vb, cd, vd) <= 0:
                raise ValueError(f"Valor inválido el {dia}: {r}")
            filas[dia] = (dia, cb, vb, round((cb + vb) / 2, 4), cd, vd, round((cd + vd) / 2, 4))
    faltan = [ultima + timedelta(days=i) for i in range(1, (hasta - ultima).days + 1) if ultima + timedelta(days=i) not in filas]
    print(f"Tabla hasta {ultima:%d/%m/%Y}. Días a cargar: {len(filas)}. Días sin dato en la fuente: {len(faltan)} {faltan[:10]}")
    if dry_run or not filas:
        return
    sql = ("INSERT INTO dbo.[Dolar BNA] (Fecha, Comp_billete, Vend_billete, Prom_billete, Comp_Divisa, Vend_Divisa, Prom_Divisa) "
           "SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM dbo.[Dolar BNA] WHERE Fecha = ?)")
    execute_write_transaction([(sql, (*f, f[0])) for _, f in sorted(filas.items())])
    print(f"Insertados {len(filas)} días, del {min(filas):%d/%m/%Y} al {max(filas):%d/%m/%Y}.")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
