"""Listado de imputación para el Estudio contable (050 US8, T043).

Reemplaza a pedido "Listado General Compras - Imputacion (1-9-2015 en adelante).xlsx" (carpeta Compras de Dropbox):
- las 14 columnas de siempre, en el mismo orden y formato, más "Importe en pesos";
- renglón fuera del esquema nuevo: una fila, como hoy;
- renglón en el esquema nuevo con imputación aprobada: una fila por cultivo/campaña (y "En stock" para lo que no se
  usó todavía); los totales de esas filas suman el total del renglón al centavo. El flete sigue a sus insumos.
Se escribe a un archivo temporal en la misma carpeta y se renombra: si el listado está abierto en Excel no se
reemplaza y el archivo anterior queda intacto.
"""

from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

from src.db.connection import fetch_all
from src.features.resultado_cultivo.costos import _REPARTO_VIGENTE, VIGENTE_050

CARPETA = Path(r"C:\Users\Sergio\Dropbox\Giamigli de Bolivar SA\Compras")
ARCHIVO = "Listado General Compras - Imputacion (1-9-2015 en adelante).xlsx"
DESDE = date(2015, 9, 1)
HOJA = "Cns_Imputacion_Compras"

COLUMNAS = ["Fecha", "Razon Social", "Tipo documento", "Nro Documento", "Moneda", "Tipo de Cambio",
            "Ajusta Tipo Cambio", "Cantidad", "Producto/Servicio", "Centro de costos", "Rubro", "Destino",
            "Campaña", "Total", "Importe en pesos"]
_ANCHOS = [10.8, 36.9, 20.1, 19.8, 12.8, 19.6, 22.9, 13.3, 52.8, 20.6, 28.6, 24.9, 13.8, 15.3, 18.0]
_FMT_FECHA = "d-mmm-yy"
_FMT_TC = '"$"\\ #.##000;\\-"$"\\ #.##000'
_FMT_TOTAL = '"$"\\ #,##0.00;"$"\\-#,##0.00'
_FMT_TOTAL_USD = '"us$"\\ #,##0.00;"us$"\\-#,##0.00'


class ListadoAbierto(Exception):
    """El archivo está abierto (en Excel): no se puede reemplazar."""


def _cant(v):
    """Cantidad como la mostraba Access (precisión simple, 7 cifras)."""
    return None if v is None else float(f"{float(v):.7g}")


def repartir_total(total: float, pesos: list[float]) -> list[float]:
    """Pura. Reparte `total` según `pesos`; la última fila absorbe los centavos para que la suma dé el total exacto."""
    suma = sum(pesos)
    if not pesos:
        return []
    if abs(suma) < 1e-9:
        return [total] + [0.0] * (len(pesos) - 1)
    out = [round(total * p / suma, 2) for p in pesos[:-1]]
    out.append(total - sum(out))  # el resto exacto: la suma da el total del renglón tal como está guardado
    return out


def _renglones() -> list[dict]:
    return fetch_all(
        """
        SELECT c.Fecha AS fecha, co.[Razon Social] AS razonSocial, c.[Tipo documento] AS tipoDocumento,
               c.[Nro Documento] AS nroDocumento, c.Moneda AS moneda, c.[Tipo de Cambio] AS tc,
               c.[Ajusta Tipo Cambio] AS ajustaTc, d.Cantidad AS cantidad, d.[Producto/Servicio] AS producto,
               cc.[Centro de costos] AS centro, r.Rubro AS rubro, de.Destino AS destino, ca.[Campaña] AS campania,
               d.Cantidad * d.[Precio Unitario] AS total, d.IdDetalleCompra AS id, d.IdCompra AS idCompra,
               pr.Nombre AS parteRubro, pt.Nombre AS parteTamiz, tz.Destino AS destinoTamiz,
               CASE WHEN tr.ReglaDepende = 'FleteInsumo' THEN 1 ELSE 0 END AS esFlete
        FROM dbo.Det_Compras d
        JOIN dbo.Compras c ON c.IdDeuda = d.IdCompra
        LEFT JOIN dbo.Contactos co ON co.IdContacto = c.IdContacto
        LEFT JOIN dbo.[Centro de Costos] cc ON cc.IdCentro = d.IdCentroCostos
        LEFT JOIN dbo.Rubros r ON r.IdRubro = d.IdRubro
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = d.IdDestino
        LEFT JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = d.[IdCampaña]
        LEFT JOIN dbo.TamizRubroDestino tr ON tr.IdRubro = d.IdRubro
        LEFT JOIN dbo.PartesEstructuraCosto pr ON pr.IdParte = tr.IdParte
        LEFT JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = d.IdDetalleCompra AND tz.Vigente = 1
        LEFT JOIN dbo.PartesEstructuraCosto pt ON pt.IdParte = tz.IdParte
        WHERE c.Fecha >= ?
        ORDER BY c.Fecha, c.IdDeuda, d.IdDetalleCompra
        """,
        (DESDE,),
    )


def _fracciones() -> dict[int, list[dict]]:
    """Fracciones aprobadas de la corrida vigente (Insumo o Directo) de cada renglón en alcance."""
    out: dict[int, list[dict]] = defaultdict(list)
    for f in fetch_all(
        """
        SELECT p.IdDetalleCompra AS id, p.IdCultivo AS idCultivo, p.IdCampania AS idCampania, p.EsGanaderia AS ganaderia,
               p.IdCentroCosto AS idCentro, p.IdOrdenTrabajo AS idOrden, p.Importe AS importe, p.Cantidad AS cantidad,
               pe.Nombre AS parte, ca.[Campaña] AS campania, de.Destino AS destino
        FROM dbo.ImputacionPropuestas p
        JOIN dbo.TamizRenglones tz ON tz.IdDetalleCompra = p.IdDetalleCompra AND tz.Vigente = 1
        LEFT JOIN dbo.PartesEstructuraCosto pe ON pe.IdParte = p.IdParte
        LEFT JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = p.IdCampania
        LEFT JOIN dbo.Map_CultivoResultado m ON m.IdCultivo = p.IdCultivo
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = m.IdDestino
        WHERE p.Origen IN ('Insumo', 'Directo')
          AND {vigente}
          AND NOT EXISTS (SELECT 1 FROM dbo.ImputacionPropuestas p3 WHERE p3.IdCorrida = p.IdCorrida AND p3.Estado <> 'Aprobada')
        """.format(vigente=VIGENTE_050)
    ):
        out[f["id"]].append(f)
    return out


def _reparto_ordenes() -> tuple[dict[int, list[dict]], set[int]]:
    """17/11/2026: facturas de contratista repartidas por órdenes de trabajo (048): fracciones por compra, y los
    renglones de labor que siguen ese reparto (clasificados "según las órdenes")."""
    por_compra: dict[int, list[dict]] = defaultdict(list)
    for f in fetch_all(
        f"""
        SELECT p.IdDetalleCompra AS idCompra, p.IdCultivo AS idCultivo, p.IdCampania AS idCampania, p.EsGanaderia AS ganaderia,
               p.IdCentroCosto AS idCentro, p.Importe AS importe, p.Cantidad AS cantidad, pe.Nombre AS parte,
               ca.[Campaña] AS campania, de.Destino AS destino
        FROM dbo.ImputacionPropuestas p
        JOIN {_REPARTO_VIGENTE} v ON v.idCorrida = p.IdCorrida
        LEFT JOIN dbo.PartesEstructuraCosto pe ON pe.IdParte = p.IdParte
        LEFT JOIN dbo.[Campañas] ca ON ca.[IdCampaña] = p.IdCampania
        LEFT JOIN dbo.Map_CultivoResultado m ON m.IdCultivo = p.IdCultivo
        LEFT JOIN dbo.DestinoCompras de ON de.IdDestino = m.IdDestino
        WHERE p.IdOrdenTrabajo IS NOT NULL
        """
    ):
        f["cantidad"] = None  # la cantidad del reparto son hectáreas de la orden, no la del renglón
        por_compra[f["idCompra"]].append(f)
    renglones = {f["id"] for f in fetch_all(
        "SELECT IdDetalleCompra AS id FROM dbo.TamizRenglones WHERE Vigente = 1 AND OrigenDecision = 'Orden'")}
    return por_compra, renglones


def _clave(f: dict, base: dict) -> tuple:
    """Agrupa las fracciones (que vienen por lote) en lo que ve el Estudio: centro, destino, campaña y parte."""
    if f["idCultivo"] is not None:
        return ("Agricultura", f["destino"] or base["destino"], f["campania"], f["parte"] or base["parteTamiz"])
    if f["ganaderia"]:
        return ("Ganaderia", "General", "No Aplica", f["parte"] or base["parteTamiz"])
    if f["idCentro"] is not None:
        return ("Adm. General", "General", "No Aplica", f["parte"] or base["parteTamiz"])
    return (base["centro"], "En stock", "No Aplica", f["parte"] or base["parteTamiz"])  # lo que sigue en stock


def _relacionadas() -> dict[int, set[int]]:
    rel: dict[int, set[int]] = defaultdict(set)
    for r in fetch_all("SELECT IdCompra AS a, IdCompraRelacionada AS b FROM dbo.CompraDocumentosRelacionados"):
        rel[r["a"]].add(r["b"])
        rel[r["b"]].add(r["a"])
    return rel


def _fila(base: dict, total: float, cantidad, centro, destino, campania, parte) -> list:
    tc = float(base["tc"] or 0)
    pesos = round(total * tc, 2) if base["moneda"] == "Dolares" else round(total, 2)
    fecha = base["fecha"].date() if hasattr(base["fecha"], "date") else base["fecha"]
    return [fecha, base["razonSocial"], base["tipoDocumento"], base["nroDocumento"], base["moneda"], base["tc"],
            bool(base["ajustaTc"]), _cant(cantidad), base["producto"], centro, base["rubro"], destino, campania,
            total, pesos]


def armar_filas() -> list[list]:
    renglones = _renglones()
    fracciones = _fracciones()
    ordenes_compra, por_ordenes = _reparto_ordenes()
    relacionadas = None
    por_compra: dict[int, list[int]] = defaultdict(list)
    for r in renglones:
        if fracciones.get(r["id"]) and not r["esFlete"]:
            por_compra[r["idCompra"]].append(r["id"])

    filas = []
    for r in renglones:
        total = float(r["total"]) if r["total"] is not None else None
        propias = fracciones.get(r["id"])
        if not propias and r["id"] in por_ordenes and ordenes_compra.get(r["idCompra"]):
            propias = ordenes_compra[r["idCompra"]]  # labor repartida según las órdenes de trabajo
        if r["esFlete"] and r["destinoTamiz"] == "CultivoStock" and not propias:
            # Flete de insumos: sigue a los usos de los insumos de su factura (o de la factura relacionada).
            destinos = list(por_compra.get(r["idCompra"], []))
            if not destinos:
                relacionadas = relacionadas if relacionadas is not None else _relacionadas()
                destinos = [i for otra in relacionadas.get(r["idCompra"], ()) for i in por_compra.get(otra, [])]
            propias = [f for i in destinos for f in fracciones[i]]
            con_cantidad = False
        else:
            con_cantidad = True
        if not propias or total is None:
            filas.append(_fila(r, r["total"], r["cantidad"], r["centro"], r["destino"], r["campania"],
                               r["parteTamiz"] or r["parteRubro"]))
            continue
        grupos: dict[tuple, dict] = {}
        for f in propias:
            g = grupos.setdefault(_clave(f, r), {"importe": 0.0, "cantidad": 0.0})
            g["importe"] += float(f["importe"] or 0)
            g["cantidad"] += float(f["cantidad"] or 0)
        claves = list(grupos)
        totales = repartir_total(total, [grupos[k]["importe"] for k in claves])
        cantidad = float(r["cantidad"] or 0)
        suma_cant = sum(grupos[k]["cantidad"] for k in claves)
        for k, t in zip(claves, totales):
            if not con_cantidad:
                q = r["cantidad"] if len(claves) == 1 else None
            elif suma_cant > 1e-9:
                q = cantidad * grupos[k]["cantidad"] / suma_cant
            else:
                q = cantidad * t / total if total else None
            filas.append(_fila(r, t, q, *k))
    return filas


def escribir(filas: list[list], destino: Path) -> None:
    """Escribe a un temporal en la misma carpeta y lo renombra sobre `destino` (no deja un archivo a medio escribir)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = HOJA
    ws.append(COLUMNAS)
    for f in filas:
        ws.append(f)
    for i, ancho in enumerate(_ANCHOS, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = ancho
    for fila in ws.iter_rows(min_row=2):
        fila[0].number_format = _FMT_FECHA
        fila[5].number_format = _FMT_TC
        fila[13].number_format = _FMT_TOTAL_USD if fila[4].value == "Dolares" else _FMT_TOTAL
        fila[14].number_format = _FMT_TOTAL
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:O{len(filas) + 1}"
    fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=str(destino.parent), prefix="~listado-")
    os.close(fd)
    try:
        wb.save(tmp)
        try:
            os.replace(tmp, destino)
        except PermissionError as e:
            raise ListadoAbierto("El listado está abierto en Excel; cerralo y volvé a generarlo.") from e
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def generar(destino: Path | None = None) -> dict:
    destino = destino or (CARPETA / ARCHIVO)
    filas = armar_filas()
    escribir(filas, destino)
    return {"filas": len(filas), "archivo": destino.name}
