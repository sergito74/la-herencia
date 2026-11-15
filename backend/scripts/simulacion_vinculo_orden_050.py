"""Simulación (solo lectura) factura de insumo ↔ orden de trabajo por cantidad exacta (050, 14/11/2026).

Hallazgo en las planillas de Sergio: el proveedor factura cada retiro (p. ej. Bayá Casal 0020-00451187, SNIPER II
620 L = Planilla Retiro 12/09/2025) y la factura se reparte como la orden de ese retiro. Entonces:
  1. Por factura + producto se suma la cantidad facturada (todos sus renglones, que Sergio abría por cultivo).
  2. Se busca la orden o combinación de hasta 4 órdenes, no usadas, cuya cantidad del producto (o, si no, del mismo
     principio activo) suma exactamente lo facturado (±0,5%), entre 365 días antes y 60 días después de la factura.
  3. Vinculada: la factura se reparte como esas órdenes (lote → cultivo/campaña). Sin vínculo: kardex FIFO por
     principio activo con pendientes (lo aplicado sin stock lo cubre la factura que llega después).
Compara contra lo imputado a mano, por factura y en el agregado por cultivo/campaña. No escribe en la base.

Uso (desde backend/):  python -m scripts.simulacion_vinculo_orden_050
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.remitos import stock_datos
from scripts.recuentos_planilla_050 import Catalogo, familia_fertilizante, leer_recuentos
from scripts.simulacion_kardex_corte_050 import CORTE, MONETARIAS, RUBROS, STOCK, Sugeridor, _anterior, _d, _ia_norm

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
NO_APLICA = 20
TOL = 0.005
# Punto de partida (Sergio 15/11): recuento del 12/05/2025, el último antes de la primera orden de 2025/26.
INICIO = date(2025, 5, 12)


def ordenes_por_producto() -> list[dict]:
    """Una fila por orden + producto: fecha, cantidad total y reparto por cultivo/campaña."""
    filas = fetch_all(
        """
        SELECT ot.IdOrdenTrabajo o, oti.IdProducto p, COALESCE(ot.FechaEjecucion, ot.FechaPedido) f, oti.CantidadTotal q,
               d.IdCultivo cu, d.IdCampania ca, d.CantidadAsignada qa
        FROM dbo.Ordenes_Trabajo ot JOIN dbo.Ordenes_Trabajo_Insumos oti ON oti.IdOrdenTrabajo = ot.IdOrdenTrabajo
        LEFT JOIN dbo.Ordenes_Trabajo_Distrib d ON d.IdOrdenInsumo = oti.IdOrdenInsumo
        WHERE ot.Estado <> 'Anulada' AND oti.CantidadTotal > 0 AND COALESCE(ot.FechaEjecucion, ot.FechaPedido) >= '2015-01-01'
        """
    )
    g: dict[tuple, dict] = {}
    vistos = set()
    for f in filas:
        k = (f["o"], f["p"])
        x = g.setdefault(k, {"orden": f["o"], "p": f["p"], "fecha": _d(f["f"]), "q": 0.0, "reparto": Counter(), "usada": False})
        if (k, id(f)) not in vistos:
            pass
        x["reparto"][(f["cu"], f["ca"])] += float(f["qa"] or 0)
    # La cantidad total es por renglón de insumo; puede haber más de un renglón del mismo producto en la orden.
    for f in fetch_all(
        """SELECT ot.IdOrdenTrabajo o, oti.IdProducto p, SUM(oti.CantidadTotal) q FROM dbo.Ordenes_Trabajo ot
           JOIN dbo.Ordenes_Trabajo_Insumos oti ON oti.IdOrdenTrabajo = ot.IdOrdenTrabajo
           WHERE ot.Estado <> 'Anulada' AND oti.CantidadTotal > 0 GROUP BY ot.IdOrdenTrabajo, oti.IdProducto"""
    ):
        if (f["o"], f["p"]) in g:
            g[(f["o"], f["p"])]["q"] = float(f["q"])
    return list(g.values())


def buscar(objetivo: float, candidatos: list[dict], fecha: date) -> list[dict] | None:
    cand = sorted((c for c in candidatos if not c["usada"] and fecha - timedelta(days=365) <= c["fecha"] <= fecha + timedelta(days=60)),
                  key=lambda c: abs((c["fecha"] - fecha).days))[:14]
    mejor = None
    for n in range(1, 5):
        for combo in combinations(cand, n):
            if abs(sum(c["q"] for c in combo) - objetivo) <= TOL * objetivo:
                dist = sum(abs((c["fecha"] - fecha).days) for c in combo)
                if mejor is None or dist < mejor[0]:
                    mejor = (dist, combo)
        if mejor:
            return list(mejor[1])
    return None


REMITOS = True
CARPETA_REMITOS = Path(__file__).resolve().parents[2] / "backups" / "baya-remitos-20261115"


def asignar_remitos(facturas: dict, sug, bases, equiv, clave) -> dict:
    """Factura → fecha de ingreso = fecha del remito cargado en el sistema (dbo.Remitos, incluidos los «SIN REMITO»
    que Sergio carga cuando el proveedor entrega sin remito) del mismo proveedor, con el mismo producto (o principio
    activo / familia) y la misma cantidad. Sergio 15/11: las cantidades ingresadas y usadas son correctas porque el
    stock cierra con el recuento físico. Entre varios iguales, el más cercano (antes que después de la factura)."""
    rem = []
    for f in fetch_all(
        """SELECT r.Fecha f, r.NroRemito n, COALESCE(r.IdContacto, r.IdProveedor) c, co.[Razon Social] prov, rd.IdFormulado p,
                  rd.Cantidad q, rd.[Unidad Medida] u
           FROM dbo.Remitos r JOIN dbo.Remitos_Detalles rd ON rd.IdRemito = r.IdRemito
           LEFT JOIN dbo.Contactos co ON co.IdContacto = COALESCE(r.IdContacto, r.IdProveedor)
           WHERE r.Fecha >= '2015-01-01' AND rd.IdFormulado > 0 AND rd.Cantidad > 0"""
    ):
        rem.append({"fecha": _d(f["f"]), "prov": f["prov"], "p": int(f["p"]), "resto": float(f["q"]) * _factor(int(f["p"]), f["u"], bases, equiv)})
    out = {}
    for k in sorted((k for k, x in facturas.items() if not x.get("apertura")), key=lambda k: facturas[k]["fecha"]):
        x = facturas[k]
        cand = [r for r in rem if r["prov"] == x["prov"] and (r["p"] == x["p"] or clave(r["p"]) == x["ia"]) and r["resto"] > 1e-6
                and abs(r["resto"] - x["q"]) <= 0.01 * max(x["q"], 1)]
        if cand:
            r = min(cand, key=lambda r: abs((r["fecha"] - x["fecha"]).days) + (0 if r["fecha"] <= x["fecha"] else 365))
            r["resto"] = 0.0
            out[k] = r["fecha"]
    return out


def _envase(txt: str | None, unidad: str | None, q: float) -> float:
    """'HERB GLIFOSATO 66% x 20 Lts', cantidad 4 y sin unidad = 4 bidones de 20 L → 80."""
    import re
    if (unidad or "").strip() or not txt:
        return 1.0
    m = re.search(r"\bX\s*(\d+(?:[.,]\d+)?)\s*(L|LT|LTS|LITROS|KG|KGS|KILOS)\b", txt.upper())
    return float(m.group(1).replace(",", ".")) if m and q < 200 else 1.0


def _factor(pid, unidad, bases, equiv) -> float:
    factor, falta = stock_datos.factor_a_base(pid, unidad, bases, equiv)
    if falta and (unidad or "").strip().upper().startswith("TON") and (bases.get(pid) or "").upper().startswith("K"):
        return 1000.0
    return factor


def main(inicio: date = INICIO, fin: date | None = None, recuento: date | None = INICIO, auditoria: bool = False,
         guardar: bool = True) -> dict:
    """Una ventana: facturas y órdenes en [inicio, fin), apertura = recuento (o nada). auditoria: sin filtro de historia."""
    # Margen: facturas y órdenes hasta 6 meses después del fin participan del emparejamiento (la factura puede
    # llegar después de la orden), pero solo se comparan las facturas de la ventana.
    hasta = (fin + timedelta(days=183)) if fin else date(2100, 1, 1)
    fin_ = hasta.isoformat()
    ia = {int(f["i"]): _ia_norm(f["a"]) for f in fetch_all(
        "SELECT IdProducto i, IngredienteActivo a FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    bases, equiv = stock_datos.unidades_base(), stock_datos.equivalencias()
    cult = {f["i"]: f["n"] for f in fetch_all("SELECT IdCultivo i, Cultivo n FROM dbo.Cultivos")}
    camp = {f["i"]: f["n"] for f in fetch_all("SELECT [IdCampaña] i, [Campaña] n FROM dbo.[Campañas]")}
    sug = Sugeridor()
    tipo_raw = {int(f["i"]): f["t"] for f in fetch_all("SELECT IdProducto i, TipoProducto t FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    nombres = {int(f["i"]): f["n"] for f in fetch_all("SELECT IdProducto i, Producto n FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}
    # Familias de fertilizante (Sergio 15/11): el arrancador (más fósforo) y la urea (más nitrógeno) se nombran con
    # cualquier producto del catálogo; se emparejan entre sí como si fueran un principio activo.
    ordenes = ordenes_por_producto()
    usados_ord = Counter(o["p"] for o in ordenes)
    rep_fam: dict[str, int] = {}
    for pid_, n_ in nombres.items():
        fam = familia_fertilizante(n_) if tipo_raw.get(pid_) == "Fertilizante" else None
        if fam:
            ia[pid_] = f"FAMILIA {fam}"
            if usados_ord[pid_] > usados_ord.get(rep_fam.get(fam), -1):
                rep_fam[fam] = pid_
    # Marcas que Sergio confirmó como la misma de las órdenes (15/11).
    alias = {"CLETODIM 36": "CLETODIM ARN EBC", "2,4 D 102,5": "2,4D EH 102,5% EBC"}
    por_nombre = {v: k for k, v in nombres.items() if usados_ord[k]}

    def identificar(txt, rubro):
        for a, marca in alias.items():
            if a in (txt or "").upper() and marca in por_nombre:
                return por_nombre[marca], "marca confirmada por Sergio"
        if rubro == "Fertilizantes":
            fam = familia_fertilizante(txt)
            if fam and fam in rep_fam:
                return rep_fam[fam], f"familia {fam.lower()}"
        return None, "sin sugerencia"

    tipo = {int(f["i"]): ("Semillas/fertilizantes" if f["t"] in ("Semilla", "Fertilizante") else "Agroquímicos")
            for f in fetch_all("SELECT IdProducto i, TipoProducto t FROM dbo.vw_ProductosBase WHERE IdProducto IS NOT NULL")}

    facturas: dict[tuple, dict] = {}
    cobertura = Counter()
    ncs: list[dict] = []
    sin_prod: list[list] = []
    for f in fetch_all(
        f"""
        SELECT d.IdCompra idc, c.Fecha f, co.[Razon Social] prov, c.[Nro Documento] nro, c.[Tipo documento] tipo,
               ISNULL(c.[Ajusta Tipo Cambio], 0) atc,
               d.IdFormulado p, d.[Producto/Servicio] txt, ru.Rubro rubro, d.Cantidad q, d.Unidad u, de.IdCultivo cu, d.[IdCampaña] ca,
               ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= ? AND c.Fecha < ? AND ru.Rubro IN ({",".join("?" * len(RUBROS))})
        """,
        (inicio.isoformat(), fin_, *RUBROS),
    ):
        td = (f["tipo"] or "").lower()
        # Sergio 15/11: los documentos que "Ajusta tipo de cambio" no mueven stock; van con su documento base
        # (documentos relacionados) y siguen su imputación.
        if f["atc"]:
            cobertura["ajusta tipo de cambio (sigue a su documento base)"] += 1
            continue
        if (f["u"] or "").strip().upper() in MONETARIAS:
            cobertura["ajuste en $ (sigue a su factura)"] += 1
            continue
        # Las notas de débito repiten la cantidad de la factura pero solo ajustan el precio (TC, diferencias):
        # no entran mercadería. Las notas de crédito con cantidad anulan un pedido facturado (PED. 43194 ↔ NC).
        if "bito" in td:
            cobertura["nota de débito (ajuste de precio, sigue a su factura)"] += 1
            continue
        if "dito" in td:
            ncs.append(f)
            continue
        if not auditoria and _anterior(camp.get(f["ca"])):
            cobertura["historia (campaña anterior)"] += 1
            continue
        pid, via = (f["p"], "con producto") if f["p"] else sug.sugerir(f["txt"])
        if pid is None or "CLETODIM 36" in (f["txt"] or "").upper() or "2,4 D 102,5" in (f["txt"] or "").upper():
            pid2, via2 = identificar(f["txt"], f["rubro"])
            if pid2:
                pid, via = pid2, via2
        if pid is None:
            cobertura["sin producto"] += 1
            sin_prod.append([_d(f["f"]), f["prov"], f["nro"], f["txt"], f["q"], f["u"], round(float(f["pesos"] or 0), 2),
                             f"{cult.get(f['cu'], '')} {camp.get(f['ca'], '')}".strip()])
            continue
        cobertura[via] += 1
        k = (f["idc"], pid)
        x = facturas.setdefault(k, {"fecha": _d(f["f"]), "prov": f["prov"], "nro": f["nro"], "txt": f["txt"], "p": pid,
                                    "ia": ia.get(pid) or f"#{pid}", "q": 0.0, "pesos": 0.0, "manual": Counter()})
        factor = _factor(pid, f["u"], bases, equiv)
        pesos = float(f["pesos"] or 0)
        x["q"] += float(f["q"] or 0) * factor * _envase(f["txt"], f["u"], float(f["q"] or 0))
        x["pesos"] += pesos
        ca = f["ca"] if f["ca"] not in (None, NO_APLICA) else None
        x["manual"][(f["cu"], ca) if f["cu"] and ca else STOCK] += pesos

    # NC con cantidad: si anula entera una factura anterior del mismo proveedor y producto, las dos se cancelan.
    import re as _re
    anuladas = set()
    for f in ncs:
        m = _re.search(r"\bFC\s*0*(\d{3,8})\b", (f["txt"] or "").upper())
        if m:
            nro = m.group(1)
            for k, x in list(facturas.items()):
                if x["prov"] == f["prov"] and _re.sub(r"\D", "", x["nro"] or "").endswith(nro.zfill(8)[-len(nro):]) and x["fecha"] <= _d(f["f"]):
                    facturas.pop(k)
                    anuladas.add(k[0])
                    cobertura["factura anulada por NC que la nombra"] += 1
    ncs = [f for f in ncs if not _re.search(r"\bFC\s*0*\d{3,8}\b", (f["txt"] or "").upper())]
    agrup_nc: dict[tuple, dict] = {}
    for f in ncs:
        pid = f["p"] or sug.sugerir(f["txt"])[0] or identificar(f["txt"], f["rubro"])[0]
        if not pid or not f["q"]:
            cobertura["nota de crédito (ajuste, sigue a su factura)"] += 1
            continue
        factor = _factor(pid, f["u"], bases, equiv)
        x = agrup_nc.setdefault((f["idc"], pid), {"prov": f["prov"], "fecha": _d(f["f"]), "p": pid, "q": 0.0, "n": 0})
        x["q"] += float(f["q"]) * factor
        x["n"] += 1
    for nk, nc in agrup_nc.items():
        cand = [k for k, x in facturas.items() if x["prov"] == nc["prov"] and x["ia"] == (ia.get(nc["p"]) or f"#{nc['p']}") and x["fecha"] <= nc["fecha"]
                and abs(x["q"] - nc["q"]) <= TOL * max(nc["q"], 1)]
        if cand:
            k = max(cand, key=lambda k: facturas[k]["fecha"])
            facturas.pop(k)
            cobertura["factura anulada por NC (se cancelan)"] += nc["n"]
        else:
            cobertura["nota de crédito (ajuste, sigue a su factura)"] += nc["n"]

    # Apertura = recuento del 12/05/2025 (planilla Stock Insumos.xlsx), valuado a la última factura anterior del
    # producto (o, si no hay, del mismo principio activo / familia).
    precio_pid, precio_ia = {}, {}
    for f in fetch_all(
        f"""
        SELECT c.Fecha f, d.IdFormulado p, d.[Producto/Servicio] txt, ru.Rubro rubro, d.Cantidad q, d.Unidad u,
               d.[Precio Unitario]*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pu
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        WHERE c.Fecha >= '2020-07-01' AND c.Fecha < ? AND c.[Tipo documento] = 'Factura' AND d.Cantidad > 0 AND d.[Precio Unitario] > 0
          AND ISNULL(d.Unidad, '') NOT IN ('ARS', 'USD') AND ru.Rubro IN ({",".join("?" * len(RUBROS))})
        ORDER BY c.Fecha
        """,
        ((recuento or inicio).isoformat(), *RUBROS),
    ):
        pid = f["p"] or identificar(f["txt"], f["rubro"])[0] or sug.sugerir(f["txt"])[0]
        if not pid:
            continue
        factor = _factor(pid, f["u"], bases, equiv)
        precio_pid[pid] = float(f["pu"]) / (factor or 1)
        precio_ia[ia.get(pid) or f"#{pid}"] = precio_pid[pid]
    cat = Catalogo()
    rec = next((r for r in leer_recuentos() if r["fecha"] == recuento), {"renglones": [], "hoja": ""}) if recuento else {"renglones": [], "hoja": ""}
    sin_valor = []
    for i_, r in enumerate(rec["renglones"]):
        pid = cat.producto(r["marca"], sug)
        if not pid or r["q"] <= 0:
            continue
        a = ia.get(pid) or f"#{pid}"
        pu = precio_pid.get(pid) or precio_ia.get(a)
        if not pu:
            sin_valor.append(r["marca"])
            pu = 0.0
        factor = _factor(pid, r["unidad"], bases, equiv)
        facturas[("recuento", i_)] = {"fecha": recuento - timedelta(days=1), "prov": f"Recuento {recuento:%d/%m/%Y}", "nro": rec["hoja"],
                                      "txt": r["marca"], "p": pid, "ia": a, "q": r["q"] * factor, "pesos": max(pu, 1e-6) * r["q"] * factor,
                                      "manual": Counter(), "apertura": True}
        cobertura["apertura: recuento"] += 1
    if sin_valor:
        print("recuento sin precio de factura:", sin_valor)

    por_prod, por_ia = defaultdict(list), defaultdict(list)
    for o in ordenes:
        por_prod[o["p"]].append(o)
        por_ia[ia.get(o["p"]) or f"#{o['p']}"].append(o)

    # Método de Sergio (facturas Bayá Casal 0020-00451187/91): por marca, las facturas en orden se asignan a las
    # órdenes en orden, por cantidad, sin importar si la factura es anterior o posterior (el proveedor guarda lo
    # pedido). Paso 1 por marca; paso 2 los remanentes por principio activo. Sobrante de factura → stock.
    motor: dict[tuple, Counter] = defaultdict(Counter)
    metodo: dict[tuple, str] = {}
    resto_f = {k: x["q"] for k, x in facturas.items() if x["q"] > 0 and x["pesos"] > 0}
    resto_o = {id(o): o["q"] for o in ordenes if inicio <= o["fecha"] < hasta}

    # Fecha de ingreso (Sergio 15/11): la del remito del proveedor, no la de la factura. Con remito, la factura entra
    # al kardex en esa fecha y no puede cubrir órdenes anteriores a su ingreso; sin remito, sin restricción.
    ingreso = asignar_remitos(facturas, sug, bases, equiv, lambda p: ia.get(p) or f"#{p}") if REMITOS else {}

    def emparejar(fks, ords, etiqueta):
        fks = sorted(fks, key=lambda k: (ingreso.get(k) or facturas[k]["fecha"], k))
        ords = sorted(ords, key=lambda o: (o["fecha"], o["orden"]))
        for k in fks:
            ing = ingreso.get(k)
            for o in ords:
                if resto_f[k] <= 1e-9:
                    break
                if resto_o[id(o)] <= 1e-9 or (ing and o["fecha"] < ing - timedelta(days=7)):
                    continue
                consumir(k, o, etiqueta)

    def consumir(k, o, etiqueta):
            t = min(resto_f[k], resto_o[id(o)])
            resto_f[k] -= t
            resto_o[id(o)] -= t
            unit = facturas[k]["pesos"] / facturas[k]["q"]
            tot = sum(o["reparto"].values()) or 1
            for kk, v in o["reparto"].items():
                motor[k][kk] += t * unit * v / tot
            metodo.setdefault(k, etiqueta)

    fpp, opp = defaultdict(list), defaultdict(list)
    for k in resto_f:
        fpp[facturas[k]["p"]].append(k)
    for o in ordenes:
        if id(o) in resto_o:
            opp[o["p"]].append(o)
    for pid in fpp:
        emparejar(fpp[pid], opp.get(pid, []), "FIFO por marca")
    fia, oia = defaultdict(list), defaultdict(list)
    for k, q in resto_f.items():
        if q > 1e-9:
            fia[facturas[k]["ia"]].append(k)
    for o in ordenes:
        if id(o) in resto_o and resto_o[id(o)] > 1e-9:
            oia[ia.get(o["p"]) or f"#{o['p']}"].append(o)
    for a in fia:
        emparejar(fia[a], oia.get(a, []), "FIFO por principio activo")
    for k, q in resto_f.items():
        if q > 1e-9:
            motor[k][STOCK] += q * facturas[k]["pesos"] / facturas[k]["q"]
            metodo.setdefault(k, "stock")

    # Comparación. Uso posterior por principio activo: lo que la simulación deja en stock al cierre y Sergio imputó a un
    # cultivo/campaña donde ese producto se aplicó después es consistente ("en stock al cierre, usado después").
    usos = defaultdict(list)
    for o in ordenes:
        for z in o["reparto"]:
            usos[ia.get(o["p"]) or f"#{o['p']}"].append((o["fecha"], z))
    res, porm = Counter(), defaultdict(Counter)
    agM, agK = Counter(), Counter()
    portipo = defaultdict(lambda: [0.0, 0.0, Counter(), Counter()])
    detalle = []
    cp = tot = 0.0
    for k, x in facturas.items():
        man, mo = x["manual"], motor.get(k, Counter())
        tm, tmo = sum(man.values()), sum(mo.values())
        if x.get("apertura") or x["pesos"] <= 0 or tm <= 0 or tmo <= 0 or (fin and x["fecha"] >= fin):
            continue
        c = sum(min(man[z] / tm, mo[z] / tmo) for z in set(man) | set(mo))
        # Lo que Sergio dejó en stock y la simulación ya asignó a una orden posterior es consistente (se usó después).
        c = min(1.0, c + man[STOCK] / tm - min(man[STOCK] / tm, mo[STOCK] / tmo))
        despues = {z for fe, z in usos.get(x["ia"], []) if fe >= x["fecha"]}
        libre = mo[STOCK] / tmo - min(man[STOCK] / tm, mo[STOCK] / tmo)
        extra = 0.0
        for z, v in man.items():
            if z != STOCK and z in despues:
                extra += max(0.0, v / tm - min(v / tm, mo[z] / tmo))
        usado_despues = min(libre, extra)
        c = min(1.0, c + usado_despues)
        b = "100%" if c > 0.995 else "90-99%" if c >= 0.9 else "50-89%" if c >= 0.5 else "<50%"
        res[b] += 1
        porm[metodo[k]][b] += 1
        cp += c * x["pesos"]
        tot += x["pesos"]
        tp = portipo[tipo.get(x["p"], "Agroquímicos")]
        tp[0] += c * x["pesos"]
        tp[1] += x["pesos"]
        for z, v in man.items():
            tp[2][z] += v
        for z, v in mo.items():
            tp[3][z] += v * x["pesos"] / tmo
        for z, v in man.items():
            agM[z] += v
        for z, v in mo.items():
            agK[z] += v * x["pesos"] / tmo
        detalle.append([x["fecha"], x["prov"], x["nro"], x["ia"], x["txt"], metodo[k], round(x["q"], 2), round(x["pesos"], 2),
                        round(c * 100, 1), _txt(man, cult, camp), _txt(mo, cult, camp), dict(man), {z: v / tmo for z, v in mo.items()},
                        round(usado_despues * 100, 1), x["p"]])
    agreg = sum(min(agM[z], agK[z]) for z in set(agM) | set(agK)) / (sum(agM.values()) or 1)

    faltantes = [["Renglón sin producto identificado", *r] for r in sin_prod]
    for k, x in facturas.items():
        mo = motor.get(k, Counter())
        if x.get("apertura") or not mo or (fin and x["fecha"] >= fin):
            continue
        en_stock = mo[STOCK] / (sum(mo.values()) or 1)
        man_cult = sum(v for z, v in x["manual"].items() if z != STOCK) / (sum(x["manual"].values()) or 1)
        if en_stock > 0.05 and man_cult > 0.05:
            faltantes.append(["Factura imputada a cultivo sin orden que la consuma", x["fecha"], x["prov"], x["nro"], x["txt"],
                              round(x["q"] * en_stock, 2), "", round(x["pesos"] * en_stock, 2), _txt(x["manual"], cult, camp)])
    for o in ordenes:
        r = resto_o.get(id(o), 0)
        if r > 1e-6 and not (fin and o["fecha"] >= fin):
            faltantes.append(["Orden aplicada sin factura que la cubra", o["fecha"], f"Orden {o['orden']}", "", nombres.get(o["p"], o["p"]),
                              round(r, 2), "", None, _txt(o["reparto"], cult, camp)])
    salida = {"detalle": detalle, "faltantes": faltantes, "portipo": portipo, "agM": agM, "agK": agK, "cp": cp, "tot": tot,
              "cobertura": cobertura, "cult": cult, "camp": camp}
    if not guardar:
        return salida

    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append(["Renglones desde 01/07/2025", "Cantidad"])
    for kk, v in cobertura.items():
        ws.append([kk, v])
    ws.append([])
    ws.append(["Método", "100%", "90-99%", "50-89%", "<50%"])
    for m, cc in porm.items():
        ws.append([m, cc["100%"], cc["90-99%"], cc["50-89%"], cc["<50%"]])
    ws.append([])
    ws.append(["Coincidencia ponderada por $ (factura por factura)", round(cp / tot * 100, 1)])
    ws.append(["Coincidencia agregada por cultivo/campaña", round(agreg * 100, 1)])
    ws.append([])
    ws.append(["Cultivo/campaña", "Manual $", "Simulación $", "Diferencia $"])
    for z in sorted(set(agM) | set(agK), key=lambda z: -agM[z]):
        nombre = "stock" if z == STOCK else f"{cult.get(z[0], z[0])} {camp.get(z[1], '')}".strip()
        ws.append([nombre, round(agM[z], 2), round(agK[z], 2), round(agK[z] - agM[z], 2)])
    w2 = wb.create_sheet("Facturas")
    w2.append(["Fecha", "Proveedor", "Nro", "Principio activo", "Renglón", "Método", "Cantidad", "Importe $", "Coincidencia %",
               "Manual", "Simulación"])
    for f in sorted(detalle, key=lambda r: (r[8], -r[7])):
        w2.append(f)
    for w in wb.worksheets:
        for cel in w[1]:
            cel.font = Font(bold=True)
    destino = SALIDA / f"simulacion-vinculo-orden-{date.today():%Y%m%d}-recuento.xlsx"
    wb.save(destino)
    print("cobertura", dict(cobertura))
    for m, cc in porm.items():
        print(m, dict(cc))
    for t, (a1, a2, m1, k1) in portipo.items():
        ag = sum(min(m1[z], k1[z]) for z in set(m1) | set(k1)) / (sum(m1.values()) or 1)
        print(t, "importe $M", round(a2 / 1e6, 1), "factura x factura", round(a1 / a2 * 100, 1), "agregado", round(ag * 100, 1))
        ws.append([t, "importe $", round(a2, 2), "factura x factura %", round(a1 / a2 * 100, 1), "agregado %", round(ag * 100, 1)])
    w3 = wb.create_sheet("Faltantes")
    w3.append(["Tipo", "Fecha", "Proveedor / Orden", "Nro", "Producto", "Cantidad", "Unidad", "Importe $", "Imputación manual"])
    for r in faltantes:
        w3.append(r)
    for cel in w3[1]:
        cel.font = Font(bold=True)
    wb.save(destino)
    print("ponderada", round(cp / tot * 100, 1), "agregada", round(agreg * 100, 1))
    print("Excel:", destino)
    return salida


def _txt(c: Counter, cult, camp) -> str:
    t = sum(c.values()) or 1
    return " · ".join(("stock" if k == STOCK else f"{cult.get(k[0], k[0])} {camp.get(k[1], '')}".strip()) + f" {v / t * 100:.0f}%"
                      for k, v in sorted(c.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main()
