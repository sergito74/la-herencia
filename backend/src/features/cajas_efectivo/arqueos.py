"""Recuentos físicos en pesos, versionados y sin reabrir evidencia confirmada."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from pydantic import Field, model_validator

from src.db.connection import atomic_reconciliation
from src.features.cajas_efectivo import operaciones as db
from src.features.cajas_efectivo.schemas import Estricto
from src.features.cajas_efectivo.service import ConflictoCaja, NoExisteCaja, huella


class Denominacion(Estricto):
    valor: Decimal = Field(gt=0, max_digits=19, decimal_places=2)
    cantidad: int = Field(ge=0, le=1000000, strict=True)


class Recuento(Estricto):
    fechaCorte: date
    secuenciaCorte: int | None = Field(default=None, ge=0)
    denominaciones: list[Denominacion] = Field(min_length=1, max_length=50)
    versionEsperada: int | None = Field(default=None, ge=0)
    idArqueoAnterior: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def unicas(self):
        if len({d.valor for d in self.denominaciones}) != len(self.denominaciones):
            raise ValueError("La denominación no puede repetirse.")
        return self


class Confirmacion(Estricto):
    versionEsperada: int = Field(ge=0)
    previewVersion: str = Field(pattern=r"^[0-9a-f]{64}$")
    aceptarDiferencia: bool = False
    advertenciasAceptadas: list[str] = Field(default_factory=list)


def _saldo(caja, fecha, secuencia):
    return db.one(
        "SELECT ISNULL(SUM(Importe),0) saldo FROM dbo.MovimientosCajaEfectivo "
        "WHERE Caja=? AND Anulada=0 AND (CAST(Fecha AS date)<? OR "
        "(CAST(Fecha AS date)=? AND IdMovimiento<=?))",
        (db.CAJAS[caja], fecha, fecha, secuencia),
    )["saldo"]


def detalle(caja, id_arqueo):
    a = db.one(
        "SELECT * FROM dbo.ArqueosCajaEfectivo WHERE Caja=? AND IdArqueo=?",
        (db.CAJAS[caja], id_arqueo),
    )
    if not a:
        raise NoExisteCaja("Arqueo inexistente.")
    # Recalculated end-of-day balance includes later-entered retroactive movements
    # and this count's adjustment; the original snapshot remains immutable.
    saldo = _saldo(caja, a["FechaCorte"], 9223372036854775807)
    context = db.caja_context(caja, date.fromisoformat(str(a["FechaCorte"])[:10][:10]))
    warnings = []
    if context["minimoPosterior"] + a["TotalContado"] - saldo < 0:
        warnings.append("SALDO_NEGATIVO")
    if any(x.get("id") != id_arqueo for x in context["arqueos"]):
        warnings.append("PERIODO_ARQUEADO")
    preview = huella(
        {
            "id": id_arqueo,
            "version": a["Version"],
            "saldo": saldo,
            "contado": a["TotalContado"],
            "fecha": a["FechaCorte"],
            "secuencia": a["SecuenciaCorte"],
            "contexto": context,
        }
    )
    return {
        "idArqueo": id_arqueo,
        "caja": caja,
        "fechaCorte": str(a["FechaCorte"])[:10],
        "secuenciaCorte": a["SecuenciaCorte"],
        "estado": a["Estado"],
        "version": a["Version"],
        "saldoSistema": f"{a['SaldoSistema']:.2f}",
        "totalContado": f"{a['TotalContado']:.2f}",
        "diferencia": f"{a['Diferencia']:.2f}",
        "saldoRecalculadoDecimal": f"{saldo:.2f}",
        "diferenciaVigenteDecimal": f"{a['TotalContado'] - saldo:.2f}",
        "previewVersion": preview,
        "advertencias": warnings,
        "idOperacionAjuste": a["IdOperacionAjuste"],
        "idArqueoAnterior": a["IdArqueoAnterior"],
        "usuario": a["Usuario"],
        "usuarioConfirmacion": a["UsuarioConfirmacion"],
        "motivoInvalidacion": a["MotivoInvalidacion"],
        "denominaciones": [
            {"valor": f"{x['Denominacion']:.2f}", "cantidad": x["Cantidad"]}
            for x in db.read(
                "SELECT Denominacion,Cantidad FROM dbo.ArqueoDenominaciones "
                "WHERE IdArqueo=? ORDER BY Denominacion DESC",
                (id_arqueo,),
            )
        ],
    }


def listar(caja, page=1, size=20):
    rows = db.read(
        "SELECT IdArqueo FROM dbo.ArqueosCajaEfectivo WHERE Caja=? ORDER BY FechaCorte DESC,IdArqueo DESC "
        "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (db.CAJAS[caja], (page - 1) * size, size),
    )
    total = db.one(
        "SELECT COUNT(*) n FROM dbo.ArqueosCajaEfectivo WHERE Caja=?", (db.CAJAS[caja],)
    )["n"]
    return {
        "items": [detalle(caja, x["IdArqueo"]) for x in rows],
        "page": page,
        "pageSize": size,
        "total": total,
    }


@atomic_reconciliation
def guardar(caja, body, user, id_arqueo=None):
    if id_arqueo:
        previous = detalle(caja, id_arqueo)
        if previous["estado"] != "Borrador" or body.versionEsperada != previous["version"]:
            raise ConflictoCaja("El arqueo cambió o ya no es borrador.")
    if body.idArqueoAnterior:
        previous = detalle(caja, body.idArqueoAnterior)
        if previous["estado"] not in ("Invalidado", "Desactualizado"):
            raise ValueError("Solo se corrige un arqueo invalidado/desactualizado.")
    last = db.one(
        "SELECT ISNULL(MAX(IdMovimiento),0) secuencia FROM dbo.MovimientosCajaEfectivo "
        "WHERE Caja=? AND CAST(Fecha AS date)<=?",
        (db.CAJAS[caja], body.fechaCorte),
    )["secuencia"]
    sequence = last if body.secuenciaCorte is None else body.secuenciaCorte
    if sequence > last:
        raise ValueError("La secuencia supera los movimientos existentes al corte.")
    saldo = _saldo(caja, body.fechaCorte, sequence)
    counted = sum((x.valor * x.cantidad for x in body.denominaciones), Decimal(0))
    if counted >= Decimal("100000000000000000"):
        raise ValueError("El total contado excede la precisión admitida.")
    params = (body.fechaCorte, sequence, saldo, counted, counted - saldo, body.idArqueoAnterior)
    if id_arqueo:
        db.write(
            "UPDATE dbo.ArqueosCajaEfectivo SET FechaCorte=?,SecuenciaCorte=?,SaldoSistema=?,TotalContado=?,"
            "Diferencia=?,IdArqueoAnterior=?,Version=Version+1 WHERE IdArqueo=?",
            (*params, id_arqueo),
        )
        db.write("DELETE FROM dbo.ArqueoDenominaciones WHERE IdArqueo=?", (id_arqueo,))
    else:
        id_arqueo = db.insert(
            "INSERT INTO dbo.ArqueosCajaEfectivo "
            "(FechaCorte,SecuenciaCorte,SaldoSistema,TotalContado,Diferencia,IdArqueoAnterior,Caja,Usuario) "
            "OUTPUT INSERTED.IdArqueo VALUES (?,?,?,?,?,?,?,?)",
            (*params, db.CAJAS[caja], user),
        )
    for d in body.denominaciones:
        db.write(
            "INSERT INTO dbo.ArqueoDenominaciones (IdArqueo,Denominacion,Cantidad) VALUES (?,?,?)",
            (id_arqueo, d.valor, d.cantidad),
        )
    return detalle(caja, id_arqueo)


@atomic_reconciliation
def confirmar(caja, id_arqueo, body, user):
    a = detalle(caja, id_arqueo)
    if a["estado"] == "Confirmado":
        return a
    if (
        a["estado"] != "Borrador"
        or a["version"] != body.versionEsperada
        or a["previewVersion"] != body.previewVersion
    ):
        raise ConflictoCaja("El arqueo o el saldo cambió. Revisá el recuento.")
    delta = Decimal(a["diferenciaVigenteDecimal"])
    if delta and not body.aceptarDiferencia:
        raise ConflictoCaja("Confirmá expresamente la diferencia de arqueo.")
    # The adjustment belongs to end-of-cutoff. Refuse an obsolete partial cutoff,
    # since a physical count cannot certify cash movements excluded on the same day.
    last = db.one(
        "SELECT ISNULL(MAX(IdMovimiento),0) secuencia FROM dbo.MovimientosCajaEfectivo "
        "WHERE Caja=? AND CAST(Fecha AS date)<=?",
        (db.CAJAS[caja], a["fechaCorte"]),
    )["secuencia"]
    if last != a["secuenciaCorte"]:
        raise ConflictoCaja("Hay movimientos al corte no incluidos. Actualizá el borrador.")
    context = db.caja_context(caja, date.fromisoformat(a["fechaCorte"]))
    warnings = set()
    if context["minimoPosterior"] + delta < 0:
        warnings.add("SALDO_NEGATIVO")
    if context["arqueos"]:
        warnings.add("PERIODO_ARQUEADO")
    if not warnings.issubset(body.advertenciasAceptadas):
        raise ConflictoCaja(
            "El ajuste afecta saldo negativo o período arqueado; confirmá las advertencias."
        )
    id_op = None
    if delta:
        request = {
            "tipo": "diferencia_arqueo",
            "caja": caja,
            "fecha": a["fechaCorte"],
            "importe": f"{abs(delta):.2f}",
            "ajusteFirmado": f"{delta:.2f}",
            "idArqueo": id_arqueo,
            "concepto": f"Diferencia de arqueo {id_arqueo}",
        }
        id_op = db.insert(
            "INSERT INTO dbo.OperacionesCajaEfectivo "
            "(ClaveIdempotencia,HuellaSolicitud,Tipo,Fecha,Concepto,Cuenta,Solicitud,Contexto,Usuario) "
            "OUTPUT INSERTED.IdOperacion VALUES (?,?,'diferencia_arqueo',?,?,'A',?,?,?)",
            (
                str(uuid4()),
                huella(request),
                a["fechaCorte"],
                f"Arqueo {id_arqueo}",
                db.dumps(request),
                db.dumps({"preview": a["previewVersion"]}),
                user,
            ),
        )
        db.insert(
            "INSERT INTO dbo.MovimientosCajaEfectivo "
            "(Caja,Fecha,Concepto,Importe,Cuenta,Usuario,IdOperacionCaja,Tipo) "
            "OUTPUT INSERTED.IdMovimiento VALUES (?,DATEADD(second,86399,CAST(? AS datetime2)),?,?,'A',?,?,'diferencia_arqueo')",
            (
                db.CAJAS[caja],
                a["fechaCorte"],
                f"Diferencia de arqueo {id_arqueo}",
                delta,
                user,
                id_op,
            ),
        )
        db.stale_arqueos([caja], a["fechaCorte"], user)
    db.write(
        "UPDATE dbo.ArqueosCajaEfectivo SET Estado='Confirmado',SaldoSistema=?,Diferencia=?,"
        "IdOperacionAjuste=?,UsuarioConfirmacion=?,FechaConfirmacion=SYSUTCDATETIME(),Version=Version+1 "
        "WHERE IdArqueo=?",
        (Decimal(a["saldoRecalculadoDecimal"]), delta, id_op, user, id_arqueo),
    )
    return detalle(caja, id_arqueo)
