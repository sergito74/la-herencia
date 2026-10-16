import pytest

from src.features.ordenes import distribucion


def _dist(dosis, superficie, aplicar=True):
    return {"dosisHa": dosis, "superficie": superficie, "aplicar": aplicar}


def test_repartir_total_proporcional_al_peso_dosis_por_superficie():
    """Ejemplo real del usuario: 260 litros de Glifosato, lotes 1/2 (soja,
    2.3 l/ha), lote 3 (maíz, 2.8 l/ha), lote 4 (girasol, 3.2 l/ha), superficies
    20/26/16/32 ha — la cantidad de cada lote es el total repartido según su
    peso dosis×superficie, no dosis×superficie en valor absoluto."""
    distribuciones = [_dist(2.3, 20), _dist(2.3, 26), _dist(2.8, 16), _dist(3.2, 32)]
    repartidas = distribucion.repartir_total(260, distribuciones)
    pesos = [2.3 * 20, 2.3 * 26, 2.8 * 16, 3.2 * 32]
    peso_total = sum(pesos)
    for r, peso in zip(repartidas, pesos):  # el lote mayor absorbe el residuo del redondeo (≤ 0,0001 por lote)
        assert r["cantidadAsignada"] == pytest.approx(260 * peso / peso_total, abs=5e-4)
    assert round(sum(r["cantidadAsignada"] for r in repartidas), 4) == 260


def test_repartir_total_lote_no_aplicado_recibe_cero():
    distribuciones = [_dist(2, 10), _dist(3, 5, aplicar=False)]
    repartidas = distribucion.repartir_total(20, distribuciones)
    assert repartidas[0]["cantidadAsignada"] == 20
    assert repartidas[1]["cantidadAsignada"] == 0


def test_repartir_total_dosis_cero_recibe_cero():
    distribuciones = [_dist(2, 10), _dist(0, 5)]
    repartidas = distribucion.repartir_total(20, distribuciones)
    assert repartidas[0]["cantidadAsignada"] == 20
    assert repartidas[1]["cantidadAsignada"] == 0


def test_repartir_total_sin_peso_no_reparte_nada():
    repartidas = distribucion.repartir_total(20, [_dist(0, 10)])
    assert repartidas[0]["cantidadAsignada"] == 0


def test_validar_cierre_exacto_no_lanza():
    distribuciones = distribucion.repartir_total(35, [_dist(2, 10), _dist(3, 5)])
    distribucion.validar_cierre(35, distribuciones)


def test_validar_cierre_sin_devolucion_lanza_si_no_cierra():
    distribuciones = distribucion.repartir_total(35, [_dist(2, 10), _dist(3, 5)])
    with pytest.raises(ValueError):
        distribucion.validar_cierre(50, distribuciones)


def test_validar_cierre_con_devolucion_cierra():
    distribuciones = distribucion.repartir_total(20, [_dist(2, 10)])  # repartido = 20
    distribucion.validar_cierre(25, distribuciones, devoluciones=[5])


def test_repartir_total_cierra_exacto_aunque_el_redondeo_no_de():
    # 16 entre tres lotes iguales da 5,3333 c/u = 15,9999: el residuo va a un lote.
    repartidas = distribucion.repartir_total(16, [_dist(1, 10), _dist(1, 10), _dist(1, 10)])
    assert round(sum(d["cantidadAsignada"] for d in repartidas), 4) == 16
    distribucion.validar_cierre(16, repartidas)


def test_mensaje_de_cierre_nombra_el_insumo():
    distribuciones = distribucion.repartir_total(35, [_dist(2, 10), _dist(3, 5)])
    with pytest.raises(ValueError) as exc:
        distribucion.validar_cierre(50, distribuciones, producto="POWER PLUS II", unidad="LTS")
    assert "«POWER PLUS II»" in exc.value.args[0][0] and "faltan 15 LTS" in exc.value.args[0][0]
