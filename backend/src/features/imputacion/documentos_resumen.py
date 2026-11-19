"""Lectura para la pantalla "Documentos" de imputación (auditoría de diseño 18/11/2026, spec 051).

Una fila por documento con sus destinos ya sumados y un estado en lenguaje llano, más los totales de todo lo filtrado
(por estado y por destino). Solo lee: las acciones (aprobar, corregir) siguen en los endpoints de siempre.
"""
from __future__ import annotations

from collections import defaultdict

from src.db.connection import fetch_all
from src.features.imputacion import repository, tamiz_repository
from src.features.imputacion.repository import _VIGENTE_SQL

ESTADOS = {"decision": "Requiere tu decisión", "revisar": "Por revisar", "pendiente": "Pendiente", "aprobado": "Aprobado"}
ORDEN_ESTADO = ["decision", "revisar", "pendiente", "aprobado"]

_FRACCIONES = f"""
SELECT x.IdCompra AS idCompra, x.IdCultivo AS idCultivo, cu.Cultivo AS cultivo, x.IdCampania AS idCampania,
       ca.Campaña AS campania, x.IdCentroCosto AS idCentro, cc.[Centro de costos] AS centro, x.EsGanaderia AS ganaderia,
       x.Estado AS estado, SUM(x.Importe) AS importe
FROM (
  SELECT dc.IdCompra, p.IdCultivo, p.IdCampania, p.IdCentroCosto, p.EsGanaderia, p.Estado, p.Importe
  FROM dbo.ImputacionPropuestas p JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = p.IdDetalleCompra
  WHERE p.Origen <> 'Contratista' AND {_VIGENTE_SQL}
  UNION ALL
  SELECT p.IdDetalleCompra, p.IdCultivo, p.IdCampania, p.IdCentroCosto, p.EsGanaderia, p.Estado, p.Importe
  FROM dbo.ImputacionPropuestas p
  WHERE p.Origen = 'Contratista' AND p.IdOrdenTrabajo IS NOT NULL AND {_VIGENTE_SQL}
) x
LEFT JOIN dbo.Cultivos cu ON cu.IdCultivo = x.IdCultivo
LEFT JOIN dbo.Campañas ca ON ca.IdCampaña = x.IdCampania
LEFT JOIN dbo.[Centro de costos] cc ON cc.IdCentro = x.IdCentroCosto
WHERE x.IdCompra IN (SELECT c.IdDeuda FROM dbo.Compras c {{where}})
GROUP BY x.IdCompra, x.IdCultivo, cu.Cultivo, x.IdCampania, ca.Campaña, x.IdCentroCosto, cc.[Centro de costos], x.EsGanaderia, x.Estado
"""


def destino(f: dict) -> tuple[str, str, str]:
    """(clave, etiqueta, familia) de un destino; la familia da el color del chip."""
    if f.get("estado") == "RequiereIntervencion":
        return "decision", "Sin destino todavía", "aviso"
    if f.get("idCultivo"):
        return f"c{f['idCultivo']}-{f.get('idCampania') or 0}", f"{f['cultivo']} {f.get('campania') or ''}".strip(), "agricultura"
    if f.get("idCentro"):
        return f"cc{f['idCentro']}", f["centro"] or "Centro de costos", "administracion"
    if f.get("ganaderia"):
        return "ganaderia", "Ganadería", "ganaderia"
    return "stock", "En stock sin consumir", "stock"


def estado_documento(estados: set[str], por_revisar: bool) -> str:
    if "RequiereIntervencion" in estados:
        return "decision"
    if por_revisar:
        return "revisar"
    if "Pendiente" in estados:
        return "pendiente"
    return "aprobado"


def _documentos(id_contacto=None, fecha_desde=None, fecha_hasta=None) -> list[dict]:
    where, params = repository._filtros_documentos(id_contacto, fecha_desde, fecha_hasta, None)
    where_sql = "WHERE " + " AND ".join(where)
    cabeceras = {d["idCompra"]: d for d in fetch_all(
        f"""SELECT c.IdDeuda AS idCompra, c.Fecha AS fecha, c.IdContacto AS idContacto, ct.[Razon Social] AS proveedor,
                   c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento, c.Moneda AS moneda
            FROM dbo.Compras c LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto {where_sql}""", tuple(params))}
    revisar: dict[int, str] = {}
    for r in tamiz_repository.para_revisar():
        revisar.setdefault(r["idCompra"], r["motivo"])
    pendientes: dict[int, set[str]] = defaultdict(set)  # corridas para aprobar en lote desde la tabla
    for r in fetch_all(f"""SELECT dc.IdCompra AS c, CAST(p.IdCorrida AS varchar(40)) AS k FROM dbo.ImputacionPropuestas p
                           JOIN dbo.Det_Compras dc ON dc.IdDetalleCompra = p.IdDetalleCompra
                           WHERE p.Origen <> 'Contratista' AND p.Estado = 'Pendiente' AND {_VIGENTE_SQL}
                           UNION SELECT p.IdDetalleCompra, CAST(p.IdCorrida AS varchar(40)) FROM dbo.ImputacionPropuestas p
                           WHERE p.Origen = 'Contratista' AND p.Estado = 'Pendiente' AND {_VIGENTE_SQL}"""):
        pendientes[r["c"]].add(r["k"])
    por_doc: dict[int, list[dict]] = defaultdict(list)
    for f in fetch_all(_FRACCIONES.format(where=where_sql), tuple(params)):
        por_doc[f["idCompra"]].append(f)
    salida = []
    for id_compra, cab in cabeceras.items():
        fr = por_doc.get(id_compra, [])
        destinos: dict[str, dict] = {}
        for f in fr:
            clave, etiqueta, familia = destino(f)
            d = destinos.setdefault(clave, {"clave": clave, "etiqueta": etiqueta, "familia": familia, "importe": 0.0})
            d["importe"] += float(f["importe"] or 0)
        importe = round(sum(d["importe"] for d in destinos.values()), 2)
        for d in destinos.values():
            d["importe"] = round(d["importe"], 2)
            d["porcentaje"] = round(d["importe"] / importe * 100) if importe else None
        est = estado_documento({f["estado"] for f in fr}, id_compra in revisar)
        salida.append({**cab, "importe": importe, "estado": est, "estadoTexto": ESTADOS[est],
                       "motivo": revisar.get(id_compra), "corridasPendientes": sorted(pendientes.get(id_compra, ())),
                       "destinos": sorted(destinos.values(), key=lambda d: -abs(d["importe"]))})
    salida.sort(key=lambda d: (str(d["fecha"]), d["idCompra"]), reverse=True)
    return salida


def resumen(id_contacto=None, fecha_desde=None, fecha_hasta=None, estado=None, clave_destino=None,
            page=1, page_size=50) -> dict:
    docs = _documentos(id_contacto, fecha_desde, fecha_hasta)
    # Contadores de estado: con los demás filtros, sin el de estado (así cada pestaña muestra cuántos tiene).
    base = [d for d in docs if not clave_destino or any(x["clave"] == clave_destino for x in d["destinos"])]
    por_estado = {k: {"cantidad": 0, "importe": 0.0} for k in ORDEN_ESTADO}
    for d in base:
        por_estado[d["estado"]]["cantidad"] += 1
        por_estado[d["estado"]]["importe"] += d["importe"]
    filtrados = [d for d in base if not estado or d["estado"] == estado]
    # Destinos: con los demás filtros, sin el de destino.
    por_destino: dict[str, dict] = {}
    for d in (x for x in docs if not estado or x["estado"] == estado):
        for x in d["destinos"]:
            t = por_destino.setdefault(x["clave"], {"clave": x["clave"], "etiqueta": x["etiqueta"], "familia": x["familia"],
                                                    "importe": 0.0, "cantidad": 0})
            t["importe"] += x["importe"]
            t["cantidad"] += 1
    por_proveedor: dict[int | None, dict] = {}
    for d in filtrados:
        t = por_proveedor.setdefault(d["idContacto"], {"idContacto": d["idContacto"], "proveedor": d["proveedor"] or "Sin proveedor",
                                                       "importe": 0.0, "cantidad": 0})
        t["importe"] += d["importe"]
        t["cantidad"] += 1
    inicio = max(page - 1, 0) * page_size
    return {
        "items": filtrados[inicio:inicio + page_size],
        "total": len(filtrados),
        "importe": round(sum(d["importe"] for d in filtrados), 2),
        "porEstado": [{"clave": k, "etiqueta": ESTADOS[k], "cantidad": v["cantidad"], "importe": round(v["importe"], 2)}
                      for k, v in por_estado.items()],
        "porProveedor": sorted(({**t, "importe": round(t["importe"], 2)} for t in por_proveedor.values()),
                               key=lambda t: -abs(t["importe"])),
        "porDestino": sorted(({**t, "importe": round(t["importe"], 2)} for t in por_destino.values()),
                             key=lambda t: -abs(t["importe"])),
    }


def detalle(id_compra: int) -> dict | None:
    cab = fetch_all(
        """SELECT c.IdDeuda AS idCompra, c.Fecha AS fecha, c.IdContacto AS idContacto, ct.[Razon Social] AS proveedor,
                  c.[Tipo documento] AS tipoDocumento, c.[Nro Documento] AS numeroDocumento, c.Moneda AS moneda,
                  c.[Tipo de Cambio] AS tipoDeCambio
           FROM dbo.Compras c LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto WHERE c.IdDeuda = ?""", (id_compra,))
    if not cab:
        return None
    lineas = repository.lineas_con_imputacion(id_compra)
    for l in lineas:
        l["totalFracciones"] = round(sum(float(f["importe"] or 0) for f in l["fracciones"]), 2)
        if str(l["producto"]).startswith("Labores según órdenes de trabajo"):
            l["producto"] = "Labores según las órdenes de trabajo"
        for f in l["fracciones"]:
            f["destino"] = destino({**f, "idCentro": f.get("idCentroCosto"), "centro": f.get("centroCosto"),
                                    "ganaderia": f.get("esGanaderia")})[1]
    motivo = next((r["motivo"] for r in tamiz_repository.para_revisar() if r["idCompra"] == id_compra), None)
    return {**cab[0], "lineas": lineas, "motivo": motivo,
            "importe": round(sum(l["totalFracciones"] for l in lineas), 2)}
