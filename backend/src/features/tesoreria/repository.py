"""Parameterized, read-only SQL queries for the Tesoreria module.

Each medio keeps its own table/columns (FR-002) — no unified query. Column
names come from data-model.md, confirmed against INFORMATION_SCHEMA on
2026-09-16. No writes are issued here (constitution principle II, FR-010).
"""

from __future__ import annotations

from datetime import date
from typing import NamedTuple

from src.db.connection import fetch_all, fetch_one
from src.db.pagination import offset_for
from src.db.params import as_sql_datetime


class MedioConfig(NamedTuple):
    table: str
    id_column: str
    id_field: str
    date_column: str
    select_columns: dict[str, str]  # API field -> SQL column/expression
    extra_join: str | None = None  # optional JOIN appended after `table` (013)


# Conducto de Mercado Pago (034, FR-017): ver `esConducto` en `MEDIOS_CONFIG["mercado-libre"]`.
CONDUCTO_ML_SQL = (
    "CASE WHEN [Movimientos Mercado Libre].IdOperacion IS NOT NULL AND EXISTS ("
    "SELECT 1 FROM dbo.[Movimientos Mercado Libre] _p "
    "WHERE _p.IdOperacion = [Movimientos Mercado Libre].IdOperacion "
    "AND _p.IdMovimiento <> [Movimientos Mercado Libre].IdMovimiento "
    "AND CAST(_p.Fecha AS date) = CAST([Movimientos Mercado Libre].Fecha AS date) "
    "AND ABS(_p.Importe + [Movimientos Mercado Libre].Importe) < 0.01 "
    "AND (_p.Descripcion LIKE 'Ingreso de dinero%' OR [Movimientos Mercado Libre].Descripcion LIKE 'Ingreso de dinero%')"
    ") THEN 1 ELSE 0 END"
)


MEDIOS_CONFIG: dict[str, MedioConfig] = {
    "bna": MedioConfig(
        table="dbo.[Movimientos BNA]",
        id_column="IdMovimientoBNA",
        id_field="idMovimientoBNA",
        date_column="[Fecha / Hora Mov#]",
        select_columns={
            "idMovimientoBNA": "IdMovimientoBNA",
            "fechaHora": "[Fecha / Hora Mov#]",
            "concepto": "Concepto",
            "importe": "Importe",
            "idContacto": "IdContacto",
            "contacto": "COALESCE((SELECT _cx.[Razon Social] FROM dbo.Contactos _cx WHERE _cx.IdContacto = NULLIF([Movimientos BNA].IdContacto, 0)), [Movimientos BNA].Contacto)",
            "idCarga": "_crm_bna.IdCarga",
            # El BNA cambio de numero de cuenta 3 veces con el tiempo; hasta
            # 2026-09 todo se cargaba como si fuera una sola cuenta
            # (`separar_cuentas_bna.py` reconstruyo IdCuentaBancaria para el
            # historico). Se muestra el numero real y la certeza de la
            # asignacion en vez de ocultar que son cuentas distintas.
            "numeroCuentaBancaria": "_cb_bna.NumeroCuenta",
            "certezaCuenta": "[Movimientos BNA].CertezaCuenta",
            # Saldo corrido por cuenta bancaria (pedido explícito del
            # usuario, 2026-09-28) — la tabla no trae un saldo propio, así
            # que se calcula como acumulado de Importe ordenado por fecha
            # dentro de cada IdCuentaBancaria (mismo criterio de
            # separación de cuentas que `numeroCuentaBancaria`).
            "saldo": (
                "SUM([Movimientos BNA].Importe) OVER ("
                "PARTITION BY [Movimientos BNA].IdCuentaBancaria "
                "ORDER BY [Movimientos BNA].[Fecha / Hora Mov#], [Movimientos BNA].IdMovimientoBNA "
                "ROWS UNBOUNDED PRECEDING)"
            ),
        },
        extra_join=(
            "LEFT JOIN dbo.CargasResumenBancario_Movimientos _crm_bna "
            "ON _crm_bna.Banco = 'BNA' AND _crm_bna.IdMovimiento = [Movimientos BNA].IdMovimientoBNA "
            "LEFT JOIN dbo.CuentasBancarias _cb_bna "
            "ON _cb_bna.IdCuentaBancaria = [Movimientos BNA].IdCuentaBancaria"
        ),
    ),
    "galicia": MedioConfig(
        table="dbo.[Movimientos Galicia]",
        # Calificado con la tabla: sin esto, el JOIN a
        # CargasResumenBancario_Movimientos (que también tiene una columna
        # IdMovimiento) vuelve "IdMovimiento" ambiguo en ORDER BY (encontrado
        # corriendo T025 contra `WC` real, 2026-09-22).
        id_column="[Movimientos Galicia].IdMovimiento",
        id_field="idMovimiento",
        date_column="Fecha",
        select_columns={
            "idMovimiento": "[Movimientos Galicia].IdMovimiento",
            "fecha": "Fecha",
            "descripcion": "[Descripción]",
            "debitos": "[Débitos]",
            "creditos": "[Créditos]",
            "saldo": "Saldo",
            "idContacto": "IdContacto",
            "contacto": "COALESCE((SELECT _cx.[Razon Social] FROM dbo.Contactos _cx WHERE _cx.IdContacto = NULLIF([Movimientos Galicia].IdContacto, 0)), [Movimientos Galicia].Contacto)",
            "idCarga": "_crm_gal.IdCarga",
        },
        extra_join=(
            "LEFT JOIN dbo.CargasResumenBancario_Movimientos _crm_gal "
            "ON _crm_gal.Banco = 'Galicia' AND _crm_gal.IdMovimiento = [Movimientos Galicia].IdMovimiento"
        ),
    ),
    "mercado-libre": MedioConfig(
        table="dbo.[Movimientos Mercado Libre]",
        id_column="[Movimientos Mercado Libre].IdMovimiento",
        id_field="idMovimiento",
        date_column="Fecha",
        select_columns={
            "idMovimiento": "[Movimientos Mercado Libre].IdMovimiento",
            "fecha": "Fecha",
            "descripcion": "Descripcion",
            "idOperacion": "IdOperacion",
            "importe": "Importe",
            "saldo": "Saldo",
            "idContacto": "[Movimientos Mercado Libre].IdContacto",
            "contacto": "_c_ml.[Razon Social]",
            # 034: conducto = misma operación, mismo día, importe opuesto y uno de los dos es "Ingreso de dinero"
            # (la billetera solo hace de puente entre un banco propio y el pago).
            "esConducto": CONDUCTO_ML_SQL,
            "idOperacionPar": f"CASE WHEN {CONDUCTO_ML_SQL} = 1 THEN [Movimientos Mercado Libre].IdOperacion END",
        },
        extra_join=(
            "LEFT JOIN dbo.Contactos _c_ml "
            "ON _c_ml.IdContacto = [Movimientos Mercado Libre].IdContacto"
        ),
    ),
    "efectivo": MedioConfig(
        table="dbo.vw_PagosEfectivoVigentes",
        id_column="IdPagoEfectivo",
        id_field="idPagoEfectivo",
        date_column="Fecha",
        select_columns={
            "idPagoEfectivo": "IdPagoEfectivo",
            "idContacto": "IdContacto",
            "fecha": "Fecha",
            "cuenta": "Cuenta",
            "caja": "Caja",
            "numeroDocumento": "[Numero documento]",
            "importeImputado": "[Importe imputado]",
            "idOperacion": "IdOperacion",
        },
    ),
    "valores-propios": MedioConfig(
        table="dbo.[Valores propios]",
        id_column="IdValor",
        id_field="idValor",
        date_column="[Fecha emision]",
        select_columns={
            "idValor": "IdValor",
            "numeroCheque": "[Numero cheque]",
            "fechaEmision": "[Fecha emision]",
            "fechaVencimiento": "[Fecha vencimiento]",
            "importe": "Importe",
            "cobrado": "Cobrado",
            "fechaCobro": "[Fecha Cobro]",
            "numeroCuenta": "[Numero Cuenta]",
            "comentarios": "Comentarios",
        },
    ),
    "valores-recibidos": MedioConfig(
        table="dbo.[Valores Recibidos]",
        id_column="IdValor",
        id_field="idValor",
        date_column="[Fecha Emision]",
        select_columns={
            "idValor": "IdValor",
            "numeroValor": "[Numero Valor]",
            "banco": "Banco",
            "fechaEmision": "[Fecha Emision]",
            "fechaVencimiento": "[Fecha Vencimiento]",
            "fechaCobro": "[Fecha Cobro]",
            "idEmisor": "IdEmisor",
            "idReceptor": "IdReceptor",
            "importe": "Importe",
            "destino": "Destino",
        },
    ),
    "tarjetas": MedioConfig(
        table="dbo.Tarjetas_Resumenes_Lineas",
        id_column="IdLineaConsumo",
        id_field="idLineaConsumo",
        date_column="FechaCompra",
        select_columns={
            "idLineaConsumo": "IdLineaConsumo",
            "idResumen": "IdResumen",
            "fechaCompra": "FechaCompra",
            "detalle": "Detalle",
            "importe": "Importe",
            "idContacto": "IdContacto",
            "numeroDocumento": "NroDocumento",
        },
    ),
}

MEDIOS = tuple(MEDIOS_CONFIG.keys())


def _select_sql(config: MedioConfig) -> str:
    return ", ".join(f"{sql} AS [{field}]" for field, sql in config.select_columns.items())


def _filtro_busqueda(config: MedioConfig, q: str | None) -> tuple[list[str], list]:
    """19/11/2026: búsqueda por texto (concepto/descripción/contacto) o por importe exacto en formato argentino."""
    if not q or not q.strip():
        return [], []
    q = q.strip()
    textos = [config.select_columns[k] for k in ("concepto", "descripcion", "contacto", "detalle") if k in config.select_columns]
    conds, params = [f"{t} LIKE ?" for t in textos], [f"%{q}%"] * len(textos)
    import re
    limpio = q.replace("$", "").replace(" ", "")
    if re.fullmatch(r"-?[\d.]*,?\d+", limpio):
        valor = float(limpio.replace(".", "").replace(",", ".")) if "," in limpio else float(limpio.replace(".", ""))
        for k in ("importe", "debitos", "creditos"):
            if k in config.select_columns:
                conds.append(f"ABS({config.select_columns[k]}) = ?")
                params.append(abs(valor))
    return ([f"({' OR '.join(conds)})"] if conds else []), params


def get_movimientos(
    medio: str,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    page: int,
    page_size: int,
    q: str | None = None,
) -> tuple[list[dict], int]:
    config = MEDIOS_CONFIG[medio]

    where_clauses, params = _filtro_busqueda(config, q)
    if fecha_desde:
        where_clauses.append(f"{config.date_column} >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        where_clauses.append(f"{config.date_column} <= ?")
        params.append(as_sql_datetime(fecha_hasta))
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    join_sql = config.extra_join or ""
    count_sql = f"SELECT COUNT(*) AS total FROM {config.table} {join_sql} {where_sql}"
    total_row = fetch_one(count_sql, tuple(params))
    total = total_row["total"] if total_row else 0

    offset = offset_for(page, page_size)
    list_sql = f"""
        SELECT {_select_sql(config)}
        FROM {config.table}
        {join_sql}
        {where_sql}
        ORDER BY {config.date_column} DESC, {config.id_column} DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    rows = fetch_all(list_sql, tuple(params) + (offset, page_size))
    return rows, total


def get_movimiento(medio: str, id_movimiento: int) -> dict | None:
    """Fetch a single movimiento row (all select_columns) by its id."""
    config = MEDIOS_CONFIG[medio]
    sql = f"""
        SELECT {_select_sql(config)}
        FROM {config.table}
        {config.extra_join or ""}
        WHERE {config.id_column} = ?
    """
    return fetch_one(sql, (id_movimiento,))


def listar_cargas(banco: str) -> list[dict]:
    """Historial de cargas confirmadas de un banco (013 US4, FR-009).

    El alias SQL de esta columna NO puede ser "insertados": ese texto
    contiene la subcadena "INSERT", que `_assert_read_only` (connection.py)
    rechaza en cualquier SELECT sin importar dónde aparezca — se alias como
    `cargados` y se renombra a la clave pública `insertados` después de
    leer, ya en Python.
    """
    tabla_banco = "BNA" if banco == "bna" else "Galicia"
    sql = """
        SELECT IdCarga AS idCarga, NombreArchivo AS nombreArchivo,
               FechaHoraCarga AS fechaHoraCarga, CantidadCargados AS cargados,
               CantidadOmitidosDuplicado AS omitidosDuplicado,
               CantidadOmitidosIncompletos AS omitidosIncompletos
        FROM dbo.CargasResumenBancario
        WHERE Banco = ?
        ORDER BY FechaHoraCarga DESC
    """
    rows = fetch_all(sql, (tabla_banco,))
    for row in rows:
        row["insertados"] = row.pop("cargados")
    return rows


def ids_pendientes(medio: str, fecha_desde: date | None, fecha_hasta: date | None, q: str | None = None) -> list[int]:
    """19/11/2026: movimientos sin conciliar (o conciliados en parte), del más nuevo al más viejo.

    Una consulta descarta lo resuelto seguro (contacto reconocido o estado vigente) y el estado exacto se calcula
    con la misma regla que la pantalla (`esta_resuelto`) solo para lo que queda."""
    from src.features.conciliacion_tesoreria.repository import _info
    from src.features.tesoreria.estado_resolucion import esta_resuelto

    info = _info(medio)
    cond = ["NOT EXISTS (SELECT 1 FROM dbo.ConciliacionesTesoreriaEstado e WHERE e.Medio = ? AND e.IdMovimiento = m.{id} "
            "AND e.IdEstado = (SELECT MAX(e2.IdEstado) FROM dbo.ConciliacionesTesoreriaEstado e2 WHERE e2.Medio = e.Medio "
            "AND e2.IdMovimiento = e.IdMovimiento) AND e.Estado <> 'EstadoQuitado')".format(id=info.id_col)]
    params: list = [medio]
    if info.contacto_col:
        cond.append(f"(ISNULL(m.{info.contacto_col}, 0) = 0 OR EXISTS (SELECT 1 FROM dbo.BancoOperacionCaja bc "
                    f"WHERE bc.Medio = ? AND bc.IdMovimiento = m.{info.id_col}))")
        params.append(medio)
    if fecha_desde:
        cond.append(f"m.{info.fecha_col} >= ?")
        params.append(as_sql_datetime(fecha_desde))
    if fecha_hasta:
        cond.append(f"m.{info.fecha_col} <= ?")
        params.append(as_sql_datetime(fecha_hasta))
    if q:  # misma búsqueda que el listado, sobre la tabla del medio
        config = MEDIOS_CONFIG[medio]
        bq, bp = _filtro_busqueda(config, q)
        if bq:
            cond.append(f"m.{info.id_col} IN (SELECT {config.id_column} FROM {config.table} {config.extra_join or ''} WHERE {bq[0]})")
            params += bp
    filas = fetch_all(f"SELECT m.{info.id_col} AS id FROM {info.tabla} m WHERE {' AND '.join(cond)} "
                      f"ORDER BY m.{info.fecha_col} DESC, m.{info.id_col} DESC", tuple(params))
    return [f["id"] for f in filas if esta_resuelto(medio, f["id"]) in ("sin_conciliar", "parcialmente_conciliado")]


def get_movimientos_por_ids(medio: str, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    config = MEDIOS_CONFIG[medio]
    marcas = ",".join("?" * len(ids))
    filas = fetch_all(f"SELECT {_select_sql(config)} FROM {config.table} {config.extra_join or ''} "
                      f"WHERE {config.id_column} IN ({marcas})", tuple(ids))
    orden = {i: k for k, i in enumerate(ids)}
    for f in filas:
        if "saldo" in f:
            f["saldo"] = None  # el saldo acumulado no aplica a una lista filtrada
    return sorted(filas, key=lambda f: orden.get(f[config.id_field], 0))


def resumen(medio: str) -> dict:
    """19/11/2026 (auditoría de Tesorería, mejora 2): saldo, lo que falta conciliar y el último extracto cargado."""
    from src.features.conciliacion_tesoreria.repository import MEDIOS_SOPORTADOS, _info

    config = MEDIOS_CONFIG[medio]
    ultimo, _ = get_movimientos(medio, None, None, 1, 1)
    salida: dict = {"saldo": (ultimo[0].get("saldo") if ultimo else None),
                    "ultimoMovimiento": (ultimo[0].get(next((k for k in ("fechaHora", "fecha") if k in config.select_columns), "fecha")) if ultimo else None)}
    if medio in MEDIOS_SOPORTADOS:
        ids = ids_pendientes(medio, None, None)
        info = _info(medio)
        total, viejo = 0.0, None
        for k in range(0, len(ids), 900):
            chunk = ids[k:k + 900]
            f = fetch_one(f"SELECT SUM(ABS({info.importe_expr})) AS t, MIN({info.fecha_col}) AS v FROM {info.tabla} "
                          f"WHERE {info.id_col} IN ({','.join('?' * len(chunk))})", tuple(chunk))
            total += float(f["t"] or 0)
            viejo = min(x for x in (viejo, f["v"]) if x is not None) if f["v"] is not None or viejo is not None else None
        salida.update({"pendientes": len(ids), "importePendiente": round(total, 2), "pendienteMasViejo": viejo})
    banco = {"bna": "BNA", "galicia": "Galicia"}.get(medio)
    if banco:
        c = fetch_one("SELECT TOP 1 FechaHoraCarga AS f, NombreArchivo AS n FROM dbo.CargasResumenBancario WHERE Banco = ? "
                      "ORDER BY FechaHoraCarga DESC", (banco,))
        salida["ultimaCarga"] = c["f"] if c else None
    return salida
