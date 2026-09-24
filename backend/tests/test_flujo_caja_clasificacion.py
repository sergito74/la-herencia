"""Casos reales conocidos de `WC` para las reglas de clasificación (018,
research.md §1) — ver clasificacion.py."""

from src.features.flujo_caja.clasificacion import es_interno


def test_galicia_inversiones_es_interno():
    assert es_interno("Galicia", None, "000916 - Inversiones") is True


def test_galicia_impuestos_no_es_interno():
    assert es_interno("Galicia", None, "000901 - Impuestos") is False


def test_galicia_transferencias_no_es_interno_por_default():
    # research.md §1: "Transferencias" (907) mezcla operativo con interno —
    # queda fuera de alcance de 018, se muestra como operativo por default.
    assert es_interno("Galicia", None, "000907 - Transferencias") is False


def test_bna_transferencia_a_cuenta_propia_es_interno():
    assert es_interno("BNA", "CRED BE O BCO-MIS TIT IBK - CUIT/CUIL: 30712114602") is True


def test_bna_transferencia_generica_no_es_interno():
    assert es_interno("BNA", "EMIS TRANSFERENCIA/GIRO") is False


def test_bna_patron_titular_con_otro_cuit_no_es_interno():
    # Mismo patrón de texto ("DIS TIT") pero con un CUIT que no es el de la
    # empresa — no se puede asumir que es una cuenta propia.
    assert es_interno("BNA", "C BE TR O/BCO-DIS TIT IBK - CUIT/CUIL: 30506792165") is False


def test_movimiento_sin_concepto_no_se_excluye():
    # FR-009: sin señal de clasificación, el movimiento se muestra como
    # operativo (nunca se excluye del neto en silencio).
    assert es_interno("BNA", None) is False
    assert es_interno("Galicia", None, None) is False
