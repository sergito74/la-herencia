"""Transformación conservadora de vistas, sin conectar a SQL Server."""

import pytest

from scripts.agregar_percepcion_iva_compras import extender_vista


SELECT = """dbo.vw_Compras_ImporteDocumento AS
SELECT c.IdDeuda, subtotal + iva
        + ISNULL(c.[Ingresos Brutos], 0)
        + ISNULL(c.[Conceptos no gravados], 0) AS ImporteDocumento
FROM dbo.Compras c
"""


@pytest.mark.parametrize("declaracion", ["CREATE VIEW", "ALTER VIEW", "CREATE OR ALTER VIEW", "\n create view"])
def test_extender_vista_conserva_formula_y_convierte_declaracion(declaracion):
    original = f"{declaracion} {SELECT}"
    resultado = extender_vista(original)
    assert resultado == "ALTER VIEW " + SELECT.replace(
        "+ ISNULL(c.[Ingresos Brutos], 0)",
        "+ ISNULL(c.[Ingresos Brutos], 0)\n        + ISNULL(c.PercepcionIVA, 0)",
    )
    assert extender_vista(resultado) is None


@pytest.mark.parametrize("definicion", [
    "CREATE VIEW " + SELECT.replace("+ ISNULL(c.[Ingresos Brutos], 0)", ""),
    "CREATE VIEW " + SELECT.replace("+ ISNULL(c.[Ingresos Brutos], 0)",
                                    "+ ISNULL(c.[Ingresos Brutos], 0) + ISNULL(c.[Ingresos Brutos], 0)"),
    "CREATE VIEW " + SELECT.replace("subtotal + iva", "subtotal + iva + c.PercepcionIVA"),
    SELECT,
])
def test_extender_vista_rechaza_drift(definicion):
    with pytest.raises(ValueError):
        extender_vista(definicion)


@pytest.mark.parametrize("alteracion", [
    lambda sql: sql.replace("+ ISNULL(c.[Ingresos Brutos], 0)", ""),
    lambda sql: sql.replace("subtotal + iva", "subtotal + iva + ISNULL(c.[PercepcionIVA], 0)"),
    lambda sql: sql.replace("ALTER VIEW ", ""),
    lambda sql: sql.replace("+ ISNULL(c.PercepcionIVA, 0)",
                            "+ ISNULL(c.PercepcionIVA, 0) + ISNULL(c.PercepcionIVA, 0)"),
])
def test_idempotencia_no_oculta_drift(alteracion):
    migrada = extender_vista("CREATE VIEW " + SELECT)
    with pytest.raises(ValueError):
        extender_vista(alteracion(migrada))
