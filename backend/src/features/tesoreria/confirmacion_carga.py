"""Confirm a previously previewed BNA/Galicia Excel summary into `WC` (013).

Never trusts a client-side preview: every confirmation re-parses the
uploaded bytes with `excel_import.validar_y_previsualizar` (FR-002), so
what gets persisted is exactly what the file contains at confirmation
time, not a stale in-memory preview.

Duplicate detection (research.md §2) has no natural key shared between
the two banks' tables and their Excel exports — neither carries a source
system id — so it relies on fecha + importe (or débito/crédito) +
concepto/descripción normalizado + comprobante (when present), compared
only against the date range actually present in the uploaded file.
"""

from __future__ import annotations

import re
from datetime import date

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.tesoreria import excel_import

_ESPACIOS_RE = re.compile(r"\s+")

BANCOS = ("bna", "galicia")


def _normalizar_concepto(texto: str | None) -> str:
    if not texto:
        return ""
    return _ESPACIOS_RE.sub(" ", texto).strip().upper()


def _norm_fecha(valor) -> date | None:
    """`fetch_all` returns SQL Server `datetime` columns as `datetime`, while
    the Excel preview produces plain `date` objects — comparing the two
    always evaluates to `False` in Python even for the same calendar day, so
    every real row would look "not a duplicate" no matter what. Normalize
    both sides to `date` before building the comparison key."""
    if valor is None:
        return None
    return valor.date() if hasattr(valor, "date") else valor


def _norm_monto(valor) -> float | None:
    """SQL Server `money` columns come back as `Decimal`; `Decimal == float`
    is always `False` in Python (never raises, just silently wrong), so
    every real amount also looked "different" from the Excel float. Cast
    both sides to `float` before comparing."""
    if valor is None:
        return None
    return round(float(valor), 2)


def _norm_comprobante(valor) -> str:
    """Both `Nro# Comprobante`/`Número de Comprobante` are `float` columns in
    SQL Server, so a real comprobante comes back as `999001.0`, while the
    Excel preview carries it as text (`"999001"`) — `str(999001.0) !=
    "999001"`, another silent mismatch. Normalize through `float` when the
    value is numeric so both sides compare equal."""
    if valor is None or valor == "":
        return ""
    try:
        return str(int(float(valor)))
    except (TypeError, ValueError):
        return str(valor).strip()


def _clave_movimiento_bna(fila: dict) -> tuple:
    return (
        _norm_fecha(fila.get("fecha")),
        _norm_monto(fila.get("importe")),
        _normalizar_concepto(fila.get("concepto")),
        _norm_comprobante(fila.get("comprobante")),
    )


def _clave_movimiento_galicia(fila: dict) -> tuple:
    return (
        _norm_fecha(fila.get("fecha")),
        _norm_monto(fila.get("debitos")),
        _norm_monto(fila.get("creditos")),
        _normalizar_concepto(fila.get("descripcion")),
        _norm_comprobante(fila.get("numeroComprobante")),
    )


def _clave_movimiento(banco: str, fila: dict) -> tuple:
    return _clave_movimiento_bna(fila) if banco == "bna" else _clave_movimiento_galicia(fila)


def _es_completa(banco: str, fila: dict) -> bool:
    if fila.get("fecha") is None:
        return False
    if banco == "bna":
        return fila.get("importe") is not None
    return fila.get("debitos") is not None or fila.get("creditos") is not None


def _existentes_del_rango(banco: str, movimientos: list[dict]) -> list[dict]:
    fechas = [m["fecha"] for m in movimientos if m.get("fecha") is not None]
    if not fechas:
        return []
    desde, hasta = min(fechas), max(fechas)
    if banco == "bna":
        sql = """
            SELECT [Fecha / Hora Mov#] AS fecha, Importe AS importe,
                   Concepto AS concepto, [Nro# Comprobante] AS comprobante
            FROM dbo.[Movimientos BNA]
            WHERE [Fecha / Hora Mov#] BETWEEN ? AND ?
        """
    else:
        sql = """
            SELECT Fecha AS fecha, [Débitos] AS debitos, [Créditos] AS creditos,
                   [Descripción] AS descripcion, [Número de Comprobante] AS numeroComprobante
            FROM dbo.[Movimientos Galicia]
            WHERE Fecha BETWEEN ? AND ?
        """
    return fetch_all(sql, (desde, hasta))


def detectar_duplicados(banco: str, movimientos: list[dict]) -> list[bool]:
    """Return, per index of `movimientos`, whether it already exists in `WC`."""
    existentes = _existentes_del_rango(banco, movimientos)
    claves_existentes = {_clave_movimiento(banco, fila) for fila in existentes}
    return [_clave_movimiento(banco, fila) in claves_existentes for fila in movimientos]


def previsualizar_confirmacion(banco: str, filename: str, contenido: bytes) -> dict:
    """Preview-only: parses and flags duplicates, writes nothing (US3)."""
    preview = excel_import.validar_y_previsualizar(filename, contenido)
    if not preview["valido"]:
        return preview

    movimientos = preview["movimientosPrevisualizados"]
    completos_idx = [i for i, m in enumerate(movimientos) if _es_completa(banco, m)]
    duplicados = detectar_duplicados(banco, [movimientos[i] for i in completos_idx])
    duplicado_por_idx = dict(zip(completos_idx, duplicados, strict=True))

    items = []
    nuevos = omitidos_duplicado = omitidos_incompletos = 0
    for i, m in enumerate(movimientos):
        if i not in duplicado_por_idx:
            estado = "omitidoIncompleto"
            omitidos_incompletos += 1
        elif duplicado_por_idx[i]:
            estado = "omitidoDuplicado"
            omitidos_duplicado += 1
        else:
            estado = "nuevo"
            nuevos += 1
        items.append({**m, "estado": estado})

    preview["movimientosPrevisualizados"] = items
    preview["resumen"] = {
        "nuevos": nuevos,
        "omitidosDuplicado": omitidos_duplicado,
        "omitidosIncompletos": omitidos_incompletos,
        "total": len(movimientos),
    }
    return preview


def _id_cuenta_bna_vigente() -> int:
    """El BNA cambio de numero de cuenta varias veces (`separar_cuentas_bna.py`
    reconstruyo el historico); toda carga nueva pertenece a la cuenta sin
    FechaBaja (la unica abierta hoy, 6150111899 a la fecha de esta migracion).
    Si en el futuro esa cuenta se da de baja y se abre otra, hay que cargar
    la cuenta nueva en `CuentasBancarias` antes de la primera carga."""
    fila = fetch_one(
        "SELECT IdCuentaBancaria FROM dbo.CuentasBancarias "
        "WHERE Banco = 'BNA' AND FechaBaja IS NULL"
    )
    if fila is None:
        raise ValueError("No hay ninguna cuenta BNA vigente en CuentasBancarias (FechaBaja IS NULL)")
    return fila["IdCuentaBancaria"]


def _insert_bna_statement(fila: dict, id_cuenta_bancaria: int):
    return (
        """
        INSERT INTO dbo.[Movimientos BNA]
            ([Fecha / Hora Mov#], [Nro# Comprobante], Concepto, Importe, IdCuentaBancaria, CertezaCuenta)
        OUTPUT INSERTED.IdMovimientoBNA
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            fila["fecha"],
            _to_float_or_none(fila.get("comprobante")),
            fila.get("concepto"),
            fila["importe"],
            id_cuenta_bancaria,
            "Alta",
        ),
    )


def _insert_galicia_statement(fila: dict):
    return (
        """
        INSERT INTO dbo.[Movimientos Galicia]
            (Fecha, [Descripción], [Débitos], [Créditos], [Número de Comprobante], Saldo)
        OUTPUT INSERTED.IdMovimiento
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            fila["fecha"],
            fila.get("descripcion"),
            fila.get("debitos"),
            fila.get("creditos"),
            _to_float_or_none(fila.get("numeroComprobante")),
            fila.get("saldo"),
        ),
    )


def _to_float_or_none(valor) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def confirmar_carga(banco: str, filename: str, contenido: bytes) -> dict:
    """Re-parse, deduplicate and persist a BNA/Galicia summary (US1/US2, FR-001..FR-006)."""
    if banco not in BANCOS:
        raise ValueError(f"Banco desconocido: {banco}")

    preview = excel_import.validar_y_previsualizar(filename, contenido)
    if not preview["valido"]:
        return {"valido": False, "errores": preview["errores"]}

    movimientos = preview["movimientosPrevisualizados"]
    completos_idx = [i for i, m in enumerate(movimientos) if _es_completa(banco, m)]
    duplicados = detectar_duplicados(banco, [movimientos[i] for i in completos_idx])
    duplicado_por_idx = dict(zip(completos_idx, duplicados, strict=True))

    nuevos = [
        movimientos[i]
        for i in completos_idx
        if not duplicado_por_idx[i]
    ]
    omitidos_duplicado = sum(1 for v in duplicado_por_idx.values() if v)
    omitidos_incompletos = len(movimientos) - len(completos_idx)

    tabla_banco = "BNA" if banco == "bna" else "Galicia"
    n = len(nuevos)

    # Un único INSERT por movimiento, luego la carga, luego un vínculo por
    # movimiento — todo en una sola transacción (FR-005) para que un fallo
    # a mitad de camino no deje movimientos sin su carga o viceversa.
    # `execute_write_transaction` resuelve cada callable con los resultados
    # ya obtenidos, en orden: `resultados[0..n-1]` son los ids de movimiento
    # y `resultados[n]` es el `IdCarga` recién insertado.
    if banco == "bna":
        id_cuenta_bancaria = _id_cuenta_bna_vigente()
        statements: list = [_insert_bna_statement(fila, id_cuenta_bancaria) for fila in nuevos]
    else:
        statements = [_insert_galicia_statement(fila) for fila in nuevos]
    statements.append(
        lambda resultados: (
            """
            INSERT INTO dbo.CargasResumenBancario
                (Banco, NombreArchivo, CantidadCargados, CantidadOmitidosDuplicado, CantidadOmitidosIncompletos)
            OUTPUT INSERTED.IdCarga
            VALUES (?, ?, ?, ?, ?)
            """,
            (tabla_banco, filename, n, omitidos_duplicado, omitidos_incompletos),
        )
    )
    for i in range(n):
        statements.append(
            lambda resultados, i=i: (
                """
                INSERT INTO dbo.CargasResumenBancario_Movimientos (IdCarga, Banco, IdMovimiento)
                VALUES (?, ?, ?)
                """,
                (resultados[n], tabla_banco, resultados[i]),
            )
        )

    resultados = execute_write_transaction(statements)
    id_carga = resultados[n]

    return {
        "valido": True,
        "banco": banco,
        "idCarga": id_carga,
        "insertados": len(nuevos),
        "omitidosDuplicado": omitidos_duplicado,
        "omitidosIncompletos": omitidos_incompletos,
        "total": len(movimientos),
    }
