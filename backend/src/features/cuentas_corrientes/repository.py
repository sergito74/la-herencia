"""Parameterized, read-only SQL queries for the Cuentas corrientes module.

Column/table names come from data-model.md. No writes are issued here
(constitution principle II, FR-010).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


def search_contactos(q: str | None, tipo_contacto: str | None) -> list[dict]:
    """Search contactos by razon social and/or tipo (FR-001, FR-002).

    `DISTINCT` porque un contacto tipo "Multiple" puede tener más de una
    fila asociada en joins usados por otras vistas — acá no hay join, pero
    se mantiene por consistencia con FR-014 y para no exponer duplicados
    si la tabla base llegara a tenerlos.
    """
    where_clauses: list[str] = []
    params: list = []

    if q:
        where_clauses.append("[Razon Social] LIKE ?")
        params.append(f"%{q}%")
    if tipo_contacto:
        where_clauses.append("[Tipo Contacto] = ?")
        params.append(tipo_contacto)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f"""
        SELECT DISTINCT
            IdContacto AS idContacto,
            [Razon Social] AS razonSocial,
            [Tipo Contacto] AS tipoContacto
        FROM dbo.Contactos
        {where_sql}
        ORDER BY [Razon Social] ASC
    """
    rows = fetch_all(sql, tuple(params))
    return [
        {
            "idContacto": row["idContacto"],
            "razonSocial": row.get("razonSocial"),
            "tipoContacto": row.get("tipoContacto"),
        }
        for row in rows
    ]


def get_saldo(id_contacto: int) -> dict | None:
    """Saldo actual del contacto con la valuación bimonetaria (036, 21/10/2026).

    La vista `vw_MovimientosCuenta_Base` pone el importe en US$ de los documentos en dólares en la misma columna que los
    pesos (no los multiplica por el tipo de cambio), así que su `SaldoParcial` mezcla monedas. La valuación bimonetaria
    pasa cada documento a pesos a su tipo de cambio y aplica las reglas de dólares (es la que usan las fichas de cierre).
    """
    from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta

    c = cargar_cuenta(id_contacto)
    if not c["filas"]:
        return None
    return {"idContacto": id_contacto, "saldoParcial": round(c["saldoPesos"], 2),
            "saldoDolares": round(c["saldoDolares"], 2) if c["tieneDolares"] else None, "moneda": c["gobierna"]}


def get_saldos_todos(orden: str = "razonSocial") -> list[dict]:
    """Saldo actual de todos los contactos con al menos un movimiento (014 US2).

    Misma regla que `get_saldo` (última fila por contacto en el orden
    `Fecha, Origen, IdOrigen`), pero para todos los contactos en una sola
    consulta vía `ROW_NUMBER() OVER (PARTITION BY IdContacto ...)` en vez de
    repetir `get_saldo` contacto por contacto. Incluye contactos con saldo
    exactamente $0 (FR-004) — nunca filtra por `SaldoParcial <> 0`.
    """
    # 22/10/2026: antes tomaba la última fila de vw_MovimientosCuenta_Saldo (saldo acumulado con ventana sobre todos los
    # movimientos); con la PC sin memoria libre esa consulta llegó a tardar 7 min y trababa al resto del sistema (esperas
    # RESOURCE_SEMAPHORE). El saldo final es la suma Credito − Deuda: mismo resultado (verificado, 522 contactos), sin ventana.
    order_sql = "saldoParcial ASC" if orden == "saldo" else "razonSocial"
    sql = f"""
        SELECT IdContacto AS idContacto, MAX([Razon Social]) AS razonSocial,
               ROUND(SUM(ISNULL(Credito, 0) - ISNULL(Deuda, 0)), 2) AS saldoParcial
        FROM dbo.vw_MovimientosCuenta_Base
        GROUP BY IdContacto
        ORDER BY {order_sql}
    """
    filas = fetch_all(sql)
    # Saldo real con la valuación bimonetaria (la misma de las fichas de cierre, 036): en las cuentas con documentos en US$
    # la suma cruda de pesos de la vista deja diferencias de pesificación aunque la cuenta esté cerrada en US$ 0
    # (ASP, Don Mario, Nidera, Allianz...). Para las cuentas en pesos el valor es el mismo.
    from src.features.auditoria_cuentas.bimonetaria import cargar_cuentas

    bim = cargar_cuentas([f["idContacto"] for f in filas])
    for f in filas:
        b = bim.get(f["idContacto"])
        if b:
            f["saldoVista"] = f["saldoParcial"]
            f["saldoParcial"] = round(b["saldoPesos"], 2)
            f["saldoDolares"] = round(b["saldoDolares"], 2) if b["tieneDolares"] else None
            f["moneda"] = b["gobierna"]
    if orden == "saldo":
        filas.sort(key=lambda f: f["saldoParcial"] or 0)
    return filas


# Único punto de entrada para nombres de columna en el ORDER BY dinámico
# de abajo — nunca se interpola el `sortBy` del cliente directo en el SQL
# (aunque venga validado por Pydantic/Literal en el schema, se revalida acá
# contra este allowlist antes de usarlo en texto).
_COLUMNAS_ORDENABLES = {
    "fecha": "Fecha",
    "documento": "Documento",
    "numeroDocumento": "[Nro Documento]",
    "deuda": "Deuda",
    "credito": "Credito",
    "saldoParcial": "SaldoParcial",
}


_ORDEN_FILAS = {
    "fecha": lambda f: (f["fecha"] or date.min),
    "documento": lambda f: f["documento"] or "",
    "numeroDocumento": lambda f: f["numeroDocumento"] or "",
    "deuda": lambda f: f["deuda"] or 0,
    "credito": lambda f: f["credito"] or 0,
    "saldoParcial": lambda f: f["saldoParcial"] or 0,
}


def get_movimientos(
    id_contacto: int,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> tuple[list[dict], int]:
    """Movimientos de cuenta corriente del contacto con la valuación bimonetaria (036, 21/10/2026).

    Deuda/Crédito en pesos (los documentos en US$ a su tipo de cambio; la vista base los sumaba en dólares como si fueran
    pesos) y saldo acumulado en pesos y en dólares, en orden cronológico real. Reordenar la lista no recalcula el saldo
    (criterio de libro mayor). Mismas filas que la vista (las mismas que el formulario Access SbfrmMovCuenta).
    """
    from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta

    c = cargar_cuenta(id_contacto)
    filas = [
        {
            "fecha": f["fecha"],
            "documento": f["documento"],
            "numeroDocumento": f["numeroDocumento"],
            "deuda": round(f["deudaPesos"], 2),
            "credito": round(f["creditoPesos"], 2),
            "origenTipo": f["origenTipo"],
            "idOrigen": f["idOrigen"],
            "saldoParcial": round(f["saldoPesos"], 2),
            "saldoDolares": round(f["saldoDolares"], 2) if c["tieneDolares"] else None,
            "moneda": f["moneda"],
            "importeOriginal": (f["deudaOriginal"] or 0) - (f["creditoOriginal"] or 0) if f["moneda"] == "Dolares" else None,
            "tipoCambio": f["tipoDeCambio"] if f["moneda"] == "Dolares" else None,
        }
        for f in c["filas"]
        if (not fecha_desde or f["fecha"] >= fecha_desde) and (not fecha_hasta or f["fecha"] <= fecha_hasta)
    ]
    clave = _ORDEN_FILAS.get(sort_by or "", _ORDEN_FILAS["fecha"])
    if sort_by in _ORDEN_FILAS and sort_by != "fecha" or sort_dir == "desc":
        filas.sort(key=clave, reverse=(sort_dir == "desc"))
    offset = offset_for(page, page_size)
    return filas[offset:offset + page_size], len(filas)


def get_compra_referencia(id_compra: int) -> dict | None:
    """Referencia mínima de una compra para resolver `Origen`/`IdOrigen`."""
    sql = """
        SELECT
            cmp.IdDeuda AS idCompra,
            cmp.[Nro Documento] AS numeroDocumento,
            c.[Razon Social] AS proveedor
        FROM dbo.Compras cmp
        LEFT JOIN dbo.Contactos c ON c.IdContacto = cmp.IdContacto
        WHERE cmp.IdDeuda = ?
    """
    return fetch_one(sql, (id_compra,))


def get_bna_referencia(id_movimiento: int) -> dict | None:
    sql = """
        SELECT
            m.IdMovimientoBNA AS idMovimiento,
            m.[Fecha / Hora Mov#] AS fecha,
            m.Importe AS importe,
            cb.NumeroCuenta AS numeroCuentaBancaria
        FROM dbo.[Movimientos BNA] m
        LEFT JOIN dbo.CuentasBancarias cb ON cb.IdCuentaBancaria = m.IdCuentaBancaria
        WHERE m.IdMovimientoBNA = ?
    """
    return fetch_one(sql, (id_movimiento,))


def get_galicia_referencia(id_movimiento: int) -> dict | None:
    sql = """
        SELECT
            IdMovimiento AS idMovimiento,
            Fecha AS fecha,
            Débitos AS debitos,
            Créditos AS creditos
        FROM dbo.[Movimientos Galicia]
        WHERE IdMovimiento = ?
    """
    row = fetch_one(sql, (id_movimiento,))
    if row is None:
        return None
    importe = row.get("debitos") or row.get("creditos")
    return {"idMovimiento": row["idMovimiento"], "fecha": row.get("fecha"), "importe": importe}


def get_efectivo_referencia(id_pago: int) -> dict | None:
    sql = """
        SELECT
            IdPagoEfectivo AS idMovimiento,
            Fecha AS fecha,
            [Importe imputado] AS importe
        FROM dbo.[Pagos efectivo]
        WHERE IdPagoEfectivo = ?
    """
    return fetch_one(sql, (id_pago,))


def get_valores_recibidos_referencia(id_valor: int) -> dict | None:
    sql = """
        SELECT
            IdValor AS idMovimiento,
            [Fecha Emision] AS fecha,
            Importe AS importe
        FROM dbo.[Valores Recibidos]
        WHERE IdValor = ?
    """
    return fetch_one(sql, (id_valor,))


def get_conciliacion_tesoreria_referencia(id_conciliacion: int) -> dict | None:
    """023-conciliacion-tesoreria: resuelve el `IdOrigen` (= IdConciliacion)
    al medio/movimiento de Tesorería original, para que el link "Origen"
    de cuentas corrientes lleve al mismo listado que cualquier otro
    movimiento de Tesorería (mismo criterio que get_bna_referencia/etc.)."""
    # `Fecha` en ConciliacionesTesoreria es el timestamp de alta (insert-only,
    # sin columna explícita seteada — la DB la completa con GETDATE()), no la
    # fecha del movimiento. Trae hora (ej. '2026-09-29 18:23:27.116') y rompe
    # la validación estricta de `Origen.fecha: date` en Pydantic (exige medianoche
    # exacta) — bug real encontrado 2026-09-29: cualquier contacto con un
    # movimiento origen "Conciliación Tesorería" resultante de la conciliación
    # masiva de hoy tira 500 en /movimientos. Se trunca acá a solo fecha.
    sql = """
        SELECT Medio AS medio, IdMovimiento AS idMovimiento, CAST(Fecha AS DATE) AS fecha, Importe AS importe
        FROM dbo.ConciliacionesTesoreria
        WHERE IdConciliacion = ?
    """
    return fetch_one(sql, (id_conciliacion,))


# --- 034-cuenta-corriente-tarjetas: referencias de los orígenes nuevos de la vista ---

def get_tarjeta_consumo_referencia(id_linea_consumo: int) -> dict | None:
    return fetch_one(
        "SELECT l.IdLineaConsumo AS idLineaConsumo, l.IdResumen AS idResumen, r.ResumenCodigo AS numeroDocumento "
        "FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen "
        "WHERE l.IdLineaConsumo = ?",
        (id_linea_consumo,),
    )


def get_tarjeta_resumen_referencia(id_resumen: int) -> dict | None:
    return fetch_one(
        "SELECT IdResumen AS idResumen, ResumenCodigo AS numeroDocumento "
        "FROM dbo.Tarjetas_Resumenes WHERE IdResumen = ?",
        (id_resumen,),
    )


def get_tarjeta_pago_referencia(id_pago: int) -> dict | None:
    return fetch_one(
        "SELECT p.IdResumen AS idResumen, r.ResumenCodigo AS numeroDocumento, p.Importe AS importe "
        "FROM dbo.Tarjetas_Resumenes_Pagos p JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = p.IdResumen "
        "WHERE p.IdPago = ?",
        (id_pago,),
    )


def get_tarjeta_cruce_referencia(id_cruce: int) -> dict | None:
    return fetch_one(
        "SELECT IdCruce AS idCruce, IdTarjeta AS idTarjeta, Importe AS importe FROM dbo.TarjetasCruces WHERE IdCruce = ?",
        (id_cruce,),
    )


def get_mercado_libre_referencia(id_movimiento: int) -> dict | None:
    return fetch_one(
        "SELECT IdMovimiento AS idMovimiento, Fecha AS fecha, Importe AS importe "
        "FROM dbo.[Movimientos Mercado Libre] WHERE IdMovimiento = ?",
        (id_movimiento,),
    )
