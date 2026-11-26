"""052 T027: verificación del resultado ganadero contra la planilla "Historico Negocio Ganadero (ver 2).xlsx".

SOLO LECTURA (no escribe en la base). Vista campaña julio–junio, campo La Herencia, 2016/17 a 2023/24.
- SC-001a: ventas, comercialización, sanidad e inseminación y gastos generales, comprobante por comprobante en pesos
  (solapas "Ventas Hacienda", "Gastos Comercializacion Liq." y "Compras") y totales en US$ (la planilla usa dólar
  billete; el sistema, el dólar de gestión: la diferencia de US$ con pesos iguales es de TC).
- SC-001b: forrajes por valor contra "Cultivos y forrajes" y "Amort Pasturas" (valores cargados a mano), sin ajustar.
Uso (desde backend/): python -m scripts.ganaderia_verificacion_planilla_20261126
Salida: specs/052-modulo-ganadero/verificacion-planilla-detalle-20261126.xlsx y un resumen por consola (JSON).
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl  # noqa: E402

from src.features.ganaderia import costos, periodos, resultado  # noqa: E402

PLANILLA = Path(r"C:\Users\Sergio\Documents\La Herencia\Ganaderia\Historico Negocio Ganadero (ver 2).xlsx")
SALIDA = Path(__file__).resolve().parents[2] / "specs/052-modulo-ganadero/verificacion-planilla-detalle-20261126.xlsx"
ANIOS = range(2016, 2024)
LA_HERENCIA = 1
CORTE = "2024-03-16"  # último comprobante de la planilla: 2023/24 se compara solo hasta acá
FORRAJES = {"avena", "pastura", "maiz", "maiz silo", "maiz diferido", "sorgo", "amortizacion pasturas", "silo"}
# bloque de SC-001a de cada rubro de la planilla
BLOQUE = {
    "productos veterinarios": "Sanidad", "inseminacion": "Sanidad", "analisis laboratorio": "Sanidad",
    "aranceles vacunacion": "Sanidad", "honorarios profesionales": "Sanidad", "tacto/ecografia": "Sanidad",
    "vacunas": "Sanidad", "flete hacienda": "Comercialización", "gastos comercializacion": "Comercialización",
    "financiamiento": "Gastos generales", "flete insumos": "Gastos generales",
    "gastos de administracion": "Gastos generales", "honorarios administracion": "Gastos generales",
    "movilidad": "Gastos generales", "insumos generales": "Gastos generales", "insumos productivos": "Gastos generales",
    "personal eventual": "Gastos generales", "secado": "Gastos generales", "seguros laborales": "Gastos generales",
    "servicio logistica": "Gastos generales", "alimento feed lot": "Alimentación (compras)",
    "alimento general": "Alimentación (compras)",
}
# los rubros del sistema que la planilla no tenía se listan aparte (no son diferencia de SC-001a)
NUEVOS = "Rubros que la planilla no tenía"


def _n(t) -> str:
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", t)


def _doc(t) -> str:
    """'0001-00000457' / '00001 - 457' → '1-457'."""
    partes = [p.lstrip("0") or "0" for p in re.findall(r"\d+", str(t or ""))]
    return "-".join(partes[-2:]) if partes else ""


def _anio(f) -> int:
    a = periodos.anio_inicio(f.date() if isinstance(f, datetime) else f, "campania")
    return a if a in ANIOS else -1


def planilla():
    wb = openpyxl.load_workbook(PLANILLA, read_only=True, data_only=True)
    ven = defaultdict(lambda: [0.0, 0.0, None])  # (año, doc) → pesos, usd, fecha
    for r in wb["Ventas Hacienda"].iter_rows(min_row=2, values_only=True):
        if not r[0] or r[2] != LA_HERENCIA:
            continue
        k = (_anio(r[0]), _doc(r[1]))
        ven[k][0] += float(r[8] or 0)
        ven[k][1] += float(r[9] or 0)
        ven[k][2] = r[0]
    com = defaultdict(lambda: [0.0, 0.0, None])
    for r in wb["Gastos Comercializacion Liq."].iter_rows(min_row=2, values_only=True):
        if not r[0] or r[1] != LA_HERENCIA:
            continue
        k = (_anio(r[0]), _doc(r[3]))
        com[k][0] += float(r[10] or 0)
        com[k][1] += float(r[11] or 0)
        com[k][2] = (r[0], r[2])
    cmp_ = defaultdict(lambda: [0.0, 0.0, None])  # (año, bloque, doc) → pesos, usd, (fecha, proveedor, rubros)
    for r in wb["Compras"].iter_rows(min_row=2, values_only=True):
        if not r[0] or _n(r[9]) != "ganaderia" or _n(r[10]) not in BLOQUE:
            continue
        k = (_anio(r[0]), BLOQUE[_n(r[10])], _doc(r[3]))
        cmp_[k][0] += float(r[13] or 0)
        cmp_[k][1] += float(r[14] or 0)
        cmp_[k][2] = (r[0], r[1], _n(r[10]))
    forr = {(_n(r[0]), int(str(r[1])[:4])): float(r[2] or 0)
            for r in wb["Cultivos y forrajes"].iter_rows(min_row=2, values_only=True) if r[0] and r[1]}
    amort = {int(r[0]): float(r[2] or 0) for r in wb["Amort Pasturas"].iter_rows(min_row=3, values_only=True)
             if isinstance(r[0], (int, float))}
    principal = {}
    filas = list(wb["Negocio Ganadero La Herencia"].iter_rows(min_row=1, max_row=56, values_only=True))
    for r in filas[2:]:
        if r[0]:
            principal[_n(r[0])] = {2016 + i: float(v or 0) for i, v in enumerate(r[1:9])}
    return ven, com, cmp_, forr, amort, principal


def sistema():
    fc = costos.forrajes(min(ANIOS), max(ANIOS), "campania")
    out = {}
    for a in ANIOS:
        # ventas y liquidaciones: solo La Herencia (como la planilla); compras: todos los campos (la planilla no
        # separaba costos por campo)
        lh = resultado.periodo(a, "campania", fc, LA_HERENCIA)["celdas"]
        todos = resultado.periodo(a, "campania", fc, None)["celdas"]
        celdas = {}
        for k in set(lh) | set(todos):
            c_t, c_l = todos.get(k), lh.get(k)
            de_compras = any(str(i.get("enlace") or "").startswith("/compras/") for i in (c_t or c_l)["detalle"])
            celdas[k] = (c_t if de_compras else c_l) or {"pesos": 0.0, "usd": 0.0, "detalle": []}
        out[a] = celdas
    return out, fc


def destino_050(doc: str, contacto: str | None) -> str:
    """Dónde quedó en el sistema un comprobante de la planilla que no aparece en Ganadería."""
    from src.db.connection import fetch_all

    rs = fetch_all(
        "SELECT d.[Producto/Servicio] item, d.IdCentroCostos cc, t.Destino destino, cu.Cultivo cultivo, "
        "(SELECT TOP 1 c2.Cultivo FROM dbo.Map_CultivoResultado m JOIN dbo.Cultivos c2 ON c2.IdCultivo = m.IdCultivo "
        " WHERE m.IdDestino = d.IdDestino AND m.Activo = 1) cultivoDestino "
        "FROM dbo.Compras c JOIN dbo.Det_Compras d ON d.IdCompra = c.IdDeuda "
        "LEFT JOIN dbo.Contactos k ON k.IdContacto = c.IdContacto "
        "LEFT JOIN dbo.TamizRenglones t ON t.IdDetalleCompra = d.IdDetalleCompra AND t.Vigente = 1 "
        "LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = t.IdCultivo "
        "WHERE k.[Razon Social] LIKE ? AND c.[Nro Documento] LIKE ?",
        (f"%{(contacto or '').split()[0] if contacto else ''}%", f"%{doc.split('-')[-1]}"))
    if not rs:
        return "no está cargado en el sistema"
    def uno(r):
        if r["destino"]:
            return r["destino"] + (f" ({r['cultivo']})" if r["cultivo"] else "")
        if r["cultivoDestino"]:
            return f"costo del cultivo {r['cultivoDestino']}"
        return "centro Ganadería" if r["cc"] == 2 else "otro centro de costos"
    d = sorted({uno(r) for r in rs})
    return "en el sistema: " + ", ".join(d)


def bloque_sistema(grupo: str, rubro: str) -> str | None:
    if grupo == "Ventas":
        return None if _n(rubro).startswith("traslados") else "Ventas"
    if grupo == "Comercializacion":
        return "Comercialización"
    if grupo == "Sanidad":
        return "Sanidad"
    if grupo in ("Directos", "Estructura"):
        return BLOQUE.get(_n(rubro), NUEVOS)
    if grupo == "Alimentacion" and _n(rubro) in ("alimento feed lot", "alimento general"):
        return "Alimentación (compras)"
    if grupo == "Alimentacion" and _n(rubro) == "pastaje (pagado)":
        return NUEVOS
    return None


def main() -> None:
    ven, com, cmp_, forr, amort, principal = planilla()
    celdas, fc = sistema()
    tot = defaultdict(lambda: {"pp": 0.0, "pu": 0.0, "sp": 0.0, "su": 0.0})
    pla_doc, sis_doc = defaultdict(float), defaultdict(float)
    info = {}
    for (a, d), (p, u, f) in ven.items():
        tot[(a, "Ventas")]["pp"] += p
        tot[(a, "Ventas")]["pu"] += u
        pla_doc[(a, "Ventas", d)] += p
        info.setdefault((a, "Ventas", d), (f, ""))
    for (a, d), (p, u, x) in com.items():
        tot[(a, "Comercialización")]["pp"] += p
        tot[(a, "Comercialización")]["pu"] += u
        pla_doc[(a, "Comercialización", d)] += p
        info.setdefault((a, "Comercialización", d), x)
    for (a, b, d), (p, u, x) in cmp_.items():
        tot[(a, b)]["pp"] += p
        tot[(a, b)]["pu"] += u
        pla_doc[(a, b, d)] += p
        info.setdefault((a, b, d), (x[0], x[1]))
    rubros_sis = defaultdict(set)
    for a, cs in celdas.items():
        for (g, r), c in cs.items():
            b = bloque_sistema(g, r)
            if not b:
                continue
            items = [it for it in c["detalle"] if not it.get("fecha") or str(it["fecha"])[:10] <= CORTE]
            tot[(a, b)]["sp"] += sum(float(it.get("importe") or 0) for it in items)
            tot[(a, b)]["su"] += c["usd"] if len(items) == len(c["detalle"]) else float("nan")
            for it in items:
                k = (a, b, _doc(it.get("documento")))
                sis_doc[k] += float(it.get("importe") or 0)
                rubros_sis[k].add(r)
                if k not in info:
                    info[k] = (it.get("fecha"), it.get("contacto"))
    difs = []
    for k in sorted(set(pla_doc) | set(sis_doc), key=lambda x: (x[0], x[1], x[2])):
        p, s = round(pla_doc.get(k, 0.0), 2), round(sis_doc.get(k, 0.0), 2)
        if abs(p - s) >= 1:
            f, quien = info.get(k, (None, None))
            estado = "solo en la planilla" if k not in sis_doc else "solo en el sistema" if k not in pla_doc else "importe distinto"
            difs.append({"campania": periodos.etiqueta(k[0]), "bloque": k[1], "documento": k[2],
                         "fecha": str(f)[:10] if f else "", "contacto": quien or "", "planilla": p, "sistema": s,
                         "diferencia": round(s - p, 2), "estado": estado,
                         "rubroSistema": ", ".join(sorted(rubros_sis.get(k, []))),
                         "dondeQuedo": destino_050(k[2], quien) if k not in sis_doc and k[1] != "Ventas" else ""})
    tot = {k: v for k, v in tot.items() if k[0] in ANIOS}
    difs = [d for d in difs if d["campania"][:4].isdigit() and int(d["campania"][:4]) in ANIOS and d["bloque"] != NUEVOS]
    resumen = [{"campania": periodos.etiqueta(a), "bloque": b, "planillaPesos": round(v["pp"], 2),
                "sistemaPesos": round(v["sp"], 2), "difPesos": round(v["sp"] - v["pp"], 2),
                "planillaUsd": round(v["pu"], 2), "sistemaUsd": None if v["su"] != v["su"] else round(v["su"], 2),
                "difUsd": None if v["su"] != v["su"] else round(v["su"] - v["pu"], 2)}
               for (a, b), v in sorted(tot.items())]
    # SC-001b: forrajes por valor (US$), sin mirar el rótulo de la fila
    sis_forr = defaultdict(float)
    for f in fc:
        sis_forr[(_n(f["rubro"]) if f["rubro"] != f["cultivo"] else _n(f["cultivo"]), f["periodo"])] += f["usd"]
    forrajes = []
    for a in ANIOS:
        pla = {k[0]: v for k, v in forr.items() if k[1] == a and v}
        if a in amort:
            pla["amortizacion pasturas (amort pasturas)"] = amort[a]
        sis = {k[0]: v for k, v in sis_forr.items() if k[1] == a and abs(v) >= 1}
        fila_ppal = {n: principal[n][a] for n in ("avena", "pastura", "maiz", "maiz silo", "maiz diferido", "sorgo",
                                                  "confeccion silo") if n in principal and principal[n].get(a)}
        forrajes.append({"campania": periodos.etiqueta(a), "solapaFuente": {k: round(v, 2) for k, v in pla.items()},
                         "solapaPrincipal": {k: round(v, 2) for k, v in fila_ppal.items()},
                         "sistema": {k: round(v, 2) for k, v in sis.items()},
                         "totalFuente": round(sum(pla.values()), 2), "totalSistema": round(sum(sis.values()), 2)})
    wb = openpyxl.Workbook()
    for nombre, filas in (("Resumen", resumen), ("Diferencias por comprobante", difs)):
        ws = wb.create_sheet(nombre)
        if filas:
            ws.append(list(filas[0]))
            for f in filas:
                ws.append(list(f.values()))
    ws = wb.create_sheet("Forrajes")
    ws.append(["Campaña", "Concepto", "Solapa fuente (US$)", "Solapa principal (US$)", "Sistema (US$)"])
    for f in forrajes:
        for k in sorted(set(f["solapaFuente"]) | set(f["sistema"]) | set(f["solapaPrincipal"])):
            ws.append([f["campania"], k, f["solapaFuente"].get(k), f["solapaPrincipal"].get(k), f["sistema"].get(k)])
    del wb["Sheet"]
    wb.save(SALIDA)
    print(json.dumps({"resumen": resumen, "diferencias": len(difs), "porEstado": {
        e: sum(1 for d in difs if d["estado"] == e) for e in ("solo en la planilla", "solo en el sistema", "importe distinto")},
        "forrajes": forrajes}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
