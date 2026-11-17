"""Acceso a datos del tamiz por rubro (050): reglas, alcance y clasificación vigente por renglón."""

from __future__ import annotations

from src.db.connection import execute_write_transaction, fetch_all, fetch_one

CAMPANIA_NO_APLICA = 20


def config() -> dict:
    return fetch_one("SELECT IdDeudaCorte AS idDeudaCorte, Activo AS activo FROM dbo.ImputacionConfig WHERE Id = 1") or {
        "idDeudaCorte": None, "activo": False,
    }


def reglas_rubro() -> dict[int, dict]:
    filas = fetch_all("SELECT IdRubro AS idRubro, Destino AS destino, IdParte AS idParte, ReglaDepende AS regla FROM dbo.TamizRubroDestino")
    return {f["idRubro"]: f for f in filas}


def reglas_producto() -> list[dict]:
    return fetch_all(
        "SELECT IdRegla AS idRegla, TextoNormalizado AS texto, IdFormulado AS idFormulado, Destino AS destino, IdParte AS idParte "
        "FROM dbo.TamizReglaProducto"
    )


def renglones_de_compra(id_compra: int) -> list[dict]:
    return fetch_all(
        """
        SELECT d.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, d.[Producto/Servicio] AS producto,
               ISNULL(d.Cantidad, 0) AS cantidad, ISNULL(d.[Precio Unitario], 0) AS precio,
               NULLIF(d.IdFormulado, 0) AS idFormulado, d.IdRubro AS idRubro, d.IdDestino AS idDestino,
               de.IdCultivo AS idCultivo, d.[IdCampaña] AS idCampania, c.Fecha AS fecha, c.IdContacto AS idContacto,
               c.[Tipo documento] AS tipoDocumento, d.Unidad AS unidad
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        WHERE d.IdCompra = ?
        ORDER BY d.IdDetalleCompra
        """,
        (id_compra,),
    )


def compra_en_alcance(id_compra: int) -> bool:
    """Una compra entra al esquema nuevo si se cargó después del corte (IdDeuda > IdDeudaCorte) o si alguno de
    sus renglones fue marcado en ImputacionAlcance (research R-01). Sin corte fijado, nada está en alcance."""
    cfg = config()
    if cfg["idDeudaCorte"] is not None and id_compra > int(cfg["idDeudaCorte"]):
        return True
    return fetch_one(
        "SELECT TOP 1 1 AS x FROM dbo.ImputacionAlcance a JOIN dbo.Det_Compras d ON d.IdDetalleCompra = a.IdDetalleCompra "
        "WHERE d.IdCompra = ?", (id_compra,),
    ) is not None


def renglones_marcados(id_compra: int) -> set[int] | None:
    """None = la compra entera es nueva (después del corte); si no, solo los renglones marcados en
    ImputacionAlcance (R-01: en una factura vieja, lo ya imputado no se toca)."""
    cfg = config()
    if cfg["idDeudaCorte"] is not None and id_compra > int(cfg["idDeudaCorte"]):
        return None
    return {f["id"] for f in fetch_all(
        "SELECT a.IdDetalleCompra AS id FROM dbo.ImputacionAlcance a JOIN dbo.Det_Compras d ON d.IdDetalleCompra = a.IdDetalleCompra "
        "WHERE d.IdCompra = ?", (id_compra,))}


def guardar_clasificaciones(clasificaciones: list[dict], usuario: str | None = None) -> None:
    """Una sola clasificación vigente por renglón: la anterior queda como historial (Vigente = 0)."""
    sentencias = []
    for c in clasificaciones:
        sentencias.append(("UPDATE dbo.TamizRenglones SET Vigente = 0 WHERE IdDetalleCompra = ? AND Vigente = 1",
                           (c["idDetalleCompra"],)))
        sentencias.append((
            "INSERT INTO dbo.TamizRenglones (IdDetalleCompra, Destino, IdParte, IdCultivo, IdCampania, OrigenDecision, "
            "Estado, Motivo, Vigente, Usuario) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (c["idDetalleCompra"], c["destino"], c["idParte"], c["idCultivo"], c["idCampania"], c["origen"],
             c["estado"], c["motivo"], usuario),
        ))
    if sentencias:
        execute_write_transaction(sentencias)


def clasificacion_vigente(id_compra: int) -> list[dict]:
    return fetch_all(
        """
        SELECT t.IdDetalleCompra AS idDetalleCompra, d.[Producto/Servicio] AS producto,
               ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) AS importe, t.IdParte AS idParte,
               t.Destino AS destino, p.Nombre AS parte, t.IdCultivo AS idCultivo,
               cu.Cultivo AS cultivo, t.IdCampania AS idCampania, ca.[Campaña] AS campania, t.OrigenDecision AS origen,
               t.Estado AS estado, t.Motivo AS motivo
        FROM dbo.TamizRenglones t
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = t.IdDetalleCompra
        LEFT JOIN dbo.PartesEstructuraCosto p ON p.IdParte = t.IdParte
        LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = t.IdCultivo
        LEFT JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = t.IdCampania
        WHERE d.IdCompra = ? AND t.Vigente = 1
        ORDER BY t.IdDetalleCompra
        """,
        (id_compra,),
    )


def pendientes(limite: int = 500) -> list[dict]:
    return fetch_all(
        f"""
        SELECT TOP {int(limite)} t.IdDetalleCompra AS idDetalleCompra, d.IdCompra AS idCompra, c.Fecha AS fecha,
               co.[Razon Social] AS proveedor, c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numero,
               d.[Producto/Servicio] AS producto, t.Motivo AS motivo, t.FechaCalculo AS fechaCalculo
        FROM dbo.TamizRenglones t
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = t.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        WHERE t.Vigente = 1 AND t.Estado = 'Pendiente'
        ORDER BY t.FechaCalculo DESC
        """
    )


def guardar_regla_producto(id_detalle: int, destino: str, id_parte: int | None, usuario: str | None) -> None:
    """Aprende la regla del producto del renglón: por IdFormulado si lo tiene, si no por texto normalizado."""
    from src.features.imputacion.tamiz import normalizar

    r = fetch_one("SELECT NULLIF(IdFormulado, 0) AS f, [Producto/Servicio] AS p FROM dbo.Det_Compras WHERE IdDetalleCompra = ?",
                  (id_detalle,))
    if r is None:
        raise ValueError("Renglón inexistente")
    texto = None if r["f"] else normalizar(r["p"])
    execute_write_transaction([(
        "INSERT INTO dbo.TamizReglaProducto (TextoNormalizado, IdFormulado, Destino, IdParte, Usuario) VALUES (?, ?, ?, ?, ?)",
        (texto, r["f"], destino, id_parte, usuario),
    )])


def campania_por_nombre(nombre: str) -> int | None:
    r = fetch_one("SELECT TOP 1 [IdCampaña] AS id FROM dbo.[Campañas] WHERE [Campaña] = ?", (nombre,))
    return r["id"] if r else None


def cultivos() -> dict[int, str]:
    return {f["id"]: f["nombre"] for f in fetch_all("SELECT IdCultivo AS id, Cultivo AS nombre FROM dbo.Cultivos")}


def cultivos_con_ordenes(id_campania: int) -> list[int]:
    """Cultivos que tienen órdenes de trabajo en la campaña (opciones para deducir el cultivo, T012)."""
    return [f["id"] for f in fetch_all(
        "SELECT DISTINCT IdCultivo AS id FROM dbo.Ordenes_Trabajo_Distrib WHERE IdCampania = ? AND Aplicar = 1 AND IdCultivo IS NOT NULL",
        (id_campania,),
    )]


def nombre_campania(id_campania: int) -> str | None:
    r = fetch_one("SELECT [Campaña] AS n FROM dbo.[Campañas] WHERE [IdCampaña] = ?", (id_campania,))
    return r["n"] if r else None


def destino_financiado(id_compra: int) -> dict | None:
    """050: un interés/financiamiento va donde fue lo que financió. Mira la factura relacionada
    (CompraDocumentosRelacionados) y toma el destino vigente de sus renglones si es uno solo."""
    filas = fetch_all(
        """
        SELECT DISTINCT tz.Destino AS destino, tz.IdParte AS idParte, tz.IdCultivo AS idCultivo, tz.IdCampania AS idCampania
        FROM dbo.CompraDocumentosRelacionados rel
        JOIN dbo.Det_Compras d ON d.IdCompra = CASE WHEN rel.IdCompra = ? THEN rel.IdCompraRelacionada ELSE rel.IdCompra END
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1 AND tz.Estado = 'Aprobada'
        WHERE ? IN (rel.IdCompra, rel.IdCompraRelacionada) AND tz.Destino <> 'CultivoStock'
        """,
        (id_compra, id_compra),
    )
    return filas[0] if len(filas) == 1 else None


_MONETARIAS = ("ARS", "USD")


def _docs_insumo(id_contacto: int, desde) -> list[dict]:
    """Facturas y NC del proveedor desde `desde`, con sus renglones de mercadería (sin ajustes en $ / us$)."""
    filas = fetch_all(
        """
        SELECT c.IdDeuda AS id, c.Fecha AS fecha, c.[Tipo documento] AS tipo, c.[Nro Documento] AS nro,
               d.[Producto/Servicio] AS texto, ISNULL(d.Cantidad, 0) AS cantidad, ISNULL(d.[Precio Unitario], 0) AS precio,
               ISNULL(d.Unidad, '') AS unidad
        FROM dbo.Compras c JOIN dbo.Det_Compras d ON d.IdCompra = c.IdDeuda
        WHERE c.IdContacto = ? AND c.Fecha >= ? AND c.[Tipo documento] IN ('Factura', 'Nota de Crédito')
        """,
        (id_contacto, desde),
    )
    docs: dict[int, dict] = {}
    for f in filas:
        d = docs.setdefault(f["id"], {"id": f["id"], "fecha": f["fecha"], "tipo": f["tipo"], "nro": f["nro"], "renglones": []})
        if (f["unidad"] or "").strip().upper() not in _MONETARIAS:
            d["renglones"].append(f)
    return list(docs.values())


def anulada(id_compra: int) -> str | None:
    """050 (16/11/2026): la factura anulada por una NC y esa NC no se imputan (la mercadería no se usó o se
    refacturó). Una NC anula una factura del mismo proveedor, anterior o del mismo día, si (a) un renglón de la NC
    la nombra con su número exacto ("NC FC 3233"), o (b) devuelve los mismos productos en la misma cantidad y por el
    mismo importe (±2%). Devuelve el motivo o None."""
    import re
    cab = fetch_one("SELECT IdContacto AS c, Fecha AS f, [Tipo documento] AS t FROM dbo.Compras WHERE IdDeuda = ?", (id_compra,))
    if cab is None or cab["t"] not in ("Factura", "Nota de Crédito"):
        return None
    docs = _docs_insumo(cab["c"], "2015-01-01")
    facturas = [d for d in docs if d["tipo"] == "Factura" and d["renglones"]]
    notas = [d for d in docs if d["tipo"] == "Nota de Crédito" and d["renglones"]]

    relacionadas = {(x["a"], x["b"]) for x in fetch_all(
        "SELECT IdCompra AS a, IdCompraRelacionada AS b FROM dbo.CompraDocumentosRelacionados "
        "UNION SELECT IdCompraRelacionada, IdCompra FROM dbo.CompraDocumentosRelacionados")}

    def numero(nro):
        dig = re.sub(r"\D", "", nro or "")
        return int(dig[-8:]) if dig else None

    def total(d):
        return abs(sum(float(r["cantidad"]) * float(r["precio"]) for r in d["renglones"]))

    def clave(d):
        return sorted((re.sub(r"\s+", " ", (r["texto"] or "").upper()).strip(), round(abs(float(r["cantidad"])), 2)) for r in d["renglones"])

    def nombra(nc, fac):
        for r in nc["renglones"]:
            m = re.search(r"\bFC\s*0*(\d{3,8})\b", (r["texto"] or "").upper())
            if m and int(m.group(1)) == numero(fac["nro"]):
                return True
        return False

    def iguales(nc, fac):
        mismo_importe = abs(total(nc) - total(fac)) <= 0.02 * max(total(fac), 1)
        agrup = lambda d: {t: sum(q for tt, q in clave(d) if tt == t) for t, _ in clave(d)}
        if agrup(nc) == agrup(fac) and mismo_importe:
            return True
        # Relacionadas en documentos relacionados, con la misma cantidad total aunque el texto difiera.
        cant = lambda d: round(sum(abs(float(r["cantidad"])) for r in d["renglones"]), 2)
        return mismo_importe and cant(nc) == cant(fac) and (nc["id"], fac["id"]) in relacionadas

    # Emparejamiento: una NC que nombra facturas anula esas (puede ser más de una); si no, anula UNA sola factura,
    # la más cercana anterior con el mismo contenido que no haya anulado otra NC.
    pares: dict[int, int] = {}  # factura -> NC
    for nc in sorted(notas, key=lambda d: (d["fecha"], d["id"])):
        nombradas = [f for f in facturas if f["fecha"] <= nc["fecha"] and nombra(nc, f)]
        if nombradas:
            for f in nombradas:
                pares.setdefault(f["id"], nc["id"])
            continue
        cand = [f for f in facturas if f["fecha"] <= nc["fecha"] and f["id"] not in pares and iguales(nc, f)]
        if cand:
            pares[max(cand, key=lambda f: (f["fecha"], f["id"]))["id"]] = nc["id"]
    nro = {d["id"]: d["nro"] for d in docs}
    if cab["t"] == "Factura":
        return f"Anulada por la nota de crédito {nro[pares[id_compra]]}" if id_compra in pares else None
    anuladas = [nro[f] for f, n in pares.items() if n == id_compra]
    return f"Anula la factura {', '.join(anuladas)}" if anuladas else None


def relacionada_con_insumos(id_compra: int) -> bool:
    """La compra está relacionada (documentos relacionados) con una factura que trae insumos de stock."""
    return fetch_one(
        """
        SELECT TOP 1 1 AS x FROM (SELECT IdCompraRelacionada AS id FROM dbo.CompraDocumentosRelacionados WHERE IdCompra = ?
                                  UNION SELECT IdCompra FROM dbo.CompraDocumentosRelacionados WHERE IdCompraRelacionada = ?) r
        JOIN dbo.Det_Compras d ON d.IdCompra = r.id
        JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro
        WHERE tr.Destino = 'CultivoStock' AND ISNULL(tr.ReglaDepende, '') <> 'FleteInsumo'
        """,
        (id_compra, id_compra),
    ) is not None


def nombre_producto(id_producto: int) -> str:
    f = fetch_one("SELECT Producto AS n FROM dbo.vw_ProductosBase WHERE IdProducto = ?", (id_producto,))
    return (f or {}).get("n") or f"producto {id_producto}"


def renglones_corregidos_a_mano(id_compra: int) -> set[int]:
    return {f["i"] for f in fetch_all(
        "SELECT tz.IdDetalleCompra AS i FROM dbo.TamizRenglones tz JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra "
        "WHERE d.IdCompra = ? AND tz.Vigente = 1 AND tz.OrigenDecision = 'Manual'", (id_compra,))}


def para_revisar() -> list[dict]:
    """050 US6: renglones en alcance que esperan una decisión: clasificación pendiente del tamiz o imputación
    pendiente (la corrida vigente no cerró). Por documento, en lenguaje llano."""
    return fetch_all(
        """
        SELECT c.IdDeuda AS idCompra, c.Fecha AS fecha, co.[Razon Social] AS proveedor, c.[Tipo documento] AS tipoDocumento,
               c.[Nro Documento] AS nroDocumento, d.IdDetalleCompra AS idDetalleCompra, d.[Producto/Servicio] AS producto,
               ISNULL(d.Cantidad, 0) * ISNULL(d.[Precio Unitario], 0) AS importe, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc,
               ISNULL(tz.Motivo, 'La imputación no cierra: revisar') AS motivo
        FROM dbo.TamizRenglones tz
        JOIN dbo.Det_Compras d ON d.IdDetalleCompra = tz.IdDetalleCompra
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        WHERE tz.Vigente = 1 AND (tz.Estado = 'Pendiente' OR EXISTS (
            SELECT 1 FROM dbo.ImputacionPropuestas p WHERE p.IdDetalleCompra = d.IdDetalleCompra AND p.Estado = 'Pendiente'
              AND p.IdCorrida = (SELECT TOP 1 p2.IdCorrida FROM dbo.ImputacionPropuestas p2
                                 WHERE p2.IdDetalleCompra = p.IdDetalleCompra AND p2.Origen = p.Origen AND p2.Estado <> 'Reemplazada' ORDER BY p2.FechaCalculo DESC, p2.IdPropuesta DESC)))
        ORDER BY c.Fecha DESC, c.IdDeuda, d.IdDetalleCompra
        """
    )


def catalogo_correccion() -> dict:
    return {
        "cultivos": fetch_all("SELECT IdCultivo AS id, Cultivo AS nombre FROM dbo.Cultivos ORDER BY Cultivo"),
        "campanias": fetch_all("SELECT TOP 12 [IdCampaña] AS id, [Campaña] AS nombre FROM dbo.[Campañas] "
                               "WHERE [Campaña] <> 'No Aplica' ORDER BY [IdCampaña] DESC"),
    }


def resumen_para_revisar() -> dict:
    """Total en pesos (al TC del comprobante) de lo que espera una decisión y todavía no entró a ningún cultivo."""
    filas = para_revisar()
    pesos = sum(float(f["importe"] or 0) * (float(f["tc"] or 0) if f["moneda"] == "Dolares" else 1.0) for f in filas)
    return {"pesos": round(pesos, 2), "documentos": len({f["idCompra"] for f in filas})}
