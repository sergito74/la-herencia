"""Tests de `compras.particular` (021-cuentas-socios, Foundational) contra
datos reales de `WC` (solo lectura) — misma fórmula ya validada en
`tarjetas_resumenes`, extraída acá para no duplicarla (research.md §3)."""

from __future__ import annotations

from src.db.connection import fetch_all
from src.features.compras.particular import importe_bruto_compra_particular, importe_personal_compra_particular


def _compra_de(razon_social_like: str) -> int:
    fila = fetch_all(
        "SELECT TOP 1 c.IdDeuda AS idDeuda FROM dbo.Compras c "
        "JOIN dbo.Contactos ct ON ct.IdContacto = c.IdContacto "
        "WHERE ct.[Razon Social] LIKE ? ORDER BY c.Fecha DESC",
        (f"%{razon_social_like}%",),
    )
    assert fila, f"no se encontró ninguna compra de {razon_social_like}"
    return fila[0]["idDeuda"]


def test_reconoce_precio_unitario_negativo_caso_2jm():
    # 2JM no es un caso "particular" en sí (factura normal pagada con
    # tarjeta) — se usa acá solo como control negativo real y estable.
    id_compra = _compra_de("2JM")
    assert importe_bruto_compra_particular(id_compra) is None


def test_reconoce_cantidad_negativa_caso_cumo_store():
    """Caso real 2026-09-26: "Cumo Store" carga la línea negativa con
    `Cantidad` negativa (no `Precio Unitario` negativo, la forma más
    común) — el detector debe reconocer ambas formas."""
    id_compra = _compra_de("Cumo Store")
    bruto = importe_bruto_compra_particular(id_compra)
    assert bruto is not None
    assert abs(bruto - 29699.10) < 0.5


def test_reconoce_cantidad_negativa_otro_caso_real():
    """Además de "Cumo Store", otras 2 compras reales usan `Cantidad`
    negativa en vez de `Precio Unitario` negativo (2143515234, 2143515232
    — hallazgo 2026-09-26). Se referencia por Id directamente: no
    pertenecen a un contacto con nombre estable para buscar por texto."""
    assert importe_bruto_compra_particular(2143515234) is not None
    assert importe_bruto_compra_particular(2143515232) is not None


def test_devuelve_none_para_compra_sin_linea_particular():
    id_compra = _compra_de("Agüero Shamaim")
    assert importe_bruto_compra_particular(id_compra) is None


def test_importe_personal_coincide_con_bruto_en_compra_100_por_ciento_particular():
    """Cuando la compra queda neteada a $0 (100% personal, caso Cumo
    Store), el importe personal y el bruto reconstruido son el mismo
    número — la diferencia entre las dos funciones solo aparece en
    splits parciales (con remanente de deuda real)."""
    id_compra = _compra_de("Cumo Store")
    bruto = importe_bruto_compra_particular(id_compra)
    personal = importe_personal_compra_particular(id_compra)
    assert bruto is not None and personal is not None
    assert abs(bruto - personal) < 0.01


def test_importe_personal_devuelve_none_para_compra_sin_linea_particular():
    id_compra = _compra_de("Agüero Shamaim")
    assert importe_personal_compra_particular(id_compra) is None
