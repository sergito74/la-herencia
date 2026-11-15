"""Simulación (solo lectura) del reparto proporcional de insumos por lo aplicado en las órdenes (050).

Pedido de Sergio 14/11/2026: simular, sin implementar, imputar cada factura de insumo en la proporción de lo
que aplicaron las órdenes de ese producto, y compararlo con su imputación manual (factura + producto).

Variantes de "qué aplicaciones cuentan":
  A  campaña vigente a la fecha de la factura (año agrícola julio-junio)
  B  ventana de uso: aplicaciones desde 60 días antes hasta 365 días después de la factura
  C  campaña cargada a mano (oráculo: aísla si el reparto entre cultivos coincide cuando la campaña es la correcta)
Métrica: coincidencia = Σ min(% manual, % motor) por cultivo+campaña (100% = mismo reparto).

Uso (desde backend/):  python -m scripts.simulacion_reparto_proporcional_050
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
NO_APLICA = 20


def _d(v):
    return v.date() if hasattr(v, "date") else v


def aplicaciones() -> dict[int, list[tuple]]:
    """Por producto: (fecha, idCultivo, idCampania, cantidad) de cada lote aplicado."""
    por_prod: dict[int, list[tuple]] = defaultdict(list)
    for a in fetch_all(
        """
        SELECT oti.IdProducto AS p, COALESCE(ot.FechaEjecucion, ot.FechaPedido) AS f, d.IdCultivo AS cu, d.IdCampania AS ca,
               oti.CantidadTotal * d.CantidadAsignada / NULLIF(t.tot, 0) AS q
        FROM dbo.Ordenes_Trabajo_Insumos oti JOIN dbo.Ordenes_Trabajo ot ON ot.IdOrdenTrabajo = oti.IdOrdenTrabajo
        JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = oti.IdOrdenInsumo
        JOIN (SELECT IdOrdenInsumo, SUM(CantidadAsignada) tot FROM dbo.Ordenes_Trabajo_Distrib GROUP BY IdOrdenInsumo) t
             ON t.IdOrdenInsumo = oti.IdOrdenInsumo
        WHERE ot.Estado <> 'Anulada' AND oti.CantidadTotal > 0
        UNION ALL
        SELECT od.IdFormulado, COALESCE(o.[Fecha Ejecucion], o.[Fecha Pedido]), dd.IdCultivo, dd.[IdCampaña],
               od.[Total Aplicado] * dd.CantidadAsignada / NULLIF(t.tot, 0)
        FROM dbo.Ordenes_Detalles od JOIN dbo.Ordenes o ON o.IdOrden = od.IdOrden
        JOIN dbo.Ordenes_Detalles_Distrib dd ON dd.IdDetalleOrden = od.IdDetalleOrden
        JOIN (SELECT IdDetalleOrden, SUM(CantidadAsignada) tot FROM dbo.Ordenes_Detalles_Distrib GROUP BY IdDetalleOrden) t
             ON t.IdDetalleOrden = od.IdDetalleOrden
        WHERE ISNULL(od.[Total Aplicado], 0) > 0
          AND NOT EXISTS (SELECT 1 FROM dbo.Ordenes_Trabajo mt
                          WHERE mt.Observaciones = 'Migrado de Orden heredada #' + CAST(o.IdOrden AS nvarchar(20)))
        """
    ):
        if a["f"] is not None and a["q"]:
            por_prod[a["p"]].append((_d(a["f"]), a["cu"], a["ca"], float(a["q"])))
    return por_prod


def _shares(c: Counter) -> dict:
    tot = sum(c.values())
    return {k: v / tot for k, v in c.items()} if tot > 0 else {}


def main() -> None:
    camp_id = {f["n"]: f["i"] for f in fetch_all("SELECT [IdCampaña] i, [Campaña] n FROM dbo.[Campañas]")}
    camp_nom = {v: k for k, v in camp_id.items()}
    cult = {f["i"]: f["n"] for f in fetch_all("SELECT IdCultivo i, Cultivo n FROM dbo.Cultivos")}
    apl = aplicaciones()
    filas = fetch_all(
        """
        SELECT d.IdCompra AS idCompra, c.Fecha AS fecha, co.[Razon Social] AS prov, c.[Nro Documento] AS nro,
               d.IdFormulado AS p, d.[Producto/Servicio] AS texto, de.IdCultivo AS cu, d.[IdCampaña] AS ca,
               ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) *
               CASE WHEN c.Moneda = 'Dolares' THEN ISNULL(c.[Tipo de Cambio], 0) ELSE 1 END AS pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= '2015-09-01' AND d.IdFormulado > 0
        """
    )
    combos: dict[tuple, dict] = {}
    for f in filas:
        k = (f["idCompra"], f["p"])
        g = combos.setdefault(k, {"f": f, "manual": Counter(), "pesos": 0.0})
        ca = f["ca"] if f["ca"] not in (None, NO_APLICA) else None
        clave = (f["cu"], ca) if f["cu"] and ca else ("fuera de cultivo", None)
        g["manual"][clave] += float(f["pesos"] or 0)
        g["pesos"] += float(f["pesos"] or 0)

    variantes = {
        "A campaña vigente": lambda g, a: a[2] == camp_id.get(_vig(g["f"]["fecha"])),
        "B ventana de uso": lambda g, a: _d(g["f"]["fecha"]) - timedelta(days=60) <= a[0] <= _d(g["f"]["fecha"]) + timedelta(days=365),
        "C campaña manual (oráculo)": lambda g, a: a[2] in {c for (_, c) in g["manual"] if c},
    }
    # El producto comprado no siempre es el mismo código que registra la orden (glifosato 33994 comprado,
    # otras marcas aplicadas): D y E agrupan por principio activo.
    variantes["D principio activo + campaña vigente"] = variantes["A campaña vigente"]
    variantes["E principio activo + campaña manual (oráculo)"] = variantes["C campaña manual (oráculo)"]
    variantes["F principio activo + campaña de la 1ra aplicación posterior"] = lambda g, a: a[2] == g.get("campF")
    variantes["G principio activo + campaña (abr-jun a la siguiente)"] = lambda g, a: a[2] == camp_id.get(_vig(g["f"]["fecha"], True))
    ia = {f["i"]: (f["a"] or "").strip().upper() for f in fetch_all(
        "SELECT NroReg_int i, [INGREDIENTE ACTIVO] a FROM dbo.Formulados WHERE NroReg_int IS NOT NULL")}
    apl_ia: dict = defaultdict(list)
    for pid, lista in apl.items():
        apl_ia[ia.get(pid) or f"#{pid}"].extend(lista)
    resumen = {v: Counter() for v in variantes}
    pesos = {v: Counter() for v in variantes}
    pond = {v: 0.0 for v in variantes}
    detalle = []
    total_pesos = 0.0
    for g in combos.values():
        if g["pesos"] <= 0:
            continue
        total_pesos += g["pesos"]
        man = _shares(g["manual"])
        desde = _d(g["f"]["fecha"]) - timedelta(days=30)
        pos = sorted(a for a in apl_ia.get(ia.get(g["f"]["p"]) or f"#{g['f']['p']}", []) if a[0] >= desde)
        g["campF"] = pos[0][2] if pos else None
        fila = [g["f"]["fecha"], g["f"]["prov"], g["f"]["nro"], g["f"]["texto"], round(g["pesos"], 2), _txt(man, cult, camp_nom)]
        for v, filtro in variantes.items():
            c = Counter()
            fuente = apl_ia.get(ia.get(g["f"]["p"]) or f"#{g['f']['p']}", []) if v[0] in "DEFG" else apl.get(g["f"]["p"], [])
            for a in fuente:
                if filtro(g, a):
                    c[(a[1], a[2])] += a[3]
            mot = _shares(c)
            if not mot:
                b, coinc = "sin aplicaciones", 0.0
            else:
                coinc = sum(min(man.get(k, 0), mot.get(k, 0)) for k in set(man) | set(mot))
                b = "100%" if coinc > 0.995 else "90-99%" if coinc >= 0.9 else "50-89%" if coinc >= 0.5 else "<50%"
            resumen[v][b] += 1
            pesos[v][b] += g["pesos"]
            pond[v] += coinc * g["pesos"]
            fila += [round(coinc * 100, 1), _txt(mot, cult, camp_nom)]
        detalle.append(fila)

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Variante", "Coincidencia", "Factura+producto", "Importe $"])
    for v in variantes:
        for b in ("100%", "90-99%", "50-89%", "<50%", "sin aplicaciones"):
            ws.append([v, b, resumen[v][b], round(pesos[v][b], 2)])
        ws.append([v, "coincidencia ponderada por $", None, round(pond[v] / total_pesos * 100, 1)])
    ws2 = wb.create_sheet("Detalle")
    ws2.append(["Fecha", "Proveedor", "Nro", "Producto", "Importe $", "Manual"] +
               [x for v in variantes for x in (f"{v} %", f"{v} reparto")])
    for f in detalle:
        ws2.append(f)
    for w in (ws, ws2):
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"simulacion-reparto-proporcional-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("combos", len(detalle))
    for v in variantes:
        print(v, dict(resumen[v]), "ponderado $:", round(pond[v] / total_pesos * 100, 1))
    print("Excel:", destino)


def _vig(fecha, anticipado=False):
    fecha = _d(fecha)
    y = fecha.year if fecha.month >= 7 else fecha.year - 1
    if anticipado and 4 <= fecha.month <= 6:
        y += 1
    return f"{y}/{y + 1}"


def _txt(sh: dict, cult, camp) -> str:
    return " · ".join(f"{cult.get(k[0], k[0])} {camp.get(k[1], '')}".strip() + f" {v * 100:.0f}%"
                      for k, v in sorted(sh.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main()
