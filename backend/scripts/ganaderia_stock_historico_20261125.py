"""052 T032: stock histórico de hacienda. Idempotente. Simula por defecto; con --aplicar hace BACKUP verificado.

Importa (los Excel se abren en solo lectura):
- "Historico Negocio Ganadero (ver 2).xlsx", solapa "Stock Hacienda": recuentos 2016–2023 (origen Planilla).
- "Sanidad/Req Vacunas Oct 26.xlsx": stock de octubre 2026 (origen Acta, fecha del archivo 15/10/2026); las
  "Terneras Miguel" son hacienda de terceros (Ganadera San Justo, contacto del contrato de pastaje).
- Un movimiento Venta por renglón de cada venta de hacienda (stock.sincronizar_venta).
Los stocks al 31/03 de los mails al Estudio no se importan como base (son de los dos campos juntos o solo totales);
se comparan en la salida.
Uso (desde backend/): python -m scripts.ganaderia_stock_historico_20261125 [--aplicar]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl  # noqa: E402

from scripts.ganaderia_tablas_20261125 import _backup  # noqa: E402
from src.db.connection import fetch_all, get_connection  # noqa: E402
from src.features.ganaderia import stock  # noqa: E402

RAIZ = Path(r"C:\Users\Sergio\Documents\La Herencia\Ganaderia")
PLANILLA = RAIZ / "Historico Negocio Ganadero (ver 2).xlsx"
ACTA = RAIZ / "Sanidad" / "Req Vacunas Oct 26.xlsx"
FECHA_ACTA = date(2026, 10, 15)
ALIAS_NUEVOS = [("Vaquillonas 2do servicio", "Vaquillonas 2 dientes", 0)]
ESTABLECIMIENTOS = {"La Herencia": 1, "San Pedro": 2}


def _alias() -> dict[str, tuple[int, bool]]:
    return {r["t"].strip().lower(): (r["c"], bool(r["e"])) for r in
            fetch_all("SELECT Texto t, IdCategoria c, EsTerceros e FROM dbo.GanCategoriaAlias")}


def _dueno_terceros() -> int:
    r = fetch_all("SELECT TOP 1 IdContactoCliente c FROM dbo.ContratosPastaje WHERE Estado = 'vigente' ORDER BY IdContratoPastaje")
    if not r:
        raise RuntimeError("No hay contrato de pastaje vigente para asignar las Terneras Miguel")
    return r[0]["c"]


def leer_planilla(alias) -> tuple[list[dict], list[str]]:
    wb = openpyxl.load_workbook(PLANILLA, read_only=True, data_only=True)
    rec: dict = {}
    sin = []
    for i, r in enumerate(wb["Stock Hacienda"].iter_rows(values_only=True)):
        if i == 0 or not r or not r[0]:
            continue
        cat, est, fecha, cab, precio = r[0], r[1], r[2], r[3], r[4]
        if not cab:
            continue
        a = alias.get(str(cat).strip().lower())
        if not a:
            sin.append(str(cat))
            continue
        k = (fecha.date(), ESTABLECIMIENTOS[est])
        rec.setdefault(k, {"fecha": k[0], "establecimiento": k[1], "origen": "Planilla", "archivo": str(PLANILLA),
                           "detalle": defaultdict(lambda: [0, None])})
        d = rec[k]["detalle"][(None, a[0])]
        d[0] += int(cab)
        d[1] = float(precio) if precio else d[1]
    return list(rec.values()), sin


def leer_acta(alias, terceros: int) -> tuple[dict, list[str]]:
    wb = openpyxl.load_workbook(ACTA, read_only=True, data_only=True)
    filas = list(wb.worksheets[0].iter_rows(min_row=1, max_row=2, values_only=True))
    cabezas, nombres = filas[0], filas[1]
    det = defaultdict(lambda: [0, None])
    sin = []
    for n, c in zip(nombres, cabezas):
        if not n or not isinstance(c, (int, float)) or str(n).strip().lower() in ("req.", "stock", "compra"):
            continue
        a = alias.get(str(n).strip().lower())
        if not a:
            sin.append(str(n))
            continue
        det[(terceros if a[1] else None, a[0])][0] += int(c)
    return {"fecha": FECHA_ACTA, "establecimiento": 1, "origen": "Acta", "archivo": str(ACTA), "detalle": det}, sin


def main():
    aplicar = "--aplicar" in sys.argv
    alias = _alias()
    cats = {r["n"]: r["i"] for r in fetch_all("SELECT IdCategoria i, Nombre n FROM dbo.GanCategoria")}
    for texto, cat, terc in ALIAS_NUEVOS:
        alias.setdefault(texto.lower(), (cats[cat], bool(terc)))
    terceros = _dueno_terceros()
    planilla, sin1 = leer_planilla(alias)
    acta, sin2 = leer_acta(alias, terceros)
    recuentos = sorted(planilla + [acta], key=lambda r: (r["fecha"], r["establecimiento"]))
    print(f"Recuentos a importar: {len(recuentos)} (planilla {len(planilla)}, acta 1)")
    for r in recuentos:
        print(f"  {r['fecha']} est {r['establecimiento']} {r['origen']}: "
              f"{sum(v[0] for v in r['detalle'].values())} cab")
    print("Alias sin resolver:", sorted(set(sin1 + sin2)) or "ninguno")

    ventas = [r["i"] for r in fetch_all("SELECT IdVenta i FROM dbo.[Venta Hacienda] ORDER BY Fecha")]
    ct = stock.categoria_de_tipo_hacienda()
    tipos_sin = fetch_all("SELECT DISTINCT d.IdTipoProducto t FROM dbo.[Det_Ventas Hacienda] d")
    print("Tipos de hacienda sin categoría:", [t["t"] for t in tipos_sin if t["t"] not in ct] or "ninguno")
    if not aplicar:
        n = sum(len(stock.movimientos_de_venta(v, ct)) for v in ventas)
        print(f"Movimientos de venta a generar: {n} de {len(ventas)} ventas")
        print("Simulación (usar --aplicar)")
        return
    if sin1 or sin2:
        sys.exit("Hay alias sin resolver: no se aplica")
    ruta = _backup()
    print(f"BACKUP_VERIFICADO={ruta}")
    with get_connection(readonly=False) as cn:
        cn.autocommit = False
        cur = cn.cursor()
        try:
            if not cur.execute("SELECT COL_LENGTH('dbo.GanMovimiento', 'IdVenta')").fetchone()[0]:
                cur.execute("ALTER TABLE dbo.GanMovimiento ADD IdVenta int NULL")
                cur.execute("CREATE INDEX IX_GanMovimiento_IdVenta ON dbo.GanMovimiento(IdVenta) WHERE IdVenta IS NOT NULL")
            for texto, cat, terc in ALIAS_NUEVOS:
                cur.execute("IF NOT EXISTS (SELECT 1 FROM dbo.GanCategoriaAlias WHERE Texto = ?) "
                            "INSERT INTO dbo.GanCategoriaAlias (Texto, IdCategoria, EsTerceros) VALUES (?, ?, ?)",
                            (texto, texto, cats[cat], terc))
            nuevos = 0
            for r in recuentos:
                if cur.execute("SELECT 1 FROM dbo.GanRecuento WHERE Fecha = ? AND IdEstablecimiento = ? AND Origen = ? "
                               "AND Anulado = 0", (r["fecha"].isoformat(), r["establecimiento"], r["origen"])).fetchone():
                    continue
                idr = cur.execute("INSERT INTO dbo.GanRecuento (Fecha, IdEstablecimiento, Origen, Archivo, CreadoPor) "
                                  "OUTPUT INSERTED.IdRecuento VALUES (?, ?, ?, ?, 'importación 052')",
                                  (r["fecha"].isoformat(), r["establecimiento"], r["origen"], r["archivo"])).fetchone()[0]
                for (du, cat), (cab, precio) in r["detalle"].items():
                    cur.execute("INSERT INTO dbo.GanRecuentoDetalle (IdRecuento, IdCategoria, IdContactoDueno, Cabezas, "
                                "PrecioCabeza, Moneda) VALUES (?, ?, ?, ?, ?, ?)",
                                (idr, cat, du, cab, precio, "ARS" if precio else None))
                nuevos += 1
            cn.commit()
        except Exception:
            cn.rollback()
            raise
    print(f"Recuentos nuevos: {nuevos}")
    n = sum(stock.sincronizar_venta(v) for v in ventas)
    print(f"Movimientos de venta: {n}")
    for f, e in ((date(2023, 10, 26), 1), (date(2026, 10, 15), 1), (date(2023, 3, 31), None), (date.today(), None)):
        s = stock.stock(f, e)
        print(f"Stock {f} est {e or 'todos'}:", [(c["categoria"], c["cabezas"], c["dueno"], c["establecimiento"])
                                                 for c in s["categorias"]])
    print("Fin", datetime.now())


if __name__ == "__main__":
    main()
