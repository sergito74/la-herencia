"""Adicional fuera de recibo de Marcelo Sierra (contacto 374), 2026-10-01.

Sierra cobra cada mes un adicional de alrededor del 38,5%, por fuera del
recibo, que se paga en efectivo desde la caja de Giamigli (aclaración de
Sergio). El detalle está en la columna "Total Bonificacion" de la hoja
"Liquidaciones Encargado" de "Personal/Remuneraciones modif..xlsx".

1. **Documento**: en los meses en que Remuneraciones tiene solo el neto del
   recibo, se agrega una fila "Adicional fuera de recibo <Mes Año>" con el
   importe en [Bonificacion adicional]. Si las filas del mes ya suman neto +
   adicional, porque se cargó todo junto, no se agrega nada. Si no da ni una
   cosa ni la otra, se informa.
2. **Pago**: los pagos "Adicional Sueldo Marcelo ..." de
   MovimientosCajaEfectivo (caja GiamigliSA) que todavía no están en
   [Pagos efectivo] se agregan ahí, con el contacto 374 y el mismo formato
   que los anteriores. La cuenta corriente lee [Pagos efectivo].

Es idempotente y hace un respaldo verificado antes de grabar.

Uso (desde backend/):  .venv/Scripts/python.exe -m scripts.cargar_adicional_sierra [--aplicar]
"""

from __future__ import annotations

import re
import sys
import warnings
from collections import defaultdict
from datetime import datetime, timedelta

import openpyxl

from src.db.connection import execute_write_transaction, fetch_all
from scripts.cargar_recibos_sueldo import MESES, _mes_anio

PLANILLA = r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Personal\Remuneraciones modif..xlsx"
SIERRA = 374
COL_PERIODO, COL_NETO, COL_BONIF = 6, 31, 35


def leer_planilla() -> dict[tuple[int, int], tuple[float, float]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(PLANILLA, data_only=True, read_only=True)
    meses = {}
    for r in wb["Liquidaciones Encargado"].iter_rows(values_only=True):
        if r and r[0] and str(r[0]).startswith("Sierra") and isinstance(r[COL_PERIODO], datetime):
            p = r[COL_PERIODO]
            meses[(p.month, p.year)] = (float(r[COL_NETO] or 0), float(r[COL_BONIF] or 0))
    return meses


def main(aplicar: bool) -> None:
    planilla = leer_planilla()
    neto_cargado: dict[tuple, float] = defaultdict(float)
    for f in fetch_all("SELECT [Periodo liquidado] AS p, ISNULL([Sueldo basico],0)+ISNULL([Adic futuros aumentos],0)"
                       "+ISNULL(Ajuste,0)+ISNULL(Vacaciones,0)+ISNULL([Dia Gremio],0)+ISNULL(Antiguedad,0)"
                       "+ISNULL([Ajuste No Remunerativo],0)+ISNULL(Aguinaldo,0)+ISNULL(Redondeo,0)"
                       "+ISNULL([Bonificacion adicional],0)-ISNULL(Jubilacion,0)-ISNULL([Ley 19032],0)"
                       "-ISNULL([Obra Social],0)-ISNULL([Obra Social Acuerdos],0)-ISNULL([Aporte Sindical],0)"
                       "-ISNULL([Servicio de Sepelio],0) AS neto FROM dbo.Remuneraciones WHERE IdContacto = ?", (SIERRA,)):
        if f["p"] and "Adicional" in f["p"]:
            k = _mes_anio(f["p"].replace("Adicional fuera de recibo ", ""))
        else:
            k = _mes_anio(f["p"] or "")
        if k:
            neto_cargado[k] += float(f["neto"])

    documentos, avisos = [], []
    for (mes, anio), (neto, bonif) in sorted(planilla.items(), key=lambda x: (x[0][1], x[0][0])):
        if bonif <= 0:
            continue
        cargado = neto_cargado.get((mes, anio), 0.0)
        tol = max(2.0, neto * 0.002)
        if abs(cargado - (neto + bonif)) <= tol:
            continue  # ya incluye el adicional
        if abs(cargado - neto) <= tol:
            fin = datetime(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)
            documentos.append((f"Adicional fuera de recibo {MESES[mes - 1]} {anio}", fin, round(bonif, 2)))
        else:
            avisos.append(f"{MESES[mes - 1]} {anio}: cargado {cargado:,.2f}, recibo {neto:,.2f}, adicional {bonif:,.2f}")

    pagos_existentes = fetch_all("SELECT Fecha AS f, [Importe imputado] AS i FROM dbo.[Pagos efectivo] WHERE IdContacto = ?",
                                 (SIERRA,))
    pagos = []
    for m in fetch_all("SELECT IdMovimiento AS id, Fecha AS f, Concepto AS c, Importe AS i, Cuenta AS cta "
                       "FROM dbo.MovimientosCajaEfectivo WHERE Caja = 'GiamigliSA' AND Importe < 0 "
                       "AND (Concepto LIKE 'Adicional%Marcelo%' OR Concepto LIKE 'Sueldo%Marcelo%')"):
        fecha = datetime.fromisoformat(str(m["f"])[:10])
        importe = -float(m["i"])
        if any(abs(float(p["i"]) - importe) < 1 and p["f"] and abs((p["f"] - fecha).days) <= 5 for p in pagos_existentes):
            continue
        pagos.append((fecha, importe, m["c"], "Blue" if (m["cta"] or "").strip().upper() == "B" else (m["cta"] or "Blue")))

    print(f"Documentos 'Adicional fuera de recibo' a agregar: {len(documentos)} (${sum(d[2] for d in documentos):,.2f})")
    for p, f, imp in documentos:
        print(f"  {p:42} {f:%d/%m/%Y} ${imp:>12,.2f}")
    print(f"Pagos en efectivo a agregar: {len(pagos)} (${sum(p[1] for p in pagos):,.2f})")
    for f, imp, c, cta in pagos:
        print(f"  {f:%d/%m/%Y} ${imp:>12,.2f}  {c}")
    for a in avisos:
        print(f"  ? {a}")
    if not aplicar:
        print("Simulación: no se escribió nada. Usar --aplicar para grabar.")
        return
    if not documentos and not pagos:
        return
    from src.features.vinculos.backup import backup_verificado
    print(f"Respaldo verificado: {backup_verificado('adicional-sierra')}")
    stmts = [("INSERT INTO dbo.Remuneraciones (IdContacto, [Fecha de pago], [Periodo liquidado], [Bonificacion adicional]) "
              "VALUES (?, ?, ?, ?)", (SIERRA, f, p, imp)) for p, f, imp in documentos]
    stmts += [("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, "
               "[Importe imputado]) VALUES (?, 1, 3, ?, ?, 'GiamigliSA', ?)", (SIERRA, f, cta, imp))
              for f, imp, _, cta in pagos]
    execute_write_transaction(stmts)
    print(f"Grabado: {len(documentos)} documentos y {len(pagos)} pagos.")


if __name__ == "__main__":
    main(aplicar="--aplicar" in sys.argv)
