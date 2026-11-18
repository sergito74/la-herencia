"""Carga el gasto de mano de obra de los trabajos eventuales que pagó un socio antes del circuito del 18/11/2026.

Sergio (18/11/2026) lo aprobó: "¿Querés que les cargue el gasto en Personal Eventual, con el centro de costos que
corresponda a cada uno? Claro que sí."

Para cada asiento del socio, el script hace tres cosas:
- Crea una operación de gasto sin comprobante que no mueve ninguna caja, con el gasto en Personal Eventual.
- Toma el asiento existente del socio como efecto ajeno: no lo duplica ni cambia su saldo.
- Registra el pago en cada trabajo, para que se vea en la cuenta del trabajador.

La campaña sale de la fecha (1/7 a 30/6). Es idempotente: si el pago ya está registrado en el trabajo, lo saltea.
Uso (desde backend/):  python -m scripts.gasto_trabajos_pagados_por_socio [--aplicar]
"""

import sys
from decimal import Decimal
from uuid import uuid4

from src.db.connection import _assert_target_is_wc, fetch_all, fetch_one
from src.features.cajas_efectivo import operaciones as db
from src.features.cajas_efectivo import service
from src.features.cajas_efectivo.schemas import OperacionCaja, RepartoCaja
from src.db.connection import atomic_reconciliation

GANADERIA, ADM = 2, 3
RUBRO = 16  # Personal Eventual
# asiento del socio -> (trabajos que paga, centro de costos)
PAGOS = {
    2058: ([83], GANADERIA), 2082: ([8, 10, 12], GANADERIA), 2119: ([35], GANADERIA), 2197: ([61], GANADERIA),
    2210: ([64], GANADERIA), 2220: ([67], GANADERIA), 2270: ([75], GANADERIA), 3261: ([84, 85, 86], GANADERIA),
}
CAMPANIAS = {2021: 15, 2022: 17, 2023: 19, 2024: 22, 2025: 24, 2026: 32}
USUARIO = "Sergio (vía Claude)"


def campania(f):
    return CAMPANIAS[f.year if f.month >= 7 else f.year - 1]


@atomic_reconciliation
def cargar(id_mov, ids, centro):
    m = fetch_one("SELECT IdSocio,CAST(Fecha AS date) Fecha,Importe,Medio,Motivo,Anulada FROM dbo.MovimientosCuentaSocio "
                  "WHERE IdMovimiento=?", (id_mov,))
    assert m and not m["Anulada"]
    ts = fetch_all("SELECT IdTrabajo,Total FROM dbo.TrabajosEventuales WHERE IdTrabajo IN (%s) ORDER BY Fecha,IdTrabajo"
                   % ",".join("?" * len(ids)), tuple(ids))
    importe = Decimal(str(m["Importe"])).quantize(Decimal("0.01"))
    assert sum(Decimal(str(t["Total"])) for t in ts) == importe, f"{id_mov}: el importe no coincide con los trabajos"
    fecha = m["Fecha"] if not isinstance(m["Fecha"], str) else __import__("datetime").date.fromisoformat(m["Fecha"][:10])
    op = OperacionCaja(tipo="gasto_sin_comprobante", caja="giamigli-sa", fecha=fecha, importe=importe,
                       concepto=m["Motivo"][:255], cuenta="B", idSocio=m["IdSocio"], medioSocio=m["Medio"],
                       repartos=[RepartoCaja(idRubro=RUBRO, idCentroCostos=centro, idCampania=campania(fecha),
                                             importePesos=importe)])
    id_op = db.create_operation(uuid4(), service.huella(op.model_dump(mode="json")), op,
                                {"historico": "gasto de trabajo eventual pagado por socio, cargado 18/11/2026"}, USUARIO)
    id_gasto = db.insert("INSERT INTO dbo.GastoCajaEfectivo (IdOperacion,Fecha,Concepto,ImportePesos,Usuario) "
                         "OUTPUT INSERTED.IdGasto VALUES (?,?,?,?,?)", (id_op, fecha, op.concepto, importe, USUARIO))
    db.effect(id_op, "GastoCaja", id_gasto)
    db.write("INSERT INTO dbo.RepartosGastoCaja (IdGasto,IdRubro,IdCentroCostos,IdDestino,IdCampania,IdLote,ImportePesos) "
             "VALUES (?,?,?,NULL,?,NULL,?)", (id_gasto, RUBRO, centro, campania(fecha), importe))
    db.effect(id_op, "MovimientoSocio", id_mov, False)  # el asiento ya existía: no se duplica ni se anula con la operación
    for t in ts:
        existe = fetch_one("SELECT IdPagoTrabajo FROM dbo.TrabajosEventualesPagos WHERE IdTrabajo=? AND IdMovimientoSocio=?",
                           (t["IdTrabajo"], id_mov))
        if existe:
            db.write("UPDATE dbo.TrabajosEventualesPagos SET IdOperacion=? WHERE IdPagoTrabajo=?", (id_op, existe["IdPagoTrabajo"]))
        else:
            db.write("INSERT INTO dbo.TrabajosEventualesPagos (IdTrabajo,Medio,IdOperacion,IdMovimientoSocio,Fecha,Importe,Usuario) "
                     "VALUES (?,?,?,?,?,?,?)", (t["IdTrabajo"], "socio", id_op, id_mov, fecha, t["Total"], USUARIO))
    return id_op


def main():
    _assert_target_is_wc()
    aplicar = "--aplicar" in sys.argv
    if aplicar:
        from src.features.vinculos.backup import backup_verificado
        print(f"Respaldo verificado: {backup_verificado('gasto-trabajos-socio')}")
    for id_mov, (ids, centro) in PAGOS.items():
        hecho = fetch_one("SELECT TOP 1 p.IdOperacion FROM dbo.TrabajosEventualesPagos p JOIN dbo.GastoCajaEfectivo g "
                          "ON g.IdOperacion=p.IdOperacion WHERE p.IdMovimientoSocio=?", (id_mov,))
        if hecho:
            print(f"{id_mov}: ya cargado (operación {hecho['IdOperacion']})")
            continue
        print(f"{id_mov}: trabajos {ids}, centro {centro}" + ("" if aplicar else " (simulación)"))
        if aplicar:
            print(f"   operación {cargar(id_mov, ids, centro)}")


if __name__ == "__main__":
    main()
