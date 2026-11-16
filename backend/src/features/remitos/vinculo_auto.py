"""Vínculo automático remito ↔ factura (050 US9, research R-04; regla validada el 16/11/2026).

Misma regla que la simulación y la revisión forense (scripts/simulacion_vinculo_orden_050.py):
  · mismo proveedor; mismo producto o equivalente (mismo principio activo, o la misma familia de fertilizante:
    arrancador / urea), porque las marcas se intercambian según lo que haya;
  · los renglones de la factura se agrupan por producto (Sergio parte cada producto en un renglón por cultivo);
  · primero un remito que cubra la factura entera; si no, producto por producto;
  · la misma cantidad (±1%) o una combinación exacta de entregas parciales;
  · remito hasta VENTANA_DIAS antes o después de la factura (el proveedor guarda lo pedido y factura antes o
    después: Bayá Casal facturó 199 días después). La ventana es para emparejar factura y remito; el producto
    puede quedar en el galpón todo lo que haga falta (FIFO);
  · entre varios candidatos, el más cercano en fecha (antes de la factura primero); si empatan, a revisión.
Nunca vincula más de lo que tiene el renglón de factura ni toma un renglón de remito que ya tiene factura.
Lo dudoso va a VinculoRemitoPendiente con los candidatos.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from itertools import combinations

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

_log = logging.getLogger(__name__)

VENTANA_DIAS = 270
TOLERANCIA = 0.01  # 1% de la cantidad
MAX_REMITOS_COMBINADOS = 4
_EPS = 1e-6


def _fecha(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v


def en_ventana(fecha_factura, fecha_remito) -> bool:
    ff, fr = _fecha(fecha_factura), _fecha(fecha_remito)
    if ff is None or fr is None:
        return False
    return abs((fr - ff).days) <= VENTANA_DIAS


def _distancia(fecha_factura, fecha_remito) -> int:
    """Días entre factura y remito; un remito posterior a la factura pesa 30 días más (primero los anteriores)."""
    ff, fr = _fecha(fecha_factura), _fecha(fecha_remito)
    return abs((fr - ff).days) + (0 if fr <= ff else 30)


def _iguales(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCIA * max(abs(a), abs(b), 1.0)


def combinaciones_exactas(pendiente: float, candidatos: list[dict]) -> list[tuple[dict, ...]]:
    """Subconjuntos de candidatos (cada uno con `disponible`, en base) cuya suma es `pendiente` (±1%)."""
    utiles = [c for c in candidatos if c["disponible"] > _EPS]
    out = []
    for n in range(1, min(MAX_REMITOS_COMBINADOS, len(utiles)) + 1):
        for combo in combinations(utiles, n):
            if _iguales(sum(c["disponible"] for c in combo), pendiente):
                out.append(combo)
    return out


def decidir(renglon: dict, candidatos: list[dict]) -> dict:
    """Pura. `renglon`: {fecha, pendiente (base)}; `candidatos`: renglones de remito equivalentes del proveedor con
    {idDetalleRemito, fecha, disponible (base), factor}. Devuelve {'accion': 'vincular', 'items'} |
    {'accion': 'revisar', 'motivo', 'candidatos'} | {'accion': 'nada'}."""
    if renglon["pendiente"] <= _EPS:
        return {"accion": "nada"}
    en_v = [c for c in candidatos if en_ventana(renglon["fecha"], c["fecha"]) and c["disponible"] > _EPS]
    if not en_v:
        return {"accion": "nada"}  # todavía no llegó el remito
    combos = combinaciones_exactas(renglon["pendiente"], en_v)
    if combos:
        dist = lambda combo: max(_distancia(renglon["fecha"], c["fecha"]) for c in combo)
        combos.sort(key=lambda combo: (len(combo), dist(combo)))
        mejor = combos[0]
        empate = [c for c in combos[1:] if len(c) == len(mejor) and dist(c) == dist(mejor)]
        if not empate:
            return {"accion": "vincular", "items": [{"idDetalleRemito": c["idDetalleRemito"], "cantidadBase": c["disponible"]}
                                                    for c in mejor]}
        motivo = "Varios remitos posibles con la misma cantidad y fecha"
    else:
        motivo = "Las cantidades de los remitos no coinciden con la factura"
    return {"accion": "revisar", "motivo": motivo,
            "candidatos": [{"idDetalleRemito": c["idDetalleRemito"], "disponible": c["disponible"]} for c in en_v]}


# ---------------------------------------------------------------- equivalencia de productos

def _normalizar(t) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().upper()
    return " ".join(t.split())


def familia_fertilizante(texto: str | None) -> str | None:
    """'ARRANCADOR' (más fósforo) o 'UREA' (más nitrógeno): Sergio los nombra con cualquier producto del catálogo."""
    t = _normalizar(texto)
    if "UREA" in t:
        return "UREA"
    if "ARRANCADOR" in t or "PROTERRA 740" in t or re.search(r"\bNP\s*\d", t):
        return "ARRANCADOR"
    m = re.search(r"(\d+)\s*N\W*(\d+)\s*P", t)
    if m:
        return "ARRANCADOR" if int(m.group(2)) > int(m.group(1)) else "UREA"
    return None


def clave_producto(id_producto: int, cache: dict | None = None) -> str:
    """Clave de equivalencia: la familia de fertilizante, o el principio activo normalizado, o el propio producto."""
    if cache is not None and id_producto in cache:
        return cache[id_producto]
    p = fetch_one("SELECT Producto AS n, TipoProducto AS t, IngredienteActivo AS a FROM dbo.vw_ProductosBase WHERE IdProducto = ?",
                  (id_producto,))
    clave = f"#{id_producto}"
    if p:
        fam = familia_fertilizante(p["n"]) if (p["t"] or "") == "Fertilizante" else None
        ia = _normalizar(p["a"]).replace("EQUIVALENTE", "")
        ia = " ".join(ia.split()[:4])
        if fam:
            clave = f"FAMILIA {fam}"
        elif ia and (p["t"] or "") not in ("Semilla",):
            clave = f"IA {ia}"
    if cache is not None:
        cache[id_producto] = clave
    return clave


# ---------------------------------------------------------------- acceso a datos

def _renglones_factura(id_compra: int) -> list[dict]:
    return fetch_all(
        """
        SELECT d.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, d.IdFormulado AS idProducto,
               d.Unidad AS unidad, ISNULL(d.Cantidad, 0) AS cantidad, c.Fecha AS fecha, c.IdContacto AS idProveedor,
               ISNULL((SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra), 0) AS vinculada
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1
        WHERE d.IdCompra = ? AND tz.Destino = 'CultivoStock' AND tz.Estado = 'Aprobada' AND NULLIF(d.IdFormulado, 0) IS NOT NULL
          AND c.[Tipo documento] = 'Factura' AND ISNULL(d.Unidad, '') NOT IN ('ARS', 'USD') AND ISNULL(d.Cantidad, 0) > 0
        """,
        (id_compra,),
    )


def _remitos_libres(id_proveedor: int) -> list[dict]:
    """Renglones de remito del proveedor sin ninguna factura vinculada (no anulados)."""
    return fetch_all(
        """
        SELECT rd.IdDetalleRemito AS idDetalleRemito, rd.IdRemito AS idRemito, r.Fecha AS fecha, rd.IdFormulado AS idProducto,
               rd.[Unidad Medida] AS unidad, ISNULL(rd.Cantidad, 0) AS cantidad
        FROM dbo.Remitos_Detalles rd JOIN dbo.Remitos r ON r.IdRemito = rd.IdRemito
        LEFT JOIN dbo.Remitos_Extra x ON x.IdRemito = r.IdRemito
        WHERE COALESCE(r.IdContacto, r.IdProveedor) = ? AND ISNULL(x.Anulado, 0) = 0 AND ISNULL(rd.Cantidad, 0) > 0
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito)
        """,
        (id_proveedor,),
    )


def _ya_pendiente(id_detalle_compra: int) -> bool:
    return fetch_one("SELECT 1 AS x FROM dbo.VinculoRemitoPendiente WHERE IdDetalleCompra = ? AND Resuelto = 0 AND Tipo = 'remito'",
                     (id_detalle_compra,)) is not None


def proponer_por_compra(id_compra: int) -> dict:
    """Sin escribir: {'vincular': [{idRemito, items:[{idDetalleRemito, idDetalleCompra, cantidad}]}], 'revisar': [...]}."""
    from src.features.remitos.stock_datos import equivalencias, factor_a_base, unidades_base

    bases, equiv = unidades_base(), equivalencias()
    cache: dict = {}

    def a_base(pid, unidad, q):
        """Cantidad en la unidad base del producto. La misma unidad escrita distinto (Kilos/KGS, BOL/BOLSA,
        LITROS/LTS, PACK) no es una conversión: vale 1. Si no hay forma de convertir, queda la cantidad tal cual."""
        from src.features.remitos.stock_datos import _familia_unidad
        u = (unidad or "").strip().upper()
        if clave_producto(pid, cache).startswith("FAMILIA") and (u.startswith("TON") or (not u and q < 100)):
            return q * 1000  # fertilizante en toneladas (o sin unidad y cantidad chica) contra remito en kilos
        f, falta = factor_a_base(pid, unidad, bases, equiv)
        return q * f if not falta else q

    renglones = _renglones_factura(id_compra)
    if not renglones:
        return {"vincular": [], "revisar": []}
    fecha_fac = renglones[0]["fecha"]
    # Grupos de la factura por producto equivalente, con lo pendiente de cada renglón (en base y en su unidad).
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in renglones:
        pend = float(r["cantidad"]) - float(r["vinculada"])
        if pend > _EPS:
            grupos[clave_producto(r["idProducto"], cache)].append({**r, "pendiente": pend,
                                                                   "pendBase": a_base(r["idProducto"], r["unidad"], pend)})
    if not grupos:
        return {"vincular": [], "revisar": []}
    libres = []
    for c in _remitos_libres(renglones[0]["idProveedor"]):
        if not en_ventana(fecha_fac, c["fecha"]):
            continue
        libres.append({**c, "disponible": a_base(c["idProducto"], c["unidad"], float(c["cantidad"])),
                       "clave": clave_producto(c["idProducto"], cache)})
    usados: set[int] = set()

    def items_grupo(lineas, asignacion):
        """Reparte los renglones de remito elegidos entre los renglones de factura del grupo (cada uno con su cantidad)."""
        out = []
        for rem in asignacion:
            for l in lineas:
                out.append({"idDetalleRemito": rem["idDetalleRemito"], "idRemito": rem["idRemito"], "idDetalleCompra": l["idDetalleCompra"],
                            "cantidad": l["pendiente"] * rem["disponible"] / sum(x["disponible"] for x in asignacion)})
        return out

    vincular: list[dict] = []
    revisar: list[dict] = []
    # 1) Un remito que cubra la factura entera (todos los grupos, cada uno con un renglón distinto del remito).
    por_remito = defaultdict(list)
    for c in libres:
        por_remito[c["idRemito"]].append(c)
    completos = []
    for id_remito, lineas_rem in por_remito.items():
        disponibles = list(lineas_rem)
        asig = {}
        for clave, lineas in grupos.items():
            total = sum(l["pendBase"] for l in lineas)
            elegido = next((c for c in disponibles if c["clave"] == clave and _iguales(c["disponible"], total)), None)
            if elegido is None:
                break
            asig[clave] = elegido
            disponibles.remove(elegido)
        else:
            completos.append((min(_distancia(fecha_fac, c["fecha"]) for c in lineas_rem), id_remito, asig))
    if completos:
        completos.sort(key=lambda x: x[0])
        if len(completos) == 1 or completos[0][0] != completos[1][0]:
            for clave, rem in completos[0][2].items():
                vincular += items_grupo(grupos[clave], [rem])
                usados.add(rem["idDetalleRemito"])
            grupos = {}
    # 2) Producto por producto.
    for clave, lineas in grupos.items():
        cand = [c for c in libres if c["clave"] == clave and c["idDetalleRemito"] not in usados]
        d = decidir({"fecha": fecha_fac, "pendiente": sum(l["pendBase"] for l in lineas)},
                    [{"idDetalleRemito": c["idDetalleRemito"], "fecha": c["fecha"], "disponible": c["disponible"]} for c in cand])
        if d["accion"] == "vincular":
            elegidos = [next(c for c in cand if c["idDetalleRemito"] == it["idDetalleRemito"]) for it in d["items"]]
            vincular += items_grupo(lineas, elegidos)
            usados.update(c["idDetalleRemito"] for c in elegidos)
        elif d["accion"] == "revisar":
            revisar += [{"idDetalleCompra": l["idDetalleCompra"], "motivo": d["motivo"], "candidatos": d["candidatos"]} for l in lineas]
    agrupado = defaultdict(list)
    for it in vincular:
        agrupado[it["idRemito"]].append({k: it[k] for k in ("idDetalleRemito", "idDetalleCompra", "cantidad")})
    return {"vincular": [{"idRemito": k, "items": v} for k, v in agrupado.items()], "revisar": revisar}


def vincular_por_compra(id_compra: int) -> dict:
    """Vincula los renglones de insumo de la factura con sus remitos (y deja lo dudoso para revisar)."""
    from src.features.remitos import repository as remitos_repo

    prop = proponer_por_compra(id_compra)
    resumen = {"vinculados": 0, "revisar": 0}
    for grupo in prop["vincular"]:
        remitos_repo.vincular_renglones(grupo["idRemito"], grupo["items"], equivalente_ok=True)
        resumen["vinculados"] += len(grupo["items"])
    for r in prop["revisar"]:
        if not _ya_pendiente(r["idDetalleCompra"]):
            execute_write_transaction([(
                "INSERT INTO dbo.VinculoRemitoPendiente (IdDetalleCompra, Tipo, CandidatosJson, Motivo) VALUES (?, 'remito', ?, ?)",
                (r["idDetalleCompra"], json.dumps(r["candidatos"], default=str), r["motivo"]),
            )])
            resumen["revisar"] += 1
    return resumen


def vincular_por_remito(id_remito: int) -> dict:
    """Al guardar un remito: intenta vincular las facturas en alcance del mismo proveedor dentro de la ventana."""
    cab = fetch_one("SELECT COALESCE(IdContacto, IdProveedor) AS p, Fecha AS f FROM dbo.Remitos WHERE IdRemito = ?", (id_remito,))
    if cab is None:
        return {"vinculados": 0, "revisar": 0}
    compras = fetch_all(
        """
        SELECT DISTINCT d.IdCompra AS id FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1 AND tz.Destino = 'CultivoStock'
        WHERE c.IdContacto = ? AND c.Fecha BETWEEN DATEADD(day, -?, ?) AND DATEADD(day, ?, ?)
        """,
        (cab["p"], VENTANA_DIAS, cab["f"], VENTANA_DIAS, cab["f"]),
    )
    total = {"vinculados": 0, "revisar": 0}
    for c in compras:
        res = vincular_por_compra(c["id"])
        total = {k: total[k] + res[k] for k in total}
    return total


def vincular_seguro(funcion, id_: int) -> None:
    """Disparo desde el guardado: un error del vínculo no impide guardar."""
    try:
        funcion(id_)
    except Exception:  # noqa: BLE001
        _log.exception("Vínculo automático 050: falló para %s", id_)
