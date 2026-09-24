"""Remitos: listado, detalle, alta, edición, anulación y vínculos con facturas.

Escribe exclusivamente contra `WC`. Las tablas heredadas (`Remitos`,
`Remitos_Detalles`, `Remitos_Facturas`, `tblRemitoCompra`) mantienen su esquema; lo
nuevo (establecimiento, observaciones, archivo, anulación, marca de duplicado) vive
en `Remitos_Extra`. El vínculo por renglón (`tblRemitoCompra`) es la fuente de
verdad y el de documento (`Remitos_Facturas`) se mantiene sincronizado.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.db.params import as_sql_datetime
from src.features.imputacion import motor as imputacion_motor
from src.features.remitos import catalogo
from src.features.remitos.stock_datos import calcular_stock, equivalencias, factor_a_base, unidades_base

NRO_FORMATO = re.compile(r"^\d{4,5}-\d{8}$")
SIN_REMITO = "SIN REMITO"
TOLERANCIA = 0.005


class RequiereConfirmacion(Exception):
    """La operación necesita que el usuario la confirme explícitamente (409)."""

    def __init__(self, mensajes: list[str]):
        super().__init__(mensajes)
        self.mensajes = mensajes


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _d(v):
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    return v.date() if isinstance(v, datetime) else v


def es_sin_remito(nro: str | None) -> bool:
    return (nro or "").strip().upper() == SIN_REMITO


# ------------------------------------------------------------------ advertencias

def advertencias(id_proveedor: int, nro_remito: str, excluir_id: int | None = None) -> dict:
    """Formato inválido y remitos duplicados (mismo proveedor y número). «SIN REMITO»
    es válido y repetible: es el número que se carga cuando el proveedor entrega sin remito."""
    nro = (nro_remito or "").strip()
    if es_sin_remito(nro):
        return {"formato": True, "duplicados": []}
    duplicados = fetch_all(
        "SELECT IdRemito AS idRemito, Fecha AS fecha FROM dbo.Remitos WHERE IdProveedor = ? AND NroRemito = ? AND IdRemito <> ?",
        (id_proveedor, nro, excluir_id or 0),
    )
    return {"formato": bool(NRO_FORMATO.match(nro)), "duplicados": [{"idRemito": d["idRemito"], "fecha": _d(d["fecha"])} for d in duplicados]}


def _mensajes_advertencia(adv: dict) -> list[str]:
    msgs = []
    if not adv["formato"]:
        msgs.append("El número de remito no tiene el formato 0000-00000000 (ni es «SIN REMITO»).")
    if adv["duplicados"]:
        msgs.append(f"Ya existe un remito de este proveedor con ese número (remito {', '.join(str(d['idRemito']) for d in adv['duplicados'])}).")
    return msgs


# ------------------------------------------------------------------ estados

def _estado_renglon(cantidad: float, vinculada: float) -> str:
    if vinculada <= TOLERANCIA:
        return "SinVincular"
    if vinculada < cantidad - TOLERANCIA:
        return "Parcial"
    if vinculada > cantidad + TOLERANCIA:
        return "ConDiferencia"
    return "Completo"


def _estado_remito(renglones: list[str], hay_facturas: bool) -> str:
    """Estado de los renglones del remito: peor caso primero."""
    if not renglones:
        return "SinVincular"
    for e in ("ConDiferencia", "Parcial", "SinVincular"):
        if e in renglones:
            return e if not (e == "SinVincular" and any(x != "SinVincular" for x in renglones)) else "Parcial"
    return "Completo"


# ------------------------------------------------------------------ listado

def listar_remitos(
    id_proveedor: int | None = None,
    proveedor: str | None = None,
    desde=None,
    hasta=None,
    producto: str | None = None,
    estado: str | None = None,
    nro_remito: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """Remitos con sus estados. `estado`: sinFactura, sinVincular, parcial, completo,
    conDiferencia, anulado, revisar (duplicados)."""
    where, params = ["1 = 1"], []
    if id_proveedor is not None:
        where.append("r.IdProveedor = ?")
        params.append(id_proveedor)
    if proveedor:
        where.append("c.[Razon Social] LIKE ?")
        params.append(f"%{proveedor.strip()}%")
    if desde is not None:
        where.append("r.Fecha >= ?")
        params.append(as_sql_datetime(desde))
    if hasta is not None:
        where.append("r.Fecha <= ?")
        params.append(as_sql_datetime(hasta))
    if nro_remito:
        where.append("r.NroRemito LIKE ?")
        params.append(f"%{nro_remito.strip()}%")
    if producto:
        where.append(
            "EXISTS (SELECT 1 FROM dbo.Remitos_Detalles x JOIN dbo.vw_ProductosBase p ON p.IdProducto = x.IdFormulado "
            "WHERE x.IdRemito = r.IdRemito AND (p.Producto LIKE ? OR p.IngredienteActivo LIKE ?))"
        )
        params += [f"%{producto.strip()}%", f"%{producto.strip()}%"]
    cabeceras = fetch_all(
        f"""
        SELECT r.IdRemito AS idRemito, r.Fecha AS fecha, r.IdProveedor AS idProveedor, c.[Razon Social] AS proveedor,
               r.NroRemito AS nroRemito, e.IdEstablecimiento AS idEstablecimiento, ISNULL(e.Anulado, 0) AS anulado,
               ISNULL(e.RevisarDuplicado, 0) AS revisarDuplicado, e.Archivo AS archivo
        FROM dbo.Remitos r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdProveedor
        LEFT JOIN dbo.Remitos_Extra e ON e.IdRemito = r.IdRemito
        WHERE {' AND '.join(where)}
        ORDER BY r.Fecha DESC, r.IdRemito DESC
        """,
        tuple(params),
    )
    ids = [c["idRemito"] for c in cabeceras]
    renglones = defaultdict(list)
    facturas = defaultdict(list)
    if ids:
        for i in range(0, len(ids), 800):
            lote = ids[i : i + 800]
            marcas = ",".join("?" for _ in lote)
            for r in fetch_all(
                f"""
                SELECT rd.IdRemito AS idRemito, rd.IdDetalleRemito AS idDetalle, rd.Cantidad AS cantidad, p.Producto AS producto,
                       (SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t WHERE t.IdDetalleRemito = rd.IdDetalleRemito) AS vinculada
                FROM dbo.Remitos_Detalles rd LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
                WHERE rd.IdRemito IN ({marcas})
                """,
                tuple(lote),
            ):
                renglones[r["idRemito"]].append(r)
            for f in fetch_all(
                f"""
                SELECT rf.IdRemito AS idRemito, c.[Tipo documento] AS tipo, c.[Nro Documento] AS numero, c.IdDeuda AS idCompra
                FROM dbo.Remitos_Facturas rf JOIN dbo.Compras c ON c.IdDeuda = rf.IdDeuda WHERE rf.IdRemito IN ({marcas})
                """,
                tuple(lote),
            ):
                facturas[f["idRemito"]].append(f)
    hoy = date.today()
    items = []
    for c in cabeceras:
        rs = renglones.get(c["idRemito"], [])
        estados_r = [_estado_renglon(_f(r["cantidad"]), _f(r["vinculada"])) for r in rs]
        fs = facturas.get(c["idRemito"], [])
        item = {
            **c,
            "fecha": _d(c["fecha"]),
            "anulado": bool(c["anulado"]),
            "revisarDuplicado": bool(c["revisarDuplicado"]),
            "renglones": len(rs),
            "productos": ", ".join(dict.fromkeys(r["producto"] for r in rs if r["producto"]))[:120],
            "facturas": [f"{f['tipo'] or ''} {f['numero'] or ''}".strip() for f in fs],
            "estadoFactura": "Facturado" if fs else "SinFactura",
            "estadoRenglones": _estado_remito(estados_r, bool(fs)),
            "diasSinFactura": (hoy - _d(c["fecha"])).days if not fs and c["fecha"] else None,
        }
        items.append(item)

    def coincide(i: dict) -> bool:
        if estado == "anulado":
            return i["anulado"]
        if i["anulado"] and estado:
            return False
        return {
            None: True,
            "": True,
            "sinFactura": i["estadoFactura"] == "SinFactura",
            "sinVincular": i["estadoRenglones"] == "SinVincular",
            "parcial": i["estadoRenglones"] == "Parcial",
            "completo": i["estadoRenglones"] == "Completo",
            "conDiferencia": i["estadoRenglones"] == "ConDiferencia",
            "revisar": i["revisarDuplicado"],
        }.get(estado, True)

    filtrados = [i for i in items if coincide(i)]
    inicio = (page - 1) * page_size
    return {"items": filtrados[inicio : inicio + page_size], "total": len(filtrados), "page": page, "pageSize": page_size}


# ------------------------------------------------------------------ detalle

def _stock_de(productos: list[int]) -> dict[int, dict]:
    resultado = {}
    for p in set(productos):
        resultado.update(calcular_stock(p))
    return resultado


def get_remito(id_remito: int) -> dict | None:
    cab = fetch_one(
        """
        SELECT r.IdRemito AS idRemito, r.Fecha AS fecha, r.IdProveedor AS idProveedor, c.[Razon Social] AS proveedor,
               r.NroRemito AS nroRemito, r.NroFactura AS nroFacturaTexto, e.IdEstablecimiento AS idEstablecimiento,
               e.Observaciones AS observaciones, e.Archivo AS archivo, ISNULL(e.Anulado, 0) AS anulado,
               e.MotivoAnulacion AS motivoAnulacion, ISNULL(e.RevisarDuplicado, 0) AS revisarDuplicado
        FROM dbo.Remitos r
        LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdProveedor
        LEFT JOIN dbo.Remitos_Extra e ON e.IdRemito = r.IdRemito
        WHERE r.IdRemito = ?
        """,
        (id_remito,),
    )
    if cab is None:
        return None
    lineas = fetch_all(
        """
        SELECT rd.IdDetalleRemito AS idDetalle, rd.IdFormulado AS idProducto, p.Producto AS producto, p.TipoProducto AS tipo,
               rd.Cantidad AS cantidad, rd.[Unidad Medida] AS unidad, rd.Vencimiento AS vencimiento
        FROM dbo.Remitos_Detalles rd LEFT JOIN dbo.vw_ProductosBase p ON p.IdProducto = rd.IdFormulado
        WHERE rd.IdRemito = ? ORDER BY rd.IdDetalleRemito
        """,
        (id_remito,),
    )
    vinculos = defaultdict(list)
    for v in fetch_all(
        """
        SELECT t.IdRemitoCompra AS idVinculo, t.IdDetalleRemito AS idDetalle, t.IdDetalleCompra AS idDetalleCompra, t.CantidadRemitida AS cantidad,
               dc.IdCompra AS idCompra, dc.[Producto/Servicio] AS descripcion, dc.Cantidad AS cantidadCompra, dc.[Precio Unitario] AS precioUnitario,
               cm.[Tipo documento] AS tipoDocumento, cm.[Nro Documento] AS numeroDocumento, cm.Fecha AS fechaCompra, cm.Moneda AS moneda
        FROM dbo.tblRemitoCompra t
        JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras cm ON cm.IdDeuda = dc.IdCompra
        WHERE t.IdDetalleRemito IN (SELECT IdDetalleRemito FROM dbo.Remitos_Detalles WHERE IdRemito = ?)
        """,
        (id_remito,),
    ):
        vinculos[v["idDetalle"]].append({**v, "cantidad": _f(v["cantidad"]), "cantidadCompra": _f(v["cantidadCompra"]), "precioUnitario": _f(v["precioUnitario"]), "fechaCompra": _d(v["fechaCompra"])})
    facturas = fetch_all(
        """
        SELECT c.IdDeuda AS idCompra, c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento, c.Fecha AS fecha, c.Moneda AS moneda
        FROM dbo.Remitos_Facturas rf JOIN dbo.Compras c ON c.IdDeuda = rf.IdDeuda WHERE rf.IdRemito = ? ORDER BY c.Fecha
        """,
        (id_remito,),
    )
    bases, equiv = unidades_base(), equivalencias()
    stock = _stock_de([l["idProducto"] for l in lineas if l["idProducto"]])
    capas = {c["id"]: c for s in stock.values() for c in s["capas"]}
    renglones = []
    for l in lineas:
        cant = _f(l["cantidad"])
        vs = vinculos.get(l["idDetalle"], [])
        vinculada = sum(v["cantidad"] for v in vs)
        factor, falta = factor_a_base(l["idProducto"], l["unidad"], bases, equiv)
        capa = capas.get(f"R{l['idDetalle']}")
        consumido_base = (capa["cantidad"] - capa["restante"]) if capa and not cab["anulado"] else 0.0
        consumido = consumido_base / factor if factor else consumido_base
        motivo = None
        if consumido > TOLERANCIA:
            motivo = "consumo"
        elif vs:
            motivo = "factura"
        renglones.append(
            {
                **l,
                "cantidad": cant,
                "vencimiento": _d(l["vencimiento"]),
                "unidadBase": bases.get(l["idProducto"]),
                "factorABase": factor,
                "equivalenciaPendiente": falta,
                "vinculos": vs,
                "cantidadVinculada": vinculada,
                "estadoVinculo": _estado_renglon(cant, vinculada),
                "costoUnitario": (capa["costoUnitario"] * factor) if capa and capa["costoUnitario"] is not None else None,
                "consumido": round(consumido, 4),
                "congelado": motivo is not None,
                "motivoCongelado": motivo,
            }
        )
    est = [r["estadoVinculo"] for r in renglones]
    return {
        **cab,
        "fecha": _d(cab["fecha"]),
        "anulado": bool(cab["anulado"]),
        "revisarDuplicado": bool(cab["revisarDuplicado"]),
        "renglones": renglones,
        "facturas": [{**f, "fecha": _d(f["fecha"])} for f in facturas],
        "estadoFactura": "Facturado" if facturas else "SinFactura",
        "estadoRenglones": _estado_remito(est, bool(facturas)),
        "congelado": any(r["congelado"] for r in renglones),
    }


# ------------------------------------------------------------------ validaciones de datos

def _validar_proveedor(id_proveedor: int) -> None:
    fila = fetch_one("SELECT [Tipo Contacto] AS tipo FROM dbo.Contactos WHERE IdContacto = ?", (id_proveedor,))
    if fila is None:
        raise ValueError([f"El proveedor {id_proveedor} no existe."])
    if (fila["tipo"] or "").lower() not in ("proveedor", "multiple"):
        raise ValueError(["El contacto elegido no es un proveedor."])


def _validar_renglones(renglones: list[dict]) -> list:
    """Valida productos/unidades y arma las sentencias de unidad base y equivalencias
    que hagan falta (se guardan en la misma transacción)."""
    if not renglones:
        raise ValueError(["El remito necesita al menos un renglón."])
    bases, equiv = unidades_base(), equivalencias()
    stmts, base_nueva, equiv_nueva = [], {}, {}
    for i, r in enumerate(renglones, start=1):
        if not r.get("cantidad") or r["cantidad"] <= 0:
            raise ValueError([f"Renglón {i}: la cantidad debe ser mayor a cero."])
        prod = r["idProducto"]
        if not catalogo.existe_producto(prod):
            raise ValueError([f"Renglón {i}: el producto {prod} no existe en el catálogo."])
        unidad = (r.get("unidad") or "").strip().upper()
        if not catalogo.existe_unidad(unidad):
            raise ValueError([f"Renglón {i}: la unidad «{unidad}» no está en la lista de unidades."])
        r["unidad"] = unidad
        base = bases.get(prod) or base_nueva.get(prod)
        if base is None:
            base = (r.get("unidadBase") or "").strip().upper() or None
            if base is None:
                producto = catalogo.get_producto(prod)
                base = unidad if catalogo._es_base(unidad) else catalogo.unidad_base_sugerida(producto["tipo"] if producto else None)
            if not catalogo._es_base(base):
                raise ValueError([f"Renglón {i}: «{base}» no es una unidad base."])
            base_nueva[prod] = base
            stmts += catalogo.stmt_unidad_base(prod, base, False, "definida al cargar un remito")
        if unidad != base and (prod, unidad) not in equiv and (prod, unidad) not in equiv_nueva:
            factor = r.get("factorUnidad")
            if not factor or factor <= 0:
                nombre = (catalogo.get_producto(prod) or {}).get("producto", prod)
                raise ValueError([f"Renglón {i}: falta la equivalencia — ¿cuántos {base} tiene 1 {unidad} de {nombre}?"])
            equiv_nueva[(prod, unidad)] = factor
            stmts += catalogo.stmt_equivalencia(prod, unidad, factor)
    return stmts


def _upsert_extra(id_remito: int, campos: dict) -> list:
    existe = fetch_one("SELECT 1 AS x FROM dbo.Remitos_Extra WHERE IdRemito = ?", (id_remito,))
    if existe:
        sets = ", ".join(f"{k} = ?" for k in campos)
        return [(f"UPDATE dbo.Remitos_Extra SET {sets} WHERE IdRemito = ?", (*campos.values(), id_remito))]
    cols = ", ".join(["IdRemito", *campos.keys()])
    marcas = ", ".join("?" for _ in range(len(campos) + 1))
    return [(f"INSERT INTO dbo.Remitos_Extra ({cols}) VALUES ({marcas})", (id_remito, *campos.values()))]


# ------------------------------------------------------------------ alta

def crear_remito(datos: dict, confirmar: bool = False) -> int:
    _validar_proveedor(datos["idProveedor"])
    nro = (datos["nroRemito"] or "").strip()
    if not nro:
        raise ValueError(["Indicá el número de remito (o «SIN REMITO»)."])
    adv = advertencias(datos["idProveedor"], nro)
    msgs = _mensajes_advertencia(adv)
    if msgs and not confirmar:
        raise RequiereConfirmacion(msgs)
    stmts_prev = _validar_renglones(datos["renglones"])

    def cab(_r: list) -> tuple:
        return (
            "INSERT INTO dbo.Remitos (Fecha, IdProveedor, NroRemito, IdContacto) OUTPUT INSERTED.IdRemito VALUES (?, ?, ?, ?)",
            (as_sql_datetime(datos["fecha"]), datos["idProveedor"], nro, datos["idProveedor"]),
        )

    def linea(r: dict):
        def build(res: list) -> tuple:
            return (
                "INSERT INTO dbo.Remitos_Detalles (IdRemito, IdFormulado, Cantidad, [Unidad Medida], Vencimiento) VALUES (?, ?, ?, ?, ?)",
                (res[0 + len(stmts_prev)], r["idProducto"], r["cantidad"], r["unidad"], as_sql_datetime(r["vencimiento"]) if r.get("vencimiento") else None),
            )

        return build

    def extra(res: list) -> tuple:
        idr = res[len(stmts_prev)]
        return (
            "INSERT INTO dbo.Remitos_Extra (IdRemito, IdEstablecimiento, Observaciones, Archivo, RevisarDuplicado) VALUES (?, ?, ?, ?, ?)",
            (idr, datos.get("idEstablecimiento"), (datos.get("observaciones") or None), (datos.get("archivo") or None), 1 if adv["duplicados"] else 0),
        )

    statements = [*stmts_prev, cab, *[linea(r) for r in datos["renglones"]], extra]
    resultados = execute_write_transaction(statements)
    return resultados[len(stmts_prev)]


# ------------------------------------------------------------------ edición

def actualizar_remito(id_remito: int, datos: dict, confirmar: bool = False) -> None:
    actual = get_remito(id_remito)
    if actual is None:
        raise ValueError([f"El remito {id_remito} no existe."])
    if actual["anulado"]:
        raise ValueError(["El remito está anulado: no se puede editar."])
    _validar_proveedor(datos["idProveedor"])
    nro = (datos["nroRemito"] or "").strip()
    if not nro:
        raise ValueError(["Indicá el número de remito (o «SIN REMITO»)."])
    adv = advertencias(datos["idProveedor"], nro, excluir_id=id_remito)
    msgs = _mensajes_advertencia(adv) if nro != (actual["nroRemito"] or "").strip() or datos["idProveedor"] != actual["idProveedor"] else []
    if msgs and not confirmar:
        raise RequiereConfirmacion(msgs)

    congeladas = {r["idDetalle"]: r for r in actual["renglones"] if r["congelado"]}
    errores = []
    if congeladas and (datos["idProveedor"] != actual["idProveedor"] or datos["fecha"] != actual["fecha"]):
        errores.append("El remito tiene renglones ya consumidos o vinculados a una factura: no se pueden cambiar la fecha ni el proveedor.")
    enviados = {r["idDetalle"]: r for r in datos["renglones"] if r.get("idDetalle")}
    for idd, viejo in congeladas.items():
        nuevo = enviados.get(idd)
        etiqueta = f"«{viejo['producto']}»"
        if nuevo is None:
            errores.append(f"No se puede quitar el renglón {etiqueta}: ya se {'consumió' if viejo['consumido'] > TOLERANCIA else 'vinculó a una factura'}. Anulá el remito con un motivo.")
            continue
        if nuevo["idProducto"] != viejo["idProducto"] or (nuevo["unidad"] or "").upper() != (viejo["unidad"] or "").upper():
            errores.append(f"Renglón {etiqueta}: no se pueden cambiar el producto ni la unidad ({'ya se consumió' if viejo['consumido'] > TOLERANCIA else 'ya está vinculado a una factura'}).")
        if viejo["vinculos"] and abs(nuevo["cantidad"] - viejo["cantidad"]) > TOLERANCIA:
            errores.append(f"Renglón {etiqueta}: no se puede cambiar la cantidad porque ya está vinculado a una factura (desvinculalo primero).")
        if nuevo["cantidad"] < viejo["consumido"] - TOLERANCIA:
            errores.append(f"Renglón {etiqueta}: la cantidad no puede bajar de {viejo['consumido']:g} (ya se consumió).")
    if errores:
        raise ValueError(errores)

    nuevos = [r for r in datos["renglones"] if not r.get("idDetalle")]
    editables = [r for r in datos["renglones"] if r.get("idDetalle") and r["idDetalle"] not in congeladas]
    stmts = _validar_renglones([*nuevos, *editables, *[r for r in datos["renglones"] if r.get("idDetalle") in congeladas]])
    stmts += [("UPDATE dbo.Remitos SET Fecha = ?, IdProveedor = ?, NroRemito = ?, IdContacto = ? WHERE IdRemito = ?",
               (as_sql_datetime(datos["fecha"]), datos["idProveedor"], nro, datos["idProveedor"], id_remito))]
    conservar = {r["idDetalle"] for r in datos["renglones"] if r.get("idDetalle")}
    for r in actual["renglones"]:
        if r["idDetalle"] not in conservar:
            stmts.append(("DELETE FROM dbo.Remitos_Detalles WHERE IdDetalleRemito = ?", (r["idDetalle"],)))
    for r in datos["renglones"]:
        venc = as_sql_datetime(r["vencimiento"]) if r.get("vencimiento") else None
        if r.get("idDetalle"):
            stmts.append(("UPDATE dbo.Remitos_Detalles SET IdFormulado = ?, Cantidad = ?, [Unidad Medida] = ?, Vencimiento = ? WHERE IdDetalleRemito = ? AND IdRemito = ?",
                          (r["idProducto"], r["cantidad"], r["unidad"], venc, r["idDetalle"], id_remito)))
        else:
            stmts.append(("INSERT INTO dbo.Remitos_Detalles (IdRemito, IdFormulado, Cantidad, [Unidad Medida], Vencimiento) VALUES (?, ?, ?, ?, ?)",
                          (id_remito, r["idProducto"], r["cantidad"], r["unidad"], venc)))
    stmts += _upsert_extra(id_remito, {"IdEstablecimiento": datos.get("idEstablecimiento"), "Observaciones": datos.get("observaciones") or None, "Archivo": datos.get("archivo") or None, "RevisarDuplicado": 1 if adv["duplicados"] else 0})
    execute_write_transaction(stmts)


# ------------------------------------------------------------------ anulación

def anular_remito(id_remito: int, motivo: str) -> None:
    if not (motivo or "").strip():
        raise ValueError(["Indicá el motivo de la anulación."])
    actual = get_remito(id_remito)
    if actual is None:
        raise ValueError([f"El remito {id_remito} no existe."])
    if actual["anulado"]:
        raise ValueError(["El remito ya está anulado."])
    problemas = []
    for prod in {r["idProducto"] for r in actual["renglones"] if r["idProducto"]}:
        antes = calcular_stock(prod).get(prod, {}).get("existencia", 0.0)
        despues = calcular_stock(prod, excluir_remito=id_remito).get(prod, {}).get("existencia", 0.0)
        if despues < -TOLERANCIA and despues < antes - TOLERANCIA:
            nombre = next((r["producto"] for r in actual["renglones"] if r["idProducto"] == prod), prod)
            problemas.append(f"«{nombre}»: quedaría en {despues:g} (ya se consumió o dio de baja parte de este remito).")
    if problemas:
        raise ValueError(["No se puede anular: dejaría sin cobertura lo ya consumido.", *problemas])
    execute_write_transaction(_upsert_extra(id_remito, {"Anulado": 1, "MotivoAnulacion": motivo.strip()}))


# ------------------------------------------------------------------ vínculos con facturas

def _sincronizar_nro_factura(id_remito: int) -> list:
    """El texto `Remitos.NroFactura` del sistema anterior queda derivado de los vínculos."""
    nros = [r["n"] for r in fetch_all(
        "SELECT c.[Nro Documento] AS n FROM dbo.Remitos_Facturas rf JOIN dbo.Compras c ON c.IdDeuda = rf.IdDeuda WHERE rf.IdRemito = ? ORDER BY c.Fecha", (id_remito,))]
    return nros


def _texto_facturas(nros: list[str]) -> str | None:
    return (", ".join(n for n in nros if n))[:255] or None


def facturas_candidatas(id_remito: int) -> list[dict]:
    """Facturas del mismo proveedor (las más cercanas en fecha primero) con todos sus
    renglones y lo que ya se vinculó de cada uno (de éste y de otros remitos) — panel de
    vinculación. Los renglones sin producto asignado también se pueden vincular: al
    hacerlo se les asigna el producto del renglón de remito."""
    cab = fetch_one("SELECT IdProveedor AS p, Fecha AS f FROM dbo.Remitos WHERE IdRemito = ?", (id_remito,))
    if cab is None:
        raise ValueError([f"El remito {id_remito} no existe."])
    facturas = fetch_all(
        """
        SELECT TOP 60 c.IdDeuda AS idCompra, c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento, c.Fecha AS fecha, c.Moneda AS moneda,
               CASE WHEN EXISTS (SELECT 1 FROM dbo.Remitos_Facturas rf WHERE rf.IdRemito = ? AND rf.IdDeuda = c.IdDeuda) THEN 1 ELSE 0 END AS vinculada
        FROM dbo.Compras c
        WHERE c.IdContacto = ? AND c.[Tipo documento] = 'Factura'
        ORDER BY ABS(DATEDIFF(day, c.Fecha, ?)) ASC, c.IdDeuda DESC
        """,
        (id_remito, cab["p"], as_sql_datetime(cab["f"])),
    )
    if not facturas:
        return []
    ids = [f["idCompra"] for f in facturas]
    marcas = ",".join("?" for _ in ids)
    lineas = defaultdict(list)
    for l in fetch_all(
        f"""
        SELECT d.IdCompra AS idCompra, d.IdDetalleCompra AS idDetalleCompra, d.IdFormulado AS idProducto, d.[Producto/Servicio] AS descripcion,
               d.Cantidad AS cantidad, d.[Precio Unitario] AS precioUnitario,
               (SELECT SUM(t.CantidadRemitida) FROM dbo.tblRemitoCompra t WHERE t.IdDetalleCompra = d.IdDetalleCompra) AS remitida
        FROM dbo.Det_Compras d WHERE d.IdCompra IN ({marcas}) ORDER BY d.IdDetalleCompra
        """,
        tuple(ids),
    ):
        lineas[l["idCompra"]].append({**l, "cantidad": _f(l["cantidad"]), "precioUnitario": _f(l["precioUnitario"]), "remitida": _f(l["remitida"]), "pendiente": round(_f(l["cantidad"]) - _f(l["remitida"]), 4), "productoAsignado": bool(l["idProducto"])})
    return [{**f, "fecha": _d(f["fecha"]), "vinculada": bool(f["vinculada"]), "lineas": lineas.get(f["idCompra"], [])} for f in facturas]


def vincular_renglones(id_remito: int, items: list[dict]) -> dict:
    """Vincula renglones de remito con renglones de factura (renglón por renglón).
    Devuelve `advertencias` (p. ej. se vincula más de lo remitido)."""
    remito = get_remito(id_remito)
    if remito is None:
        raise ValueError([f"El remito {id_remito} no existe."])
    if remito["anulado"]:
        raise ValueError(["El remito está anulado."])
    por_id = {r["idDetalle"]: r for r in remito["renglones"]}
    stmts, avisos, compras, sumar = [], [], set(), defaultdict(float)
    for it in items:
        r = por_id.get(it["idDetalleRemito"])
        if r is None:
            raise ValueError([f"El renglón {it['idDetalleRemito']} no pertenece a este remito."])
        if it["cantidad"] <= 0:
            raise ValueError(["La cantidad a vincular debe ser mayor a cero."])
        dc = fetch_one(
            """
            SELECT d.IdCompra AS idCompra, d.IdFormulado AS idProducto, d.[Producto/Servicio] AS descripcion, c.IdContacto AS idProveedor
            FROM dbo.Det_Compras d JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra WHERE d.IdDetalleCompra = ?
            """,
            (it["idDetalleCompra"],),
        )
        if dc is None:
            raise ValueError([f"El renglón de factura {it['idDetalleCompra']} no existe."])
        if dc["idProveedor"] != remito["idProveedor"]:
            raise ValueError(["La factura es de otro proveedor."])
        if dc["idProducto"] not in (None, 0, r["idProducto"]):
            raise ValueError([f"El renglón de factura «{dc['descripcion']}» corresponde a otro producto."])
        if fetch_one("SELECT 1 AS x FROM dbo.tblRemitoCompra WHERE IdDetalleRemito = ? AND IdDetalleCompra = ?", (it["idDetalleRemito"], it["idDetalleCompra"])):
            raise ValueError([f"El renglón «{r['producto']}» ya está vinculado a ese renglón de la factura."])
        if not dc["idProducto"]:
            stmts.append(("UPDATE dbo.Det_Compras SET IdFormulado = ? WHERE IdDetalleCompra = ?", (r["idProducto"], it["idDetalleCompra"])))
        stmts.append((
            "INSERT INTO dbo.tblRemitoCompra (IdDeuda, IdDetalleRemito, IdDetalleCompra, CantidadRemitida, DescripFormuladoRemito, DescripProductoFactura) VALUES (?, ?, ?, ?, ?, ?)",
            (dc["idCompra"], it["idDetalleRemito"], it["idDetalleCompra"], it["cantidad"], (r["producto"] or "")[:255], (dc["descripcion"] or "")[:255]),
        ))
        compras.add(dc["idCompra"])
        sumar[it["idDetalleRemito"]] += it["cantidad"]
    for idd, extra in sumar.items():
        r = por_id[idd]
        if r["cantidadVinculada"] + extra > r["cantidad"] + TOLERANCIA:
            avisos.append(f"«{r['producto']}»: se vincula {r['cantidadVinculada'] + extra:g} y el remito tiene {r['cantidad']:g}.")
    actuales = {f["idCompra"] for f in remito["facturas"]}
    for idc in compras - actuales:
        stmts.append(("INSERT INTO dbo.Remitos_Facturas (IdRemito, IdDeuda) VALUES (?, ?)", (id_remito, idc)))
    nros = _sincronizar_nro_factura(id_remito) + [fetch_one("SELECT [Nro Documento] AS n FROM dbo.Compras WHERE IdDeuda = ?", (c,))["n"] for c in compras - actuales]
    stmts.append(("UPDATE dbo.Remitos SET NroFactura = ? WHERE IdRemito = ?", (_texto_facturas(nros), id_remito)))
    execute_write_transaction(stmts)
    # Nuevo vínculo renglón↔factura: recalcula cualquier propuesta pendiente
    # del motor de imputación para estos renglones (017-imputacion-automatica-costos).
    for it in items:
        imputacion_motor.recalcular_si_corresponde(it["idDetalleCompra"], "Insumo")
    return {"advertencias": avisos}


def desvincular_renglon(id_remito: int, id_vinculo: int) -> None:
    fila = fetch_one(
        """
        SELECT t.IdRemitoCompra AS id, t.IdDetalleCompra AS idDetalleCompra, rd.IdFormulado AS idProducto
        FROM dbo.tblRemitoCompra t JOIN dbo.Remitos_Detalles rd ON rd.IdDetalleRemito = t.IdDetalleRemito
        WHERE t.IdRemitoCompra = ? AND rd.IdRemito = ?
        """,
        (id_vinculo, id_remito),
    )
    if fila is None:
        raise ValueError(["El vínculo no pertenece a este remito."])
    stmts = [("DELETE FROM dbo.tblRemitoCompra WHERE IdRemitoCompra = ?", (id_vinculo,))]
    # Si el vínculo había asignado el producto al renglón de factura (estaba vacío) y
    # nada más lo referencia, se revierte: si no, queda "huérfano" sin ningún remito
    # que lo respalde (hallazgo de la revisión SQL).
    otros = fetch_one(
        "SELECT COUNT(*) AS c FROM dbo.tblRemitoCompra WHERE IdDetalleCompra = ? AND IdRemitoCompra <> ?",
        (fila["idDetalleCompra"], id_vinculo),
    )
    if otros["c"] == 0:
        dc = fetch_one("SELECT IdFormulado AS p FROM dbo.Det_Compras WHERE IdDetalleCompra = ?", (fila["idDetalleCompra"],))
        if dc and dc["p"] == fila["idProducto"]:
            stmts.append(("UPDATE dbo.Det_Compras SET IdFormulado = NULL WHERE IdDetalleCompra = ?", (fila["idDetalleCompra"],)))
    execute_write_transaction(stmts)
    imputacion_motor.recalcular_si_corresponde(fila["idDetalleCompra"], "Insumo")


def vincular_factura(id_remito: int, id_compra: int) -> None:
    """Vínculo por documento (sin renglones)."""
    remito = fetch_one("SELECT IdProveedor AS p FROM dbo.Remitos WHERE IdRemito = ?", (id_remito,))
    compra = fetch_one("SELECT IdContacto AS p, [Nro Documento] AS n FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,))
    if remito is None or compra is None:
        raise ValueError(["El remito o la factura no existen."])
    if remito["p"] != compra["p"]:
        raise ValueError(["La factura es de otro proveedor."])
    if fetch_one("SELECT 1 AS x FROM dbo.Remitos_Facturas WHERE IdRemito = ? AND IdDeuda = ?", (id_remito, id_compra)):
        return
    nros = _sincronizar_nro_factura(id_remito) + [compra["n"]]
    execute_write_transaction([
        ("INSERT INTO dbo.Remitos_Facturas (IdRemito, IdDeuda) VALUES (?, ?)", (id_remito, id_compra)),
        ("UPDATE dbo.Remitos SET NroFactura = ? WHERE IdRemito = ?", (_texto_facturas(nros), id_remito)),
    ])


def desvincular_factura(id_remito: int, id_compra: int) -> None:
    """Quita el vínculo por documento y los vínculos por renglón de esa factura."""
    resto = [r["n"] for r in fetch_all(
        "SELECT c.[Nro Documento] AS n FROM dbo.Remitos_Facturas rf JOIN dbo.Compras c ON c.IdDeuda = rf.IdDeuda WHERE rf.IdRemito = ? AND rf.IdDeuda <> ? ORDER BY c.Fecha", (id_remito, id_compra))]
    execute_write_transaction([
        ("DELETE FROM dbo.tblRemitoCompra WHERE IdDetalleRemito IN (SELECT IdDetalleRemito FROM dbo.Remitos_Detalles WHERE IdRemito = ?) "
         "AND IdDetalleCompra IN (SELECT IdDetalleCompra FROM dbo.Det_Compras WHERE IdCompra = ?)", (id_remito, id_compra)),
        ("DELETE FROM dbo.Remitos_Facturas WHERE IdRemito = ? AND IdDeuda = ?", (id_remito, id_compra)),
        ("UPDATE dbo.Remitos SET NroFactura = ? WHERE IdRemito = ?", (_texto_facturas(resto), id_remito)),
    ])


def facturas_sin_remito(desde=None, hasta=None, proveedor: str | None = None, page: int = 1, page_size: int = 25) -> dict:
    """Facturas con renglones de insumos que no tienen ningún remito vinculado."""
    where, params = ["c.[Tipo documento] = 'Factura'"], []
    if desde is not None:
        where.append("c.Fecha >= ?")
        params.append(as_sql_datetime(desde))
    if hasta is not None:
        where.append("c.Fecha <= ?")
        params.append(as_sql_datetime(hasta))
    if proveedor:
        where.append("ct.[Razon Social] LIKE ?")
        params.append(f"%{proveedor.strip()}%")
    base = f"""
        FROM dbo.Compras c
        JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
        JOIN dbo.Det_Compras d ON d.IdCompra = c.IdDeuda AND ISNULL(d.IdFormulado, 0) <> 0
        WHERE {' AND '.join(where)}
          AND NOT EXISTS (SELECT 1 FROM dbo.Remitos_Facturas rf WHERE rf.IdDeuda = c.IdDeuda)
          AND NOT EXISTS (SELECT 1 FROM dbo.tblRemitoCompra t JOIN dbo.Det_Compras d2 ON d2.IdDetalleCompra = t.IdDetalleCompra WHERE d2.IdCompra = c.IdDeuda)
        GROUP BY c.IdDeuda, c.Fecha, c.[Tipo documento], c.[Nro Documento], ct.[Razon Social], c.IdContacto, c.Moneda
    """
    total = fetch_one(f"SELECT COUNT(*) AS n FROM (SELECT c.IdDeuda {base}) x", tuple(params))["n"]
    filas = fetch_all(
        f"""
        SELECT c.IdDeuda AS idCompra, c.Fecha AS fecha, c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento,
               ct.[Razon Social] AS proveedor, c.IdContacto AS idProveedor, c.Moneda AS moneda,
               COUNT(*) AS renglones, SUM(d.Cantidad * d.[Precio Unitario]) AS neto
        {base}
        ORDER BY c.Fecha DESC, c.IdDeuda DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        (*params, (page - 1) * page_size, page_size),
    )
    return {"items": [{**f, "fecha": _d(f["fecha"]), "neto": _f(f["neto"])} for f in filas], "total": total, "page": page, "pageSize": page_size}
