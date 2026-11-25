"""Stock de hacienda por eventos (052 FR-005/006/007, US2).

Existencia a una fecha, por campo, dueño y categoría = último recuento del campo con fecha ≤ la pedida, más los
movimientos posteriores (hasta la fecha inclusive) que no estén anulados. Las cabezas de un movimiento se guardan en
positivo y el Tipo da el signo (Venta y Muerte restan, Nacimiento y Compra suman); el AjusteRecuento lleva su signo.
Un recuento que no coincide con la existencia teórica deja la diferencia "sin explicar" a la vista.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

ENTRADAS = ("Nacimiento", "Compra", "PastajeEntrada")
SALIDAS = ("Venta", "Muerte", "Consumo", "PastajeSalida")
TIPOS = ENTRADAS + SALIDAS + ("CambioCategoria", "Traslado", "AjusteRecuento")


class StockNegativo(Exception):
    def __init__(self, faltantes: list[dict]):
        super().__init__("La existencia quedaría negativa")
        self.faltantes = faltantes


def _d(v) -> date:
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v.date() if hasattr(v, "hour") else v


def efectos(m: dict) -> list[tuple[int, int | None, int, int]]:
    """[(establecimiento, dueño, categoría, delta de cabezas)] de un movimiento."""
    c, est, dueno, cat = int(m["cabezas"]), m["establecimiento"], m.get("dueno"), m["categoria"]
    t = m["tipo"]
    if t in ENTRADAS or t == "AjusteRecuento":
        return [(est, dueno, cat, c)]
    if t in SALIDAS:
        return [(est, dueno, cat, -c)]
    if t == "CambioCategoria":
        return [(est, dueno, cat, -c), (est, dueno, m["categoriaDestino"], c)]
    if t == "Traslado":
        return [(est, dueno, cat, -c), (m["establecimientoDestino"], dueno, cat, c)]
    raise ValueError(f"Tipo de movimiento desconocido: {t}")


def _base(recuentos: list[dict], est: int, fecha: date, antes_de: bool = False) -> dict | None:
    cands = [r for r in recuentos if r["establecimiento"] == est
             and (_d(r["fecha"]) < fecha if antes_de else _d(r["fecha"]) <= fecha)]
    return max(cands, key=lambda r: (_d(r["fecha"]), r.get("id") or 0)) if cands else None


def _teorica(recuentos, movimientos, est: int, fecha: date, antes_de_recuento: bool = False):
    """(base, {(dueño, cat): cabezas}) del campo a la fecha. antes_de_recuento: ignora un recuento de ese mismo día."""
    base = _base(recuentos, est, fecha, antes_de_recuento)
    stock: dict = defaultdict(int)
    if base:
        for d in base["detalle"]:
            stock[(d.get("dueno"), d["categoria"])] += int(d["cabezas"])
    desde = _d(base["fecha"]) if base else None
    for m in movimientos:
        f = _d(m["fecha"])
        if f > fecha or (desde is not None and f <= desde):
            continue
        for e, dueno, cat, delta in efectos(m):
            if e == est:
                stock[(dueno, cat)] += delta
    return base, stock


def existencia(recuentos: list[dict], movimientos: list[dict], fecha: date, establecimientos: list[int]) -> dict:
    """Función pura. recuentos: [{id, fecha, establecimiento, origen, detalle: [{categoria, dueno, cabezas}]}];
    movimientos: [{fecha, tipo, categoria, categoriaDestino, cabezas, dueno, establecimiento, establecimientoDestino}]
    (sin anulados). Devuelve {est: {base, stock: {(dueño, cat): cabezas}, sinExplicar: {(dueño, cat): diferencia}}}."""
    out = {}
    for est in establecimientos:
        base, stock = _teorica(recuentos, movimientos, est, fecha)
        sin = {}
        if base:
            _, previo = _teorica(recuentos, movimientos, est, _d(base["fecha"]), antes_de_recuento=True)
            contado = defaultdict(int)
            for d in base["detalle"]:
                contado[(d.get("dueno"), d["categoria"])] += int(d["cabezas"])
            for k in set(previo) | set(contado):
                dif = contado.get(k, 0) - previo.get(k, 0)
                if dif:
                    sin[k] = dif
        out[est] = {"base": base, "stock": dict(stock), "sinExplicar": sin}
    return out


def faltantes(recuentos, movimientos, nuevo: dict) -> list[dict]:
    """Claves que quedarían negativas en la fecha del movimiento nuevo o en cualquier fecha posterior conocida."""
    todos = movimientos + [nuevo]
    fechas = {_d(nuevo["fecha"])} | {_d(m["fecha"]) for m in movimientos if _d(m["fecha"]) > _d(nuevo["fecha"])}
    malos = []
    for e, dueno, cat, delta in efectos(nuevo):
        if delta >= 0:
            continue
        for f in sorted(fechas):
            _, st = _teorica(recuentos, todos, e, f)
            if st.get((dueno, cat), 0) < 0:
                malos.append({"establecimiento": e, "dueno": dueno, "categoria": cat, "fecha": f.isoformat(),
                              "existencia": st[(dueno, cat)]})
                break
    return malos


# ---------------------------------------------------------------- base de datos

def _recuentos_db() -> list[dict]:
    from src.db.connection import fetch_all

    cab = fetch_all("SELECT IdRecuento id, Fecha fecha, IdEstablecimiento establecimiento, Origen origen, "
                    "Archivo archivo, Observaciones observaciones FROM dbo.GanRecuento WHERE Anulado = 0")
    det = defaultdict(list)
    for d in fetch_all("SELECT IdRecuento r, IdCategoria categoria, IdContactoDueno dueno, Cabezas cabezas, "
                       "KgPromedio kgPromedio FROM dbo.GanRecuentoDetalle"):
        det[d["r"]].append(d)
    for c in cab:
        c["detalle"] = det.get(c["id"], [])
    return cab


_MOV_SQL = """
    SELECT m.IdMovimiento id, m.Fecha fecha, m.Tipo tipo, m.IdCategoria categoria, m.IdCategoriaDestino categoriaDestino,
           m.Cabezas cabezas, m.Kg kg, m.KgEstimado kgEstimado, m.IdContactoDueno dueno, m.IdEstablecimiento establecimiento,
           m.IdEstablecimientoDestino establecimientoDestino, m.IdVenta idVenta, m.IdDetalleVenta idDetalleVenta,
           m.Causa causa, m.Fuente fuente, m.Motivo motivo, m.Anulado anulado
    FROM dbo.GanMovimiento m"""


def _movimientos_db(incluir_anulados: bool = False) -> list[dict]:
    from src.db.connection import fetch_all

    return fetch_all(_MOV_SQL + ("" if incluir_anulados else " WHERE m.Anulado = 0"))


def _catalogos():
    from src.db.connection import fetch_all

    cats = {r["id"]: r for r in fetch_all("SELECT IdCategoria id, Nombre nombre, PesoTipicoKg peso, CoefEV ev, Orden orden "
                                          "FROM dbo.GanCategoria")}
    ests = {r["Id"]: r["Establecimiento"] for r in fetch_all("SELECT Id, Establecimiento FROM dbo.Establecimientos")}
    return cats, ests


def _nombres_contactos(ids) -> dict:
    from src.db.connection import fetch_all

    ids = [i for i in set(ids) if i is not None]
    if not ids:
        return {}
    marcas = ",".join("?" * len(ids))
    return {r["i"]: r["n"] for r in fetch_all(
        f"SELECT IdContacto i, [Razon Social] n FROM dbo.Contactos WHERE IdContacto IN ({marcas})", tuple(ids))}


def _pasa_dueno(dueno, filtro: str) -> bool:
    return filtro == "todos" or (filtro == "propia" and dueno is None) or (filtro == "terceros" and dueno is not None)


def stock(fecha: date, establecimiento: int | None = None, dueno: str = "todos") -> dict:
    cats, ests = _catalogos()
    ids = [establecimiento] if establecimiento else sorted(ests)
    rec = _recuentos_db()
    ex = existencia(rec, _movimientos_db(), fecha, ids)
    kg_base = {}
    for e in ids:
        b = ex[e]["base"]
        for d in (b["detalle"] if b else []):
            if d.get("kgPromedio"):
                kg_base[(e, d.get("dueno"), d["categoria"])] = float(d["kgPromedio"])
    duenos = _nombres_contactos(k[0] for e in ids for k in list(ex[e]["stock"]) + list(ex[e]["sinExplicar"]))
    filas, sin, bases = [], [], []
    for e in ids:
        b = ex[e]["base"]
        if b:
            bases.append({"establecimiento": ests.get(e), "fecha": _d(b["fecha"]).isoformat(), "origen": b["origen"]})
        for (du, cat), cab in ex[e]["stock"].items():
            if not cab or not _pasa_dueno(du, dueno):
                continue
            c = cats[cat]
            kg_cab = kg_base.get((e, du, cat)) or float(c["peso"] or 0)
            filas.append({"idCategoria": cat, "categoria": c["nombre"], "orden": c["orden"], "cabezas": cab,
                          "kg": round(cab * kg_cab, 1), "kgEstimado": (e, du, cat) not in kg_base,
                          "ev": round(cab * float(c["ev"] or 0), 1), "dueno": "Propia" if du is None else "De terceros",
                          "duenoNombre": duenos.get(du), "idEstablecimiento": e, "establecimiento": ests.get(e)})
        for (du, cat), dif in ex[e]["sinExplicar"].items():
            if _pasa_dueno(du, dueno):
                sin.append({"categoria": cats[cat]["nombre"], "diferencia": dif, "establecimiento": ests.get(e),
                            "dueno": "Propia" if du is None else duenos.get(du)})
    filas.sort(key=lambda f: (f["idEstablecimiento"], f["dueno"], f["orden"]))
    return {"fecha": fecha.isoformat(), "bases": bases, "categorias": filas, "sinExplicar": sin,
            "totalCabezas": sum(f["cabezas"] for f in filas), "totalEv": round(sum(f["ev"] for f in filas), 1)}


def movimientos(desde: date | None, hasta: date | None, tipo: str | None, categoria: int | None,
                establecimiento: int | None, limite: int = 500) -> list[dict]:
    cats, ests = _catalogos()
    filas = [m for m in _movimientos_db(incluir_anulados=True)
             if (not desde or _d(m["fecha"]) >= desde) and (not hasta or _d(m["fecha"]) <= hasta)
             and (not tipo or m["tipo"] == tipo) and (not categoria or m["categoria"] == categoria)
             and (not establecimiento or establecimiento in (m["establecimiento"], m["establecimientoDestino"]))]
    filas.sort(key=lambda m: (_d(m["fecha"]), m["id"]), reverse=True)
    filas = filas[:limite]
    duenos = _nombres_contactos(m["dueno"] for m in filas)
    for m in filas:
        m["fecha"] = _d(m["fecha"]).isoformat()
        m["categoriaNombre"] = cats[m["categoria"]]["nombre"]
        m["categoriaDestinoNombre"] = cats[m["categoriaDestino"]]["nombre"] if m["categoriaDestino"] else None
        m["establecimientoNombre"] = ests.get(m["establecimiento"])
        m["duenoNombre"] = "Propia" if m["dueno"] is None else duenos.get(m["dueno"])
        m["enlace"] = f"/ventas/hacienda/{m['idVenta']}/editar" if m["idVenta"] else None
    return filas


def registrar_movimiento(d: dict, usuario: str | None, confirmar: bool = False) -> int:
    from src.db.connection import execute_insert_returning_id

    if d["tipo"] not in TIPOS or d["tipo"] == "Venta":
        raise ValueError("Tipo de movimiento inválido (las ventas se registran en Ventas de hacienda)")
    if int(d["cabezas"]) == 0:
        raise ValueError("Indicá las cabezas")
    if d["tipo"] != "AjusteRecuento" and int(d["cabezas"]) < 0:
        raise ValueError("Las cabezas van en positivo; el tipo de movimiento da el signo")
    if d["tipo"] == "AjusteRecuento" and not (d.get("motivo") or "").strip():
        raise MotivoFaltante()
    if d["tipo"] == "CambioCategoria" and not d.get("categoriaDestino"):
        raise ValueError("Indicá la categoría nueva")
    if d["tipo"] == "Traslado" and not d.get("establecimientoDestino"):
        raise ValueError("Indicá el campo de destino")
    if not confirmar:
        malos = faltantes(_recuentos_db(), _movimientos_db(), d)
        if malos:
            raise StockNegativo(malos)
    return execute_insert_returning_id(
        "INSERT INTO dbo.GanMovimiento (Fecha, Tipo, IdCategoria, IdCategoriaDestino, Cabezas, Kg, KgEstimado, "
        "IdContactoDueno, IdEstablecimiento, IdEstablecimientoDestino, Causa, Fuente, Motivo, CreadoPor) "
        "OUTPUT INSERTED.IdMovimiento VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)",
        (d["fecha"], d["tipo"], d["categoria"], d.get("categoriaDestino"), int(d["cabezas"]), d.get("kg"),
         d.get("dueno"), d["establecimiento"], d.get("establecimientoDestino"), d.get("causa"),
         "Carga manual", (d.get("motivo") or "").strip() or None, usuario))


class MotivoFaltante(Exception):
    pass


def anular_movimiento(id_movimiento: int, motivo: str) -> None:
    from src.db.connection import execute_write, fetch_one

    m = fetch_one("SELECT IdVenta v, Anulado a FROM dbo.GanMovimiento WHERE IdMovimiento = ?", (id_movimiento,))
    if not m:
        raise LookupError("Movimiento inexistente")
    if m["v"]:
        raise ValueError("El movimiento de una venta se corrige editando la venta")
    if not (motivo or "").strip():
        raise MotivoFaltante()
    execute_write("UPDATE dbo.GanMovimiento SET Anulado = 1, Motivo = LEFT(ISNULL(Motivo + ' · ', '') + ?, 300) "
                  "WHERE IdMovimiento = ?", (f"Anulado: {motivo.strip()}", id_movimiento))


def recuentos() -> list[dict]:
    cats, ests = _catalogos()
    out = []
    for r in sorted(_recuentos_db(), key=lambda r: _d(r["fecha"]), reverse=True):
        out.append({"id": r["id"], "fecha": _d(r["fecha"]).isoformat(), "establecimiento": ests.get(r["establecimiento"]),
                    "origen": r["origen"], "observaciones": r["observaciones"],
                    "cabezas": sum(int(d["cabezas"]) for d in r["detalle"])})
    return out


def registrar_recuento(d: dict, usuario: str | None) -> dict:
    """Guarda el recuento y devuelve la diferencia contra la existencia teórica de ese día (antes del recuento)."""
    from src.db.connection import execute_write_transaction

    fecha = d["fecha"] if isinstance(d["fecha"], date) else date.fromisoformat(str(d["fecha"]))
    est = int(d["establecimiento"])
    base, teo = _teorica(_recuentos_db(), _movimientos_db(), est, fecha)
    contado = defaultdict(int)
    for x in d["detalle"]:
        if int(x["cabezas"]) < 0:
            raise ValueError("Las cabezas no pueden ser negativas")
        contado[(x.get("dueno"), int(x["categoria"]))] += int(x["cabezas"])
    difs = {k: contado.get(k, 0) - teo.get(k, 0) for k in set(teo) | set(contado)}
    difs = {k: v for k, v in difs.items() if v}
    if difs and (base or teo) and not (d.get("observaciones") or "").strip():
        raise MotivoFaltante()
    stmts = [("INSERT INTO dbo.GanRecuento (Fecha, IdEstablecimiento, Origen, Archivo, Observaciones, CreadoPor) "
              "OUTPUT INSERTED.IdRecuento VALUES (?, ?, ?, ?, ?, ?)",
              (fecha, est, d.get("origen") or "Recuento", d.get("archivo"), (d.get("observaciones") or "").strip() or None,
               usuario))]
    for (du, cat), cab in contado.items():
        kg = next((x.get("kgPromedio") for x in d["detalle"] if int(x["categoria"]) == cat and x.get("dueno") == du), None)
        stmts.append(lambda res, du=du, cat=cat, cab=cab, kg=kg: (
            "INSERT INTO dbo.GanRecuentoDetalle (IdRecuento, IdCategoria, IdContactoDueno, Cabezas, KgPromedio) "
            "VALUES (?, ?, ?, ?, ?)", (res[0], cat, du, cab, kg)))
    res = execute_write_transaction(stmts)
    cats, _ = _catalogos()
    return {"id": res[0], "diferencias": [{"categoria": cats[c]["nombre"], "dueno": du, "diferencia": v}
                                          for (du, c), v in sorted(difs.items(), key=lambda kv: cats[kv[0][1]]["orden"])]}


# ---------------------------------------------------------------- ventas → movimientos (T030)

def categoria_de_tipo_hacienda() -> dict[int, int]:
    """[Tipo Hacienda] → GanCategoria por el nombre del tipo (alias); si no hay alias, la primera categoría del tipo."""
    from src.db.connection import fetch_all

    out = {}
    for r in fetch_all("SELECT t.IdTipoHacienda t, a.IdCategoria a, "
                       "(SELECT TOP 1 IdCategoria FROM dbo.GanCategoria g WHERE g.IdTipoHacienda = t.IdTipoHacienda "
                       " ORDER BY g.Orden) g FROM dbo.[Tipo Hacienda] t "
                       "LEFT JOIN dbo.GanCategoriaAlias a ON a.Texto = t.[Tipo de Hacienda] AND a.EsTerceros = 0"):
        if r["a"] or r["g"]:
            out[r["t"]] = r["a"] or r["g"]
    return out


def movimientos_de_venta(id_venta: int, cat_de_tipo: dict | None = None) -> list[dict]:
    """Un movimiento Venta por renglón de hacienda (regla R4); los renglones en pesos no son hacienda."""
    from src.db.connection import fetch_all
    from src.features.ganaderia import categorias

    cat_de_tipo = cat_de_tipo if cat_de_tipo is not None else categoria_de_tipo_hacienda()
    filas = fetch_all(
        "SELECT d.IdDetalleVenta det, v.Fecha fecha, v.IdEstableciemiento est, v.[Nro documento] doc, d.IdTipoProducto tipo, "
        "d.Cantidad cantidad, d.[Unidad de medida] unidad, d.[Peso Total] peso "
        "FROM dbo.[Det_Ventas Hacienda] d JOIN dbo.[Venta Hacienda] v ON v.IdVenta = d.IdVenta "
        "WHERE d.IdVenta = ?", (id_venta,))
    pesos = {r["i"]: float(r["p"] or 0) or None for r in fetch_all("SELECT IdCategoria i, PesoTipicoKg p FROM dbo.GanCategoria")}
    out = []
    for f in filas:
        cat = cat_de_tipo.get(f["tipo"])
        if not cat:
            continue
        r = categorias.cabezas_y_kg(f["cantidad"], f["unidad"], f["peso"], pesos.get(cat))
        if not r["esHacienda"] or not r["cabezas"]:
            continue
        out.append({"fecha": _d(f["fecha"]), "tipo": "Venta", "categoria": cat, "cabezas": r["cabezas"],
                    "kg": r["kg"] or None, "kgEstimado": r["kgEstimado"], "establecimiento": f["est"] or 1,
                    "idVenta": id_venta, "idDetalleVenta": f["det"], "fuente": f"Venta {f['doc'] or id_venta}"[:120]})
    return out


def sincronizar_venta(id_venta: int) -> int:
    """Reemplaza los movimientos derivados de una venta por los de sus renglones actuales (alta, edición o baja)."""
    from src.db.connection import execute_write_transaction

    stmts: list = [("DELETE FROM dbo.GanMovimiento WHERE IdVenta = ? AND Tipo = 'Venta'", (id_venta,))]
    nuevos = movimientos_de_venta(id_venta)
    for m in nuevos:
        stmts.append(("INSERT INTO dbo.GanMovimiento (Fecha, Tipo, IdCategoria, Cabezas, Kg, KgEstimado, IdEstablecimiento, "
                      "IdVenta, IdDetalleVenta, Fuente, CreadoPor) VALUES (?, 'Venta', ?, ?, ?, ?, ?, ?, ?, ?, 'ventas')",
                      (m["fecha"], m["categoria"], m["cabezas"], m["kg"], 1 if m["kgEstimado"] else 0,
                       m["establecimiento"], id_venta, m["idDetalleVenta"], m["fuente"])))
    execute_write_transaction(stmts)
    return len(nuevos)
