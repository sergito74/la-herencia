"""Simulación (solo lectura) del kardex FIFO desde el corte del recuento físico (15/12/2025), 050 — 14/11/2026.

Por qué desde el corte: entre 2015 y 2020 las compras superan largamente lo registrado en órdenes (p. ej. glifosato
2017: 7.440 L comprados, 1.640 L en órdenes), así que un kardex desde 2015 acumula stock que no existe. La historia
queda como la imputó Sergio; el kardex arranca con lo contado.

Pasos:
 1. Producto sugerido para los renglones de insumo sin producto (IdFormulado = 0): mismo texto ya cargado con
    producto, texto parecido, o marca comercial de un producto usado en órdenes/recuentos.
 2. Kardex por principio activo: apertura = recuento 15/12/2025; entran facturas posteriores; salen aplicaciones
    posteriores, en orden de llegada (FIFO) y repartidas como la orden.
 3. Controles: (a) stock simulado = contado en cada recuento posterior; (b) reparto de cada factura vs lo imputado a mano.

Uso (desde backend/):  python -m scripts.simulacion_kardex_corte_050
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from src.db.connection import fetch_all
from src.features.imputacion.aprendizaje import tokens
from src.features.imputacion.tamiz import normalizar
from src.features.remitos import stock_datos
from scripts.simulacion_reparto_proporcional_050 import aplicaciones

SALIDA = Path(__file__).resolve().parents[2] / "specs" / "050-tamizado-imputacion-cultivos"
CORTE = date(2025, 7, 1)  # inicio campaña 2025/26; los recuentos quedan como control
MONETARIAS = {"ARS", "USD", "$", "U$S"}
NO_APLICA = 20
STOCK = ("stock", None)
RUBROS = ("Herbicidas", "Insecticidas", "Fungicidas", "Coadyuvantes", "Fertilizantes", "Semillas", "Curasemillas")


def _d(v):
    if isinstance(v, str):
        v = datetime.strptime(v[:10], "%Y-%m-%d")
    return v.date() if hasattr(v, "date") else v


def _ia_norm(a):
    return " ".join((a or "").upper().replace("EQUIVALENTE ACIDO", "").replace("EQUIVALETE ACIDO", "").split())


def _palabras(t: str) -> frozenset:
    """Palabras del texto normalizado conservando códigos con números (3970, 46R18), sin conectores ni unidades."""
    ruido = {"DE", "DEL", "LA", "EL", "Y", "X", "KG", "KGS", "LTS", "LT", "L", "LITROS", "BOLSA", "BOLSAS", "BIG", "BAG",
             "GRANEL", "TRAT", "C", "B1", "B2", "SEMILLA", "SEMILLAS"}
    return frozenset(w for w in re.split(r"[^A-Z0-9]+", t) if len(w) >= 2 and w not in ruido)


class Sugeridor:
    def __init__(self):
        self.exacto: dict[str, Counter] = defaultdict(Counter)
        self.toks: dict[str, frozenset] = {}
        for f in fetch_all("SELECT [Producto/Servicio] t, IdFormulado p FROM dbo.Det_Compras WHERE IdFormulado > 0"):
            t = normalizar(f["t"])
            self.exacto[t][f["p"]] += 1
            self.toks.setdefault(t, tokens(t))
        # Fitosanitarios, semillas y fertilizantes (vw_ProductosBase) usados en órdenes o recuentos.
        usados = fetch_all(
            """SELECT DISTINCT CAST(v.IdProducto AS bigint) p, v.Producto m FROM dbo.vw_ProductosBase v
               WHERE v.IdProducto IN (SELECT IdProducto FROM dbo.Ordenes_Trabajo_Insumos UNION SELECT IdFormulado FROM dbo.Ordenes_Detalles
                                      UNION SELECT IdProducto FROM dbo.Stock_Recuentos_Detalle)""")
        self.marcas = [(_palabras(normalizar(u["m"])), u["p"]) for u in usados if u["m"]]

    def sugerir(self, texto) -> tuple[int | None, str]:
        t = normalizar(texto)
        if self.exacto.get(t):
            return self.exacto[t].most_common(1)[0][0], "mismo texto"
        mios = tokens(t)
        mejor, pid = 0.0, None
        for otro, tk in self.toks.items():
            if tk and mios:
                s = len(mios & tk) / len(mios | tk)
                if s > mejor:
                    mejor, pid = s, self.exacto[otro].most_common(1)[0][0]
        if mejor >= 0.6:
            return pid, "texto parecido"
        mis = _palabras(t)
        mejor_m = (0.0, 0, None)
        for m, p in self.marcas:
            if not m:
                continue
            s = len(m & mis) / len(m)
            # "SYN 3970" = "SYN 3970 CL": todo el texto (con su código numérico) está dentro de la marca.
            todo = len(m & mis) >= 2 and mis <= m and any(ch.isdigit() for w in mis for ch in w)
            if (s >= 0.67 or todo) and len(m & mis) >= 1 and (s, len(m), p) > mejor_m:
                mejor_m = (s, len(m), p)
        if mejor_m[2]:
            return int(mejor_m[2]), "marca comercial"
        # Código de la marca escrito distinto ("SOJA DM 46 R 18" = DON MARIO 46R18, "MAIZ LT 725 TRE" = LT725TRE), o una
        # palabra distintiva que solo tiene una marca (Rinder = DIFLU 50 RINDER).
        compacto = re.sub(r"[^A-Z0-9]", "", t)
        cand = set()
        for m, p in self.marcas:
            cod = [w for w in m if any(ch.isdigit() for ch in w) and len(w) >= 4]
            if cod and all(w in compacto for w in cod) and len(re.sub(r"\D", "", "".join(cod))) >= 3:
                cand.add(int(p))
        if len(cand) == 1:
            return cand.pop(), "código de marca"
        if not hasattr(self, "_unicas"):
            cuenta = Counter(w for m, _ in self.marcas for w in m)
            self._unicas = {w: int(p) for m, p in self.marcas for w in m if cuenta[w] == 1 and len(w) >= 5 and w.isalpha()}
        hits = {self._unicas[w] for w in mis if w in self._unicas}
        if len(hits) == 1:
            return hits.pop(), "palabra única de marca"
        return None, "sin sugerencia"


def main() -> None:
    ia = {f["i"]: _ia_norm(f["a"]) for f in fetch_all(
        "SELECT NroReg_int i, [INGREDIENTE ACTIVO] a FROM dbo.Formulados WHERE NroReg_int IS NOT NULL")}
    bases, equiv = stock_datos.unidades_base(), stock_datos.equivalencias()
    cult = {f["i"]: f["n"] for f in fetch_all("SELECT IdCultivo i, Cultivo n FROM dbo.Cultivos")}
    camp = {f["i"]: f["n"] for f in fetch_all("SELECT [IdCampaña] i, [Campaña] n FROM dbo.[Campañas]")}
    sug = Sugeridor()

    # Recuentos vigentes (por principio activo).
    recuentos: dict[date, Counter] = defaultdict(Counter)
    for r in fetch_all("""SELECT r.Fecha f, d.IdProducto p, d.Contado q FROM dbo.Stock_Recuentos r
                          JOIN dbo.Stock_Recuentos_Detalle d ON d.IdRecuento = r.IdRecuento WHERE r.Anulado = 0"""):
        recuentos[_d(r["f"])][ia.get(r["p"]) or f"#{r['p']}"] += float(r["q"] or 0)
    apertura = Counter()

    # Renglones de insumo desde el corte.
    entradas: dict[str, list[dict]] = defaultdict(list)
    manual: dict[tuple, Counter] = defaultdict(Counter)
    info: dict[tuple, dict] = {}
    cobertura = Counter()
    sin_sug = []
    for f in fetch_all(
        f"""
        SELECT d.IdDetalleCompra id, d.IdCompra idc, c.Fecha f, co.[Razon Social] prov, c.[Nro Documento] nro, c.[Tipo documento] tipo,
               d.IdFormulado p, d.[Producto/Servicio] txt, d.Cantidad q, d.Unidad u, de.IdCultivo cu, d.[IdCampaña] ca, ru.Rubro rubro,
               ISNULL(d.Cantidad,0)*ISNULL(d.[Precio Unitario],0)*CASE WHEN c.Moneda='Dolares' THEN ISNULL(c.[Tipo de Cambio],0) ELSE 1 END pesos
        FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.Rubros ru ON ru.IdRubro = d.IdRubro
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE c.Fecha >= ? AND ru.Rubro IN ({",".join("?" * len(RUBROS))})
        """,
        (CORTE.isoformat(), *RUBROS),
    ):
        if (f["u"] or "").strip().upper() in MONETARIAS:
            cobertura["ajuste en $ (sigue a su factura)"] += 1
            continue
        if _anterior(camp.get(f["ca"])):
            cobertura["historia: imputado a campaña anterior al arranque"] += 1
            continue
        pid, via = (f["p"], "con producto") if f["p"] else sug.sugerir(f["txt"])
        cobertura[via] += 1
        if pid is None:
            sin_sug.append([f["f"], f["prov"], f["nro"], f["rubro"], f["txt"], float(f["pesos"] or 0)])
            continue
        a = ia.get(pid) or f"#{pid}"
        k = (f["idc"], a)
        pesos = float(f["pesos"] or 0)
        ca = f["ca"] if f["ca"] not in (None, NO_APLICA) else None
        manual[k][(f["cu"], ca) if f["cu"] and ca else STOCK] += pesos
        g = info.setdefault(k, {"fecha": f["f"], "prov": f["prov"], "nro": f["nro"], "txt": f["txt"], "via": via, "pesos": 0.0})
        g["pesos"] += pesos
        factor, _ = stock_datos.factor_a_base(pid, f["u"], bases, equiv)
        q = float(f["q"] or 0) * factor
        if q > 0 and "credito" not in (f["tipo"] or "").lower():
            entradas[a].append({"k": k, "fecha": _d(f["f"]), "q": q, "unit": pesos / q, "resto": q})

    salidas: dict[str, list[tuple]] = defaultdict(list)
    for pid, lista in aplicaciones().items():
        for s in lista:
            if s[0] >= CORTE:
                salidas[ia.get(pid) or f"#{pid}"].append(s)

    # La apertura NO se deduce del recuento: al 15/12/2025 había mercadería entregada sin facturar (facturas de
    # marzo 2026) y el recuento la cuenta; deducirla absorbe el consumo y corre las facturas a la campaña siguiente.

    # Kardex FIFO con apertura; se cortan saldos en cada fecha de recuento para el control.
    fechas_rec = sorted(recuentos)
    motor: dict[tuple, Counter] = defaultdict(Counter)
    control = []
    faltante = Counter()
    for a in set(entradas) | set(salidas) | set(apertura) | {x for r in recuentos.values() for x in r}:
        capas = ([{"k": ("apertura", a), "fecha": CORTE, "q": apertura[a], "unit": 0.0, "resto": apertura[a]}] if apertura.get(a) else [])
        capas += sorted(entradas.get(a, []), key=lambda e: e["fecha"])
        # Eventos en orden: entrada de capa (0), salida (1), recuento (2). Lo aplicado sin stock queda pendiente
        # (se entregó con remito/retiro y se factura después) y lo cubre la primera factura que llega.
        eventos = sorted([(c["fecha"], 0, c) for c in capas] + [(s[0], 1, s) for s in salidas.get(a, [])]
                         + [(fr, 2, None) for fr in fechas_rec], key=lambda x: (x[0], x[1]))
        abiertas: list[dict] = []
        pendientes: list[list] = []  # [cantidad, cultivo, campaña]
        for fecha, tipo, x in eventos:
            if tipo == 0:
                while pendientes and x["resto"] > 1e-9:
                    pe = pendientes[0]
                    t = min(pe[0], x["resto"])
                    x["resto"] -= t
                    pe[0] -= t
                    motor[x["k"]][(pe[1], pe[2])] += t * x["unit"]
                    if pe[0] <= 1e-9:
                        pendientes.pop(0)
                abiertas.append(x)
            elif tipo == 2:
                sim = sum(c["resto"] for c in abiertas) - sum(pe[0] for pe in pendientes)
                if a in recuentos[fecha] or abs(sim) > 1e-6:
                    control.append([fecha, a, round(sim, 3), round(recuentos[fecha].get(a, 0), 3)])
            else:
                pend = x[3]
                for c in abiertas:
                    if pend <= 1e-9:
                        break
                    t = min(c["resto"], pend)
                    if t <= 0:
                        continue
                    c["resto"] -= t
                    pend -= t
                    motor[c["k"]][(x[1], x[2])] += t * c["unit"]
                if pend > 1e-9:
                    pendientes.append([pend, x[1], x[2]])
        faltante[a] = sum(pe[0] for pe in pendientes)
        for c in capas:
            if c["resto"] > 1e-9:
                motor[c["k"]][STOCK] += c["resto"] * c["unit"]

    res, pes = Counter(), Counter()
    detalle = []
    cp = tot = 0.0
    for k, man in manual.items():
        p = info[k]["pesos"]
        mo = motor.get(k, Counter())
        tm, tmo = sum(man.values()), sum(mo.values())
        if p <= 0 or tm <= 0 or tmo <= 0:
            continue
        c = sum(min(man[x] / tm, mo[x] / tmo) for x in set(man) | set(mo))
        b = "100%" if c > 0.995 else "90-99%" if c >= 0.9 else "50-89%" if c >= 0.5 else "<50%"
        res[b] += 1
        pes[b] += p
        cp += c * p
        tot += p
        detalle.append([info[k]["fecha"], info[k]["prov"], info[k]["nro"], k[1], info[k]["txt"], info[k]["via"], round(p, 2),
                        round(c * 100, 1), _txt(man, cult, camp), _txt(mo, cult, camp)])

    ok_rec = sum(1 for r in control if abs(r[2] - r[3]) <= max(0.005 * abs(r[3]), 0.01))
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    for fila in ([["Renglones de insumo desde el corte", "Cantidad"]] + [[k, v] for k, v in cobertura.items()]
                 + [[], ["Coincidencia con lo imputado a mano", "Factura+principio activo", "Importe $"]]
                 + [[b, res[b], round(pes[b], 2)] for b in ("100%", "90-99%", "50-89%", "<50%")]
                 + [["ponderada por $", None, round(cp / tot * 100, 1) if tot else None], [],
                    ["Control recuentos: stock simulado = contado", f"{ok_rec} de {len(control)}"]]):
        ws.append(fila)
    hojas = {
        "Diferencias": (["Fecha", "Proveedor", "Nro", "Principio activo", "Renglón", "Producto", "Importe $", "Coincidencia %",
                         "Manual", "Kardex"], sorted(detalle, key=lambda r: (r[7], -r[6]))),
        "Control recuentos": (["Fecha recuento", "Principio activo", "Simulado", "Contado"], sorted(control, key=lambda r: (r[0], r[1]))),
        "Sin producto": (["Fecha", "Proveedor", "Nro", "Rubro", "Renglón", "Importe $"], sin_sug),
    }
    for nombre, (enc, filas) in hojas.items():
        w = wb.create_sheet(nombre)
        w.append(enc)
        for f in filas:
            w.append(f)
    for w in wb.worksheets:
        for c in w[1]:
            c.font = Font(bold=True)
    destino = SALIDA / f"simulacion-kardex-corte-{date.today():%Y%m%d}.xlsx"
    wb.save(destino)
    print("cobertura", dict(cobertura))
    print("coincidencia", dict(res), "ponderada", round(cp / tot * 100, 1) if tot else None)
    print("recuentos ok", ok_rec, "de", len(control))
    print("Excel:", destino)


def _anterior(nombre: str | None) -> bool:
    """Campaña anterior al arranque (2025/2026): 'AAAA/AAAA' con inicio < 2025, o anual ('Avena 2025') <= 2025."""
    if not nombre or not nombre[:4].isdigit():
        return False
    y = int(nombre[:4])
    return y < CORTE.year if "/" in nombre else y <= CORTE.year


def _txt(c: Counter, cult, camp) -> str:
    t = sum(c.values()) or 1
    return " · ".join(("stock" if k == STOCK else f"{cult.get(k[0], k[0])} {camp.get(k[1], '')}".strip()) + f" {v / t * 100:.0f}%"
                      for k, v in sorted(c.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main()
