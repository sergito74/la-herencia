"""Stock de insumos: existencias valorizadas por FIFO, kardex, bajas y ajustes.

Las bajas descuentan stock de productos que salen sin usarse en una orden de
trabajo (deterioro, vencimiento, uso interno…): no se vinculan a cultivo ni
campaña y son un gasto de la empresa, imputado a un Rubro y un Centro de Costos.
Los ajustes corrigen faltantes o sobrantes de inventario.
"""

from __future__ import annotations

from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.db.params import as_sql_datetime
from src.features.remitos import catalogo
from src.features.remitos.repository import RequiereConfirmacion, TOLERANCIA
from src.features.remitos.stock_datos import calcular_stock, equivalencias, factor_a_base, unidades_base

MOTIVOS_BAJA = {
    "Deterioro": "Deterioro",
    "Vencimiento": "Vencimiento",
    "UsoInterno": "Uso interno / mantenimiento",
    "Otro": "Otro",
}
RUBRO_PERDIDAS = "Pérdidas y bajas de insumos"


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _d(v):
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v.date() if isinstance(v, datetime) else v


# ------------------------------------------------------------------ existencias

def _productos_por_id(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    out = {}
    for i in range(0, len(ids), 800):
        lote = ids[i : i + 800]
        marcas = ",".join("?" for _ in lote)
        for p in fetch_all(
            f"SELECT CAST(IdProducto AS int) AS idProducto, Producto AS producto, TipoProducto AS tipo FROM dbo.vw_ProductosBase WHERE IdProducto IN ({marcas})",
            tuple(lote),
        ):
            out[p["idProducto"]] = p
    return out


def existencias(q: str | None = None, tipo: str | None = None, estado: str | None = None) -> dict:
    """Existencia y valor FIFO por producto. `estado`: conStock (default), negativo,
    costoPendiente, todos."""
    stock = calcular_stock()
    prods = _productos_por_id(list(stock))
    items = []
    for pid, s in stock.items():
        p = prods.get(pid, {"producto": f"Producto {pid}", "tipo": None})
        existencia = round(s["existencia"], 4)
        item = {
            "idProducto": pid,
            "producto": p["producto"],
            "tipo": p["tipo"],
            "unidadBase": s["unidadBase"],
            "existencia": existencia,
            "valor": s["valor"],
            "costoPromedio": round(s["valor"] / existencia, 4) if existencia > TOLERANCIA and s["valor"] else None,
            "cantidadCostoPendiente": round(s["cantidad_costo_pendiente"], 4),
            "negativo": existencia < -TOLERANCIA,
            "equivalenciaPendiente": s["flags"]["equivalenciaPendiente"],
            "sinUnidadBase": s["flags"]["sinUnidadBase"],
        }
        items.append(item)
    if q:
        items = [i for i in items if q.strip().lower() in (i["producto"] or "").lower()]
    if tipo:
        items = [i for i in items if i["tipo"] == tipo]
    filtro = {
        None: lambda i: abs(i["existencia"]) > TOLERANCIA,
        "": lambda i: abs(i["existencia"]) > TOLERANCIA,
        "conStock": lambda i: i["existencia"] > TOLERANCIA,
        "negativo": lambda i: i["negativo"],
        "costoPendiente": lambda i: i["cantidadCostoPendiente"] > TOLERANCIA,
        "todos": lambda i: True,
    }.get(estado, lambda i: True)
    items = sorted((i for i in items if filtro(i)), key=lambda i: (i["producto"] or ""))
    return {
        "items": items,
        "totales": {
            "productos": len(items),
            "valor": round(sum(i["valor"] for i in items), 2),
            "conCostoPendiente": sum(1 for i in items if i["cantidadCostoPendiente"] > TOLERANCIA),
            "negativos": sum(1 for i in items if i["negativo"]),
        },
    }


def kardex(id_producto: int) -> dict | None:
    """Movimientos de un producto con el saldo y el costo FIFO de cada salida."""
    prod = _productos_por_id([id_producto]).get(id_producto)
    if prod is None:
        return None
    s = calcular_stock(id_producto).get(id_producto)
    if s is None:
        return {"producto": prod, "unidadBase": None, "movimientos": [], "existencia": 0.0, "valor": 0.0}
    movs = []
    for c in s["capas"]:
        movs.append({
            "fecha": _d(c["fecha"]), "orden": 0, "clave": c["id"], "tipo": "Entrada" if c["origen"] == "remito" else "Sobrante",
            "detalle": (f"Remito {c['nroRemito']}" if c["origen"] == "remito" else f"Ajuste: {c.get('motivo')}"),
            "idRemito": c.get("idRemito"), "cantidad": c["cantidad"], "costoUnitario": c["costoUnitario"],
            "importe": round(c["cantidad"] * c["costoUnitario"], 2) if c["costoUnitario"] is not None else None,
            "costoPendiente": c["costoUnitario"] is None, "restante": c["restante"],
        })
    for sid, cons in s["consumos"].items():
        m = s["salidaMeta"][sid]
        cantidad = sum(i["cantidad"] for i in cons["items"]) + cons["sin_cobertura"]
        detalle = {"orden": f"Orden de trabajo {m.get('idOrden')}", "baja": f"Baja: {MOTIVOS_BAJA.get(m.get('motivo'), m.get('motivo'))}",
                   "faltante": f"Ajuste (faltante): {m.get('motivo')}"}[m["tipo"]]
        movs.append({
            "fecha": _d(m["fecha"]), "orden": 1, "clave": sid, "tipo": {"orden": "Orden de trabajo", "baja": "Baja", "faltante": "Faltante"}[m["tipo"]],
            "detalle": detalle, "idOrden": m.get("idOrden"), "idBaja": m.get("idBaja"), "cantidad": -cantidad,
            "costoUnitario": (cons["costo"] / (cantidad - cons["cantidad_costo_pendiente"] - cons["sin_cobertura"])) if cantidad - cons["cantidad_costo_pendiente"] - cons["sin_cobertura"] > TOLERANCIA else None,
            "importe": -cons["costo"], "costoPendiente": cons["provisoria"], "sinCobertura": cons["sin_cobertura"],
        })
    movs.sort(key=lambda m: (m["fecha"] or date.min, m["orden"], m["clave"]))
    saldo = 0.0
    for m in movs:
        saldo += m["cantidad"]
        m["saldo"] = round(saldo, 4)
    return {"producto": prod, "unidadBase": s["unidadBase"], "movimientos": movs, "existencia": round(s["existencia"], 4), "valor": s["valor"], "flags": s["flags"]}


def _convertir_a_base(id_producto: int, cantidad: float, unidad: str | None) -> float:
    bases, equiv = unidades_base(), equivalencias()
    if id_producto not in bases:
        raise ValueError([f"El producto {id_producto} todavía no tiene unidad base definida (se define al cargar su primer remito)."])
    factor, falta = factor_a_base(id_producto, unidad, bases, equiv)
    if falta:
        raise ValueError([f"Falta la equivalencia de {unidad} para el producto {id_producto}."])
    return cantidad * factor


def _existencia(id_producto: int) -> float:
    return calcular_stock(id_producto).get(id_producto, {}).get("existencia", 0.0)


# ------------------------------------------------------------------ bajas

def opciones_bajas() -> dict:
    rubros = fetch_all(
        "SELECT IdRubro AS idRubro, Rubro AS rubro FROM dbo.Rubros WHERE Rubro = ? OR Rubro LIKE 'Mantenimiento%' ORDER BY Rubro", (RUBRO_PERDIDAS,)
    )
    centros = fetch_all("SELECT IdCentro AS idCentro, [Centro de costos] AS centro FROM dbo.[Centro de costos] ORDER BY IdCentro")
    perdidas = next((r["idRubro"] for r in rubros if r["rubro"] == RUBRO_PERDIDAS), None)
    return {
        "motivos": [{"value": k, "label": v} for k, v in MOTIVOS_BAJA.items()],
        "rubros": rubros,
        "centros": centros,
        "rubroPerdidas": perdidas,
    }


def crear_baja(datos: dict, confirmar: bool = False) -> int:
    if datos["motivo"] not in MOTIVOS_BAJA:
        raise ValueError([f"Motivo inválido: {datos['motivo']!r}."])
    if datos["motivo"] == "Otro" and not (datos.get("detalle") or "").strip():
        raise ValueError(["Indicá el detalle cuando el motivo es «Otro»."])
    opciones = opciones_bajas()
    if datos["idRubro"] not in {r["idRubro"] for r in opciones["rubros"]}:
        raise ValueError(["El rubro debe ser «Pérdidas y bajas de insumos» o uno de Mantenimiento."])
    if datos["idCentro"] not in {c["idCentro"] for c in opciones["centros"]}:
        raise ValueError(["Elegí un centro de costos válido."])
    if not datos["renglones"]:
        raise ValueError(["Elegí al menos un producto."])
    items, negativos = [], []
    acumulado: dict[int, float] = {}
    for i, r in enumerate(datos["renglones"], start=1):
        if not r["cantidad"] or r["cantidad"] <= 0:
            raise ValueError([f"Renglón {i}: la cantidad debe ser mayor a cero."])
        if not catalogo.existe_producto(r["idProducto"]):
            raise ValueError([f"Renglón {i}: el producto {r['idProducto']} no existe."])
        base = _convertir_a_base(r["idProducto"], r["cantidad"], r.get("unidad"))
        acumulado[r["idProducto"]] = acumulado.get(r["idProducto"], 0.0) + base
        items.append((r["idProducto"], base))
    for pid, total in acumulado.items():
        if _existencia(pid) - total < -TOLERANCIA:
            nombre = _productos_por_id([pid]).get(pid, {}).get("producto", pid)
            negativos.append(f"«{nombre}»: hay {_existencia(pid):g} y se da de baja {total:g}: el stock quedaría negativo.")
    if negativos and not confirmar:
        raise RequiereConfirmacion(negativos)

    def cab(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Stock_Bajas (Fecha, Motivo, Detalle, IdRubro, IdCentro) OUTPUT INSERTED.IdBaja VALUES (?, ?, ?, ?, ?)",
            (as_sql_datetime(datos["fecha"]), datos["motivo"], (datos.get("detalle") or None), datos["idRubro"], datos["idCentro"]),
        )

    def linea(pid: int, base: float):
        return lambda res: ("INSERT INTO dbo.Stock_Bajas_Detalle (IdBaja, IdProducto, Cantidad) VALUES (?, ?, ?)", (res[0], pid, base))

    return execute_write_transaction([cab, *[linea(p, b) for p, b in items]])[0]


def listar_bajas(desde=None, hasta=None, motivo: str | None = None, producto: str | None = None, incluir_anuladas: bool = False, page: int = 1, page_size: int = 25) -> dict:
    where, params = ["1 = 1"], []
    if not incluir_anuladas:
        where.append("b.Anulada = 0")
    if desde is not None:
        where.append("b.Fecha >= ?")
        params.append(as_sql_datetime(desde))
    if hasta is not None:
        where.append("b.Fecha <= ?")
        params.append(as_sql_datetime(hasta))
    if motivo:
        where.append("b.Motivo = ?")
        params.append(motivo)
    if producto:
        where.append("EXISTS (SELECT 1 FROM dbo.Stock_Bajas_Detalle x JOIN dbo.vw_ProductosBase p ON p.IdProducto = x.IdProducto WHERE x.IdBaja = b.IdBaja AND p.Producto LIKE ?)")
        params.append(f"%{producto.strip()}%")
    cabeceras = fetch_all(
        f"""
        SELECT b.IdBaja AS idBaja, b.Fecha AS fecha, b.Motivo AS motivo, b.Detalle AS detalle, b.IdRubro AS idRubro, r.Rubro AS rubro,
               b.IdCentro AS idCentro, c.[Centro de costos] AS centro, b.Anulada AS anulada, b.MotivoAnulacion AS motivoAnulacion
        FROM dbo.Stock_Bajas b LEFT JOIN dbo.Rubros r ON r.IdRubro = b.IdRubro LEFT JOIN dbo.[Centro de costos] c ON c.IdCentro = b.IdCentro
        WHERE {' AND '.join(where)} ORDER BY b.Fecha DESC, b.IdBaja DESC
        """,
        tuple(params),
    )
    total = len(cabeceras)
    pagina = cabeceras[(page - 1) * page_size : page * page_size]
    if not pagina:
        return {"items": [], "total": total, "page": page, "pageSize": page_size, "gastoTotal": 0.0}
    ids = [b["idBaja"] for b in pagina]
    marcas = ",".join("?" for _ in ids)
    lineas = fetch_all(
        f"SELECT d.IdBajaDetalle AS id, d.IdBaja AS idBaja, CAST(d.IdProducto AS int) AS idProducto, d.Cantidad AS cantidad FROM dbo.Stock_Bajas_Detalle d WHERE d.IdBaja IN ({marcas})",
        tuple(ids),
    )
    stock = calcular_stock()
    prods = _productos_por_id(list({l["idProducto"] for l in lineas}))
    por_baja: dict[int, list] = {}
    for l in lineas:
        cons = stock.get(l["idProducto"], {}).get("consumos", {}).get(f"B{l['id']}")
        por_baja.setdefault(l["idBaja"], []).append({
            "idProducto": l["idProducto"], "producto": prods.get(l["idProducto"], {}).get("producto"), "cantidad": _f(l["cantidad"]),
            "unidadBase": stock.get(l["idProducto"], {}).get("unidadBase"),
            "costo": cons["costo"] if cons else None, "costoPendiente": bool(cons and cons["provisoria"]),
        })
    items = []
    for b in pagina:
        ls = por_baja.get(b["idBaja"], [])
        items.append({**b, "fecha": _d(b["fecha"]), "anulada": bool(b["anulada"]), "motivoLabel": MOTIVOS_BAJA.get(b["motivo"], b["motivo"]),
                      "renglones": ls, "gasto": round(sum(l["costo"] or 0 for l in ls), 2), "costoPendiente": any(l["costoPendiente"] for l in ls)})
    return {"items": items, "total": total, "page": page, "pageSize": page_size, "gastoTotal": round(sum(i["gasto"] for i in items if not i["anulada"]), 2)}


def anular_baja(id_baja: int, motivo: str) -> None:
    if not (motivo or "").strip():
        raise ValueError(["Indicá el motivo de la anulación."])
    b = fetch_one("SELECT Anulada AS a FROM dbo.Stock_Bajas WHERE IdBaja = ?", (id_baja,))
    if b is None:
        raise ValueError([f"La baja {id_baja} no existe."])
    if b["a"]:
        raise ValueError(["La baja ya está anulada."])
    execute_write_transaction([("UPDATE dbo.Stock_Bajas SET Anulada = 1, MotivoAnulacion = ? WHERE IdBaja = ?", (motivo.strip(), id_baja))])


# ------------------------------------------------------------------ ajustes

def crear_ajuste(datos: dict, confirmar: bool = False) -> int:
    """`cantidad` con signo: positiva = sobrante, negativa = faltante."""
    if not (datos.get("motivo") or "").strip():
        raise ValueError(["Indicá el motivo del ajuste."])
    if not datos["cantidad"]:
        raise ValueError(["La cantidad del ajuste no puede ser cero."])
    if not catalogo.existe_producto(datos["idProducto"]):
        raise ValueError([f"El producto {datos['idProducto']} no existe."])
    base = _convertir_a_base(datos["idProducto"], abs(datos["cantidad"]), datos.get("unidad")) * (1 if datos["cantidad"] > 0 else -1)
    if base < 0 and _existencia(datos["idProducto"]) + base < -TOLERANCIA:
        nombre = _productos_por_id([datos["idProducto"]]).get(datos["idProducto"], {}).get("producto")
        msg = f"«{nombre}»: hay {_existencia(datos['idProducto']):g} y el faltante es {-base:g}: el stock quedaría negativo."
        if not confirmar:
            raise RequiereConfirmacion([msg])
    costo = datos.get("costoUnitario") if base > 0 else None
    return execute_write_transaction([(
        "INSERT INTO dbo.Stock_Ajustes (Fecha, IdProducto, Cantidad, CostoUnitario, Motivo) OUTPUT INSERTED.IdAjuste VALUES (?, ?, ?, ?, ?)",
        (as_sql_datetime(datos["fecha"]), datos["idProducto"], base, costo, datos["motivo"].strip()),
    )])[0]


def listar_ajustes(desde=None, hasta=None, producto: str | None = None, page: int = 1, page_size: int = 25) -> dict:
    where, params = ["1 = 1"], []
    if desde is not None:
        where.append("a.Fecha >= ?")
        params.append(as_sql_datetime(desde))
    if hasta is not None:
        where.append("a.Fecha <= ?")
        params.append(as_sql_datetime(hasta))
    if producto:
        where.append("p.Producto LIKE ?")
        params.append(f"%{producto.strip()}%")
    filas = fetch_all(
        f"""
        SELECT a.IdAjuste AS idAjuste, a.Fecha AS fecha, CAST(a.IdProducto AS int) AS idProducto, p.Producto AS producto, a.Cantidad AS cantidad,
               a.CostoUnitario AS costoUnitario, a.Motivo AS motivo, a.Anulado AS anulado, a.MotivoAnulacion AS motivoAnulacion, u.UnidadBase AS unidadBase
        FROM dbo.Stock_Ajustes a LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = a.IdProducto LEFT JOIN dbo.Producto_Unidad u ON u.IdProducto = a.IdProducto
        WHERE {' AND '.join(where)} ORDER BY a.Fecha DESC, a.IdAjuste DESC
        """,
        tuple(params),
    )
    total = len(filas)
    pagina = filas[(page - 1) * page_size : page * page_size]
    return {"items": [{**f, "fecha": _d(f["fecha"]), "cantidad": _f(f["cantidad"]), "costoUnitario": _f(f["costoUnitario"]) if f["costoUnitario"] is not None else None, "anulado": bool(f["anulado"])} for f in pagina],
            "total": total, "page": page, "pageSize": page_size}


def anular_ajuste(id_ajuste: int, motivo: str) -> None:
    if not (motivo or "").strip():
        raise ValueError(["Indicá el motivo de la anulación."])
    a = fetch_one("SELECT IdAjuste AS id, CAST(IdProducto AS int) AS prod, Cantidad AS cant, Anulado AS anulado FROM dbo.Stock_Ajustes WHERE IdAjuste = ?", (id_ajuste,))
    if a is None:
        raise ValueError([f"El ajuste {id_ajuste} no existe."])
    if a["anulado"]:
        raise ValueError(["El ajuste ya está anulado."])
    if _f(a["cant"]) > 0 and _existencia(a["prod"]) - _f(a["cant"]) < -TOLERANCIA:
        raise ValueError(["No se puede anular el sobrante: ya se usó parte de ese stock y quedaría negativo."])
    execute_write_transaction([("UPDATE dbo.Stock_Ajustes SET Anulado = 1, MotivoAnulacion = ? WHERE IdAjuste = ?", (motivo.strip(), id_ajuste))])
