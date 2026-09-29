"""Cuentas corrientes de socios/directores y condominio (021).

`MovimientosCuentaSocio` es inmutable: se inserta o se anula, nunca se
edita (spec FR-006, mismo patrón que `AplicacionesPago` en 019). El saldo
de un socio se calcula siempre en el momento (`SUM` sobre vigentes), nunca
se guarda como campo fijo. Cada asignación/reversión/devolución queda
además registrada en `AuditoriaReflejoSocio` (tabla dedicada, decisión
explícita del usuario 2026-09-24 — no el patrón liviano de otras
features).
"""

from __future__ import annotations

from datetime import date

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.compras.particular import APLICA_PARTICULAR_JOIN, importe_personal_compra_particular

TOLERANCIA_REDONDEO = 1.0


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def listar_compras_particulares_candidatas(proveedor: str | None = None) -> list[dict]:
    """Compras "particular" (research.md §3) sin asignación vigente a
    ningún socio — candidatas para `asignar_gasto`. `importePersonal` es
    el valor absoluto de la línea negativa (lo que se le asignaría al
    socio), no el total reconstruido — puede ser menor al importe de la
    compra cuando el descuento fue parcial (split, 2026-09-26)."""
    where = ["1 = 1"]
    params: list = []
    if proveedor:
        where.append("ct.[Razon Social] LIKE ?")
        params.append(f"%{proveedor.strip()}%")

    sql = f"""
        SELECT w.IdDeuda AS idCompra, w.Fecha AS fecha, ct.[Razon Social] AS proveedor,
               w.[Nro Documento] AS numeroDocumento, ABS(pa.cp) AS importePersonal
        FROM dbo.vw_Compras_ImporteDocumento w
        {APLICA_PARTICULAR_JOIN}
        JOIN dbo.Contactos ct ON ct.IdContacto = w.IdContacto
        WHERE {' AND '.join(where)}
          AND pa.cp <> 0
          AND NOT EXISTS (
              SELECT 1 FROM dbo.MovimientosCuentaSocio m
              WHERE m.Origen = 'CompraParticular' AND m.IdOrigen = w.IdDeuda
                AND m.Tipo = 'AsignacionGasto' AND m.Anulada = 0
          )
        ORDER BY w.Fecha DESC
    """
    filas = fetch_all(sql, tuple(params))
    return [{**f, "importePersonal": round(_f(f["importePersonal"]), 2)} for f in filas]


def _tiene_asignacion_vigente(id_compra: int) -> bool:
    fila = fetch_one(
        "SELECT 1 AS x FROM dbo.MovimientosCuentaSocio "
        "WHERE Origen = 'CompraParticular' AND IdOrigen = ? AND Tipo = 'AsignacionGasto' AND Anulada = 0",
        (id_compra,),
    )
    return fila is not None


def asignar_gasto(id_socio: int, id_compra: int, usuario: str, motivo: str | None = None) -> dict:
    """Asigna una compra particular a un socio (spec FR-002/FR-003).
    Rechaza si ya tiene una asignación vigente (FR-009) — el índice único
    filtrado en base es la garantía final, esto es el mensaje legible
    antes de llegar ahí."""
    if _tiene_asignacion_vigente(id_compra):
        raise ValueError(f"La compra {id_compra} ya tiene una asignación vigente a un socio.")

    importe = importe_personal_compra_particular(id_compra)
    if importe is None:
        raise ValueError(f"La compra {id_compra} no es una compra particular (no tiene línea negativa 'particular').")

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.MovimientosCuentaSocio "
                "(IdSocio, Tipo, Importe, Origen, IdOrigen, Motivo, Usuario) "
                "OUTPUT INSERTED.IdMovimiento "
                "VALUES (?, 'AsignacionGasto', ?, 'CompraParticular', ?, ?, ?)",
                (id_socio, importe, id_compra, motivo, usuario),
            ),
            lambda resultados: (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES ('Asignacion', ?, ?, ?, ?)",
                (resultados[0], id_socio, usuario, f"Compra particular #{id_compra}"),
            ),
        ]
    )
    return _movimiento_por_id(resultados[0])


def _movimiento_por_id(id_movimiento: int) -> dict:
    fila = fetch_one(
        "SELECT IdMovimiento AS idMovimiento, IdSocio AS idSocio, Tipo AS tipo, Importe AS importe, "
        "Fecha AS fecha, Origen AS origen, IdOrigen AS idOrigen, Medio AS medio, Motivo AS motivo, "
        "Usuario AS usuario, Anulada AS anulada, MotivoAnulacion AS motivoAnulacion "
        "FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = ?",
        (id_movimiento,),
    )
    assert fila is not None
    return {**fila, "importe": _f(fila["importe"])}


def anular_movimiento(id_movimiento: int, motivo: str, usuario: str) -> dict:
    """Anulación no destructiva (spec FR-006): nunca `UPDATE`/`DELETE` del
    importe/tipo/origen — solo se marca `Anulada`. Registra en
    `AuditoriaReflejoSocio` la reversión correspondiente según el `Tipo`
    del movimiento anulado."""
    movimiento = fetch_one(
        "SELECT IdMovimiento AS idMovimiento, IdSocio AS idSocio, Tipo AS tipo, Anulada AS anulada "
        "FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = ?",
        (id_movimiento,),
    )
    if movimiento is None:
        raise ValueError(f"El movimiento {id_movimiento} no existe.")
    if movimiento["anulada"]:
        raise ValueError(f"El movimiento {id_movimiento} ya está anulado.")

    accion = "ReversionAsignacion" if movimiento["tipo"] == "AsignacionGasto" else "ReversionDevolucion"
    execute_write_transaction(
        [
            (
                "UPDATE dbo.MovimientosCuentaSocio SET Anulada = 1, MotivoAnulacion = ?, "
                "UsuarioAnulacion = ?, FechaAnulacion = SYSUTCDATETIME() WHERE IdMovimiento = ?",
                (motivo, usuario, id_movimiento),
            ),
            (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES (?, ?, ?, ?, ?)",
                (accion, id_movimiento, movimiento["idSocio"], usuario, motivo),
            ),
        ]
    )
    return _movimiento_por_id(id_movimiento)


def calcular_saldo(id_socio: int) -> float:
    fila = fetch_one(
        "SELECT SUM(CASE WHEN Tipo = 'AsignacionGasto' THEN Importe ELSE -Importe END) AS saldo "
        "FROM dbo.MovimientosCuentaSocio WHERE IdSocio = ? AND Anulada = 0",
        (id_socio,),
    )
    return round(_f(fila["saldo"] if fila else None), 2)


def listar_socios_con_saldo() -> list[dict]:
    socios = fetch_all("SELECT IdSocio AS idSocio, Nombre AS nombre FROM dbo.Socios ORDER BY IdSocio")
    return [{**s, "saldo": calcular_saldo(s["idSocio"])} for s in socios]


def listar_movimientos(id_socio: int) -> list[dict]:
    """Movimientos de un socio, incluidos los anulados (nunca se ocultan,
    FR-005/FR-006). Cada `AsignacionGasto` trae el proveedor/documento de
    origen si la compra sigue existiendo, y se marca `huerfano` si no
    (FR-011) — nunca desaparece del historial ni se recalcula como válido."""
    filas = fetch_all(
        """
        SELECT m.IdMovimiento AS idMovimiento, m.Tipo AS tipo, m.Importe AS importe, m.Fecha AS fecha,
               m.Origen AS origen, m.IdOrigen AS idOrigen, m.Medio AS medio, m.Motivo AS motivo,
               m.Usuario AS usuario, m.Anulada AS anulada, m.MotivoAnulacion AS motivoAnulacion,
               ct.[Razon Social] AS proveedorOrigen, c.[Nro Documento] AS numeroDocumentoOrigen,
               CASE WHEN m.Origen IS NOT NULL AND c.IdDeuda IS NULL THEN 1 ELSE 0 END AS huerfano
        FROM dbo.MovimientosCuentaSocio m
        LEFT JOIN dbo.Compras c ON m.Origen = 'CompraParticular' AND c.IdDeuda = m.IdOrigen
        LEFT JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto
        WHERE m.IdSocio = ?
        ORDER BY m.Fecha ASC, m.IdMovimiento ASC
        """,
        (id_socio,),
    )
    return [{**f, "importe": _f(f["importe"]), "huerfano": bool(f["huerfano"])} for f in filas]


def registrar_devolucion(id_socio: int, importe: float, fecha: date, medio: str, motivo: str, usuario: str) -> dict:
    """Devolución/compensación manual (spec FR-008). Se acepta aunque
    supere el saldo deudor actual (Edge Case de la spec: el socio puede
    quedar con saldo a favor, no se rechaza)."""
    if importe <= 0:
        raise ValueError("El importe de la devolución debe ser mayor a $0.")
    if not motivo or not motivo.strip():
        raise ValueError("El motivo es obligatorio para registrar una devolución.")

    resultados = execute_write_transaction(
        [
            (
                "INSERT INTO dbo.MovimientosCuentaSocio (IdSocio, Tipo, Importe, Fecha, Medio, Motivo, Usuario) "
                "OUTPUT INSERTED.IdMovimiento "
                "VALUES (?, 'Devolucion', ?, ?, ?, ?, ?)",
                (id_socio, importe, fecha, medio, motivo, usuario),
            ),
            lambda resultados: (
                "INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) "
                "VALUES ('Devolucion', ?, ?, ?, ?)",
                (resultados[0], id_socio, usuario, motivo),
            ),
        ]
    )
    return _movimiento_por_id(resultados[0])
