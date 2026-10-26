"""Router para consulta y actualización de cotizaciones unificadas (Dólar BNA e Índice INMAG)."""
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.db.connection import fetch_all, _assert_target_is_wc
from src.features.pastaje import inmag
from scripts.indice_inmag import actualizar_dolar

router = APIRouter(prefix="/api/finanzas/cotizaciones", tags=["Cotizaciones"])


class CotizacionDia(BaseModel):
    fecha: str
    inmag: Optional[float] = None
    cabezasIngresadas: Optional[int] = None
    inmagOrigen: Optional[str] = None
    dolarCompraBillete: Optional[float] = None
    dolarVentaBillete: Optional[float] = None
    dolarPromedioBillete: Optional[float] = None
    dolarCompraDivisa: Optional[float] = None
    dolarVentaDivisa: Optional[float] = None


@router.get("", response_model=list[CotizacionDia])
def listar_cotizaciones(
    desde: Optional[str] = Query(None, description="Fecha desde (AAAA-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha hasta (AAAA-MM-DD)"),
    mes: Optional[str] = Query(None, description="Mes en formato AAAA-MM")
):
    if mes:
        año, m = map(int, mes.split("-"))
        f_desde = date(año, m, 1)
        if m == 12:
            f_hasta = date(año + 1, 1, 1) - timedelta(days=1)
        else:
            f_hasta = date(año, m + 1, 1) - timedelta(days=1)
        desde_str = f_desde.isoformat()
        hasta_str = f_hasta.isoformat()
    else:
        desde_str = desde or (date.today() - timedelta(days=60)).isoformat()
        hasta_str = hasta or date.today().isoformat()

    sql = """
        SELECT 
            COALESCE(i.Fecha, CAST(d.Fecha AS date)) AS Fecha,
            i.Indice AS Inmag,
            i.CabIngresadas,
            i.Origen AS InmagOrigen,
            d.Comp_billete AS DolarCompraBillete,
            d.Vend_billete AS DolarVentaBillete,
            d.Prom_billete AS DolarPromedioBillete,
            d.Comp_Divisa AS DolarCompraDivisa,
            d.Vend_Divisa AS DolarVentaDivisa
        FROM dbo.IndiceINMAG i
        FULL OUTER JOIN dbo.[Dolar BNA] d ON i.Fecha = CAST(d.Fecha AS date)
        WHERE COALESCE(i.Fecha, CAST(d.Fecha AS date)) BETWEEN ? AND ?
        ORDER BY Fecha DESC
    """
    filas = fetch_all(sql, (desde_str, hasta_str))
    res = []
    for r in filas:
        f = r["Fecha"]
        fecha_str = f.isoformat() if hasattr(f, "isoformat") else str(f)[:10]
        res.append(CotizacionDia(
            fecha=fecha_str,
            inmag=float(r["Inmag"]) if r["Inmag"] is not None else None,
            cabezasIngresadas=r["CabIngresadas"],
            inmagOrigen=r["InmagOrigen"],
            dolarCompraBillete=float(r["DolarCompraBillete"]) if r["DolarCompraBillete"] is not None else None,
            dolarVentaBillete=float(r["DolarVentaBillete"]) if r["DolarVentaBillete"] is not None else None,
            dolarPromedioBillete=float(r["DolarPromedioBillete"]) if r["DolarPromedioBillete"] is not None else None,
            dolarCompraDivisa=float(r["DolarCompraDivisa"]) if r["DolarCompraDivisa"] is not None else None,
            dolarVentaDivisa=float(r["DolarVentaDivisa"]) if r["DolarVentaDivisa"] is not None else None,
        ))
    return res


@router.post("/actualizar")
def actualizar_cotizaciones():
    _assert_target_is_wc()
    res_inmag = inmag.actualizar()
    res_dolar = 0
    try:
        res_dolar = actualizar_dolar()
    except Exception as e:
        pass
    return {
        "status": "ok",
        "inmag_agregados": res_inmag.get("agregados", 0),
        "dolar_agregados": res_dolar,
        "mensaje": f"Cotizaciones sincronizadas: {res_inmag.get('agregados', 0)} días de INMAG, {res_dolar} días de Dólar BNA."
    }

