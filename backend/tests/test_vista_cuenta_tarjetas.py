"""034 (T027/T028): invariantes de SOLO LECTURA contra WC de la cuenta de tarjetas.

No escriben nada. Las pruebas que necesitan la vista ampliada se saltean mientras
`scripts.vista_tarjeta_cuenta_corriente` no se haya ejecutado.
"""
import json
import re
from pathlib import Path

import pytest

from src.db.connection import fetch_all, fetch_one

CONTACTOS_TARJETA = (372, 373, 503, 532, 533)
UATRE = 315
ORIGENES_NUEVOS = ("Tarjeta consumo", "Tarjeta cargo", "Tarjeta devolución", "Tarjeta pago", "Mercado Pago")
FLUJO_CAJA = Path(__file__).resolve().parents[1] / "src" / "features" / "flujo_caja"
SNAPSHOT = Path(r"C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Auditoria cuentas corrientes\instantanea_034_antes.json")


def _vista_ampliada() -> bool:
    d = fetch_one("SELECT OBJECT_DEFINITION(OBJECT_ID('dbo.vw_MovimientosCuenta_Base')) AS d", ())["d"] or ""
    return all(f"'{o}'" in d for o in ORIGENES_NUEVOS)


def test_consumos_de_tarjeta_igual_a_vinculados_mas_resto_mas_sin_proveedor():
    """FR-018 / SC-008: la deuda de consumos tiene su contrapartida en el proveedor, o queda señalada sin proveedor."""
    fila = fetch_one(
        """
        SELECT ROUND(SUM(x.imp), 2) AS consumos, ROUND(SUM(x.vinc), 2) AS vinculado,
               ROUND(SUM(CASE WHEN x.ic IS NOT NULL THEN x.imp - x.vinc ELSE 0 END), 2) AS resto_con_proveedor,
               ROUND(SUM(CASE WHEN x.ic IS NULL THEN x.imp - x.vinc ELSE 0 END), 2) AS sin_proveedor
        FROM (SELECT l.Importe AS imp, l.IdContacto AS ic,
                     ISNULL((SELECT SUM(v.ImporteImputado) FROM dbo.Tarjetas_Resumenes_Lineas_Compras v
                             WHERE v.IdLineaConsumo = l.IdLineaConsumo), 0) AS vinc
              FROM dbo.Tarjetas_Resumenes_Lineas l JOIN dbo.Tarjetas_Resumenes r ON r.IdResumen = l.IdResumen
              WHERE ISNULL(r.EstadoResumen, '') <> 'Cerrado') x
        """, ())
    assert abs(float(fila["consumos"]) - (float(fila["vinculado"]) + float(fila["resto_con_proveedor"]) + float(fila["sin_proveedor"]))) < 0.01
    # Lo que queda sin proveedor es pequeño y conocido (kit Starlink y sus compensaciones): nunca crece sin que lo señale el control.
    assert abs(float(fila["sin_proveedor"])) < 300_000


def test_ningun_pago_de_resumen_esta_asignado_a_un_proveedor():
    """FR-010a: los pagos bancarios de resúmenes van solo a contactos de tarjeta (o a la cuenta de la administración anterior)."""
    anteriores = [r["IdContactoAnterior"] for r in fetch_all(
        "SELECT IdContactoAnterior FROM dbo.TarjetasContacto WHERE IdContactoAnterior IS NOT NULL", ())] \
        if fetch_one("SELECT OBJECT_ID('dbo.TarjetasContacto', 'U') AS t", ())["t"] else []
    permitidos = set(CONTACTOS_TARJETA) | set(anteriores)
    ajenos = fetch_all(
        """
        SELECT p.IdPago, p.Origen, COALESCE(b.IdContacto, g.IdContacto) AS contacto
        FROM dbo.Tarjetas_Resumenes_Pagos p
        LEFT JOIN dbo.[Movimientos BNA] b ON p.Origen = 'BNA' AND b.IdMovimientoBNA = p.IdMovimientoOrigen
        LEFT JOIN dbo.[Movimientos Galicia] g ON p.Origen = 'Galicia' AND g.IdMovimiento = p.IdMovimientoOrigen
        WHERE p.Origen IN ('BNA', 'Galicia')
        """, ())
    assert [a for a in ajenos if a["contacto"] not in permitidos] == []


@pytest.mark.skipif(not _vista_ampliada(), reason="la vista todavía no tiene las ramas de 034")
def test_ramas_nuevas_solo_tocan_contactos_de_tarjeta_salvo_uatre():
    """FR-005: las ramas nuevas no suman filas a contactos que no son tarjetas, salvo UATRE (pago de la billetera del 04/09/2024)."""
    anteriores = [r["IdContactoAnterior"] for r in fetch_all(
        "SELECT IdContactoAnterior FROM dbo.TarjetasContacto WHERE IdContactoAnterior IS NOT NULL", ())]
    permitidos = set(CONTACTOS_TARJETA) | set(anteriores) | {UATRE}
    marcas = ",".join("?" * len(ORIGENES_NUEVOS))
    filas = fetch_all(
        f"SELECT DISTINCT IdContacto FROM dbo.vw_MovimientosCuenta_Base WHERE Origen IN ({marcas})", ORIGENES_NUEVOS)
    assert [f["IdContacto"] for f in filas if f["IdContacto"] not in permitidos] == []


@pytest.mark.skipif(not _vista_ampliada(), reason="la vista todavía no tiene las ramas de 034")
def test_saldo_de_cada_tarjeta_coincide_con_su_pendiente_neto_salvo_casos_senalados():
    """FR-009: el saldo de la cuenta coincide con el pendiente neto del módulo de tarjetas (< $1) salvo los casos que el control señala."""
    from src.features.tarjetas.compensaciones import get_compensaciones

    for id_tarjeta, contacto in {1: 373, 2: 503, 4: 532, 5: 533}.items():
        saldo = float(fetch_one(
            "SELECT ISNULL(SUM(ISNULL(Credito,0) - ISNULL(Deuda,0)), 0) AS s FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?",
            (contacto,))["s"])
        pendiente = sum(v["saldoPendiente"] for v in get_compensaciones(id_tarjeta).values())
        if id_tarjeta == 1:
            continue  # AgroNacion: depende del cruce de la devolución (US4); se valida allí
        assert abs(saldo + pendiente) < 1, (id_tarjeta, saldo, pendiente)


def test_flujo_de_caja_solo_lee_movimientos_bancarios_y_filtra_la_vista_por_compras():
    """FR-017: el flujo de caja real no consulta las ramas nuevas de la vista."""
    for archivo in FLUJO_CAJA.glob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        for rama in ORIGENES_NUEVOS:
            assert rama not in texto, (archivo.name, rama)
        for linea in texto.splitlines():
            if "vw_MovimientosCuenta_Base" in linea:
                # la única consulta existente se acota por origen 'Compras'
                contexto = texto[texto.index(linea): texto.index(linea) + 250]
                assert "Origen = 'Compras'" in contexto, (archivo.name, linea.strip())


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="no hay instantánea previa de 034")
def test_totales_mensuales_del_flujo_de_caja_son_identicos_a_la_instantanea_previa():
    """SC-007."""
    from scripts.vista_tarjeta_cuenta_corriente import _flujo_mensual

    previa = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["flujo"]
    assert _flujo_mensual() == previa
