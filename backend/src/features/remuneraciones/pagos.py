"""Pagos de liquidaciones de sueldo (18/11/2026).

Sergio: "con el pago quiero que quede vinculado el egreso de una sola vez", sin doble carga. Un solo egreso paga una
o varias liquidaciones del mismo empleado, de la más vieja a la más nueva:
  - socio: asiento a favor del socio en su cuenta + vínculo al empleado (PagosSocioProveedor), como Irma/Lucy;
  - galicia / bna: débito del extracto de Giamigli ya cargado a nombre del empleado;
  - caja: salida de caja como PAGO al empleado (no gasto: el sueldo ya es costo por la liquidación).
Anular el egreso (cuenta del socio o caja) libera las liquidaciones.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.remuneraciones.repository import _IMPORTE_SQL
from src.features.trabajos_eventuales.repository import dinero, repartir_pago

_VIGENTES = """FROM dbo.RemuneracionesPagos p
LEFT JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion = p.IdOperacion
LEFT JOIN dbo.MovimientosCuentaSocio ms ON ms.IdMovimiento = p.IdMovimientoSocio
LEFT JOIN dbo.Socios so ON so.IdSocio = ms.IdSocio
WHERE (p.Medio <> 'caja' OR o.Estado <> 'Anulada') AND (p.Medio <> 'socio' OR ms.Anulada = 0)"""


def _dia(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def pagos_de(ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    out: dict[int, list[dict]] = {i: [] for i in ids}
    for p in fetch_all(
            "SELECT p.IdSalario AS idSalario, p.IdPagoRemuneracion AS idPago, p.Medio AS medio, p.Fecha AS fecha, p.Importe AS importe, "
            "so.Nombre AS socio " + _VIGENTES + f" AND p.IdSalario IN ({','.join('?' * len(ids))}) "
            "ORDER BY p.Fecha, p.IdPagoRemuneracion", tuple(ids)):
        out[p["idSalario"]].append(p)
    return out


def liquidaciones(ids: list[int]) -> list[dict]:
    if not ids:
        raise ValueError("Elegí al menos una liquidación")
    ids = list(dict.fromkeys(ids))
    filas = fetch_all(
        f"SELECT r.IdSalario AS idSalario, r.IdContacto AS idContacto, c.[Razon Social] AS empleado, r.[Fecha de pago] AS fecha, "
        f"r.[Periodo liquidado] AS periodo, ({_IMPORTE_SQL}) AS neto FROM dbo.Remuneraciones r "
        f"JOIN dbo.Contactos c ON c.IdContacto = r.IdContacto WHERE r.IdSalario IN ({','.join('?' * len(ids))})", tuple(ids))
    if len(filas) != len(ids):
        raise ValueError("Alguna liquidación no existe")
    if len({f["idContacto"] for f in filas}) > 1:
        raise ValueError("Las liquidaciones tienen que ser del mismo empleado")
    pagos = pagos_de(ids)
    for f in filas:
        f["pagado"] = sum(dinero(p["importe"]) for p in pagos[f["idSalario"]])
        f["falta"] = max(Decimal(0), dinero(f["neto"]) - f["pagado"])
    filas = [f for f in filas if f["falta"] > 0]
    if not filas:
        raise ValueError("Las liquidaciones elegidas ya tienen su pago vinculado")
    return sorted(filas, key=lambda f: (_dia(f["fecha"]), f["idSalario"]))


def _detalle(ls) -> str:
    return f"{ls[0]['empleado']} · Sueldo " + ", ".join(str(l["periodo"]).strip() for l in ls)


def _filas_pago(partes, medio, fecha, usuario, socio=None, banco=None, operacion=None):
    return [lambda r, i=i, parte=parte: (
        "INSERT INTO dbo.RemuneracionesPagos (IdSalario, Medio, IdMovimientoSocio, IdMovimientoBanco, IdOperacion, Fecha, Importe, Usuario) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (i, medio, r[0] if socio else None, banco, operacion, fecha, parte, usuario[:100])) for i, parte in partes]


def pagar_por_socio(ids, datos, usuario):
    from src.features.cuentas_socios.repository import _insert_asiento, validar_medio

    validar_medio(datos.idSocio, datos.medio)

    ls = liquidaciones(ids)
    partes = repartir_pago([(l["idSalario"], l["falta"]) for l in ls], datos.importe)
    ops = [_insert_asiento(datos.idSocio, "haber", float(datos.importe), datos.fecha, datos.medio, _detalle(ls)[:250], usuario),
           lambda r: ("INSERT INTO dbo.AuditoriaReflejoSocio (Accion, IdMovimiento, IdSocio, Usuario, Detalle) VALUES (?, ?, ?, ?, ?)",
                      ("Devolucion", r[0], datos.idSocio, usuario, "Pago de sueldo " + ", ".join(f"#{i}" for i, _ in partes))),
           lambda r: ("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio, IdContacto, Criterio) VALUES (?, ?, ?)",
                      (r[0], ls[0]["idContacto"], "sueldo"))]
    execute_write_transaction(ops + _filas_pago(partes, "socio", datos.fecha, usuario, socio=True))
    return {"pagadas": [i for i, _ in partes]}


def transferencias_candidatas(ids) -> list[dict]:
    """Débitos de Giamigli al empleado ya cargados del extracto, sin vincular a otra liquidación ni a un trabajo eventual."""
    ls = liquidaciones(ids)
    desde = min(_dia(l["fecha"]) for l in ls) - timedelta(days=20)
    usados = {(r["m"], r["i"]) for r in fetch_all(
        "SELECT Medio AS m, IdMovimientoBanco AS i FROM dbo.RemuneracionesPagos WHERE IdMovimientoBanco IS NOT NULL "
        "UNION SELECT Medio, IdMovimientoBanco FROM dbo.TrabajosEventualesPagos WHERE IdMovimientoBanco IS NOT NULL")}
    filas = fetch_all(
        "SELECT 'galicia' AS medio, IdMovimiento AS id, Fecha AS fecha, [Débitos] AS importe, [Descripción] AS detalle "
        "FROM dbo.[Movimientos Galicia] WHERE IdContacto = ? AND [Débitos] > 0 AND Fecha >= ? "
        "UNION ALL SELECT 'bna', IdMovimientoBNA, [Fecha / Hora Mov#], -Importe, Concepto FROM dbo.[Movimientos BNA] "
        "WHERE IdContacto = ? AND Importe < 0 AND [Fecha / Hora Mov#] >= ?",
        (ls[0]["idContacto"], desde, ls[0]["idContacto"], desde))
    filas = [f for f in filas if (f["medio"], f["id"]) not in usados]
    ref = _dia(ls[-1]["fecha"])
    return sorted(filas, key=lambda f: abs((_dia(f["fecha"]) - ref).days))


def pagar_con_transferencia(ids, medio, id_movimiento, usuario):
    m = next((f for f in transferencias_candidatas(ids) if f["medio"] == medio and f["id"] == id_movimiento), None)
    if not m:
        raise ValueError("Ese movimiento del banco no es del empleado o ya está vinculado")
    ls = liquidaciones(ids)
    faltas = [(l["idSalario"], l["falta"]) for l in ls]
    partes = repartir_pago(faltas, min(dinero(m["importe"]), sum((f for _, f in faltas), Decimal(0))))
    execute_write_transaction([op([None]) for op in _filas_pago(partes, medio, _dia(m["fecha"]), usuario, banco=id_movimiento)])
    return {"pagadas": [i for i, _ in partes]}


def _operacion_caja(ls, datos):
    from src.features.cajas_efectivo.schemas import OperacionCaja

    return OperacionCaja(tipo="pago", caja=datos.caja, fecha=datos.fecha, importe=datos.importe,
                         concepto=_detalle(ls)[:255], cuenta=datos.cuenta, idContacto=ls[0]["idContacto"],
                         idSalario=ls[0]["idSalario"])


def previsualizar_caja(ids, datos):
    import json

    from src.features.cajas_efectivo import operaciones, service

    ls = liquidaciones(ids)
    repartir_pago([(l["idSalario"], l["falta"]) for l in ls], datos.importe)
    return json.loads(operaciones.dumps(service.previsualizar(_operacion_caja(ls, datos))))


def pagar_con_caja(ids, datos, usuario):
    from uuid import uuid4

    from src.features.cajas_efectivo import service
    from src.features.cajas_efectivo.schemas import ConfirmarOperacion

    ls = liquidaciones(ids)
    partes = repartir_pago([(l["idSalario"], l["falta"]) for l in ls], datos.importe)
    hecho, _ = service.crear(ConfirmarOperacion(operacion=_operacion_caja(ls, datos), previewVersion=datos.previewVersion,
                                                advertenciasAceptadas=datos.advertenciasAceptadas), uuid4(), usuario)
    execute_write_transaction([op([None]) for op in _filas_pago(partes, "caja", datos.fecha, usuario, operacion=hecho["idOperacion"])])
    return {"pagadas": [i for i, _ in partes]}
