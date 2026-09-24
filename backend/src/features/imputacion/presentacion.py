"""Contexto comercial y destinos legibles, sin recalcular ni escribir propuestas."""

from src.db.connection import fetch_all


def enriquecer_fracciones(filas: list[dict]) -> list[dict]:
    if not filas:
        return filas
    ids = tuple(dict.fromkeys(f["idPropuesta"] for f in filas))
    contexto = {}
    # Respetar el límite de parámetros ODBC también al consultar un detalle completo.
    for inicio in range(0, len(ids), 1000):
        lote = ids[inicio:inicio + 1000]
        marcas = ",".join("?" for _ in lote)
        for fila in fetch_all(
            f"""SELECT p.IdPropuesta AS idPropuesta,
                CASE WHEN p.Origen = 'Contratista' THEN 'Servicios de contratista'
                     ELSE dc.[Producto/Servicio] END AS producto,
                c.IdDeuda AS idCompra, ct.[Razon Social] AS proveedor,
                c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento,
                c.Fecha AS fechaDocumento, c.Moneda AS monedaDocumento,
                cu.Cultivo AS cultivo, ca.Campaña AS campania,
                lo.[Numero Lote] AS lote, cc.[Centro de costos] AS centroCosto
            FROM dbo.ImputacionPropuestas p
            LEFT JOIN dbo.Det_Compras dc
                ON p.Origen = 'Insumo' AND dc.IdDetalleCompra = p.IdDetalleCompra
            LEFT JOIN dbo.Compras c ON c.IdDeuda =
                CASE WHEN p.Origen = 'Contratista' THEN p.IdDetalleCompra ELSE dc.IdCompra END
            LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
            LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = p.IdCultivo
            LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = p.IdCampania
            LEFT JOIN dbo.Lotes lo ON lo.IdLote = p.IdLote
            LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = p.IdCentroCosto
            WHERE p.IdPropuesta IN ({marcas})""",
            lote,
        ):
            contexto[fila["idPropuesta"]] = fila
    return [{**f, **contexto.get(f["idPropuesta"], {})} for f in filas]
