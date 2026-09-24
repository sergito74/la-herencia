"""Lectura normalizada y agregación de movimientos bancarios reales (018).

Solo lectura (`fetch_all`) sobre `Movimientos BNA`/`Movimientos Galicia` —
nunca escribe (constitución II, FR-006). No introduce una fuente de verdad
paralela: los mismos totales que muestra Tesorería para un banco/rango deben
coincidir exactamente con lo que agrega este módulo (SC-002).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from src.db.connection import fetch_all
from src.db.params import as_sql_datetime
from src.features.flujo_caja.clasificacion import es_interno

FECHA_PRIMER_SALDO_CONOCIDO = date(2010, 8, 31)


def get_movimientos_normalizados(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    """Movimientos de BNA (3 cuentas ya distinguidas) + Galicia en un mismo
    formato: `{fecha, banco, numeroCuentaBancaria, importe, concepto,
    idContacto, contacto, esInterno}`."""
    desde, hasta = as_sql_datetime(fecha_desde), as_sql_datetime(fecha_hasta)

    filas_bna = fetch_all(
        """
        SELECT m.[Fecha / Hora Mov#] AS fecha, m.Importe AS importe, m.Concepto AS concepto,
               m.IdContacto AS idContacto, m.Contacto AS contacto,
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
            "numeroCuentaBancaria": f["numeroCuentaBancaria"],
            "importe": float(f["importe"]),
            "concepto": f["concepto"],
            "idContacto": f["idContacto"],
            "contacto": f["contacto"],
            "esInterno": es_interno("BNA", f["concepto"]),
        }
        for f in filas_bna
    ]

    filas_galicia = fetch_all(
        """
        SELECT Fecha AS fecha, [Débitos] AS debitos, [Créditos] AS creditos,
               [Descripción] AS concepto, [Grupo de Conceptos] AS grupoConceptos,
               IdContacto AS idContacto, Contacto AS contacto
        FROM dbo.[Movimientos Galicia]
        WHERE Fecha BETWEEN ? AND ?
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
                "numeroCuentaBancaria": numero_cuenta_galicia,
                "importe": importe,
                "concepto": f["concepto"],
                "idContacto": f["idContacto"],
                "contacto": f["contacto"],
                "esInterno": es_interno("Galicia", None, f["grupoConceptos"]),
            }
        )

    return movimientos


def _clave_periodo(fecha: datetime, granularidad: str) -> str:
    if granularidad == "semanal":
        iso = fecha.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
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
    return resultado
