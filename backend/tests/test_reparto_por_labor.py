from src.features.imputacion.motor import misma_labor


def test_cada_renglon_va_a_su_labor():
    assert misma_labor("Siembra", "Siembra")
    assert misma_labor("Fertilizacion", "Fertilizacion terrestre")
    assert misma_labor("Fumigacion", "Pulverizacion aerea")
    assert not misma_labor("Siembra", "Fertilizacion terrestre")
    assert not misma_labor("Fertilizacion", "Siembra")
    assert not misma_labor("Cosecha", "Siembra")
