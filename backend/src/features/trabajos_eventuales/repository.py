"""Trabajos y distribución operativa; nunca crea deuda salarial ni pagos."""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import atomic_reconciliation, execute_insert_returning_id, execute_write, fetch_all, fetch_one
from src.features.remuneraciones import repository as salarios
from src.features.trabajos_eventuales.schemas import TrabajoInput

CENTAVO = Decimal("0.01")


def dinero(v):
    return Decimal(str(v or 0)).quantize(CENTAVO, ROUND_HALF_UP)


def total_trabajo(dias, jornal, viaticos=0, redondeo=0):
    resultado = dinero(Decimal(str(dias)) * Decimal(str(jornal)) + Decimal(str(viaticos))) + dinero(redondeo)
    if resultado > Decimal("9999999999999999.99"):
        raise ValueError("El total del trabajo es demasiado grande")
    if resultado <= 0:
        raise ValueError("El total del trabajo debe ser mayor que cero")
    return resultado


BASE = """FROM dbo.TrabajosEventuales t JOIN dbo.Contactos c ON c.IdContacto=t.IdContacto
OUTER APPLY (SELECT SUM(v.Importe) AS Vinculado FROM dbo.TrabajosEventualesVinculos v WHERE v.IdTrabajo=t.IdTrabajo) s
OUTER APPLY (SELECT COUNT(*) AS Hay, SUM(CASE WHEN p.Medio<>'caja' OR o.Estado<>'Anulada' THEN p.Importe END) AS Pagado
             FROM dbo.TrabajosEventualesPagos p LEFT JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion=p.IdOperacion
             WHERE p.IdTrabajo=t.IdTrabajo) pg"""
COLS = """t.IdTrabajo AS idTrabajo,t.IdContacto AS idContacto,c.[Razon Social] AS trabajador,t.Fecha AS fecha,
t.Descripcion AS descripcion,t.Dias AS dias,t.Jornal AS jornal,t.Viaticos AS viaticos,t.Redondeo AS redondeo,
t.Total AS total,CASE WHEN pg.Hay=0 THEN t.EstadoPago WHEN ISNULL(pg.Pagado,0)>=t.Total THEN 'Pagado' ELSE 'Pendiente' END AS estadoPago,t.NumeroRecibo AS numeroRecibo,t.Observaciones AS observaciones,
ISNULL(s.Vinculado,0) AS vinculado,t.Total-ISNULL(s.Vinculado,0) AS sinVincular,t.OrigenClave AS origen"""


def listar(id_contacto=None, desde=None, hasta=None, estado=None, vinculacion=None, id_salario=None, page=1, page_size=50):
    where, params = [], []
    for condicion, valor in (("t.IdContacto=?", id_contacto), ("t.Fecha>=?", desde), ("t.Fecha<=?", hasta),
                              ("(CASE WHEN pg.Hay=0 THEN t.EstadoPago WHEN ISNULL(pg.Pagado,0)>=t.Total THEN 'Pagado' ELSE 'Pendiente' END)=?", estado)):
        if valor is not None:
            where.append(condicion)
            params.append(valor)
    if vinculacion:
        where.append({"sin": "ISNULL(s.Vinculado,0)=0", "parcial": "ISNULL(s.Vinculado,0)>0 AND s.Vinculado<t.Total",
                      "completo": "t.Total>0 AND s.Vinculado=t.Total"}[vinculacion])
    if id_salario:
        where.append("EXISTS (SELECT 1 FROM dbo.TrabajosEventualesVinculos x WHERE x.IdTrabajo=t.IdTrabajo AND x.IdSalario=?)")
        params.append(id_salario)
    filtro = " WHERE " + " AND ".join(where) if where else ""
    resumen = fetch_one("SELECT COUNT(*) AS cantidad,ISNULL(SUM(t.Total),0) AS totalTrabajos,"
                        "ISNULL(SUM(s.Vinculado),0) AS totalVinculado,"
                        "ISNULL(SUM(t.Total-ISNULL(s.Vinculado,0)),0) AS sinVincular " + BASE + filtro, tuple(params))
    items = fetch_all("SELECT " + COLS + " " + BASE + filtro + " ORDER BY t.Fecha DESC,t.IdTrabajo DESC "
                      "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", (*params, (page-1)*page_size, page_size))
    return {"items": items, "total": resumen["cantidad"], "page": page, "pageSize": page_size, "resumen": resumen}


def obtener(id_trabajo):
    t = fetch_one("SELECT " + COLS + " " + BASE + " WHERE t.IdTrabajo=?", (id_trabajo,))
    if t:
        t["vinculos"] = fetch_all("SELECT v.IdSalario AS idSalario,v.Importe AS importe,r.[Periodo liquidado] AS periodo,"
                                  "r.[Fecha de pago] AS fecha FROM dbo.TrabajosEventualesVinculos v "
                                  "JOIN dbo.Remuneraciones r ON r.IdSalario=v.IdSalario WHERE v.IdTrabajo=? ORDER BY v.IdSalario", (id_trabajo,))
        t["pagos"] = pagos(id_trabajo)
        t["pagado"] = sum(dinero(p['importe']) for p in t["pagos"])
        # Un pago en efectivo anulado en la caja deja de contar: el estado sale de los pagos vigentes.
        if t["pagos"] or fetch_one("SELECT 1 AS x FROM dbo.TrabajosEventualesPagos WHERE IdTrabajo=?", (id_trabajo,)):
            t["estadoPago"] = 'Pagado' if t["pagado"] >= dinero(t["total"]) else 'Pendiente'
    return t


def liquidaciones(id_trabajo):
    t = obtener(id_trabajo)
    if not t:
        return None
    return fetch_all("SELECT TOP (200) r.IdSalario AS idSalario,r.[Periodo liquidado] AS periodo,"
                     "r.[Fecha de pago] AS fecha,(" + salarios._IMPORTE_SQL + ") AS neto,"
                     "(" + salarios._IMPORTE_SQL + ")-ISNULL(v.Importe,0) AS disponible "
                     "FROM dbo.Remuneraciones r OUTER APPLY (SELECT SUM(Importe) AS Importe "
                     "FROM dbo.TrabajosEventualesVinculos WHERE IdSalario=r.IdSalario) v "
                     "WHERE r.IdContacto=? ORDER BY r.[Fecha de pago] DESC,r.IdSalario DESC", (t["idContacto"],))


def auditar(id_trabajo, accion, datos, usuario):
    execute_write("INSERT INTO dbo.TrabajosEventualesAuditoria (IdTrabajo,Accion,Datos,Usuario) VALUES (?,?,?,?)",
                  (id_trabajo, accion, json.dumps(datos, ensure_ascii=False, default=str), usuario[:100]))


def validar_edicion(anterior, nuevo, total):
    if dinero(anterior["vinculado"]) > total:
        raise ValueError("El total no puede quedar por debajo de lo incluido en liquidaciones")
    if anterior["vinculado"] and anterior["idContacto"] != nuevo.idContacto:
        raise ValueError("Quitá los vínculos antes de cambiar de trabajador")


@atomic_reconciliation
def guardar(datos: TrabajoInput, usuario: str, id_trabajo=None):
    total = total_trabajo(datos.dias, datos.jornal, datos.viaticos, datos.redondeo)
    if not salarios.existe_contacto_empleado(datos.idContacto):
        raise ValueError("Seleccioná un trabajador de Personal")
    valores = (datos.idContacto, datos.fecha, datos.descripcion, datos.dias, datos.jornal, datos.viaticos,
               datos.redondeo, total, datos.estadoPago, datos.numeroRecibo, datos.observaciones, usuario[:100])
    anterior = obtener(id_trabajo) if id_trabajo else None
    if id_trabajo:
        if not anterior:
            return None
        validar_edicion(anterior, datos, total)
        execute_write("UPDATE dbo.TrabajosEventuales SET IdContacto=?,Fecha=?,Descripcion=?,Dias=?,Jornal=?,Viaticos=?,"
                      "Redondeo=?,Total=?,EstadoPago=?,NumeroRecibo=?,Observaciones=?,Usuario=?,Actualizado=SYSDATETIME() "
                      "WHERE IdTrabajo=?", (*valores, id_trabajo))
    else:
        id_trabajo = execute_insert_returning_id("INSERT INTO dbo.TrabajosEventuales "
            "(IdContacto,Fecha,Descripcion,Dias,Jornal,Viaticos,Redondeo,Total,EstadoPago,NumeroRecibo,Observaciones,Usuario) "
            "OUTPUT INSERTED.IdTrabajo VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", valores)
    auditar(id_trabajo, "editar" if anterior else "crear", {"anterior": anterior, "nuevo": datos.model_dump()}, usuario)
    return obtener(id_trabajo)


def validar_vinculo(trabajo, liquidacion, importe, usado):
    importe = dinero(importe)
    if importe <= 0:
        raise ValueError("El importe debe ser mayor que cero")
    if trabajo["idContacto"] != liquidacion["idContacto"]:
        raise ValueError("La liquidación corresponde a otro trabajador")
    if importe > dinero(trabajo["sinVincular"]):
        raise ValueError("El importe supera lo que falta vincular de este trabajo")
    if importe > dinero(liquidacion["neto"]) - dinero(usado):
        raise ValueError("El importe supera lo disponible de la liquidación")


@atomic_reconciliation
def vincular(id_trabajo, id_salario, importe, usuario):
    t = obtener(id_trabajo)
    r = fetch_one("SELECT r.IdContacto AS idContacto,(" + salarios._IMPORTE_SQL + ") AS neto "
                  "FROM dbo.Remuneraciones r WHERE r.IdSalario=?", (id_salario,))
    if not t or not r:
        raise ValueError("No se encontró el trabajo o la liquidación")
    if fetch_one("SELECT 1 AS x FROM dbo.TrabajosEventualesVinculos WHERE IdTrabajo=? AND IdSalario=?", (id_trabajo, id_salario)):
        raise ValueError("Ese trabajo ya tiene un importe en esta liquidación; quitá el vínculo para corregirlo")
    usado = fetch_one("SELECT ISNULL(SUM(Importe),0) AS importe FROM dbo.TrabajosEventualesVinculos WHERE IdSalario=?", (id_salario,))["importe"]
    validar_vinculo(t, r, importe, usado)
    execute_write("INSERT INTO dbo.TrabajosEventualesVinculos (IdTrabajo,IdSalario,Importe,Usuario) VALUES (?,?,?,?)",
                  (id_trabajo, id_salario, importe, usuario[:100]))
    auditar(id_trabajo, "vincular", {"idSalario": id_salario, "importe": importe}, usuario)
    return obtener(id_trabajo)


@atomic_reconciliation
def desvincular(id_trabajo, id_salario, usuario):
    anterior = fetch_one("SELECT Importe AS importe FROM dbo.TrabajosEventualesVinculos WHERE IdTrabajo=? AND IdSalario=?", (id_trabajo, id_salario))
    if not anterior:
        return None
    execute_write("DELETE FROM dbo.TrabajosEventualesVinculos WHERE IdTrabajo=? AND IdSalario=?", (id_trabajo, id_salario))
    auditar(id_trabajo, "desvincular", {"idSalario": id_salario, **anterior}, usuario)
    return obtener(id_trabajo)


# --- Pago de trabajos (04/11/2026): en efectivo desde una caja o por transferencia ya cargada del banco ---------
# Muchos se pagan sin recibo: el recibo no es obligatorio. El pago en efectivo se registra en la caja como gasto sin
# comprobante (descuenta el saldo de la caja); la transferencia se vincula al movimiento del extracto (ya está
# en el banco, no se vuelve a registrar). Si la operación de caja se anula, el pago deja de contar.

def _dia(v):
    from datetime import date, datetime

    if isinstance(v, datetime):
        return v.date()
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


PAGOS_VIGENTES = """FROM dbo.TrabajosEventualesPagos p
LEFT JOIN dbo.OperacionesCajaEfectivo o ON o.IdOperacion=p.IdOperacion
WHERE p.IdTrabajo=? AND (p.Medio<>'caja' OR o.Estado<>'Anulada')"""


def pagos(id_trabajo) -> list[dict]:
    return fetch_all("SELECT p.IdPagoTrabajo AS idPago,p.Medio AS medio,p.Caja AS caja,p.Fecha AS fecha,p.Importe AS importe,"
                     "p.IdOperacion AS idOperacion,p.IdMovimientoBanco AS idMovimientoBanco " + PAGOS_VIGENTES +
                     " ORDER BY p.Fecha,p.IdPagoTrabajo", (id_trabajo,))


def _actualizar_estado(id_trabajo):
    t = fetch_one("SELECT Total FROM dbo.TrabajosEventuales WHERE IdTrabajo=?", (id_trabajo,))
    pagado = sum(dinero(p['importe']) for p in pagos(id_trabajo))
    estado = 'Pagado' if pagado >= dinero(t['Total']) else 'Pendiente'
    execute_write("UPDATE dbo.TrabajosEventuales SET EstadoPago=?,Actualizado=SYSDATETIME() WHERE IdTrabajo=?",
                  (estado, id_trabajo))


def _operacion_caja(t, datos):
    """Efectivo: sale de la caja como gasto sin comprobante (decisión de Sergio 04/11/2026: estos trabajos no tienen
    factura), repartido al rubro/centro de costos elegido. La liquidación de sueldo sigue siendo solo una referencia."""
    from src.features.cajas_efectivo.schemas import OperacionCaja, RepartoCaja

    f = _dia(t['fecha'])
    concepto = f"Trabajo eventual {t['trabajador']} {f:%d/%m/%Y}: {t['descripcion']}"[:255]
    reparto = RepartoCaja(idRubro=datos.idRubro, idCentroCostos=datos.idCentroCostos, idDestino=datos.idDestino,
                          idCampania=datos.idCampania, importePesos=datos.importe)
    return OperacionCaja(tipo="gasto_sin_comprobante", caja=datos.caja, fecha=datos.fecha, importe=datos.importe,
                         concepto=concepto, cuenta=datos.cuenta, repartos=[reparto])


def previsualizar_pago_caja(id_trabajo, datos):
    from src.features.cajas_efectivo import operaciones, service

    t = obtener(id_trabajo)
    if not t:
        return None
    return json.loads(operaciones.dumps(service.previsualizar(_operacion_caja(t, datos))))


def pagar_con_caja(id_trabajo, datos, usuario):
    from uuid import uuid4

    from src.features.cajas_efectivo import service
    from src.features.cajas_efectivo.schemas import ConfirmarOperacion

    t = obtener(id_trabajo)
    if not t:
        return None
    op = _operacion_caja(t, datos)
    hecho, _ = service.crear(ConfirmarOperacion(operacion=op, previewVersion=datos.previewVersion,
                                                advertenciasAceptadas=datos.advertenciasAceptadas), uuid4(), usuario)
    execute_write("INSERT INTO dbo.TrabajosEventualesPagos (IdTrabajo,Medio,IdOperacion,Caja,Fecha,Importe,Usuario) "
                  "VALUES (?,?,?,?,?,?,?)", (id_trabajo, 'caja', hecho['idOperacion'], datos.caja, datos.fecha,
                                              datos.importe, usuario[:100]))
    _actualizar_estado(id_trabajo)
    auditar(id_trabajo, "pago-caja", {"idOperacion": hecho['idOperacion'], **datos.model_dump(mode="json")}, usuario)
    return obtener(id_trabajo)


def transferencias_candidatas(id_trabajo) -> list[dict]:
    """Débitos del banco ya cargados a nombre del trabajador, no vinculados a otro trabajo, más cercanos primero."""
    t = obtener(id_trabajo)
    if not t:
        return []
    usados = {(r['m'], r['i']) for r in fetch_all(
        "SELECT Medio m, IdMovimientoBanco i FROM dbo.TrabajosEventualesPagos WHERE IdMovimientoBanco IS NOT NULL")}
    filas = fetch_all(
        "SELECT 'galicia' medio, IdMovimiento id, Fecha fecha, [Débitos] importe, [Descripción] detalle "
        "FROM dbo.[Movimientos Galicia] WHERE IdContacto=? AND [Débitos]>0 AND Fecha>=DATEADD(day,-15,?) "
        "UNION ALL SELECT 'bna', IdMovimientoBNA, [Fecha / Hora Mov#], -Importe, Concepto FROM dbo.[Movimientos BNA] "
        "WHERE IdContacto=? AND Importe<0 AND [Fecha / Hora Mov#]>=DATEADD(day,-15,?)",
        (t['idContacto'], _dia(t['fecha']), t['idContacto'], _dia(t['fecha'])))
    filas = [f for f in filas if (f['medio'], f['id']) not in usados]

    return sorted(filas, key=lambda f: abs((_dia(f['fecha']) - _dia(t['fecha'])).days))


def pagar_con_transferencia(id_trabajo, medio, id_movimiento, usuario):
    m = next((f for f in transferencias_candidatas(id_trabajo) if f['medio'] == medio and f['id'] == id_movimiento), None)
    if not m:
        raise ValueError("Ese movimiento del banco no es del trabajador o ya está vinculado a otro trabajo")
    t = obtener(id_trabajo)
    importe = min(dinero(m['importe']), dinero(t['total']) - dinero(t['pagado']))
    if importe <= 0:
        raise ValueError("El trabajo ya está pagado")
    fecha = _dia(m['fecha'])
    execute_write("INSERT INTO dbo.TrabajosEventualesPagos (IdTrabajo,Medio,IdMovimientoBanco,Fecha,Importe,Usuario) "
                  "VALUES (?,?,?,?,?,?)", (id_trabajo, medio, id_movimiento, fecha, importe, usuario[:100]))
    _actualizar_estado(id_trabajo)
    auditar(id_trabajo, "pago-transferencia", {"medio": medio, "idMovimiento": id_movimiento, "importe": str(importe)}, usuario)
    return obtener(id_trabajo)


def quitar_pago(id_trabajo, id_pago, usuario):
    """Solo transferencias: el pago en efectivo se anula desde la caja (así se repone el saldo)."""
    p = fetch_one("SELECT Medio FROM dbo.TrabajosEventualesPagos WHERE IdPagoTrabajo=? AND IdTrabajo=?", (id_pago, id_trabajo))
    if not p:
        return None
    if p['Medio'] == 'caja':
        raise ValueError("El pago en efectivo se anula desde la caja, para que se reponga el saldo")
    execute_write("DELETE FROM dbo.TrabajosEventualesPagos WHERE IdPagoTrabajo=?", (id_pago,))
    _actualizar_estado(id_trabajo)
    auditar(id_trabajo, "quitar-pago", {"idPago": id_pago}, usuario)
    return obtener(id_trabajo)
