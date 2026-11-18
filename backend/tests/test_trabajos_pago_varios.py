from decimal import Decimal

import pytest

from src.features.trabajos_eventuales import repository as repo
from src.features.trabajos_eventuales.schemas import PagoVariosSocioInput, Trabajo


def test_reparte_del_mas_viejo_al_mas_nuevo():
    faltas = [(84, Decimal("38500")), (85, Decimal("77000")), (86, Decimal("38500"))]
    assert repo.repartir_pago(faltas, Decimal("154000")) == faltas
    assert repo.repartir_pago(faltas, Decimal("100000")) == [(84, Decimal("38500")), (85, Decimal("61500"))]


def test_no_acepta_mas_de_lo_que_falta_ni_cero():
    with pytest.raises(ValueError):
        repo.repartir_pago([(1, Decimal("100"))], Decimal("100.01"))
    with pytest.raises(ValueError):
        repo.repartir_pago([(1, Decimal("100"))], Decimal("0"))


def _trabajo(i, contacto, fecha, total, pagado=0):
    return {"idTrabajo": i, "idContacto": contacto, "trabajador": "Diego Pardo", "fecha": fecha, "descripcion": "x",
            "total": total, "pagado": pagado}


def test_pago_del_socio_carga_gasto_y_credito_al_socio_en_un_paso(monkeypatch):
    from src.features.cajas_efectivo import operaciones, service
    from src.features.cuentas_socios import repository as socios

    base = {84: _trabajo(84, 632, "2026-11-09", 38500), 85: _trabajo(85, 632, "2026-11-10", 77000),
            86: _trabajo(86, 632, "2026-11-12", 38500)}
    monkeypatch.setattr(repo, "obtener", lambda i: base.get(i))
    monkeypatch.setattr(repo, "_actualizar_estado", lambda i: None)
    monkeypatch.setattr(repo, "auditar", lambda *a: None)
    monkeypatch.setattr(socios, "validar_medio", lambda *a: None)
    creadas = []
    monkeypatch.setattr(service, "previsualizar", lambda op: {"previewVersion": "a" * 64, "advertencias": []})
    monkeypatch.setattr(service, "crear", lambda body, key, user: creadas.append(body.operacion) or ({"idOperacion": 50}, True))
    monkeypatch.setattr(operaciones, "effects", lambda i: [{"TipoEfecto": "GastoCaja", "IdRegistro": 7},
                                                           {"TipoEfecto": "MovimientoSocio", "IdRegistro": 999}])
    lotes = []
    import src.db.connection as conn
    monkeypatch.setattr(conn, "execute_write_transaction", lambda ops: lotes.append(ops) or [])
    datos = PagoVariosSocioInput(idSocio=1, fecha="2026-11-18", importe=Decimal("154000"), medio="ICBC",
                                 idCentroCostos=2, idsTrabajo=[86, 84, 85])
    repo.pagar_varios_por_socio(datos.idsTrabajo, datos, "sergio")
    op = creadas[0]
    # una sola operación: gasto de mano de obra (Personal Eventual) que no sale de ninguna caja y queda a favor del socio
    assert len(creadas) == 1 and op.tipo == "gasto_sin_comprobante" and op.idSocio == 1 and op.medioSocio == "ICBC"
    assert op.repartos[0].idRubro == 16 and op.repartos[0].importePesos == Decimal("154000")
    assert service.piernas(op) == {}
    sqls = lotes[0]
    pagos = [s for s in sqls if "TrabajosEventualesPagos" in s[0]]
    assert [p[1][0] for p in pagos] == [84, 85, 86] and all(p[1][2] == 50 and p[1][3] == 999 for p in pagos)
    assert not any("PagosSocioProveedor" in s[0] for s in sqls)  # no pasa por la cuenta del trabajador


def test_gasto_de_socio_requiere_medio_y_rubro():
    from src.features.cajas_efectivo.schemas import OperacionCaja

    with pytest.raises(ValueError):
        OperacionCaja(tipo="gasto_sin_comprobante", caja="giamigli-sa", fecha="2026-11-18", importe=1, concepto="x",
                      cuenta="B", idSocio=1)


def test_no_mezcla_trabajadores(monkeypatch):
    base = {1: _trabajo(1, 632, "2026-11-09", 100), 2: _trabajo(2, 700, "2026-11-10", 100)}
    monkeypatch.setattr(repo, "obtener", lambda i: base.get(i))
    with pytest.raises(ValueError):
        repo._trabajos_a_pagar([1, 2])


def test_la_ficha_devuelve_los_pagos():
    t = Trabajo(**{**_trabajo(80, 632, "2026-11-04", 40000, 40000), "dias": 0.5, "jornal": 80000, "viaticos": 0, "redondeo": 0,
                   "estadoPago": "Pagado", "vinculado": 0, "sinVincular": 40000,
                   "pagos": [{"idPago": 4, "medio": "caja", "caja": "giamigli-sa", "fecha": "2026-11-04", "importe": 40000}]})
    assert t.pagado == 40000 and len(t.pagos) == 1
