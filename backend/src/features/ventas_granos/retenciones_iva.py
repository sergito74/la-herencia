"""Retenciones de IVA de ventas de granos (RETIVA / SISA) y su devolución por ARCA (24/11/2026).

La retención va aparte de la venta (Sergio 24/11/2026): cada certificado de [Retenciones IVA Granos] es un crédito con
ARCA, que lo devuelve por transferencia («AFIP 5000 625») unos 90 días después, a veces agrupando varios certificados.

`listar()` asocia cada devolución acreditada en el Galicia o en el BNA con el grupo de certificados pendientes que suma
exactamente su importe (los más viejos primero; cada certificado se usa una sola vez) y da el estado de cada uno:
  · devuelto (fecha y banco de la acreditación),
  · pendiente (dentro de los 90 días),
  · vencido (más de 90 días sin acreditarse) → alarma,
  · aplicado (importe a devolver 0: el crédito se usó para otro impuesto, no se espera devolución).
Solo lectura: se calcula cada vez, así una devolución nueva en el extracto cierra sola su certificado.
"""

from __future__ import annotations

from datetime import date, datetime
from itertools import combinations

from src.db.connection import fetch_all

PLAZO_DIAS = 90
VENTANA_DIAS = 400  # una devolución no se asocia a certificados de más de ~13 meses antes
MAX_CANDIDATOS = 30
TOLERANCIA_AGRUPADA = 0.02


def _d(v) -> date | None:
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


def _certificados() -> list[dict]:
    return fetch_all(
        """
        SELECT r.IdRetencion AS id, r.[Nro Certificado] AS certificado, CAST(r.[Importe Retenido] AS float) AS importe,
               CAST(ISNULL(r.[Importe Devolucion], r.[Importe Retenido]) AS float) AS aDevolver, r.Imagen AS archivo,
               v.IdVenta AS idVenta, v.Fecha AS fecha, v.[Nro Documento] AS coe, g.Grano AS grano, v.[Campaña] AS campania,
               ag.[Razon Social] AS agente
        FROM dbo.[Retenciones IVA Granos] r
        JOIN dbo.[Venta Granos] v ON v.IdVenta = r.IdLiquidacion
        LEFT JOIN dbo.Granos g ON g.IdGrano = v.IdProducto
        LEFT JOIN dbo.Contactos ag ON ag.IdContacto = r.[Agente Retencion]
        WHERE ISNULL(r.[Importe Retenido], 0) > 0
        ORDER BY v.Fecha, r.IdRetencion
        """)


def _devoluciones() -> list[dict]:
    galicia = fetch_all(
        "SELECT Fecha AS fecha, CAST([Créditos] AS float) AS importe, 'Galicia' AS banco, IdMovimiento AS id "
        "FROM dbo.[Movimientos Galicia] WHERE [Créditos] > 0 AND (LeyendasAdicionales1 LIKE '%AFIP 5000 625%' "
        "OR [Descripción] LIKE '%AFIP 5000 625%')")
    bna = fetch_all(
        "SELECT [Fecha / Hora Mov#] AS fecha, CAST(Importe AS float) AS importe, 'Nación' AS banco, IdMovimientoBNA AS id "
        "FROM dbo.[Movimientos BNA] WHERE Importe > 0 AND Concepto LIKE '%AFIP 5000 625%'")
    return sorted(galicia + bna, key=lambda x: (_d(x["fecha"]), x["importe"]))


def _grupo(pendientes: list[dict], importe: float, fecha: date) -> tuple[list[dict], bool] | None:
    """Subconjunto de certificados pendientes (cualquier cantidad) que suma exactamente la devolución; si no hay, el que
    más se acerque por debajo con una diferencia de hasta TOLERANCIA_AGRUPADA (retenciones viejas sin certificado en la
    tabla que ARCA devolvió en la misma transferencia). Devuelve (grupo, exacto)."""
    cand = [c for c in pendientes if _d(c["fecha"]) <= fecha and (fecha - _d(c["fecha"])).days <= VENTANA_DIAS][:MAX_CANDIDATOS]
    objetivo = round(importe * 100)
    alcanzables: dict[int, tuple[int, ...]] = {0: ()}
    for k, c in enumerate(cand):
        v = round(c["aDevolver"] * 100)
        for suma, idx in list(alcanzables.items()):
            nueva = suma + v
            if nueva <= objetivo and nueva not in alcanzables:
                alcanzables[nueva] = idx + (k,)
    if objetivo in alcanzables and alcanzables[objetivo]:
        return [cand[k] for k in alcanzables[objetivo]], True
    mejor = max((s_ for s_ in alcanzables if s_ > 0), default=0)
    if mejor and (objetivo - mejor) <= objetivo * TOLERANCIA_AGRUPADA:
        return [cand[k] for k in alcanzables[mejor]], False
    return None


def listar(hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    certs = _certificados()
    # Importe a devolver 0: ARCA no lo devuelve porque el crédito se aplicó a otro impuesto (ej. 09601-2022-064957, Sergio
    # 24/11/2026). No espera devolución ni es alarma; en la cuenta de AFIP tampoco figura como crédito.
    pendientes = [c for c in certs if round(c["aDevolver"], 2) > 0]
    devolucion: dict[int, dict] = {}
    for dv in _devoluciones():
        f = _d(dv["fecha"])
        r = _grupo(pendientes, dv["importe"], f)
        if not r:
            continue
        grupo, exacto = r
        for c in grupo:
            devolucion[c["id"]] = {"fecha": f, "banco": dv["banco"], "importe": round(dv["importe"], 2),
                                   "agrupa": len(grupo), "exacto": exacto}
            pendientes.remove(c)
    items = []
    for c in certs:
        f = _d(c["fecha"])
        dv = devolucion.get(c["id"])
        dias = (hoy - f).days if f else 0
        estado = ("devuelto" if dv else "aplicado" if round(c["aDevolver"], 2) <= 0
                  else "vencido" if dias > PLAZO_DIAS else "pendiente")
        items.append({
            "idRetencion": c["id"], "certificado": c["certificado"], "importe": round(c["importe"], 2),
            "idVenta": c["idVenta"], "fecha": f, "coe": c["coe"], "grano": c["grano"], "campania": c["campania"],
            "agente": c["agente"], "archivo": c["archivo"], "estado": estado, "dias": dias,
            "devolucion": dv,
        })
    items.sort(key=lambda x: (x["fecha"] or date.min), reverse=True)

    def total(e):
        return round(sum(i["importe"] for i in items if i["estado"] == e), 2)

    return {"items": items, "resumen": {
        "devuelto": total("devuelto"), "pendiente": total("pendiente"), "vencido": total("vencido"),
        "aplicado": total("aplicado"),
        "cantidadVencidos": sum(1 for i in items if i["estado"] == "vencido")}}
