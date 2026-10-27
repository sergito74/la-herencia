"""Lectura normalizada y agregación de movimientos bancarios reales (018).

Solo lectura (`fetch_all`) sobre `Movimientos BNA`/`Movimientos Galicia` —
nunca escribe (constitución II, FR-006). No introduce una fuente de verdad
paralela: los mismos totales que muestra Tesorería para un banco/rango deben
coincidir exactamente con lo que agrega este módulo (SC-002).
"""

from __future__ import annotations

from functools import lru_cache

from collections import defaultdict
from datetime import date, datetime, timedelta

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.flujo_caja import atribucion
from src.features.flujo_caja import cotizacion as cot
import json
from pathlib import Path
from src.features.flujo_caja.clasificacion import TIPOS_INTERNOS, emparejar_traspasos, es_interno, tipo_interno

def _posiciones_fima_oficiales() -> dict[str, float]:
    json_path = Path(__file__).resolve().parent / "fima_posiciones.json"
    if not json_path.exists():
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {item["periodo"]: float(item["saldo"]) for item in data.values()}

FECHA_PRIMER_SALDO_CONOCIDO = date(2010, 8, 31)


def get_movimientos_normalizados(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    """Movimientos de BNA (3 cuentas ya distinguidas) + Galicia en un mismo
    formato: `{fecha, banco, numeroCuentaBancaria, importe, concepto,
    idContacto, contacto, esInterno}`."""
    desde, hasta = as_sql_datetime(fecha_desde), as_sql_datetime(fecha_hasta)

    filas_bna = fetch_all(
        """
        SELECT m.IdMovimientoBNA AS idMovimiento, m.[Fecha / Hora Mov#] AS fecha, m.Importe AS importe,
               m.Concepto AS concepto, m.IdContacto AS idContacto, m.Contacto AS contacto,
               cb.NumeroCuenta AS numeroCuentaBancaria
        FROM dbo.[Movimientos BNA] m
        LEFT JOIN dbo.CuentasBancarias cb ON cb.IdCuentaBancaria = m.IdCuentaBancaria
        WHERE m.[Fecha / Hora Mov#] BETWEEN ? AND ?
        """,
        (desde, hasta),
    )
    movimientos = [
        {
            "fecha": f["fecha"],
            "banco": "BNA",
            "origenMovimiento": "bna",
            "idMovimientoOrigen": f["idMovimiento"],
            "numeroCuentaBancaria": f["numeroCuentaBancaria"],
            "importe": float(f["importe"]),
            "concepto": f["concepto"],
            "idContacto": f["idContacto"],
            "contacto": f["contacto"],
            "esInterno": es_interno("BNA", f["concepto"]),
            "tipoInterno": tipo_interno("BNA", float(f["importe"]), f["concepto"]),
        }
        for f in filas_bna
    ]

    filas_galicia = fetch_all(
        """
        SELECT g.IdMovimiento AS idMovimiento, g.Fecha AS fecha, g.[Débitos] AS debitos, g.[Créditos] AS creditos,
               g.[Descripción] AS concepto, g.[Grupo de Conceptos] AS grupoConceptos,
               g.LeyendasAdicionales1 AS leyendasAdicionales1,
               g.IdContacto AS idContacto, COALESCE(c.[Razon Social], g.Contacto) AS contacto
        FROM dbo.[Movimientos Galicia] g
        LEFT JOIN dbo.Contactos c ON c.IdContacto = g.IdContacto
        WHERE g.Fecha BETWEEN ? AND ?
        """,
        (desde, hasta),
    )
    numero_cuenta_galicia = "0000798-8 383-4"
    for f in filas_galicia:
        importe = float(f["creditos"] or 0) - float(f["debitos"] or 0)
        movimientos.append(
            {
                "fecha": f["fecha"],
                "banco": "Galicia",
                "origenMovimiento": "galicia",
                "idMovimientoOrigen": f["idMovimiento"],
                "numeroCuentaBancaria": numero_cuenta_galicia,
                "importe": importe,
                "concepto": f["concepto"],
                "leyendas": f.get("leyendasAdicionales1") or "",
                "idContacto": f["idContacto"],
                "contacto": f["contacto"],
                "esInterno": es_interno("Galicia", f["concepto"], f["grupoConceptos"]),
                "tipoInterno": tipo_interno("Galicia", importe, f["concepto"], f["grupoConceptos"]),
            }
        )

    filas_cajas = fetch_all(
        """
        SELECT m.IdMovimiento AS idMovimiento, m.Caja AS caja, CAST(m.Fecha AS datetime) AS fecha,
               m.Importe AS importe, m.Concepto AS concepto, m.Detalle AS detalle,
               m.IdContactoRelacionado AS idContacto, c.[Razon Social] AS contacto,
               m.IdPagoEfectivo AS idPagoEfectivo, m.Tipo AS tipo
        FROM dbo.vw_MovimientosCajaEfectivoOperativos m
        LEFT JOIN dbo.Contactos c ON c.IdContacto = m.IdContactoRelacionado
        WHERE m.Anulada = 0 AND m.Caja IN ('GiamigliSA', 'CampoChica')
          AND CAST(m.Fecha AS date) BETWEEN ? AND ?
        """,
        (desde, hasta),
    )
    for f in filas_cajas:
        importe = float(f["importe"] or 0)
        con_base = (f["concepto"] or "").strip()
        det_base = (f["detalle"] or "").strip()
        concepto_completo = f"{con_base} ({det_base})" if det_base and det_base.lower() != con_base.lower() else (con_base or det_base)
        cuenta_caja = "Giamigli SA" if f["caja"] == "GiamigliSA" else "Campo Chica"
        es_int = es_interno("Caja Efectivo", concepto_completo, f["caja"])
        tipo_int = tipo_interno("Caja Efectivo", importe, concepto_completo, f["caja"])
        movimientos.append(
            {
                "fecha": f["fecha"],
                "banco": "Caja Efectivo",
                "origenMovimiento": "efectivo" if f["idPagoEfectivo"] is not None else "caja-efectivo",
                "idMovimientoOrigen": f["idPagoEfectivo"] if f["idPagoEfectivo"] is not None else f["idMovimiento"],
                "numeroCuentaBancaria": cuenta_caja,
                "importe": importe,
                "concepto": concepto_completo,
                "idContacto": f["idContacto"],
                "contacto": f["contacto"],
                "esInterno": es_int,
                "tipoInterno": tipo_int,
            }
        )

    return movimientos


def _clave_periodo(fecha: datetime, granularidad: str) -> str:
    if granularidad == "semanal":
        iso = fecha.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularidad == "trimestral":
        return f"{fecha.year:04d}-T{(fecha.month - 1) // 3 + 1}"
    if granularidad == "anual":
        return f"{fecha.year:04d}"
    return f"{fecha.year:04d}-{fecha.month:02d}"


def agregar_por_periodo(movimientos: list[dict], granularidad: str) -> list[dict]:
    """Agrupa `movimientos` (de `get_movimientos_normalizados`) por mes o
    semana, separando el neto operativo de los movimientos internos
    (FR-001/FR-002) y contando lo sin clasificar (FR-009)."""
    periodos: dict[str, dict] = {}

    for m in movimientos:
        clave = _clave_periodo(m["fecha"], granularidad)
        periodo = periodos.setdefault(
            clave,
            {
                "periodo": clave,
                "porCuenta": {},
                "totalIngresos": 0.0,
                "totalEgresos": 0.0,
                "internosIngresos": 0.0,
                "internosEgresos": 0.0,
                "sinClasificarCantidad": 0,
                "sinClasificarImporte": 0.0,
            },
        )

        cuenta_key = (m["banco"], m["numeroCuentaBancaria"])
        cuenta = periodo["porCuenta"].setdefault(
            cuenta_key, {"banco": m["banco"], "numeroCuenta": m["numeroCuentaBancaria"], "ingresos": 0.0, "egresos": 0.0}
        )

        importe = m["importe"]
        if m["esInterno"]:
            if importe >= 0:
                periodo["internosIngresos"] += importe
            else:
                periodo["internosEgresos"] += importe
        else:
            if importe >= 0:
                periodo["totalIngresos"] += importe
                cuenta["ingresos"] += importe
            else:
                periodo["totalEgresos"] += importe
                cuenta["egresos"] += importe

        if not m["esInterno"] and m["idContacto"] is None:
            periodo["sinClasificarCantidad"] += 1
            periodo["sinClasificarImporte"] += abs(importe)

    resultado = []
    for clave in sorted(periodos.keys()):
        p = periodos[clave]
        resultado.append(
            {
                "periodo": p["periodo"],
                "porCuenta": [
                    {**c, "neto": round(c["ingresos"] + c["egresos"], 2)} for c in p["porCuenta"].values()
                ],
                "totalIngresos": round(p["totalIngresos"], 2),
                "totalEgresos": round(p["totalEgresos"], 2),
                "totalNeto": round(p["totalIngresos"] + p["totalEgresos"], 2),
                "movimientosInternos": {
                    "ingresos": round(p["internosIngresos"], 2),
                    "egresos": round(p["internosEgresos"], 2),
                    "total": round(p["internosIngresos"] + p["internosEgresos"], 2),
                },
                "sinClasificar": {
                    "cantidad": p["sinClasificarCantidad"],
                    "importeAbsoluto": round(p["sinClasificarImporte"], 2),
                },
            }
        )
    return resultado


def ultima_fecha_por_cuenta() -> list[dict]:
    """`MAX(Fecha)` por cuenta conocida (FR-004) — incluye las 3 cuentas BNA
    (también las dadas de baja) y Galicia, sin filtrar por vigencia."""
    filas_bna = fetch_all(
        """
        SELECT cb.Banco AS banco, cb.NumeroCuenta AS numeroCuenta,
               MAX(m.[Fecha / Hora Mov#]) AS fecha
        FROM dbo.CuentasBancarias cb
        LEFT JOIN dbo.[Movimientos BNA] m ON m.IdCuentaBancaria = cb.IdCuentaBancaria
        WHERE cb.Banco = 'BNA'
        GROUP BY cb.Banco, cb.NumeroCuenta
        """
    )
    fecha_galicia = fetch_all("SELECT MAX(Fecha) AS fecha FROM dbo.[Movimientos Galicia]")
    resultado = [
        {"banco": f["banco"], "numeroCuenta": f["numeroCuenta"], "fecha": f["fecha"]} for f in filas_bna
    ]
    resultado.append(
        {
            "banco": "Galicia",
            "numeroCuenta": "0000798-8 383-4",
            "fecha": fecha_galicia[0]["fecha"] if fecha_galicia else None,
        }
    )
    filas_cajas = fetch_all(
        """
        SELECT Caja AS caja, CAST(MAX(Fecha) AS datetime) AS fecha
        FROM dbo.vw_MovimientosCajaEfectivoOperativos
        WHERE Anulada = 0 AND Caja IN ('GiamigliSA', 'CampoChica')
        GROUP BY Caja
        """
    )
    fechas_caja = {f["caja"]: f["fecha"] for f in filas_cajas}
    resultado.append({"banco": "Caja Efectivo", "numeroCuenta": "Giamigli SA", "fecha": fechas_caja.get("GiamigliSA")})
    resultado.append({"banco": "Caja Efectivo", "numeroCuenta": "Campo Chica", "fecha": fechas_caja.get("CampoChica")})
    return resultado


CUENTA_NACION = "Nación"
CUENTA_GALICIA = "Galicia CC"
CUENTA_FIMA = "Galicia Fondo FIMA"
CUENTA_CAJA_GIAMIGLI = "Caja Giamigli SA"
CUENTA_CAJA_CAMPO = "Caja chica del campo"
ACLARACION_FIMA = "Saldo valorizado del Fondo FIMA Premium Clase A según extractos oficiales de Banco Galicia"
SIN_CENTRO = atribucion.CENTRO_COSTO_SIN_ASIGNAR


def _cuenta(m: dict) -> str:
    if m["banco"] == "BNA":
        return CUENTA_NACION
    if m["banco"] == "Caja Efectivo":
        return CUENTA_CAJA_CAMPO if m.get("numeroCuentaBancaria") == "Campo Chica" else CUENTA_CAJA_GIAMIGLI
    return CUENTA_GALICIA


def _dia(fecha) -> date:
    return fecha.date() if isinstance(fecha, datetime) else fecha


def _clasificar_concepto_o_contacto(m: dict) -> tuple[str, str | None] | None:
    """Clasificación conceptual directa para que ningún movimiento quede pendiente ni mal imputado."""
    con = (m.get("concepto") or "").upper()
    contacto = (m.get("contacto") or "").upper()
    leyendas = (m.get("leyendas") or "").upper()
    texto_total = f"{con} {contacto} {leyendas}"
    imp = m.get("importe") or 0.0
    id_con = m.get("idContacto")

    # 1. Ley 25413 / 25314 (Impuestos bancarios)
    if atribucion.es_ley_25413(con):
        return atribucion.RUBRO_LEY_25413, atribucion.CENTRO_COSTO_LEY_25413

    # 2. Retenciones y Percepciones IIBB / ARBA Bancario
    if any(k in con for k in ["GRAVAMEN IB", "RETEN. IB", "PERCEP. IB", "RECAUDACION BANCARIA", "RECAUD. BANCARIA", "SIRCREB", "IMP. ING. BRUTOS"]) or (
        ("ARBA" in con or "ING. BRUTOS" in con or "IIBB" in con) and any(k in con for k in ["RET", "PERCEP", "GRAV", "RECAUD"])
    ):
        return atribucion.RUBRO_ARBA_RECAUDACION, atribucion.CENTRO_COSTO_LEY_25413
    if id_con == 12 and imp > 0:
        # Reintegro o devolución de saldo a favor de IIBB
        return atribucion.RUBRO_ARBA_RECAUDACION, None

    # 3. Tasas municipales y provinciales (Egresos)
    if id_con == 72 or any(k in texto_total for k in ["MUNICIPALIDAD DE BOLIVAR", "TASA VIAL", "MINISTERIO DE TRABAJO", "TASAS NO IMP"]):
        if imp < 0:
            return "Tasas municipales y provinciales", atribucion.CENTRO_COSTO_IMPUESTOS
    if ("BOLIVAR" in con or "BOLIVAR" in leyendas) and "GIAMIGLI" not in texto_total:
        if imp < 0:
            return "Tasas municipales y provinciales", atribucion.CENTRO_COSTO_IMPUESTOS

    # 4. Impuestos ARBA boletas (Inmobiliario / Automotor / Sellos)
    if id_con == 12 or any(k in texto_total for k in ["ARBA INMOB", "ARBA AUTOM", "INMOBIL.PCIA.BS.AS.", "INMOB.COMPL"]):
        if imp < 0:
            return "Impuestos ARBA", atribucion.CENTRO_COSTO_IMPUESTOS

    # 5. Impuestos nacionales (AFIP / VEP / SENASA)
    if "AFIP" in con or "VEP" in con or "AFIP" in contacto or id_con == 119:
        if imp > 0:
            return "Venta Granos", None
        return "Impuestos AFIP", atribucion.CENTRO_COSTO_IMPUESTOS
    if "SENASA" in texto_total:
        return "Tasas municipales y provinciales", atribucion.CENTRO_COSTO_IMPUESTOS

    # 6. Gastos y comisiones bancarias de cuenta (Centro de costos: Adm. General)
    if any(k in con for k in ["COMISION", "COM.", "MANTENIMIENTO", "PAQUETES", "SERVICIO DE CUENTA", "GESTION TRANSF"]):
        return "Gastos bancarios", "Adm. General"
    if any(k in con for k in ["I.V.A.", "IVA", "PERCEP. IVA", "SELLOS", "INTERESES SOBRE SALDOS", "RETEN. I.V.A"]):
        return "Gastos bancarios", atribucion.CENTRO_COSTO_LEY_25413

    # 7. Tarjetas corporativas y de crédito agropecuario
    if 966650 < abs(imp) < 966660:
        return "Compensacion bancaria por error (AgroNacion)", ("Adm. General" if imp < 0 else None)
    if "AGRONACION" in texto_total or "AGRONAC." in con:
        return "Tarjeta AgroNacion", "Adm. General"
    if "VISA" in texto_total:
        return "Tarjeta Visa Galicia", "Adm. General"
    if "GALICIA RURAL" in texto_total:
        return "Tarjeta Galicia Rural", "Adm. General"
    if any(k in con for k in ["TCORP", "TARJETA", "MASTER"]):
        return "Tarjeta Corporativa BNA", "Adm. General"

    # 8. Seguros
    if any(k in texto_total for k in ["ALLIANZ", "GARANTIZAR", "SEGURO", "SANCOR", "GALICIA SEGUROS", "SEGUROS GALICIA"]) or id_con in [171, 515, 575]:
        if imp > 0:
            return "Seguros Agricolas", None
        return "Seguros Generales", "Adm. General"

    # 9. Financiamiento / Préstamos
    if "PRESTAMO" in con or "PAGO PRESTAMO" in con:
        return "Financiamiento", "Adm. General"

    # 10. Socios (Cuentas de socios / Retiros / Aportes)
    if any(s in texto_total for s in ["SERGIO GIAMBERARDINI", "ALBINA IGLINA", "VIRGINIA", "VIRGIN", "LUCY", "APORTE EFECTIVO", "RETIRO EFECTIVO"]) or id_con in [375, 390, 564]:
        return atribucion.RUBRO_CUENTA_SOCIOS, (atribucion.CENTRO_COSTO_SOCIOS if imp < 0 else None)

    # 11. Cargas sociales (UATRE)
    if "UATRE" in texto_total or id_con == 315 or "32200018050000545700" in con or "32200018050000545700" in leyendas:
        return "Cargas sociales (UATRE)", atribucion.CENTRO_COSTO_PERSONAL

    # 12. Sueldos y contratistas rurales frecuentes
    if any(k in texto_total for k in ["HABERES", "SUELDO", "MARCELO SIERRA", "SIERRA MARCELO"]) or id_con in [123, 374]:
        return atribucion.RUBRO_SUELDOS, atribucion.CENTRO_COSTO_PERSONAL
    if id_con == 376 or "MORI" in texto_total:
        return "Servicios y labores contratadas", "Agricultura"
    if any(k in texto_total for k in ["MENDOZA", "CALDERON", "YANQUELEN", "ZURRA", "GOROSITO"]):
        return "Servicios y labores contratadas", "Agricultura"
    if id_con == 210 or "CRIADO" in texto_total:
        return "Honorarios Profesionales", "Adm. General"
    if "PARDO" in texto_total or "PRESTISIMONE" in texto_total:
        return "Honorarios Profesionales", "Adm. General"

    # 13. Electricidad y servicios públicos
    if id_con == 23 or any(k in texto_total for k in ["COOPERATIVA ELECTRICA", "COOP BOLIVAR", "COOP. BOLIVAR", "ELECTRICIDAD"]):
        return "Electricidad", "Adm. General"
    if "MOVISTAR" in texto_total or "TELEFONO" in texto_total:
        return "Telefono", "Adm. General"

    # 14. Clientes y Granos (Cargill, etc.)
    if "CARGILL" in texto_total or id_con == 258 or "30506792165" in con:
        if imp < 0:
            # Los egresos de insumos no se fuerzan genéricamente a Agricultura; se atribuyen según sus comprobantes
            return None
        f = _dia(m["fecha"])
        if f < date(2025, 7, 20):
            return "Venta Maiz", None
        elif f <= date(2026, 2, 28):
            return "Venta Soja", None
        elif f <= date(2026, 4, 30):
            return "Venta Girasol", None
        elif f <= date(2026, 5, 25):
            return "Venta Maiz", None
        else:
            return "Venta Soja", None

    # 15. Alquileres / Arrendamientos (Fideicomiso La Esperanza, etc.)
    if id_con == 562 or "ESPERANZA" in texto_total:
        if imp > 0:
            return "Arrendamientos", None
        return "Gastos de Administracion", "Adm. General"

    # 16. Cheques y echeqs
    if "ECHEQ" in con or "G. DE ECHEQ" in con:
        if imp > 0:
            if id_con == 562:
                return "Arrendamientos", None
            return "Cobranza cheques de terceros", None
        return "Gastos de Administracion", "Adm. General"

    # 17. Hacienda
    if "CAMPOS Y MONTES" in texto_total or "BERMEJO" in texto_total or id_con == 432:
        return "Venta Terneros", None
    if "VENTA VACA" in con or "DELASERNA" in con or "DE LA SERNA" in con:
        return "Venta Vacas", None
    if "COMISION VENTA" in con:
        return "Gastos Comercializacion", "Ganaderia"
    if "VACUNACION" in con or "DESTETE" in con or id_con == 379:
        return "Aranceles Vacunacion", "Ganaderia"
    if "YEGUA" in con:
        return "Compra Hacienda", "Ganaderia"

    # 18. Insumos y labores varias
    if "BAYA CASAL" in texto_total:
        return None
    if "LAVALLE" in texto_total:
        return "Mantenimiento Instalaciones", "Adm. General"

    # 19. Conceptos operativos de Cajas en Efectivo
    if "GARRAFA" in con or "EXTRAGAS" in contacto or id_con in [37, 560]:
        return "Gas", "Adm. General"
    if any(k in con for k in ["MOTOSIERRA", "MADERA", "CEMENTO", "PALOMINO", "LEMOS", "ESCOMBRO", "PRECINTOS", "ETHERNET", "J&H"]) or id_con in [80, 343, 573, 3655]:
        return "Mantenimiento Instalaciones", "Adm. General"
    if any(k in con for k in ["GATO", "ASADO", "POLLO", "MILANESA", "PAN RALLADO", "VINAGRE", "SUPERMERCADO", "PROPINA", "VIATICOS", "CAMBIO"]) or id_con == 249:
        return "Viaticos", "Adm. General"
    if any(k in con for k in ["NAFTA", "EESS", "COMBUSTIBLE", "GASOIL"]):
        return "Combustible", "Adm. General"

    # 20. Devoluciones / Anulaciones
    if "ANULACION DE TRANSFERENCIA" in con:
        return "Servicios y labores contratadas", "Ganaderia"

    return None


def _atribucion_fallback(m: dict, indice_ingresos) -> tuple[str, str | None]:
    """Regla con fallback completo para que ningún movimiento quede sin imputación."""
    directo = _clasificar_concepto_o_contacto(m)
    if directo:
        return directo

    fecha = _dia(m["fecha"])
    importe_abs = round(abs(m["importe"]), 2)
    if m["importe"] < 0:
        atrib = atribucion.atribuir_egreso(m["idContacto"], fecha, importe_abs)
    else:
        atrib = atribucion.atribuir_ingreso(indice_ingresos, m["idContacto"], fecha, importe_abs)

    if atrib["rubro"] != atribucion.SIN_RUBRO:
        return atrib["rubro"], atrib["centroCosto"]

    # Si aún no tiene rubro, clasificar por naturaleza de ingreso o egreso
    if m["importe"] > 0:
        return "Otros ingresos operativos", None
    return "Gastos generales varios", "Adm. General"


@lru_cache(maxsize=1)
def _sisa_reintegros_map() -> dict[tuple[str, int], list[dict]]:
    """Mapeo automatico de acreditaciones AFIP por reintegro sistemico de retenciones IVA (SISA)
    a sus correspondientes liquidaciones de Venta Granos con grano y campania."""
    from itertools import combinations
    rows = fetch_all("""
        SELECT riva.IdRetencion, riva.[Importe Retenido], vg.IdVenta, vg.Fecha, g.Grano, vg.Campaña
        FROM dbo.[Retenciones IVA Granos] riva
        JOIN dbo.[Venta Granos] vg ON vg.IdVenta = riva.IdLiquidacion
        JOIN dbo.Granos g ON g.IdGrano = vg.IdProducto
        ORDER BY riva.IdRetencion DESC
    """)
    creditos = fetch_all("""
        SELECT Fecha, [Créditos], IdMovimiento
        FROM dbo.[Movimientos Galicia]
        WHERE (IdContacto = 119 OR Contacto LIKE '%AFIP%' OR [Descripción] LIKE '%AFIP%' OR LeyendasAdicionales1 LIKE '%AFIP%') AND [Créditos] > 0
        ORDER BY Fecha DESC
    """)
    sisa_partes: dict[tuple[str, int], list[dict]] = {}
    for c in creditos:
        c_imp = round(float(c["Créditos"]), 2)
        cands = [r for r in rows if r["Fecha"] <= c["Fecha"] and (c["Fecha"] - r["Fecha"]).days <= 180]
        for r_len in range(1, min(8, len(cands) + 1)):
            found = False
            for combo in combinations(cands, r_len):
                if round(sum(x["Importe Retenido"] for x in combo), 2) == c_imp:
                    partes = []
                    for item in combo:
                        grano_nombre = item["Grano"]
                        if "Girasol" in grano_nombre:
                            rubro = "Venta Girasol"
                        elif "Maiz" in grano_nombre or "Maíz" in grano_nombre:
                            rubro = "Venta Maiz"
                        elif "Soja" in grano_nombre:
                            rubro = "Venta Soja"
                        elif "Trigo" in grano_nombre:
                            rubro = "Venta Trigo"
                        else:
                            rubro = f"Venta {grano_nombre}"
                        partes.append({
                            "rubro": rubro,
                            "centroCosto": None,
                            "importe": round(float(item["Importe Retenido"]), 2),
                            "documentoAplicado": {
                                "tipo": "VentaGranos",
                                "id": item["IdVenta"],
                                "campania": item["Campaña"],
                                "grano": item["Grano"],
                                "via": "sisa_reintegro",
                            },
                        })
                    sisa_partes[("galicia", c["IdMovimiento"])] = partes
                    found = True
                    break
            if found:
                break
    return sisa_partes


def _partes_desde_compras_proveedor(id_contacto: int, fecha: date, importe_abs: float) -> list[dict] | None:
    """Distribuye proporcionalmente un egreso a un proveedor de insumos/servicios según
    los rubros y centros de costos de sus facturas/notas de débito reales cercanas a la fecha (≤ 7 días),
    respetando si los insumos corresponden a Agricultura, Ganadería o Adm. General."""
    if not id_contacto or not fecha:
        return None
    filas = fetch_all(
        """
        SELECT c.IdDeuda, c.Fecha,
               ABS(DATEDIFF(day, c.Fecha, ?)) AS diff_dias
        FROM dbo.Compras c
        WHERE c.IdContacto = ? AND c.Fecha BETWEEN DATEADD(day, -7, ?) AND DATEADD(day, 7, ?)
        ORDER BY diff_dias ASC
        """,
        (fecha, id_contacto, fecha, fecha),
    )
    if not filas:
        return None
    min_diff = filas[0]["diff_dias"]
    compras_cercanas = [f["IdDeuda"] for f in filas if f["diff_dias"] <= min_diff + 2]
    grupos: dict[tuple, float] = defaultdict(float)
    doc_id_por_grupo: dict[tuple, int] = {}
    for id_deuda in compras_cercanas:
        for l in atribucion._rubros_de_compra(id_deuda):
            rubro = l["rubro"] or "Insumos productivos"
            centro = l["centroCosto"] or "Adm. General"
            peso = max(float(l.get("peso") or 0), 0)
            grupos[(rubro, centro)] += peso
            doc_id_por_grupo[(rubro, centro)] = id_deuda
    if not grupos:
        return None
    total_peso = sum(grupos.values())
    if total_peso <= 0:
        return None

    partes = []
    for (rubro, centro), peso in grupos.items():
        share = peso / total_peso
        partes.append({
            "rubro": rubro,
            "centroCosto": centro,
            "importe": round(importe_abs * share, 2),
            "documentoAplicado": {
                "tipo": "CompraDeuda",
                "id": doc_id_por_grupo[(rubro, centro)],
                "via": "facturas_proveedor",
            },
        })
    dif = round(importe_abs - sum(p["importe"] for p in partes), 2)
    if dif != 0 and partes:
        mayor = max(partes, key=lambda p: p["importe"])
        mayor["importe"] = round(mayor["importe"] + dif, 2)
    return partes


def atribuir_movimientos(movimientos: list[dict]) -> list[dict]:
    """Agrega `partes` a cada movimiento (030): una o más `{seccion, rubro,
    centroCosto, importeArs, documentoAplicado}` cuya suma es el importe del
    movimiento. Los internos van a su fila de "Movimientos entre cuentas
    propias"; el resto se reparte por las aplicaciones (019) o, sin ellas,
    con la regla de 018 v2. `rubro`/`centroCosto` quedan con la parte mayor,
    por compatibilidad con los consumidores de 018."""
    emparejar_traspasos(movimientos)
    reales = [m for m in movimientos if not m["esInterno"]]
    indice_ingresos = {}
    aplicaciones = {}
    sisa_map = _sisa_reintegros_map()
    if reales:
        fechas = [_dia(m["fecha"]) for m in reales]
        indice_ingresos = atribucion.construir_indice_ingresos(min(fechas), max(fechas))
        # 031: todas las vías de vinculación, con las cadenas de tarjeta y
        # cheque, no solo AplicacionesPago.
        from src.features.vinculos import cadenas, fuente

        aplicaciones = cadenas.documentos_de_movimiento(fuente.cargar()["vinculos"])
    memo_compras: dict = {}

    for m in movimientos:
        signo = 1 if m["importe"] >= 0 else -1
        if m["esInterno"]:
            partes = [{"seccion": "internos", "rubro": m.get("tipoInterno") or "Traspaso entre bancos",
                       "centroCosto": None, "importe": round(abs(m["importe"]), 2), "documentoAplicado": None}]
        else:
            fijo = atribucion.es_ley_25413(m.get("concepto")) or atribucion.es_arba_recaudacion(m.get("concepto"))
            partes = None
            if not fijo:
                sisa_partes = sisa_map.get((m.get("origenMovimiento"), m.get("idMovimientoOrigen")))
                if sisa_partes:
                    partes = [dict(p) for p in sisa_partes]
                else:
                    partes = atribucion.partes_desde_aplicaciones(
                    aplicaciones.get((m.get("origenMovimiento"), m.get("idMovimientoOrigen")), []),
                    m["importe"], m["fecha"], memo_compras)
            if partes is None:
                if m["importe"] < 0 and m.get("idContacto"):
                    partes = _partes_desde_compras_proveedor(m["idContacto"], _dia(m["fecha"]), round(abs(m["importe"]), 2))
                if partes is None:
                    rubro, centro = _atribucion_fallback(m, indice_ingresos)
                    partes = [{"rubro": rubro, "centroCosto": centro, "importe": round(abs(m["importe"]), 2), "documentoAplicado": None}]
            for p in partes:
                p["seccion"] = "ingresos" if signo > 0 else "egresos"
        for p in partes:
            p["importeArs"] = round(signo * p.pop("importe"), 2)
            if p["seccion"] == "egresos" and not p["centroCosto"]:
                p["centroCosto"] = SIN_CENTRO
            p.update(fecha=_dia(m["fecha"]), cuenta=_cuenta(m), concepto=m.get("concepto"), contacto=m.get("contacto"),
                     origenMovimiento=m.get("origenMovimiento"), idMovimiento=m.get("idMovimientoOrigen"),
                     importeMovimiento=round(m["importe"], 2), sinContraparte=bool(m.get("sinContraparte")),
                     esFima=m["banco"] == "Galicia" and m["esInterno"] and m.get("tipoInterno") != "Traspaso entre bancos")
        m["partes"] = partes
        mayor = max(partes, key=lambda p: abs(p["importeArs"]))
        m["rubro"], m["centroCosto"] = mayor["rubro"], mayor["centroCosto"]
    return movimientos


def partes_de_movimientos(movimientos: list[dict]) -> list[dict]:
    return [p for m in atribuir_movimientos(movimientos) for p in m["partes"]]


def convertir_partes_a_usd(partes: list[dict], serie: dict) -> None:
    """Cada parte con la cotización BNA vendedor divisa de su día (o la
    anterior ≤ 7 días). Sin cotización → `importeUsd=None` (se informa, no se inventa)."""
    for p in partes:
        c = cot.cotizacion_del_dia(serie, p["fecha"])
        if c is None:
            p.update(cotizacion=None, fechaCotizacion=None, importeUsd=None)
        else:
            p.update(cotizacion=c[0], fechaCotizacion=c[1], importeUsd=round(p["importeArs"] / c[0], 2))


def periodos_del_rango(desde: date, hasta: date, granularidad: str) -> list[str]:
    claves: list[str] = []
    d = desde
    while d <= hasta:
        k = _clave_periodo(d, granularidad)
        if not claves or claves[-1] != k:
            claves.append(k)
        d += timedelta(days=1)
    return claves


def fin_de_periodo(clave: str, desde: date, hasta: date, granularidad: str) -> date:
    fin = desde
    d = desde
    while d <= hasta:
        if _clave_periodo(d, granularidad) == clave:
            fin = d
        d += timedelta(days=1)
    return fin


def _valor(p: dict, moneda: str) -> float | None:
    return p["importeArs"] if moneda == "ARS" else p.get("importeUsd")


def clave_celda(p: dict) -> tuple:
    return (p["seccion"], p["centroCosto"] if p["seccion"] == "egresos" else None, p["rubro"])


def agregar_por_rubro(partes: list[dict], granularidad: str, periodos: list[str], moneda: str = "ARS") -> dict:
    """Ingresos por rubro, egresos por centro de costo con subtotal, internos
    en sus tres filas fijas y los netos por período (030, contracts/api.md)."""
    celdas: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sin_tc: dict[tuple, dict] = {}
    for p in partes:
        per = _clave_periodo(p["fecha"], granularidad)
        v = _valor(p, moneda)
        clave = clave_celda(p)
        if v is None:
            s = sin_tc.setdefault((per,) + clave, {"periodo": per, "seccion": p["seccion"], "centroCosto": clave[1],
                                                     "rubro": p["rubro"], "cantidad": 0, "importeArs": 0.0})
            s["cantidad"] += 1
            s["importeArs"] = round(s["importeArs"] + p["importeArs"], 2)
            continue
        celdas[clave][per] += v

    def fila(rubro, valores):
        vals = {per: round(valores.get(per, 0.0), 2) for per in periodos}
        return {"rubro": rubro, "valores": vals, "total": round(sum(vals.values()), 2)}

    def totales(filas):
        return {per: round(sum(f["valores"][per] for f in filas), 2) for per in periodos}

    ingresos = [fila(r, v) for (sec, _, r), v in sorted(celdas.items()) if sec == "ingresos"]
    grupos: dict[str, list] = defaultdict(list)
    for (sec, centro, r), v in sorted(celdas.items()):
        if sec == "egresos":
            grupos[centro].append(fila(r, v))
    centros = []
    for centro, filas in sorted(grupos.items()):
        sub = totales(filas)
        centros.append({"centroCosto": centro, "rubros": filas, "subtotalPorPeriodo": sub, "subtotal": round(sum(sub.values()), 2)})
    internos = [fila(t, celdas.get(("internos", None, t), {})) for t in TIPOS_INTERNOS]

    tot_ing, tot_int = totales(ingresos), totales(internos)
    tot_egr = {per: round(sum(c["subtotalPorPeriodo"][per] for c in centros), 2) for per in periodos}
    return {
        "periodos": periodos,
        "ingresos": {"rubros": ingresos, "totalPorPeriodo": tot_ing},
        "egresos": {"centrosCosto": centros, "totalPorPeriodo": tot_egr},
        "netoOperativoPorPeriodo": {per: round(tot_ing[per] + tot_egr[per], 2) for per in periodos},
        "internos": {"rubros": internos, "totalPorPeriodo": tot_int},
        "sinTipoCambio": list(sin_tc.values()),
    }


def saldos_por_cuenta_al(fecha: date) -> dict[str, float]:
    """Saldo de cada cuenta al inicio de `fecha` (exclusive), en pesos: Nación
    (las 3 cuentas BNA), Galicia CC, el FIMA reconstruido y las Cajas en Efectivo
    (Caja Giamigli SA y Caja chica del campo)."""
    hasta = as_sql_datetime(fecha)
    aperturas = fetch_all("SELECT Banco AS banco, SUM(SaldoApertura) AS saldo FROM dbo.CuentasBancarias GROUP BY Banco")
    apertura = {a["banco"]: float(a["saldo"] or 0) for a in aperturas}
    bna = fetch_all("SELECT SUM(Importe) AS total FROM dbo.[Movimientos BNA] WHERE [Fecha / Hora Mov#] < ?", (hasta,))
    gal = fetch_all(
        "SELECT SUM(ISNULL([Créditos],0) - ISNULL([Débitos],0)) AS total, "
        "SUM(CASE WHEN Concepto LIKE '%FIMA%' OR [Descripción] LIKE '%FIMA%' THEN ISNULL([Créditos],0) - ISNULL([Débitos],0) ELSE 0 END) AS fima "
        "FROM dbo.[Movimientos Galicia] WHERE Fecha < ?",
        (hasta,),
    )
    cajas = fetch_all(
        "SELECT Caja AS caja, SUM(Importe) AS total "
        "FROM dbo.vw_MovimientosCajaEfectivoOperativos "
        "WHERE Anulada = 0 AND Caja IN ('GiamigliSA', 'CampoChica') AND CAST(Fecha AS date) < ? "
        "GROUP BY Caja",
        (hasta,),
    )
    saldo_cajas = {c["caja"]: float(c["total"] or 0) for c in cajas}
    fima_oficiales = _posiciones_fima_oficiales()
    mes_anterior = (fecha.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    if mes_anterior in fima_oficiales:
        saldo_fima = fima_oficiales[mes_anterior]
    else:
        saldo_fima = max(0.0, -float(gal[0]["fima"] or 0))
    return {
        CUENTA_NACION: round(apertura.get("BNA", 0) + float(bna[0]["total"] or 0), 2),
        CUENTA_GALICIA: round(apertura.get("Galicia", 0) + float(gal[0]["total"] or 0), 2),
        CUENTA_FIMA: round(saldo_fima, 2),
        CUENTA_CAJA_GIAMIGLI: round(saldo_cajas.get("GiamigliSA", 0.0), 2),
        CUENTA_CAJA_CAMPO: round(saldo_cajas.get("CampoChica", 0.0), 2),
    }


def saldo_inicial_al(fecha_desde: date) -> float:
    """Total de disponibilidades (Nación + Galicia CC + Cajas Efectivo, sin el FIMA reconstruido)."""
    s = saldos_por_cuenta_al(fecha_desde)
    return round(
        s[CUENTA_NACION]
        + s[CUENTA_GALICIA]
        + s.get(CUENTA_CAJA_GIAMIGLI, 0.0)
        + s.get(CUENTA_CAJA_CAMPO, 0.0),
        2,
    )


def saldos_finales(saldos_iniciales: dict[str, float], partes: list[dict], granularidad: str, periodos: list[str]) -> dict[str, dict[str, float]]:
    """Saldo en pesos de cada cuenta al cierre de cada período. Una colocación
    FIMA resta de Galicia CC y suma al FIMA (total sin cambio)."""
    netos: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for p in partes:
        per = _clave_periodo(p["fecha"], granularidad)
        netos[p["cuenta"]][per] += p["importeArs"]
        if p["esFima"]:
            netos[CUENTA_FIMA][per] -= p["importeArs"]
    resultado: dict[str, dict[str, float]] = {}
    fima_oficiales = _posiciones_fima_oficiales()
    for cuenta, inicial in saldos_iniciales.items():
        acumulado, serie = inicial, {}
        for per in periodos:
            if cuenta == CUENTA_FIMA and granularidad == "mensual" and per in fima_oficiales:
                acumulado = fima_oficiales[per]
                serie[per] = round(acumulado, 2)
            else:
                acumulado += netos[cuenta].get(per, 0.0)
                if cuenta == CUENTA_FIMA:
                    acumulado = max(0.0, acumulado)
                serie[per] = round(acumulado, 2)
        resultado[cuenta] = serie
    return resultado


def flujo_por_rubro(desde: date, hasta: date, granularidad: str, moneda: str) -> dict:
    """Cálculo completo de la pantalla (030), recalculado siempre (FR-009)."""
    movimientos = get_movimientos_normalizados(desde, hasta)
    partes = partes_de_movimientos(movimientos)
    periodos = periodos_del_rango(desde, hasta, granularidad)
    serie = None
    if moneda == "USD":
        serie = cot.cargar_serie(desde, hasta)
        convertir_partes_a_usd(partes, serie)
    agregado = agregar_por_rubro(partes, granularidad, periodos, moneda)

    iniciales = saldos_por_cuenta_al(desde)
    finales = saldos_finales(iniciales, partes, granularidad, periodos)
    saldos_sin_tc: list[str] = []

    def convertir(valor: float, fecha: date, etiqueta: str) -> float | None:
        if moneda == "ARS":
            return valor
        c = cot.cotizacion_del_dia(serie, fecha)
        if c is None:
            if etiqueta not in saldos_sin_tc:
                saldos_sin_tc.append(etiqueta)
            return None
        return round(valor / c[0], 2)

    cuentas_ini = [
        {"cuenta": c, "importe": convertir(v, desde, "inicial")}
        for c, v in iniciales.items()
    ]
    total_ini = convertir(sum(iniciales.values()), desde, "inicial")
    fin_por = {per: fin_de_periodo(per, desde, hasta, granularidad) for per in periodos}
    final_cuenta = {c: {per: convertir(v, fin_por[per], per) for per, v in serie_c.items()} for c, serie_c in finales.items()}
    final_total = {per: (round(convertir(sum(finales[c][per] for c in finales), fin_por[per], per), 2) if convertir(sum(finales[c][per] for c in finales), fin_por[per], per) is not None else None) for per in periodos}

    return {
        "moneda": moneda,
        **agregado,
        "saldoInicial": {"cuentas": cuentas_ini, "total": total_ini},
        "saldoFinalPorPeriodo": final_total,
        "saldoFinalPorCuenta": final_cuenta,
        "saldosSinTipoCambio": saldos_sin_tc,
        "traspasosSinContraparte": [
            {"fecha": p["fecha"], "cuenta": p["cuenta"], "importe": p["importeArs"], "idMovimiento": p["idMovimiento"]}
            for p in partes if p["sinContraparte"]
        ],
        "ultimaFechaCotizacion": cot.ultima_fecha_serie() if moneda == "USD" else None,
        "_partes": partes,
    }


def _obtener_detalles_documentos(documentos: list[tuple[str, int]]) -> dict[tuple[str, int], dict]:
    resultado = {}
    compras_ids = [doc_id for tipo, doc_id in documentos if tipo == "CompraDeuda"]
    if compras_ids:
        for i in range(0, len(compras_ids), 500):
            batch = compras_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT c.IdDeuda, c.[Tipo documento] as tipoComprobante, c.[Nro Documento] as nroComprobante,
                       ct.[Razon Social] as proveedor,
                       (SELECT STRING_AGG(dc.[Producto/Servicio], ', ') WITHIN GROUP (ORDER BY dc.IdDetalleCompra)
                        FROM dbo.Det_Compras dc WHERE dc.IdCompra = c.IdDeuda) as detalleConcepto
                FROM dbo.Compras c
                LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
                WHERE c.IdDeuda IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                resultado[("CompraDeuda", r["IdDeuda"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": r["detalleConcepto"],
                }

    impuestos_ids = [doc_id for tipo, doc_id in documentos if tipo == "Impuesto"]
    if impuestos_ids:
        for i in range(0, len(impuestos_ids), 500):
            batch = impuestos_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT i.IdImpuesto, ti.[Nombre Impuesto] as tipoComprobante, i.[Numero de documento] as nroComprobante,
                       c.[Razon Social] as proveedor, i.[Periodo liquidado] as detalleConcepto
                FROM dbo.Impuestos i
                LEFT JOIN dbo.Contactos c ON c.IdContacto = i.IdOrganismo
                LEFT JOIN dbo.[Tipo Impuesto] ti ON ti.IdTipoImpuesto = i.IdTipoImpuesto
                WHERE i.IdImpuesto IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                per = r["detalleConcepto"]
                resultado[("Impuesto", r["IdImpuesto"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": f"Periodo {per}" if per else None,
                }

    remun_ids = [doc_id for tipo, doc_id in documentos if tipo == "Remuneracion"]
    if remun_ids:
        for i in range(0, len(remun_ids), 500):
            batch = remun_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT r.IdSalario, 'Recibo de Sueldo' as tipoComprobante, r.Recibo as nroComprobante,
                       c.[Razon Social] as proveedor, r.[Periodo liquidado] as detalleConcepto
                FROM dbo.Remuneraciones r
                LEFT JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto
                WHERE r.IdSalario IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                per = r["detalleConcepto"]
                resultado[("Remuneracion", r["IdSalario"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": f"Periodo {per}" if per else None,
                }

    granos_ids = [doc_id for tipo, doc_id in documentos if tipo == "VentaGranos"]
    if granos_ids:
        for i in range(0, len(granos_ids), 500):
            batch = granos_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT vg.IdVenta, 'Liquidacion Granos' as tipoComprobante, vg.[Nro Documento] as nroComprobante,
                       c.[Razon Social] as proveedor, g.Grano, vg.[Campaña] as campania
                FROM dbo.[Venta Granos] vg
                LEFT JOIN dbo.Contactos c ON c.IdContacto = vg.IdConsignatario
                LEFT JOIN dbo.Granos g ON g.IdGrano = vg.IdProducto
                WHERE vg.IdVenta IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                grano = r["Grano"]
                camp = r["campania"]
                resultado[("VentaGranos", r["IdVenta"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": f"{grano} (Campaña {camp})" if camp else grano,
                }

    hacienda_ids = [doc_id for tipo, doc_id in documentos if tipo == "VentaHacienda"]
    if hacienda_ids:
        for i in range(0, len(hacienda_ids), 500):
            batch = hacienda_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT vh.IdVenta, 'Liquidacion Hacienda' as tipoComprobante, vh.[Nro documento] as nroComprobante,
                       c.[Razon Social] as proveedor
                FROM dbo.[Venta Hacienda] vh
                LEFT JOIN dbo.Contactos c ON c.IdContacto = vh.IdConsignatario
                WHERE vh.IdVenta IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                resultado[("VentaHacienda", r["IdVenta"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": "Liquidacion de hacienda",
                }

    pastaje_ids = [doc_id for tipo, doc_id in documentos if tipo == "Pastaje"]
    if pastaje_ids:
        for i in range(0, len(pastaje_ids), 500):
            batch = pastaje_ids[i:i+500]
            placeholders = ",".join("?" for _ in batch)
            rows = fetch_all(f"""
                SELECT pc.IdComprobante, 'Factura Pastaje' as tipoComprobante,
                       CONCAT(pc.Letra, ' ', FORMAT(pc.PuntoVenta, '0000'), '-', FORMAT(pc.Numero, '00000000')) as nroComprobante,
                       c.[Razon Social] as proveedor, pc.Detalle as detalleConcepto
                FROM dbo.PastajeComprobantes pc
                LEFT JOIN dbo.ContratosPastaje cp ON cp.IdContratoPastaje = pc.IdContratoPastaje
                LEFT JOIN dbo.Contactos c ON c.IdContacto = cp.IdCliente
                WHERE pc.IdComprobante IN ({placeholders})
            """, tuple(batch))
            for r in rows:
                resultado[("Pastaje", r["IdComprobante"])] = {
                    "tipoComprobante": r["tipoComprobante"],
                    "nroComprobante": r["nroComprobante"],
                    "proveedor": r["proveedor"],
                    "detalleConcepto": r["detalleConcepto"],
                }

    return resultado


def detalle_celda(desde: date, hasta: date, granularidad: str, moneda: str, periodo: str, seccion: str,
                  rubro: str, centro_costo: str | None) -> dict:
    """Partes que componen una celda; `total` es exactamente el valor de la
    celda en `flujo_por_rubro` con los mismos parámetros (FR-006)."""
    if periodo not in periodos_del_rango(desde, hasta, granularidad):
        raise ValueError("El período no corresponde al rango y la granularidad elegidos.")
    partes = partes_de_movimientos(get_movimientos_normalizados(desde, hasta))
    if moneda == "USD":
        convertir_partes_a_usd(partes, cot.cargar_serie(desde, hasta))
    clave = (seccion, centro_costo if seccion == "egresos" else None, rubro)
    items = [p for p in partes if _clave_periodo(p["fecha"], granularidad) == periodo and clave_celda(p) == clave]
    items.sort(key=lambda p: (p["fecha"], p["cuenta"], p["idMovimiento"] or 0))
    total = round(sum((_valor(p, moneda) or 0) for p in items if _valor(p, moneda) is not None), 2)

    docs = [(p["documentoAplicado"]["tipo"], p["documentoAplicado"]["id"]) for p in items if p.get("documentoAplicado") and p["documentoAplicado"].get("id")]
    detalles_doc = _obtener_detalles_documentos(docs) if docs else {}

    res_items = []
    for p in items:
        item_dict = {k: v for k, v in p.items() if k != "esFima"}
        if p.get("documentoAplicado") and p["documentoAplicado"].get("id"):
            doc_key = (p["documentoAplicado"]["tipo"], p["documentoAplicado"]["id"])
            if doc_key in detalles_doc:
                item_dict["documentoDetalle"] = detalles_doc[doc_key]
        res_items.append(item_dict)

    return {"total": total, "items": res_items}
