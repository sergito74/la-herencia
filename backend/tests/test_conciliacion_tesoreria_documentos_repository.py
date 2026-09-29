"""026: fixtures puras; no escribe en WC."""

import pytest
from contextlib import nullcontext

from src.db import connection
from src.features.conciliacion_tesoreria import repository as repo, documentos
from src.features.tarjetas_resumenes import repository as tarjetas

from src.features.conciliacion_tesoreria import documentos_adapter as adapter


def doc(origen="Compras", id=1, saldo=100, moneda="Pesos", tc=None):
    return dict(
        origen=origen,
        idOrigen=id,
        saldoPendiente=saldo,
        importeOriginal=saldo,
        moneda=moneda,
        tipoDeCambio=tc,
    )


def test_identidad_compuesta_en_reparto_y_sugerencias():
    docs = [doc(o) for o in ("Compras", "Impuestos", "Remuneraciones", "Alquileres")]
    r = adapter.calcular(100, docs)
    assert len(r["imputados"]) == 4
    assert [i["importeImputado"] for i in r["imputados"]] == [25] * 4
    assert len(adapter.sugerencias(400, docs)[0]["documentos"]) == 4


def test_reparto_real_fixture_y_centavos():
    docs = [doc(id=i + 1, saldo=n) for i, n in enumerate([23051.11, 43195.98, 13798])]
    r = adapter.calcular(3717.61, docs)
    assert r["pagoParcial"]
    assert round(sum(i["importeImputado"] for i in r["imputados"]), 2) == 3717.61
    for item, d in zip(r["imputados"], docs, strict=True):
        assert abs(item["importeImputado"] - 3717.61 * d["saldoPendiente"] / 80045.09) < 0.02


def test_nc_firmada_reduce_total():
    r = adapter.calcular(90, [doc(saldo=100), doc(id=2, saldo=-10)])
    assert r["estado"] == "exacta"
    assert [i["importeImputado"] for i in r["imputados"]] == [100, -10]


def test_usa_saldo_restante_en_pesos_sin_convertir_dos_veces():
    r = adapter.calcular(500, [doc(saldo=1000, moneda="Dolares", tc=1000)])
    assert r["imputados"][0]["importeImputado"] == 500
    assert r["diferencia"] == -500


def test_menor_seleccion_deja_parcial():
    assert adapter.calcular(150, [doc()])["permiteParcial"]


@pytest.mark.parametrize("docs", [[], [doc(), doc()], [doc(saldo=-10)]])
def test_selecciones_invalidas(docs):
    with pytest.raises(ValueError):
        adapter.calcular(100, docs)


@pytest.fixture(autouse=True)
def prohibir_conexion_real(monkeypatch):
    def fail(*a, **k):
        raise AssertionError("Los tests 026 no escriben ni leen WC")

    monkeypatch.setattr(connection.pyodbc, "connect", fail)


@pytest.fixture
def negocio(monkeypatch):
    monkeypatch.setattr(connection, "reconciliation_transaction", nullcontext)
    monkeypatch.setattr(
        repo,
        "_movimiento_original",
        lambda *a: dict(importe=110, fecha="2026-01-01", idContacto=None),
    )
    monkeypatch.setattr(repo, "listar_conciliaciones", lambda *a: [])
    monkeypatch.setattr(repo, "_estado_vigente", lambda *a: None)
    monkeypatch.setattr(repo, "_tiene_traspaso_interno_activo", lambda *a: False)
    monkeypatch.setattr(
        documentos,
        "por_referencias",
        lambda refs: [
            dict(doc(r["origen"], r["idOrigen"]), idContacto=42, importePesos=100) for r in refs
        ],
    )
    monkeypatch.setattr(repo, "_contacto_reconocido_por_origen_automatico", lambda *a: None)
    return monkeypatch


def test_lote_diferencia_y_filas_en_una_transaccion(negocio):
    statements = []
    negocio.setattr(
        repo,
        "execute_write_transaction",
        lambda stmts: statements.extend(stmts) or [1] * len(stmts),
    )
    repo.vincular_lote(
        "bna",
        1,
        [dict(origen="Compras", idOrigen=1)],
        dict(motivo="Impuesto", detalle="Ley"),
        "tester",
    )
    assert len(statements) == 2
    assert statements[0][1][3] == 100
    assert statements[1][1][2:] == ("DiferenciaAceptada", "Impuesto", "Ley", 10.0, "tester")


def test_diferencia_negativa_conserva_pago_real(negocio):
    negocio.setattr(
        repo,
        "_movimiento_original",
        lambda *a: dict(importe=90, fecha="2026-01-01", idContacto=None),
    )
    statements = []
    negocio.setattr(
        repo, "execute_write_transaction", lambda s: statements.extend(s) or [1] * len(s)
    )
    repo.vincular_lote(
        "bna", 1, [dict(origen="Compras", idOrigen=1)], dict(motivo="Redondeo"), "tester"
    )
    assert statements[0][1][3] == 90
    assert statements[1][1][5] == -10


def test_parcial_continua_sobre_residual(negocio):
    negocio.setattr(repo, "listar_conciliaciones", lambda *a: [dict(importe=60)])
    assert (
        repo.calcular_conciliacion("bna", 1, [dict(origen="Compras", idOrigen=1)])["imputados"][0][
            "importeImputado"
        ]
        == 50
    )


@pytest.mark.parametrize("estado", ["conciliado", "ya_reconocido", "sin_documento"])
def test_bloqueos_por_otra_via(negocio, estado):
    negocio.setattr(repo, "calcular_estado", lambda *a: dict(estado=estado, saldoPendiente=100))
    with pytest.raises(ValueError, match="resuelto"):
        repo.calcular_conciliacion("bna", 1, [dict(origen="Compras", idOrigen=1)])


def test_traspaso_bloquea_lote(negocio):
    negocio.setattr(repo, "_tiene_traspaso_interno_activo", lambda *a: True)
    with pytest.raises(ValueError, match="traspaso"):
        repo.vincular_lote("bna", 1, [dict(origen="Compras", idOrigen=1)], None, "tester")


def test_sin_documento_no_admite_parcial(negocio):
    negocio.setattr(repo, "listar_conciliaciones", lambda *a: [dict(importe=60)])
    with pytest.raises(ValueError, match="imputaciones"):
        repo.marcar_sin_documento("bna", 1, "Impuesto", None, "tester")


def test_quitar_vinculo_borra_la_fila(negocio):
    negocio.setattr(repo, "fetch_one", lambda *a: dict(IdConciliacion=88))
    borrados = []
    negocio.setattr(repo, "execute_write", lambda sql, params: borrados.append((sql, params)) or 1)
    repo.quitar_vinculo("mercado-libre", 25, 88)
    sql, params = borrados[0]
    assert "DELETE FROM dbo.ConciliacionesTesoreria" in sql
    assert params == (88,)


def test_quitar_vinculo_rechaza_conciliacion_inexistente(negocio):
    negocio.setattr(repo, "fetch_one", lambda *a: None)
    with pytest.raises(ValueError, match="No existe la conciliación"):
        repo.quitar_vinculo("mercado-libre", 25, 999)


def test_excepcion_cierra_parcial_y_reversion_lo_recupera(negocio):
    negocio.setattr(repo, "listar_conciliaciones", lambda *a: [dict(importe=100)])
    evento = dict(estado="DiferenciaAceptada")
    negocio.setattr(repo, "_estado_vigente", lambda *a: evento)
    r = repo.calcular_estado("bna", 1)
    assert r["estado"] == "conciliado" and r["saldoPendiente"] == 0
    sent = []
    negocio.setattr(repo, "execute_write_transaction", lambda s: sent.extend(s))
    repo.quitar_estado("bna", 1, "tester")
    assert sent[0][1][2] == "EstadoQuitado"
    assert "DELETE" not in sent[0][0]
    negocio.setattr(repo, "_estado_vigente", lambda *a: None)
    assert repo.calcular_estado("bna", 1)["saldoPendiente"] == 10
    repo.quitar_estado("bna", 1, "tester")
    assert len(sent) == 1


@pytest.mark.parametrize(
    "estado,motivo,detalle",
    [
        ("SinDocumento", "Redondeo", None),
        ("DiferenciaAceptada", "Otro", " "),
        ("SinDocumento", "Impuesto", "x" * 256),
    ],
)
def test_motivos_en_repository(estado, motivo, detalle):
    with pytest.raises(ValueError):
        repo._stmt_estado("bna", 1, estado, motivo, detalle, None, "tester")


def test_estado_ultima_fila_revocada(monkeypatch):
    monkeypatch.setattr(repo, "fetch_one", lambda sql, params: dict(estado="EstadoQuitado"))
    assert repo._estado_vigente("bna", 1) is None


def test_saldo_compartido_usado_por_tarjetas(monkeypatch):
    sqls = []

    def total(sql, params):
        sqls.append(sql)
        return {"total": 40}

    monkeypatch.setattr(tarjetas, "fetch_one", total)
    d = tarjetas._documento_dict(dict(idCompra=1, importeOriginal=100, moneda="Pesos"))
    assert d["saldoPendiente"] == 60
    assert "ConciliacionesTesoreria" in sqls[0] and "Tarjetas_Resumenes_Lineas_Compras" in sqls[0]


def test_saldo_compartido_conserva_signo_nc(monkeypatch):
    monkeypatch.setattr(tarjetas, "fetch_one", lambda *a: dict(total=-40))
    assert (
        tarjetas._documento_dict(dict(idCompra=1, importeOriginal=-100, moneda="Pesos"))[
            "saldoPendiente"
        ]
        == -60
    )


def test_tarjetas_rechaza_vinculo_manual_que_excede_saldo(negocio):
    negocio.setattr(tarjetas, "existe_compra", lambda *a: True)
    negocio.setattr(documentos, "saldo_documento", lambda *a: 60)
    with pytest.raises(ValueError, match="saldo documental"):
        tarjetas.vincular_compra(1, 1, 80)


def test_busqueda_parametrizada_y_acotada(monkeypatch):
    calls = []
    monkeypatch.setattr(
        documentos, "fetch_all", lambda sql, params: calls.append((sql, params)) or []
    )
    documentos.buscar("x' OR 1=1 --")
    sql, params = calls[0]
    assert "x' OR" not in sql and params[0] == 40
    assert all(
        table in sql
        for table in (
            "dbo.Remuneraciones",
            "dbo.Impuestos",
            "dbo.[Detalle Cobro Alquiler]",
            "dbo.vw_Compras_ImporteDocumento",
        )
    )
    assert "Tarjetas_Resumenes_Lineas_Compras" in sql


def test_calculo_rechaza_documento_agotado(negocio):
    negocio.setattr(
        documentos,
        "por_referencias",
        lambda refs: [dict(doc(saldo=0), idContacto=42, importePesos=100)],
    )
    with pytest.raises(ValueError, match="saldo pendiente"):
        repo.calcular_conciliacion("bna", 1, [dict(origen="Compras", idOrigen=1)])


def test_corpus_sugerencias_seis_medios_cuatro_origenes(negocio):
    encontrados = 0
    for medio in repo.MEDIOS_SOPORTADOS:
        for origen in documentos.ORIGENES:
            esperado = dict(doc(origen, saldo=110), idContacto=42, importePesos=110)
            negocio.setattr(
                documentos,
                "buscar",
                lambda *a, esperado=esperado, **kw: [esperado, doc(id=99, saldo=300)],
            )
            result = repo.candidatos(medio, 1)
            encontrados += any(
                s["documentos"] == [dict(origen=origen, idOrigen=1)] for s in result["sugerencias"]
            )
    assert encontrados == 24  # corpus controlado; no estima el porcentaje real de producción


class FakeConnection:
    """Simula commit/rollback y exclusión entre sesiones del helper real."""

    def __init__(self, state, lock):
        self.state = state
        self.lock = lock
        self.description = [("result",)]
        self.held = False
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self

    def execute(self, sql, params=()):
        if "sp_getapplock" in sql:
            self.lock.acquire()
            self.held = True
            self.pending = self.state["saldo"]
        return self

    def fetchone(self):
        return (0,)

    def commit(self):
        self.state["saldo"] = self.pending
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True
        if self.held:
            self.lock.release()
            self.held = False


def test_transaccion_anidada_reusa_conexion_y_revierte(monkeypatch):
    from threading import Lock

    state = dict(saldo=100)
    connections = []

    def connect(*a, **k):
        c = FakeConnection(state, Lock())
        connections.append(c)
        return c

    monkeypatch.setattr(connection.pyodbc, "connect", connect)
    with pytest.raises(ValueError, match="fallo"):
        with connection.reconciliation_transaction():
            with connection.get_connection() as c:
                c.pending = 30
                with connection.reconciliation_transaction():
                    with connection.get_connection(readonly=False) as same:
                        assert same is c
                        raise ValueError("fallo")
    assert len(connections) == 1 and connections[0].rollbacks == 1 and connections[0].closed
    assert state["saldo"] == 100 and connection._reconciliation_connection.get() is None


@pytest.mark.parametrize("same_movement", [True, False])
def test_dos_confirmaciones_revalidan_dentro_del_bloqueo(monkeypatch, same_movement):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock, Barrier

    state = dict(saldo=100)
    lock = Lock()
    barrier = Barrier(2)
    monkeypatch.setattr(connection.pyodbc, "connect", lambda *a, **k: FakeConnection(state, lock))

    def pendiente(medio, id):
        c = connection._reconciliation_connection.get()
        assert c is not None and c.held
        return dict(estado="sin_conciliar", saldoPendiente=c.pending if same_movement else 100)

    monkeypatch.setattr(repo, "_pendiente", pendiente)

    def refs(rs):
        saldo = connection._reconciliation_connection.get().pending
        return [dict(doc(saldo=saldo), idContacto=42, importePesos=100)]

    monkeypatch.setattr(documentos, "por_referencias", refs)

    def write(stmts):
        c = connection._reconciliation_connection.get()
        c.pending -= stmts[0][1][3]
        return [1]

    monkeypatch.setattr(repo, "execute_write_transaction", write)
    monkeypatch.setattr(repo, "listar_conciliaciones", lambda *a: [])

    def worker(id):
        barrier.wait()
        try:
            repo.vincular_lote(
                "bna",
                1 if same_movement else id,
                [dict(origen="Compras", idOrigen=1)],
                None,
                "tester",
            )
            return "ok"
        except ValueError:
            return "conflicto"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [1, 2]))
    assert sorted(results) == ["conflicto", "ok"] and state["saldo"] == 0
