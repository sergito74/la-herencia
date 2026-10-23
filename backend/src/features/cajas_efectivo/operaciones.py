"""Persistencia 038. Decimales nativos y conexión transaccional compartida.

Las tablas/columnas de las escrituras son constantes del módulo, no del cliente.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, time
from decimal import Decimal

from src.db.connection import (
    _assert_read_only,
    _coerce_params,
    execute_insert_returning_id,
    execute_write,
    get_connection,
)

CAJAS = {
    "giamigli-sa": "GiamigliSA",
    "giamigli-dolares": "GiamigliUSD",
    "campo-chica": "CampoChica",
    "condominio-lsc": "CondominioLSC",
}


def read(sql, params=()):
    """Keep Decimal: legacy fetch_all intentionally coerces it to float."""
    _assert_read_only(sql)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, _coerce_params(tuple(params)))
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def one(sql, params=()):
    rows = read(sql, params)
    return rows[0] if rows else None


def insert(sql, params):
    return execute_insert_returning_id(sql, tuple(params))


def write(sql, params=()):
    return execute_write(sql, tuple(params))


def dumps(value):
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def find_key(key):
    return one("SELECT * FROM dbo.OperacionesCajaEfectivo WHERE ClaveIdempotencia=?", (str(key),))


def get_operation(id_operation):
    return one("SELECT * FROM dbo.OperacionesCajaEfectivo WHERE IdOperacion=?", (id_operation,))


def detail(id_operation):
    op = get_operation(id_operation)
    if not op:
        return None
    return {
        "idOperacion": op["IdOperacion"],
        "estado": op["Estado"],
        "version": op["Version"],
        "operacion": json.loads(op["Solicitud"]),
        "contexto": json.loads(op["Contexto"]),
        "usuario": op["Usuario"],
        "fechaCarga": str(op["FechaCarga"]),
        "motivoAnulacion": op["MotivoAnulacion"],
        "usuarioAnulacion": op["UsuarioAnulacion"],
        "fechaAnulacion": str(op["FechaAnulacion"]) if op["FechaAnulacion"] else None,
        "movimientos": read(
            "SELECT IdMovimiento idMovimiento,Caja caja,Fecha fecha, "
            "CONVERT(varchar(40),CAST(Importe AS decimal(19,2))) importeDecimal,"
            "Anulada anulada FROM dbo.vw_MovimientosCajaEfectivoOperativos "
            "WHERE IdOperacionCaja=? ORDER BY IdMovimiento",
            (id_operation,),
        ),
        "efectos": read(
            "SELECT TipoEfecto tipo,IdRegistro idRegistro,EsCreadoPorOperacion propio "
            "FROM dbo.EfectosOperacionCaja WHERE IdOperacion=? ORDER BY IdEfecto",
            (id_operation,),
        ),
    }


def create_operation(key, fingerprint, op, context, user):
    return insert(
        "INSERT INTO dbo.OperacionesCajaEfectivo "
        "(ClaveIdempotencia,HuellaSolicitud,Tipo,Fecha,Concepto,Cuenta,IdContacto,IdSocio,"
        "Solicitud,Contexto,Usuario) OUTPUT INSERTED.IdOperacion VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            str(key),
            fingerprint,
            op.tipo,
            op.fecha,
            op.concepto,
            op.cuenta,
            op.idContacto,
            op.idSocio,
            dumps(op.model_dump(mode="json")),
            dumps(context),
            user,
        ),
    )


def effect(id_operation, kind, id_record, own=True, snapshot=None):
    return insert(
        "INSERT INTO dbo.EfectosOperacionCaja "
        "(IdOperacion,TipoEfecto,IdRegistro,EsCreadoPorOperacion,Snapshot) "
        "OUTPUT INSERTED.IdEfecto VALUES (?,?,?,?,?)",
        (id_operation, kind, id_record, own, dumps(snapshot) if snapshot is not None else None),
    )


def cash(id_operation, op, box, signed_amount, user, payment=None):
    return insert(
        "INSERT INTO dbo.MovimientosCajaEfectivo "
        "(Caja,Fecha,Concepto,Detalle,Importe,Cuenta,IdContactoRelacionado,Usuario,"
        "IdPagoEfectivo,IdOperacionCaja,Tipo) OUTPUT INSERTED.IdMovimiento "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            CAJAS[box],
            op.fecha,
            op.concepto,
            op.motivoRelacionGiamigli,
            signed_amount,
            op.cuenta,
            op.idContacto,
            user,
            payment,
            id_operation,
            op.tipo,
        ),
    )


def payment(id_operation, op, signed_credit):
    # Credito in vw_MovimientosCuenta_Base = Importe imputado (opposite to cash).
    id_payment = insert(
        "INSERT INTO dbo.[Pagos efectivo] "
        "(IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,[Importe imputado]) "
        "OUTPUT INSERTED.IdPagoEfectivo VALUES (?,?,3,?,?,?,?)",
        (
            op.idContacto,
            1 if signed_credit > 0 else 2,
            op.fecha,
            op.cuenta,
            CAJAS[op.caja],
            signed_credit,
        ),
    )
    effect(id_operation, "PagoEfectivo", id_payment)
    return id_payment


def caja_context(box, when, excluir_operacion=None):
    start = datetime.combine(when, time.min)
    rows = read(
        "SELECT IdMovimiento id,Fecha fecha,Importe importe,Anulada anulada,IdOperacionCaja operacion "
        "FROM dbo.vw_MovimientosCajaEfectivoOperativos WHERE Caja=? ORDER BY Fecha,IdMovimiento",
        (CAJAS[box],),
    )
    balance = Decimal(0)
    initial = Decimal(0)
    later = []
    excluded = 0
    after_exclusion = []
    for row in rows:
        if row["anulada"]:
            continue
        if excluir_operacion is not None and row.get('operacion') == excluir_operacion:
            excluded += 1
        else:
            balance += row["importe"]
        if excluded:
            after_exclusion.append(balance)
        # New operations have midnight date and identity > previous records that day.
        moment = row["fecha"]
        if isinstance(moment, str):
            moment = datetime.fromisoformat(moment)
        if moment <= start:
            initial = balance
        else:
            later.append(balance)
    arqueos = read(
        "SELECT IdArqueo id,FechaCorte fecha,SecuenciaCorte secuencia,Version version,Estado estado "
        "FROM dbo.ArqueosCajaEfectivo WHERE Caja=? AND Estado IN ('Confirmado','Desactualizado') "
        "AND FechaCorte>=? ORDER BY IdArqueo",
        (CAJAS[box], when),
    )
    return {
        "saldoActual": balance,
        "saldoFecha": initial,
        "minimoPosterior": min(after_exclusion or [balance]) if excluir_operacion is not None else min([initial] + later),
        "movimientosExcluidos": excluded,
        "huellaMovimientos": hashlib.sha256(dumps(rows).encode("utf-8")).hexdigest(),
        "arqueos": arqueos,
    }


def stale_arqueos(boxes, when, user):
    for box in boxes:
        write(
            "UPDATE dbo.ArqueosCajaEfectivo SET Estado='Desactualizado',Version=Version+1, "
            "MotivoInvalidacion=N'Movimiento posterior con fecha retroactiva',UsuarioInvalidacion=?,"
            "FechaInvalidacion=SYSUTCDATETIME() WHERE Caja=? AND FechaCorte>=? AND Estado='Confirmado'",
            (user, CAJAS[box], when),
        )


def effects(id_operation):
    return read(
        "SELECT * FROM dbo.EfectosOperacionCaja WHERE IdOperacion=? ORDER BY IdEfecto DESC",
        (id_operation,),
    )
