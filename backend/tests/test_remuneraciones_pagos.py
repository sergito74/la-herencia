from decimal import Decimal

import pytest

from src.features.remuneraciones import pagos


def _liq(i, contacto, fecha, neto):
    return {"idSalario": i, "idContacto": contacto, "empleado": "Marcelo Sierra", "fecha": fecha, "periodo": "Octubre 2026", "neto": neto}


def test_no_mezcla_empleados(monkeypatch):
    monkeypatch.setattr(pagos, "fetch_all", lambda *a: [_liq(1, 374, "2026-10-31", 100), _liq(2, 397, "2026-10-31", 100)])
    with pytest.raises(ValueError):
        pagos.liquidaciones([1, 2])


def test_falta_descuenta_lo_ya_vinculado(monkeypatch):
    monkeypatch.setattr(pagos, "fetch_all", lambda *a: [_liq(1, 374, "2026-09-30", 1000), _liq(2, 374, "2026-10-31", 500)])
    monkeypatch.setattr(pagos, "pagos_de", lambda ids: {1: [{"importe": 1000}], 2: [{"importe": 200}]})
    ls = pagos.liquidaciones([1, 2])
    assert [(l["idSalario"], l["falta"]) for l in ls] == [(2, Decimal("300.00"))]


def test_pago_en_caja_es_pago_al_empleado_no_gasto():
    from types import SimpleNamespace

    op = pagos._operacion_caja([_liq(1, 374, "2026-10-31", 100)],
                               SimpleNamespace(caja="giamigli-sa", fecha="2026-11-18", importe=Decimal("100"), cuenta="B"))
    assert op.tipo == "pago" and op.idContacto == 374 and op.idSalario == 1 and not op.repartos and not op.aplicaciones


def test_un_solo_asiento_del_socio(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(pagos, "liquidaciones", lambda ids: [
        {**_liq(1, 374, "2026-09-30", 100), "falta": Decimal("100")}, {**_liq(2, 374, "2026-10-31", 50), "falta": Decimal("50")}])
    lotes = []
    monkeypatch.setattr(pagos, "execute_write_transaction", lambda ops: lotes.append(ops) or [7])
    datos = SimpleNamespace(idSocio=1, fecha="2026-11-18", importe=Decimal("150"), medio="Banco Galicia")
    assert pagos.pagar_por_socio([1, 2], datos, "sergio") == {"pagadas": [1, 2]}
    resueltos = [op([7]) if callable(op) else op for op in lotes[0][1:]]
    filas = [r for r in resueltos if "RemuneracionesPagos" in r[0]]
    assert len(lotes) == 1 and [f[1][0] for f in filas] == [1, 2] and all(f[1][2] == 7 for f in filas)
