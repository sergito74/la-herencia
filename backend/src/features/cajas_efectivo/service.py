"""Coordinador transaccional de caja 038. Ningún adaptador confirma por separado."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from src.db.connection import atomic_reconciliation
from src.features.cajas_efectivo import operaciones as db
from src.features.cajas_efectivo.schemas import OperacionCaja
from src.features.cuentas_socios import valuacion


class ConflictoCaja(ValueError):
    pass


class NoExisteCaja(ValueError):
    pass


def huella(value):
    return hashlib.sha256(db.dumps(value).encode("utf-8")).hexdigest()


def _caja_particular(socio):
    return {
        1: "Particular S",
        2: "Particular L",
        3: "Particular Condominio",
        4: "Particular C",
    }.get(socio, f"Particular {socio}")


def piernas(op):
    positive = op.tipo in ("cobro", "aporte", "extraccion_banco", "retorno_sueldo_opcion_a", "ingreso_dolares")
    result = {op.caja: op.importe if positive else -op.importe}
    target = op.cajaDestino or op.cajaContraparte
    if target:
        result[target] = -result[op.caja]
    return result


def _validar_documentos(op):
    from src.features.aplicaciones_pago import repository as aplicaciones
    from src.features.vinculos import fuente

    result = []
    for a in op.aplicaciones:
        if a.tipoDocumento == "CompraDeuda":
            doc = db.one(
                "SELECT c.IdContacto contacto,c.Moneda moneda,c.[Tipo de Cambio] tc,c.Fecha fechaCompra,"
                "pa.cp importeParticular FROM dbo.Compras c OUTER APPLY "
                "(SELECT SUM(d.Cantidad*d.[Precio Unitario]*(1+ISNULL(d.IVA,0)/100.0)) cp "
                "FROM dbo.Det_Compras d WHERE d.IdCompra=c.IdDeuda AND d.Cantidad*d.[Precio Unitario]<0 "
                "AND d.[Producto/Servicio] LIKE '%particular%') pa WHERE c.IdDeuda=?",
                (a.idDocumento,),
            )
        elif a.tipoDocumento == "VentaHacienda":
            doc = db.one(
                "SELECT IdConsignatario contacto FROM dbo.[Venta Hacienda] WHERE IdVenta=?",
                (a.idDocumento,),
            )
        elif a.tipoDocumento == "VentaGranos":
            doc = db.one(
                "SELECT IdConsignatario contacto FROM dbo.[Venta Granos] WHERE IdVenta=?",
                (a.idDocumento,),
            )
        else:
            doc = db.one(
                "SELECT a.IdContacto contacto,d.Estado estado,d.[Importe Cuota] total "
                "FROM dbo.[Detalle Cobro Alquiler] d JOIN dbo.Alquileres a ON a.IdAlquiler=d.IdAlquiler "
                "WHERE d.IdCobroAlquiler=?",
                (a.idDocumento,),
            )
        if not doc or doc["contacto"] != op.idContacto:
            raise ValueError(
                f"Documento {a.tipoDocumento}/{a.idDocumento} no pertenece al contacto."
            )
        if doc.get("moneda") == "Dolares" and (not doc.get("tc") or doc["tc"] <= 0):
            raise ValueError("El comprobante en dólares requiere un tipo de cambio válido.")
        total = Decimal(str(aplicaciones._importe_total_documento(a.tipoDocumento, a.idDocumento)))
        if op.compraParticular and op.compraParticular.idCompra == a.idDocumento:
            from src.features.compras.particular import importe_bruto_compra_particular

            bruto = importe_bruto_compra_particular(a.idDocumento)
            if bruto is None:
                raise ValueError("La compra no tiene parte particular documentada.")
            total = Decimal(str(bruto))
            if doc.get("moneda") == "Dolares":
                if not doc.get("tc") or doc["tc"] <= 0:
                    raise ValueError("La compra particular en dólares requiere TC del comprobante.")
                total *= Decimal(str(doc["tc"]))
        paid = Decimal(
            str(
                fuente.pagado_de_documentos([(a.tipoDocumento, a.idDocumento)])[
                    (a.tipoDocumento, a.idDocumento)
                ]
            )
        )
        if a.tipoDocumento == "Alquiler" and doc.get("estado") == "Cobrado" and paid == 0:
            raise ConflictoCaja(
                "La cuota figura cobrada históricamente; revisar su origen antes de aplicar otro cobro."
            )
        total = total.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        paid = paid.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        if a.importeAplicado > total - paid:
            raise ConflictoCaja(f"Documento {a.idDocumento}: aplicación supera saldo disponible.")
        if doc.get("importeParticular") and not op.compraParticular:
            assigned = db.one(
                "SELECT IdMovimiento FROM dbo.MovimientosCuentaSocio "
                "WHERE Origen='CompraParticular' AND IdOrigen=? AND Anulada=0",
                (a.idDocumento,),
            )
            note = db.one(
                "SELECT TOP 1 p.IdPagoEfectivo FROM dbo.vw_PagosEfectivoVigentes p "
                "JOIN dbo.EfectosOperacionCaja e ON e.IdRegistro=p.IdPagoEfectivo AND e.TipoEfecto='PagoEfectivo' "
                "JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion=e.IdOperacion "
                "WHERE p.IdContacto=? AND p.[Importe imputado]<0 AND p.Caja LIKE 'Particular%' "
                "AND JSON_VALUE(o.Solicitud,'$.compraParticular.idCompra')=?",
                (op.idContacto, str(a.idDocumento)),
            )
            if not assigned or not note:
                raise ValueError(
                    "La factura tiene parte particular: marcá compra particular y elegí el socio."
                )
            doc["soporteParticular"] = {
                "socio": assigned["IdMovimiento"],
                "asiento": note["IdPagoEfectivo"],
            }
        result.append(
            {
                "tipo": a.tipoDocumento,
                "id": a.idDocumento,
                "total": total,
                "pagado": paid,
                "origen": doc,
            }
        )
    return result


def _references(op):
    context = {}
    if op.idContacto and not db.one(
        "SELECT IdContacto FROM dbo.Contactos WHERE IdContacto=?", (op.idContacto,)
    ):
        raise ValueError("Contacto inexistente.")
    if op.idSocio:
        if not db.one("SELECT IdSocio FROM dbo.Socios WHERE IdSocio=?", (op.idSocio,)):
            raise ValueError("Socio inexistente.")
    if op.tipo in ("aporte", "retiro_a_cuenta") or (
        op.tipo == "pago" and op.caja == "condominio-lsc"
    ):
        context["valuacion"] = (valuacion.dolares_a_fecha(op.importe, op.fecha)
                                if op.caja == "giamigli-dolares" else valuacion.a_fecha(op.importe, op.fecha))
    if op.aplicaciones:
        context["documentos"] = _validar_documentos(op)
    if op.compraParticular:
        from src.features.compras.particular import importe_personal_compra_particular

        cp = op.compraParticular
        if not db.one("SELECT IdSocio FROM dbo.Socios WHERE IdSocio=?", (cp.idSocio,)):
            raise ValueError("Socio de compra particular inexistente.")
        amount = importe_personal_compra_particular(cp.idCompra)
        doc_meta = next(d["origen"] for d in context["documentos"] if d["id"] == cp.idCompra)
        if amount is not None and doc_meta.get("moneda") == "Dolares":
            amount = Decimal(str(amount)) * Decimal(str(doc_meta["tc"]))
        if amount is None or Decimal(str(amount)) <= 0:
            raise ValueError("La compra no tiene una parte particular respaldada.")
        amount = Decimal(str(amount))
        amount = amount.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        source_date = doc_meta.get("fechaCompra") or op.fecha
        source_date = (
            source_date.date()
            if isinstance(source_date, datetime)
            else date.fromisoformat(str(source_date)[:10])
        )
        previous = db.one(
            "SELECT IdMovimiento,IdSocio,Anulada,Importe,ImporteUSD,ImporteKgCarne FROM dbo.MovimientosCuentaSocio "
            "WHERE Origen='CompraParticular' AND IdOrigen=? AND Anulada=0",
            (cp.idCompra,),
        )
        if previous and previous["IdSocio"] != cp.idSocio:
            raise ConflictoCaja("La compra está asignada a otro socio.")
        context["particular"] = {
            "importe": amount,
            "asignacion": previous,
            "valuacion": valuacion.a_fecha(amount, source_date),
            "fechaCompra": source_date,
        }
        if previous and 'ImporteUSD' in previous:
            context['particular']['valuacion'] = {
                'importeUSD': previous['ImporteUSD'], 'importeKgCarne': previous['ImporteKgCarne'],
            }
            context['particular']['preexistente'] = True
        candidates = db.read(
            "SELECT p.IdPagoEfectivo,p.Caja,p.Fecha,p.[Importe imputado] importe,"
            "CASE WHEN EXISTS (SELECT 1 FROM dbo.EfectosOperacionCaja e "
            "JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion=e.IdOperacion "
            "WHERE e.TipoEfecto='PagoEfectivo' AND e.IdRegistro=p.IdPagoEfectivo "
            "AND JSON_VALUE(o.Solicitud,'$.compraParticular.idCompra')=?) THEN 1 ELSE 0 END formal "
            "FROM dbo.vw_PagosEfectivoVigentes p WHERE p.IdContacto=? AND p.Caja LIKE ? "
            "AND (CAST(p.Fecha AS date)=? OR p.[Numero documento]=?) AND p.[Importe imputado]=?",
            (str(cp.idCompra), op.idContacto, "Particular%", op.fecha, cp.idCompra, -amount),
        )
        if cp.idAsientoParticular:
            chosen = [x for x in candidates if x["IdPagoEfectivo"] == cp.idAsientoParticular]
            if len(chosen) != 1:
                raise ConflictoCaja(
                    "El asiento particular seleccionado no coincide con proveedor/fecha/importe."
                )
            context["particular"]["asiento"] = chosen[0]
        elif len([x for x in candidates if x["formal"]]) == 1:
            context["particular"]["asiento"] = next(x for x in candidates if x["formal"])
        elif candidates and not cp.confirmarAsientoNuevo:
            raise ConflictoCaja(
                "Hay asientos particulares posibles; seleccionar el existente o confirmar que es otro."
            )
        else:
            context["particular"]["asiento"] = None
    for rep in op.repartos:
        for value, table, key in (
            (rep.idRubro, "dbo.Rubros", "IdRubro"),
            (rep.idCentroCostos, "dbo.[Centro de costos]", "IdCentro"),
            (rep.idDestino, "dbo.DestinoCompras", "IdDestino"),
            (rep.idCampania, "dbo.Campañas", "IdCampaña"),
        ):
            if value and not db.one(f"SELECT {key} FROM {table} WHERE {key}=?", (value,)):
                raise ValueError(f"Referencia de reparto inválida: {key}.")
        if rep.idLote:
            raise ValueError(
                "La referencia de lote requiere verificar su relación productiva antes de habilitarse."
            )
    if op.banco:
        from src.features.traspasos_internos_tesoreria import repository as transfers
        from src.features.tesoreria import estado_resolucion

        bank = transfers._movimiento_referencia(op.banco.medio, op.banco.idMovimiento)
        if abs(Decimal(str(bank["importe"]))) != op.importe:
            raise ValueError("El importe no coincide con el movimiento bancario.")
        expected_sign = -1 if op.tipo != "deposito_banco" else 1
        if Decimal(str(bank["importe"])) * expected_sign <= 0:
            raise ValueError("El signo bancario no corresponde a extracción/depósito.")
        active = db.one(
            "SELECT b.IdOperacion FROM dbo.BancoOperacionCaja b JOIN dbo.OperacionesCajaEfectivo o "
            "ON o.IdOperacion=b.IdOperacion WHERE b.Medio=? AND b.IdMovimiento=? AND o.Estado='Vigente'",
            (op.banco.medio, op.banco.idMovimiento),
        )
        state = estado_resolucion.esta_resuelto(op.banco.medio, op.banco.idMovimiento)
        if active or state not in ("sin_conciliar", "ya_reconocido"):
            raise ConflictoCaja("El movimiento bancario ya está vinculado o conciliado.")
        dependencies = db.read(
            "SELECT IdAplicacion FROM dbo.AplicacionesPago WHERE OrigenMovimiento=? "
            "AND IdMovimientoOrigen=? AND Anulada=0",
            (op.banco.medio, op.banco.idMovimiento),
        )
        conciliations = db.read(
            "SELECT IdConciliacion FROM dbo.ConciliacionesTesoreria "
            "WHERE Medio=? AND IdMovimiento=?",
            (op.banco.medio, op.banco.idMovimiento),
        )
        if dependencies or conciliations:
            raise ConflictoCaja(
                "El banco tiene aplicaciones/conciliaciones ajenas; resolverlas antes del traspaso."
            )
        if state == "ya_reconocido" and not op.evidencia:
            raise ValueError(
                "El banco está en una cuenta de contacto: indicar evidencia del traspaso."
            )
        bank["estadoPrevio"] = state
        bank["cuentasExcluidas"] = db.read(
            "SELECT IdContacto,Origen,IdOrigen,Deuda,Credito "
            "FROM dbo.vw_MovimientosCuenta_Base WHERE "
            "Origen=? AND IdOrigen=?",
            (
                {"bna": "Banco Nacion", "galicia": "Galicia", "mercado-libre": "Mercado Pago"}[
                    op.banco.medio
                ],
                op.banco.idMovimiento,
            ),
        )
        context["banco"] = bank
    if op.tipo == "retorno_sueldo_opcion_a":
        from src.features.remuneraciones.repository import _IMPORTE_SQL

        salary = db.one(
            f"SELECT r.IdContacto contacto,r.[Fecha de pago] fecha,r.[Periodo liquidado] periodo,"
            f"({_IMPORTE_SQL}) total FROM dbo.Remuneraciones r WHERE r.IdSalario=?",
            (op.idSalario,),
        )
        if not salary or salary["contacto"] != 375 or salary["total"] != op.importe:
            raise ValueError(
                "Opción A: requiere liquidación completa de Sergio empleado por el mismo importe."
            )
        existing = db.read(
            "SELECT a.IdAjuste,a.Importe FROM dbo.AjustesCuentaCorriente a WHERE a.IdContacto=375 "
            "AND a.Motivo LIKE ? AND NOT EXISTS (SELECT 1 FROM dbo.EfectosOperacionCaja e "
            "JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion=e.IdOperacion "
            "WHERE e.TipoEfecto='AjusteNoCobrado' AND e.IdRegistro=a.IdAjuste "
            "AND e.EsCreadoPorOperacion=1 AND o.Estado='Anulada')",
            (f"%IdSalario {op.idSalario})%",),
        )
        if existing:
            raise ConflictoCaja(
                "La liquidación ya tiene un ajuste de no cobrado; vincular la historia sin duplicarla."
            )
        salary_apps = db.read(
            "SELECT IdConciliacion FROM dbo.ConciliacionesTesoreria "
            "WHERE TipoOrigenDocumento='Remuneraciones' AND IdOrigenDocumento=?",
            (op.idSalario,),
        )
        if salary_apps:
            raise ConflictoCaja("La liquidación tiene pagos vinculados. Revisar antes de opción A.")
        if (
            salary["fecha"].year in (2017, 2018)
            and salary["fecha"].date().isoformat() >= "2017-11-01"
        ):
            raise ConflictoCaja(
                "Período histórico con pares de socio: conservar tratamiento 036 y revisar vínculos."
            )
        context["salario"] = salary
    return context


def previsualizar(op: OperacionCaja):
    context = _references(op)
    context["cajas"] = {box: db.caja_context(box, op.fecha) for box in sorted(piernas(op))}
    warnings = []
    for box, amount in piernas(op).items():
        current = context["cajas"][box]
        if box != "condominio-lsc" and current["minimoPosterior"] + amount < 0:
            warnings.append("SALDO_NEGATIVO")
        if current["arqueos"]:
            warnings.append("PERIODO_ARQUEADO")
    return {
        "previewVersion": huella({"operacion": op.model_dump(mode="json"), "contexto": context}),
        "advertencias": sorted(set(warnings)),
        "contexto": context,
        "efectosPrevistos": [
            {
                "caja": box,
                "importe": f"{amount:.2f}",
                "saldoResultante": f"{context['cajas'][box]['saldoActual'] + amount:.2f}",
            }
            for box, amount in piernas(op).items()
        ],
    }


def _socio(
    id_op,
    op,
    user,
    socio,
    tipo,
    valuation,
    origin="Caja038",
    id_origin=None,
    importe=None,
    fecha=None,
):
    id_mov = db.insert(
        "INSERT INTO dbo.MovimientosCuentaSocio "
        "(IdSocio,Tipo,Importe,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,ImporteUSD,ImporteKgCarne) "
        "OUTPUT INSERTED.IdMovimiento VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            socio,
            tipo,
            importe if importe is not None else valuation.get("importePesos", op.importe),
            fecha if fecha is not None else op.fecha,
            origin,
            id_origin or id_op,
            "Efectivo USD" if op.caja == "giamigli-dolares" else "Efectivo",
            op.concepto,
            user,
            valuation["importeUSD"],
            valuation["importeKgCarne"],
        ),
    )
    db.effect(id_op, "MovimientoSocio", id_mov)
    db.write(
        "INSERT INTO dbo.AuditoriaReflejoSocio (Accion,IdMovimiento,IdSocio,Usuario,Detalle) VALUES (?,?,?,?,?)",
        (
            "Asignacion" if tipo == "AsignacionGasto" else "Devolucion",
            id_mov,
            socio,
            user,
            op.concepto,
        ),
    )
    return id_mov


def _aplicar(id_op, op, user, context):
    payment = None
    if op.tipo in ("pago", "cobro"):
        payment = db.payment(id_op, op, op.importe if op.tipo == "pago" else -op.importe)
        # Capacity/contact already checked under the same transaction. Keep Decimal,
        # including a particular document whose fiscal net excludes its personal part.
        for a in op.aplicaciones:
            app = db.insert(
                "INSERT INTO dbo.AplicacionesPago "
                "(OrigenMovimiento,IdMovimientoOrigen,TipoDocumento,IdDocumentoAplicado,"
                "ImporteAplicado,Usuario) OUTPUT INSERTED.IdAplicacion VALUES (?,?,?,?,?,?)",
                ("efectivo", payment, a.tipoDocumento, a.idDocumento, a.importeAplicado, user),
            )
            db.effect(id_op, "Aplicacion", app)
        if not op.compraParticular:
            for doc in context.get("documentos", []):
                support = doc["origen"].get("soporteParticular")
                if support:
                    db.effect(id_op, "MovimientoSocio", support["socio"], False)
                    db.effect(id_op, "AsientoParticular", support["asiento"], False)
        if op.caja == "condominio-lsc" and op.tipo == "pago":
            _socio(id_op, op, user, 3, "Devolucion", context["valuacion"])
        if op.compraParticular:
            cp = op.compraParticular
            previous = context["particular"]["asignacion"]
            if previous:
                db.effect(id_op, "MovimientoSocio", previous["IdMovimiento"], False)
            else:
                _socio(
                    id_op,
                    op,
                    user,
                    cp.idSocio,
                    "AsignacionGasto",
                    context["particular"]["valuacion"],
                    "CompraParticular",
                    cp.idCompra,
                    context["particular"]["importe"],
                    context["particular"]["fechaCompra"],
                )
            # Particular: the negative line already exists in the original document.
            # Explicit linked compensating entry restores its supplier amount, once.
            prior = context["particular"]["asiento"]
            if prior:
                db.effect(id_op, "AsientoParticular", prior["IdPagoEfectivo"], False)
            else:
                id_part = db.insert(
                    "INSERT INTO dbo.[Pagos efectivo] "
                    "(IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,"
                    "[Numero documento],[Importe imputado]) OUTPUT INSERTED.IdPagoEfectivo "
                    "VALUES (?,2,NULL,?,?,?,?,?)",
                    (
                        op.idContacto,
                        op.fecha,
                        op.cuenta,
                        _caja_particular(cp.idSocio),
                        cp.idCompra,
                        -context["particular"]["importe"],
                    ),
                )
                db.effect(id_op, "PagoEfectivo", id_part)
    elif op.tipo in ("aporte", "retiro_a_cuenta"):
        _socio(
            id_op,
            op,
            user,
            op.idSocio,
            "Devolucion" if op.tipo == "aporte" else "AsignacionGasto",
            context["valuacion"],
        )
    elif op.tipo == "gasto_sin_comprobante":
        id_gasto = db.insert(
            "INSERT INTO dbo.GastoCajaEfectivo "
            "(IdOperacion,Fecha,Concepto,ImportePesos,Usuario) OUTPUT INSERTED.IdGasto VALUES (?,?,?,?,?)",
            (id_op, op.fecha, op.concepto, op.importe, user),
        )
        db.effect(id_op, "GastoCaja", id_gasto)
        for rep in op.repartos:
            db.write(
                "INSERT INTO dbo.RepartosGastoCaja "
                "(IdGasto,IdRubro,IdCentroCostos,IdDestino,IdCampania,IdLote,ImportePesos) VALUES (?,?,?,?,?,?,?)",
                (
                    id_gasto,
                    rep.idRubro,
                    rep.idCentroCostos,
                    rep.idDestino,
                    rep.idCampania,
                    rep.idLote,
                    rep.importePesos,
                ),
            )
    if op.banco:
        # Explicit bridge in the existing treasury book, not another cash-box entry.
        bridge = db.payment(id_op, op, -next(iter(piernas(op).values())))
        payment = bridge
        db.write(
            "INSERT INTO dbo.BancoOperacionCaja (IdOperacion,Medio,IdMovimiento) VALUES (?,?,?)",
            (id_op, op.banco.medio, op.banco.idMovimiento),
        )
        event = db.insert(
            "INSERT INTO dbo.TraspasosInternosTesoreria "
            "(MedioA,IdMovimientoA,MedioB,IdMovimientoB,Accion,Usuario) "
            "OUTPUT INSERTED.IdEvento VALUES (?,?,'efectivo',?,'Vincular',?)",
            (op.banco.medio, op.banco.idMovimiento, bridge, user),
        )
        db.effect(id_op, "TraspasoTesoreria", event)
    if op.tipo == "retorno_sueldo_opcion_a":
        salary = context["salario"]
        adjustment = db.insert(
            "INSERT INTO dbo.AjustesCuentaCorriente "
            "(IdContacto,Fecha,Lado,Importe,Motivo,Usuario) "
            "OUTPUT INSERTED.IdAjuste VALUES (375,?,'Credito',?,?,?)",
            (
                salary["fecha"],
                op.importe,
                f"Sueldo {salary['periodo']} no cobrado, retorno documentado (IdSalario {op.idSalario})",
                user,
            ),
        )
        db.effect(id_op, "AjusteNoCobrado", adjustment)
    for box, amount in piernas(op).items():
        db.cash(id_op, op, box, amount, user, payment if box == op.caja else None)
    db.stale_arqueos(piernas(op), op.fecha, user)


def _bloquear(op):
    """Range locks also protect against writers that do not use our applock."""
    for box in sorted(piernas(op)):
        db.read(
            "SELECT IdMovimiento FROM dbo.MovimientosCajaEfectivo WITH (UPDLOCK,HOLDLOCK) WHERE Caja=?",
            (db.CAJAS[box],),
        )
    for app in sorted(op.aplicaciones, key=lambda a: (a.tipoDocumento, a.idDocumento)):
        db.read(
            "SELECT IdAplicacion FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) "
            "WHERE TipoDocumento=? AND IdDocumentoAplicado=?",
            (app.tipoDocumento, app.idDocumento),
        )
    if op.banco:
        db.read(
            "SELECT IdConciliacion FROM dbo.ConciliacionesTesoreria WITH (UPDLOCK,HOLDLOCK) "
            "WHERE Medio=? AND IdMovimiento=?",
            (op.banco.medio, op.banco.idMovimiento),
        )
        db.read(
            "SELECT IdAplicacion FROM dbo.AplicacionesPago WITH (UPDLOCK,HOLDLOCK) "
            "WHERE OrigenMovimiento=? AND IdMovimientoOrigen=?",
            (op.banco.medio, op.banco.idMovimiento),
        )


@atomic_reconciliation
def crear(body, key, user):
    if not user or len(user) > 60:
        raise ValueError("Usuario de sesión inválido.")
    op = body.operacion
    fingerprint = huella(op.model_dump(mode="json"))
    previous = db.find_key(key)
    if previous:
        if previous["HuellaSolicitud"] != fingerprint:
            raise ConflictoCaja("La clave idempotente ya se usó con otro contenido.")
        return db.detail(previous["IdOperacion"]), False
    _bloquear(op)
    preview = previsualizar(op)
    if preview["previewVersion"] != body.previewVersion:
        raise ConflictoCaja("Cambió el contexto. Volvé a previsualizar la operación.")
    if not set(preview["advertencias"]).issubset(body.advertenciasAceptadas):
        raise ConflictoCaja("Confirmá las advertencias vigentes antes de guardar.")
    id_op = db.create_operation(key, fingerprint, op, preview["contexto"], user)
    _aplicar(id_op, op, user, preview["contexto"])
    return db.detail(id_op), True


@atomic_reconciliation
def anular(id_op, body, user):
    op = db.get_operation(id_op)
    if not op:
        raise NoExisteCaja("Operación inexistente.")
    if op["Estado"] == "Anulada":
        return db.detail(id_op)
    if op["Version"] != body.versionEsperada:
        raise ConflictoCaja("La operación cambió. Actualizá antes de anular.")
    raw_request = json.loads(op["Solicitud"])
    if raw_request["tipo"] != "diferencia_arqueo":
        _bloquear(OperacionCaja.model_validate(raw_request))
    preview = previsualizar_anulacion(id_op)
    if body.previewVersion and body.previewVersion != preview['previewVersion']:
        raise ConflictoCaja('Cambió el contexto de la anulación. Revisá sus efectos nuevamente.')
    if preview['advertencias'] and (body.previewVersion != preview['previewVersion'] or
                                  not set(preview['advertencias']).issubset(body.advertenciasAceptadas)):
        raise ConflictoCaja('La anulación afecta saldo negativo o período arqueado. Revisá y confirmá sus advertencias.')
    effects = db.effects(id_op)
    own_apps = {
        e["IdRegistro"]
        for e in effects
        if e["TipoEfecto"] == "Aplicacion" and e["EsCreadoPorOperacion"]
    }
    if raw_request.get("compraParticular") and any(
        e["TipoEfecto"] == "MovimientoSocio" and e["EsCreadoPorOperacion"] for e in effects
    ):
        from src.features.vinculos import fuente

        cp_id = raw_request["compraParticular"]["idCompra"]
        total_paid = Decimal(
            str(fuente.pagado_de_documentos([("CompraDeuda", cp_id)])[("CompraDeuda", cp_id)])
        )
        own_paid = sum(
            (Decimal(str(a["importeAplicado"])) for a in raw_request["aplicaciones"]), Decimal(0)
        )
        if total_paid > own_paid:
            raise ConflictoCaja(
                "La parte particular respalda otros pagos de la factura. Revertí primero sus operaciones dependientes."
            )
    for e in effects:
        if e["TipoEfecto"] == "PagoEfectivo" and e["EsCreadoPorOperacion"]:
            others = db.read(
                "SELECT IdAplicacion FROM dbo.AplicacionesPago WHERE OrigenMovimiento='efectivo' "
                "AND IdMovimientoOrigen=? AND Anulada=0",
                (e["IdRegistro"],),
            )
            extra = [x["IdAplicacion"] for x in others if x["IdAplicacion"] not in own_apps]
            if extra:
                raise ConflictoCaja(f"Hay aplicaciones posteriores ajenas: {extra}.")
            external = db.read(
                "SELECT 'Reasignacion' tipo,IdReasignacion id FROM dbo.ReasignacionesContacto "
                "WHERE Origen='Pagos efectivo' AND IdOrigen=? UNION ALL "
                "SELECT 'Conciliacion',IdConciliacion FROM dbo.ConciliacionesTesoreria "
                "WHERE Medio='efectivo' AND IdMovimiento=? UNION ALL "
                "SELECT 'PagoTarjeta',IdPago FROM dbo.Tarjetas_Resumenes_Pagos "
                "WHERE Origen='efectivo' AND IdMovimientoOrigen=?",
                (e["IdRegistro"], e["IdRegistro"], e["IdRegistro"]),
            )
            if external:
                raise ConflictoCaja(f"El efectivo tiene vínculos posteriores ajenos: {external}.")
        if e["TipoEfecto"] == "MovimientoSocio" and e["EsCreadoPorOperacion"]:
            from src.features.impuestos import particular

            try:
                particular.guardia_movimiento(e["IdRegistro"])
            except particular.ErrorParticular as exc:
                raise ConflictoCaja(exc.mensaje) from exc
            except Exception as exc:  # tablas 041 todavía no creadas
                if "Invalid object name" not in str(exc):
                    raise
            linked = db.read(
                "SELECT IdMovimientoSocio id,IdContacto contacto FROM dbo.PagosSocioProveedor "
                "WHERE IdMovimientoSocio=?",
                (e["IdRegistro"],),
            )
            if linked:
                raise ConflictoCaja(
                    f"El movimiento de socio tiene vínculos de proveedor posteriores: {linked}."
                )
    from src.features.aplicaciones_pago import repository as apps
    from src.features.cuentas_socios import repository as socios
    from src.features.traspasos_internos_tesoreria import repository as transfers

    for e in effects:
        if not e["EsCreadoPorOperacion"]:
            continue
        kind, ref = e["TipoEfecto"], e["IdRegistro"]
        if kind == "Aplicacion":
            current = db.one(
                "SELECT Anulada FROM dbo.AplicacionesPago WHERE IdAplicacion=?", (ref,)
            )
            if current and not current["Anulada"]:
                apps.anular_aplicacion(ref, body.motivo, user)
        elif kind == "MovimientoSocio":
            current = db.one(
                "SELECT Anulada FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento=?", (ref,)
            )
            if current and not current["Anulada"]:
                socios.anular_movimiento(ref, body.motivo, user, desde_operacion_caja=True)
        elif kind == "GastoCaja":
            db.write(
                "UPDATE dbo.GastoCajaEfectivo SET Anulada=1,MotivoAnulacion=?,UsuarioAnulacion=?,"
                "FechaAnulacion=SYSUTCDATETIME() WHERE IdGasto=?",
                (body.motivo, user, ref),
            )
        elif kind == "TraspasoTesoreria":
            event = db.one("SELECT * FROM dbo.TraspasosInternosTesoreria WHERE IdEvento=?", (ref,))
            active = transfers.vinculo_activo(event["MedioA"], event["IdMovimientoA"])
            if not active or active["IdEvento"] != ref:
                raise ConflictoCaja(f"El vínculo bancario {ref} cambió por fuera de la operación.")
            transfers.deshacer(event["MedioA"], event["IdMovimientoA"], user)
    db.write("UPDATE dbo.MovimientosCajaEfectivo SET Anulada=1 WHERE IdOperacionCaja=?", (id_op,))
    db.write(
        "UPDATE dbo.OperacionesCajaEfectivo SET Estado='Anulada',Version=Version+1,"
        "MotivoAnulacion=?,UsuarioAnulacion=?,FechaAnulacion=SYSUTCDATETIME() WHERE IdOperacion=?",
        (body.motivo, user, id_op),
    )
    db.write(
        "UPDATE dbo.ArqueosCajaEfectivo SET Estado='Invalidado',Version=Version+1,"
        "MotivoInvalidacion=?,UsuarioInvalidacion=?,FechaInvalidacion=SYSUTCDATETIME() "
        "WHERE IdOperacionAjuste=?",
        (body.motivo, user, id_op),
    )
    request_data = json.loads(op["Solicitud"])
    if request_data["tipo"] == "diferencia_arqueo":
        from datetime import date

        db.stale_arqueos([request_data["caja"]], date.fromisoformat(request_data["fecha"]), user)
    else:
        request = OperacionCaja.model_validate(request_data)
        db.stale_arqueos(piernas(request), request.fecha, user)
    return db.detail(id_op)


def previsualizar_anulacion(id_op):
    operation = db.get_operation(id_op)
    if not operation:
        raise NoExisteCaja('Operación inexistente.')
    if operation['Estado'] == 'Anulada':
        return None
    raw = json.loads(operation['Solicitud'])
    when = date.fromisoformat(raw['fecha'])
    boxes = [raw['caja']] if raw['tipo'] == 'diferencia_arqueo' else sorted(piernas(OperacionCaja.model_validate(raw)))
    contexts = {box: db.caja_context(box, when, excluir_operacion=id_op) for box in boxes}
    warnings = set()
    for box, context in contexts.items():
        if context.get('movimientosExcluidos', 1) == 0:
            raise ConflictoCaja('El movimiento físico ya cambió fuera de la operación; revisar sus vínculos.')
        if box != 'condominio-lsc' and context['minimoPosterior'] < 0:
            warnings.add('SALDO_NEGATIVO')
        if context['arqueos']:
            warnings.add('PERIODO_ARQUEADO')
    return {'previewVersion': huella({'id':id_op,'version':operation['Version'],'cajas':contexts}),
            'advertencias': sorted(warnings),
            'efectosPrevistos': [{'caja':box,'saldoResultante':f"{c['saldoActual']:.2f}"} for box,c in contexts.items()]}
