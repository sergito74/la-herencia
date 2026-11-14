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
               de.IdCultivo AS idCultivo, d.[IdCampaña] AS idCampania, c.Fecha AS fecha, c.IdContacto AS idContacto
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
        SELECT t.IdDetalleCompra AS idDetalleCompra, t.Destino AS destino, p.Nombre AS parte, t.IdCultivo AS idCultivo,
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
