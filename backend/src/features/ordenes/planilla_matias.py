"""Órdenes de pulverización desde la planilla de Matías (18/11/2026).

Fuente: solapa "orden pulv LH" de la planilla de presupuesto agrícola (Dropbox). Columnas: CAMPO, POTRERO, CULTIVO,
FECHA, SUP, PRODUCT/LABOR, DOSIS, TOT UNIDADES, Moment. Cada FECHA es una orden; "PULV" es la labor (pulverización
terrestre), el resto son insumos con su nombre genérico.

Se lee solo cuando Sergio lo pide (botón "Leer ahora", al llegar la orden por WhatsApp; nunca automático).
Cada orden nueva se crea "Planificada" (el stock se descuenta al ejecutarla):
  - potrero → lotes del plan agrícola del cultivo y campaña (1B → 1B1, 6/6A → 6 + 6A, 6BC → 6B + 6C, 3A Loma → 3AL);
  - campaña: la del plan que tiene ese cultivo en ese lote y que todavía no se cosechó a la fecha de la orden;
  - nombre genérico → productos por principio activo (catálogo SENASA) y concentración; entre los que tienen stock se
    elige por FIFO de remitos (la entrada más vieja primero), descontando lo comprometido por otras órdenes
    planificadas; si no alcanza se reparte entre productos y el faltante queda informado.
Si la planilla no cierra (superficie × dosis distinto del total, lote repetido, potrero o producto desconocido) la
orden NO se crea: queda en el resultado con el motivo, para que Matías corrija la planilla.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.db.connection import execute_write, fetch_all, fetch_one

_log = logging.getLogger(__name__)

PLANILLA = Path(r"C:\Users\Sergio\Dropbox\La Herencia\presupuest Agri 26-27 LH.xlsx")
SOLAPA = "orden pulv LH"
TIPO_LABOR_PULVERIZACION = 1
TOLERANCIA_TOTAL = 0.02  # 2% entre superficie × dosis y el total de la planilla

CULTIVOS = {"TR": "Trigo", "GR": "Girasol", "MZ": "Maiz", "MZ DIF": "Maiz diferido", "AV": "Avena", "PAST": "Pastura",
            "PI": "Pastura", "SG": "Sorgo", "SO": "Sorgo", "CB": "Cebada"}

# Nombre genérico de la planilla → cómo reconocer el producto (principio activo del catálogo, nombre, concentración).
PRODUCTOS = {
    "GLIFOSATO": {"ia": ["GLIFOSATO"]},
    "24D ESTER ETILHEXIL": {"ia": ["2,4-D", "2,4 D", "2.4 D", "2,4D"]},
    "ACEITE VEGETAL METILADO": {"ia": ["ESTERES METILICOS"]},
    "AMISTAR XTRA": {"ia": ["AZOXISTROBINA", "CYPROCONAZOLE"], "todos": True},
    "ATRAZINA 90": {"ia": ["ATRAZINA"], "solo": True},
    "BIFENTRIN 10%": {"ia": ["BIFENTRIN"], "solo": True, "excluir": ["25"]},
    "CARFENTRAZONE": {"ia": ["CARFENTRAZONE"]},
    "CLETODIM": {"ia": ["CLETODIM"]},
    "CRIPTON XPRO": {"nombre": "CRIPTON XPRO"},
    "DICAMBA": {"ia": ["DICAMBA"], "solo": True},
    "FLUMETSULAM 12%": {"ia": ["FLUMETSULAM"], "solo": True},
    "FLUMIOXAZIN": {"ia": ["FLUMIOXAZIN"], "solo": True},
    "FLUROCLORIDONA": {"ia": ["FLUROCLORIDONA"], "solo": True},
    "LAMBDA 25%": {"ia": ["LAMBDACIALOTRINA"], "nombre_con": "25"},
    "METSULFURON": {"ia": ["METSULFURON"], "solo": True},
    "PARAQUAT": {"ia": ["PARAQUAT"]},
    "PICLORAM": {"ia": ["PICLORAM"], "solo": True},
    "S-METOLACLOR": {"ia": ["METOLACLOR"], "solo": True},
    "SILICONADO": {"ia": ["TRISILOXANO"], "nombre": "SILICONADO"},
    "SILICONADO BC": {"ia": ["TRISILOXANO"], "nombre": "SILICONADO"},
    "SOLOMON": {"nombre": "SOLOMON"},
    "SULFENTRAZONE": {"ia": ["SULFENTRAZONE"], "solo": True},
}

_lock = threading.Lock()


def _norm(t) -> str:
    return re.sub(r"\s+", " ", str(t or "").strip().upper())


def _dia(v) -> date:
    return v.date() if isinstance(v, datetime) else v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


# ------------------------------------------------------------------ lectura

def leer_planilla(path: Path = PLANILLA) -> dict[date, list[dict]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        ws = wb[SOLAPA]
        ordenes: dict[date, list[dict]] = defaultdict(list)
        for n, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            campo, potrero, cultivo, fecha, sup, prod, dosis, total, momento = (list(r[1:10]) + [None] * 9)[:9]
            if not campo or _norm(campo) == "CAMPO" or not prod or not fecha:
                continue
            ordenes[_dia(fecha)].append({"fila": n, "potrero": _norm(potrero), "cultivo": _norm(cultivo), "sup": float(sup or 0),
                                         "producto": _norm(prod), "dosis": float(dosis or 0), "total": float(total or 0),
                                         "momento": str(momento or "").strip()})
        return dict(ordenes)
    finally:
        wb.close()


def huella(filas: list[dict]) -> str:
    return hashlib.sha1(json.dumps(sorted((f["potrero"], f["cultivo"], f["sup"], f["producto"], f["dosis"]) for f in filas),
                                   default=str).encode()).hexdigest()


# ------------------------------------------------------------------ reglas puras

def _n(v: float) -> str:
    """Número en formato argentino, sin decimales de más (1,6 · 0,06 · 16)."""
    s = f"{v:,.3f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _prod(nombre: str) -> str:
    return nombre.strip().capitalize()


def problemas_de_planilla(filas: list[dict]) -> list[str]:
    """Pura: lo que impide crear la orden tal como está la planilla, en palabras para Matías, agrupado por potrero."""
    out = []
    sups = defaultdict(set)
    for f in filas:
        sups[(f["potrero"], f["cultivo"])].add(f["sup"])
    for (pot, cu), s in sups.items():
        if len(s) > 1:
            out.append(f"El potrero {pot} ({cultivo_de(cu, '') or cu}) figura más de una vez, con "
                       + " y con ".join(f"{_n(x)} ha" for x in sorted(s)) + ".")
    no_cierran = defaultdict(list)
    for f in filas:
        if f["producto"] == "PULV":
            continue
        if f["sup"] <= 0 or f["dosis"] <= 0:
            out.append(f"En el potrero {f['potrero']}, {_prod(f['producto'])} no tiene superficie o dosis.")
            continue
        calc = f["sup"] * f["dosis"]
        if f["total"] and abs(calc - f["total"]) > TOLERANCIA_TOTAL * max(calc, f["total"]):
            no_cierran[(f["potrero"], f["sup"])].append(f"{_prod(f['producto'])} dice {_n(f['total'])} y corresponde {_n(calc)}")
    for (pot, sup), detalles in no_cierran.items():
        out.append(f"En el potrero {pot} con {_n(sup)} ha, el total no coincide con superficie × dosis: " + "; ".join(detalles) + ".")
    return out


def potreros_a_lotes(potrero: str, lotes_plan: list[str]) -> list[str]:
    """Pura: nombre de potrero de Matías → lotes del plan (1B → 1B1, 6/6A → 6 + 6A, 6BC → 6B + 6C, 3A Loma → 3AL)."""
    plan = {_norm(l).replace(" ", ""): l for l in lotes_plan}
    p = _norm(potrero).replace(" LOMA", "L").replace(" BAJO", "B").replace(" ", "")
    partes = p.split("/") if "/" in p else [p]
    out = []
    for parte in partes:
        if parte in plan:
            out.append(plan[parte])
            continue
        m = re.fullmatch(r"(\d+)([A-Z]{2,})", parte)
        if m and all(m.group(1) + c in plan for c in m.group(2)):  # 6BC → 6B + 6C
            out += [plan[m.group(1) + c] for c in m.group(2)]
            continue
        sub = [v for k, v in plan.items() if k.startswith(parte)]  # 1B → 1B1
        if len(sub) == 1:
            out.append(sub[0])
        else:
            return []
    return out


def cultivo_de(codigo: str, momento: str) -> str | None:
    c = _norm(codigo)
    if c == "SJ":
        return "Soja segunda" if _norm(momento).startswith("S2") else "Soja primera"
    return CULTIVOS.get(c)


def producto_coincide(regla: dict, nombre: str, ia: str) -> bool:
    """Pura: un producto del catálogo corresponde al nombre genérico de la planilla."""
    nombre, ia = _norm(nombre), _norm(ia)
    if regla.get("nombre") and regla["nombre"] in nombre and not regla.get("ia"):
        return True
    if regla.get("ia"):
        partes = [x.strip() for x in ia.split("+")]
        hits = [t for t in regla["ia"] if any(t in p for p in partes)]
        ok = (len(hits) == len(regla["ia"])) if regla.get("todos") else bool(hits)
        if ok and regla.get("solo") and len(partes) > 1:
            ok = False
        if not ok and regla.get("nombre") and regla["nombre"] in nombre:
            ok = True
        if ok and regla.get("nombre_con") and regla["nombre_con"] not in nombre and regla["nombre_con"] not in ia:
            ok = False
        if ok and any(x in nombre for x in regla.get("excluir", [])):
            ok = False
        return ok
    return False


def asignar_fifo(cantidad: float, candidatos: list[dict]) -> tuple[list[tuple[int, float]], float]:
    """Pura: reparte la cantidad entre productos ordenados por su entrada más vieja con saldo (FIFO de remitos).
    `candidatos`: [{idProducto, disponible, desde}]. Devuelve [(idProducto, cantidad)] y el faltante."""
    resto, out = cantidad, []
    for c in sorted(candidatos, key=lambda c: (c["desde"] or date.max, c["idProducto"])):
        if resto <= 1e-9:
            break
        toma = min(resto, max(0.0, c["disponible"]))
        if toma > 1e-9:
            out.append((c["idProducto"], round(toma, 4)))
            resto -= toma
    return out, round(max(0.0, resto), 4)


# ------------------------------------------------------------------ datos

def _catalogo() -> list[dict]:
    return fetch_all("SELECT IdProducto AS id, Producto AS nombre, ISNULL(IngredienteActivo, '') AS ia FROM dbo.vw_ProductosBase")


def _comprometido() -> dict[int, float]:
    """Insumos de órdenes planificadas (todavía no descontados del stock)."""
    return {int(f["p"]): float(f["q"]) for f in fetch_all(
        "SELECT i.IdProducto AS p, SUM(i.CantidadTotal) AS q FROM dbo.Ordenes_Trabajo_Insumos i "
        "JOIN dbo.Ordenes_Trabajo o ON o.IdOrdenTrabajo = i.IdOrdenTrabajo WHERE o.Estado = 'Planificada' GROUP BY i.IdProducto")}


def _candidatos(generico: str, catalogo, stock, comprometido) -> tuple[list[dict], list[int]]:
    regla = PRODUCTOS.get(generico)
    if not regla:
        return [], []
    ids = [int(p["id"]) for p in catalogo if producto_coincide(regla, p["nombre"], p["ia"])]
    cands = []
    for pid in ids:
        s = stock.get(pid)
        if not s:
            continue
        libres = [c for c in s["capas"] if (c.get("restante") or 0) > 1e-9]
        disp = float(s["existencia"]) - comprometido.get(pid, 0.0)
        if disp > 1e-9:
            cands.append({"idProducto": pid, "disponible": disp, "desde": min((c["fecha"] for c in libres), default=None)})
    return cands, ids


def _ultimo_comprado(ids: list[int]) -> int | None:
    """Sin stock de ningún producto de la familia: el que se compró (remito) más recientemente; si nunca se compró,
    el más usado en órdenes. Así el faltante queda en el producto que se suele comprar."""
    if not ids:
        return None
    marcas = ",".join("?" * len(ids))
    f = fetch_one(f"SELECT TOP 1 rd.IdFormulado AS p FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito "
                  f"WHERE rd.IdFormulado IN ({marcas}) ORDER BY r.Fecha DESC", tuple(ids))
    if not f:
        f = fetch_one(f"SELECT TOP 1 IdProducto AS p FROM dbo.Ordenes_Trabajo_Insumos WHERE IdProducto IN ({marcas}) "
                      f"GROUP BY IdProducto ORDER BY COUNT(*) DESC", tuple(ids))
    return int(f["p"]) if f else ids[0]


def _lotes_plan(id_cultivo: int) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    for f in fetch_all("SELECT p.[IdCampaña] AS ca, l.IdLote AS idLote, l.[Numero Lote] AS lote, l.Superficie AS sup "
                       "FROM dbo.PlanAgricola p JOIN dbo.Lotes l ON l.IdLote = p.IdLote WHERE p.IdCultivo = ? AND ISNULL(p.NoSembrado, 0) = 0",
                       (id_cultivo,)):
        out[int(f["ca"])].append(f)
    return out


def _campania_para(id_cultivo: int, fecha: date, potrero: str) -> tuple[int, list[dict]] | None:
    """La campaña del plan con ese cultivo en ese potrero que todavía no se cosechó a la fecha (la más vieja abierta)."""
    nombres = {int(f["i"]): f["c"] for f in fetch_all("SELECT [IdCampaña] AS i, [Campaña] AS c FROM dbo.[Campañas]")}
    from src.features.resultado_cultivo import formularios_access as F
    try:
        id_destino = F._destino(id_cultivo)[0]
    except ValueError:
        id_destino = None
    opciones = []
    for ca, lotes in _lotes_plan(id_cultivo).items():
        nombre = nombres.get(ca, "")
        if not nombre[:4].isdigit():
            continue
        fin = date(int(nombre[:4]) + (1 if "/" in nombre else 0), 12 if "/" not in nombre else 6, 30 if "/" in nombre else 31)
        inicio = date(int(nombre[:4]) - 1, 7, 1)
        if not (inicio <= fecha <= fin):
            continue
        cosecha = fetch_one("SELECT MAX(Fecha) AS f FROM dbo.[Datos Cosecha] WHERE IdDestino = ? AND IdCampaña = ?",
                            (id_destino, ca)) if id_destino else None
        if cosecha and cosecha["f"] and _dia(cosecha["f"]) < fecha:
            continue
        elegidos = potreros_a_lotes(potrero, [l["lote"] for l in lotes])
        if elegidos:
            opciones.append((nombre, ca, [l for l in lotes if l["lote"] in elegidos]))
    if not opciones:
        return None
    _, ca, lotes = sorted(opciones)[0]
    return ca, lotes


# ------------------------------------------------------------------ armado de la orden

def armar_orden(fecha: date, filas: list[dict]) -> dict:
    """Arma los datos de `crear_orden` (sin escribir). Devuelve {"datos", "faltantes", "problemas", "detalle"}."""
    from src.features.remitos.stock_datos import calcular_stock

    problemas = problemas_de_planilla(filas)
    cultivos = {f["Cultivo"]: int(f["IdCultivo"]) for f in fetch_all("SELECT IdCultivo, Cultivo FROM dbo.Cultivos")}
    stock, catalogo, comprometido = calcular_stock(), _catalogo(), _comprometido()
    # Necesidad por genérico, repartida por lote del sistema.
    necesidad: dict[str, list[dict]] = defaultdict(list)
    for f in filas:
        if f["producto"] == "PULV" or problemas:
            continue
        nombre_cultivo = cultivo_de(f["cultivo"], f["momento"])
        if not nombre_cultivo or nombre_cultivo not in cultivos:
            problemas.append(f"fila {f['fila']}: cultivo '{f['cultivo']}' desconocido")
            continue
        id_cultivo = cultivos[nombre_cultivo]
        res = _campania_para(id_cultivo, fecha, f["potrero"])
        if not res:
            problemas.append(f"fila {f['fila']}: el potrero {f['potrero']} no está en el plan de {nombre_cultivo} para esa fecha")
            continue
        ca, lotes = res
        sup_lotes = sum(float(l["sup"]) for l in lotes) or 1.0
        for l in lotes:
            necesidad[f["producto"]].append({"idLote": int(l["idLote"]), "idCultivo": id_cultivo, "idCampania": ca,
                                             "dosisHa": f["dosis"], "superficie": round(f["sup"] * float(l["sup"]) / sup_lotes, 2)})
    renglones, faltantes = [], []
    for generico, dist in necesidad.items():
        if generico not in PRODUCTOS:
            problemas.append(f"producto '{generico}': no sé a qué producto del stock corresponde")
            continue
        total = round(sum(d["dosisHa"] * d["superficie"] for d in dist), 4)
        cands, ids = _candidatos(generico, catalogo, stock, comprometido)
        partes, falta = asignar_fifo(total, cands)
        if falta > 0:
            base = partes[-1][0] if partes else _ultimo_comprado(ids)
            if base is None:
                problemas.append(f"producto '{generico}': no existe en el catálogo")
                continue
            faltantes.append({"producto": _prod(generico), "falta": falta, "idProducto": base,
                              "unidad": (fetch_one("SELECT UnidadBase AS u FROM dbo.Producto_Unidad WHERE IdProducto = ?", (base,)) or {}).get("u")})
            partes = [(p, q + (falta if p == base else 0)) for p, q in partes] if any(p == base for p, _ in partes) \
                else partes + [(base, falta)]
        for pid, q in partes:
            share = q / total
            unidad = stock.get(pid, {}).get("unidadBase") or (fetch_one("SELECT UnidadBase AS u FROM dbo.Producto_Unidad WHERE IdProducto = ?", (pid,)) or {}).get("u") or "Lts"
            renglones.append({"idProducto": pid, "unidad": unidad, "cantidadTotal": round(q, 4),
                              "distribuciones": [{**d, "superficie": d["superficie"], "dosisHa": round(d["dosisHa"] * share, 6)} for d in dist]})
    contratista = fetch_one("SELECT TOP 1 IdContratistaContacto AS c FROM dbo.Ordenes_Trabajo WHERE IdTipoLabor = ? "
                            "AND IdContratistaContacto IS NOT NULL ORDER BY FechaPedido DESC", (TIPO_LABOR_PULVERIZACION,))
    momentos = sorted({f["momento"] for f in filas if f["momento"]})
    datos = {"fecha": fecha, "idTipoLabor": TIPO_LABOR_PULVERIZACION, "idContratistaContacto": (contratista or {}).get("c"),
             "observaciones": f"Orden de Matías del {fecha:%d/%m/%Y} (planilla de presupuesto): {', '.join(momentos)}"[:500],
             "renglones": renglones}
    return {"datos": datos, "faltantes": faltantes, "problemas": problemas}


# ------------------------------------------------------------------ registro de lo importado y corrida

def _momentos(filas: list[dict]) -> list[str]:
    return sorted({f["momento"] for f in filas if f["momento"]})


def _importadas() -> dict[date, dict]:
    return {_dia(f["Fecha"]): f for f in fetch_all("SELECT Fecha, IdOrdenTrabajo, Huella FROM dbo.OrdenesPlanillaMatias")}


def leer_y_cargar(path: Path = PLANILLA, solo_ver: bool = False) -> dict:
    """Lee la planilla y crea las órdenes nuevas. Devuelve lo hecho y lo que quedó para revisar."""
    from src.features.ordenes import repository

    with _lock:
        ordenes = leer_planilla(path)
        hechas = _importadas()
        resultado = {"leida": datetime.now().isoformat(timespec="seconds"), "creadas": [], "paraRevisar": [], "cambiadas": []}
        for fecha, filas in sorted(ordenes.items()):
            h = huella(filas)
            previa = hechas.get(fecha)
            if previa:
                if previa["Huella"] and previa["Huella"] != h:
                    resultado["cambiadas"].append({"fecha": fecha.isoformat(), "idOrden": previa["IdOrdenTrabajo"],
                                                   "detalle": "Matías cambió esta orden en la planilla después de cargarla"})
                continue
            armado = armar_orden(fecha, filas)
            if armado["problemas"] or not armado["datos"]["renglones"]:
                resultado["paraRevisar"].append({"fecha": fecha.isoformat(), "momentos": _momentos(filas),
                                                 "problemas": armado["problemas"] or ["La orden no tiene insumos."]})
                continue
            if solo_ver:
                resultado["creadas"].append({"fecha": fecha.isoformat(), "idOrden": None, "momentos": _momentos(filas), "faltantes": armado["faltantes"],
                                             "renglones": len(armado["datos"]["renglones"])})
                continue
            creada = repository.crear_orden(armado["datos"], confirmar=True)
            execute_write("INSERT INTO dbo.OrdenesPlanillaMatias (Fecha, IdOrdenTrabajo, Huella) VALUES (?, ?, ?)",
                          (fecha, creada["idOrden"], h))
            resultado["creadas"].append({"fecha": fecha.isoformat(), "idOrden": creada["idOrden"], "momentos": _momentos(filas),
                                         "faltantes": armado["faltantes"]})
        if not solo_ver:
            execute_write("INSERT INTO dbo.OrdenesPlanillaMatiasLecturas (Resultado) VALUES (?)",
                          (json.dumps(resultado, ensure_ascii=False, default=str),))
        return resultado


def ultima_lectura() -> dict | None:
    f = fetch_one("SELECT TOP 1 Resultado AS r FROM dbo.OrdenesPlanillaMatiasLecturas ORDER BY IdLectura DESC")
    return json.loads(f["r"]) if f else None


def marcar_resuelta(fecha_iso: str, path: Path = PLANILLA) -> dict:
    """19/11/2026 (Sergio): un aviso de la planilla que ya se resolvió a mano (orden cargada en el sistema, o el cambio
    ya revisado) se deja de mostrar. Se registra con la huella actual: si Matías la vuelve a cambiar, avisa de nuevo."""
    fecha = date.fromisoformat(fecha_iso[:10])
    with _lock:
        filas = leer_planilla(path).get(fecha)
        h = huella(filas) if filas else None
        if _importadas().get(fecha):
            execute_write("UPDATE dbo.OrdenesPlanillaMatias SET Huella = ? WHERE Fecha = ?", (h, fecha))
        else:
            execute_write("INSERT INTO dbo.OrdenesPlanillaMatias (Fecha, IdOrdenTrabajo, Huella) VALUES (?, NULL, ?)", (fecha, h))
        u = ultima_lectura() or {}
        if u:
            for k in ("paraRevisar", "cambiadas"):
                u[k] = [x for x in u.get(k, []) if x.get("fecha", "")[:10] != fecha.isoformat()]
            execute_write("INSERT INTO dbo.OrdenesPlanillaMatiasLecturas (Resultado) VALUES (?)",
                          (json.dumps(u, ensure_ascii=False, default=str),))
        return u
