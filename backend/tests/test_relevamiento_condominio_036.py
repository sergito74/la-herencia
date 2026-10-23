from datetime import date
from decimal import Decimal
import pytest
from scripts.relevar_condominio_ef_2011_2016_036 import candidates
from scripts.atribuir_aportes_condominio_22150_036 import validar, evidencias


def test_cruce_conserva_ambiguedad_y_signo():
    rows = [
        {"id": 1, "fecha": "2012-01-01", "importe": Decimal("100")},
        {"id": 2, "fecha": "2012-01-02", "importe": Decimal("100")},
        {"id": 3, "fecha": "2012-01-01", "importe": Decimal("-100")},
    ]
    assert [r["id"] for r in candidates(rows, 100, date(2012, 1, 1), 5)] == [1, 2]
    assert [r["id"] for r in candidates(rows, 100, date(2012, 1, 1), 5, -1)] == [3]
    assert not candidates(rows, 100, date(2012, 2, 1), 5)


def test_no_atribuye_si_cuenta_destino_cerrada():
    class Cursor:
        def execute(self, *args):
            return self

        def fetchone(self):
            return ("cerrada-con-excepcion",)

    with pytest.raises(RuntimeError, match="cerrada"):
        validar(Cursor())


def test_cambio_de_fuente_impide_atribucion(monkeypatch):
    from scripts import atribuir_aportes_condominio_22150_036 as script

    class Sheet:
        def iter_rows(self, **kwargs):
            return iter([(date(2020, 1, 1), None, None, None, None)])

    class Book:
        def __getitem__(self, k):
            return Sheet()

        def close(self):
            pass

    class Source:
        def read_bytes(self):
            return b"simulada"

    monkeypatch.setattr(script, "SOURCES", [(Source(), "Movs", [(1, 0, 1), (2, 0, 1)])])
    monkeypatch.setattr(script, "load_workbook", lambda *a, **kw: Book())
    with pytest.raises(ValueError, match="Cambió la evidencia"):
        evidencias()
