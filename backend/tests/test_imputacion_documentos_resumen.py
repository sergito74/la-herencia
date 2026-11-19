from src.features.imputacion.documentos_resumen import destino, estado_documento


def test_destino_por_familia():
    assert destino({"idCultivo": 6, "cultivo": "Girasol", "idCampania": 32, "campania": "2026/2027", "estado": "Aprobada"})[1:] == ("Girasol 2026/2027", "agricultura")
    assert destino({"idCentro": 3, "centro": "Adm. General", "estado": "Aprobada"})[1:] == ("Adm. General", "administracion")
    assert destino({"ganaderia": True, "estado": "Aprobada"})[0] == "ganaderia"
    assert destino({"estado": "Aprobada"})[0] == "stock"
    assert destino({"estado": "RequiereIntervencion", "idCultivo": 6})[0] == "decision"


def test_estado_del_documento_toma_el_mas_urgente():
    assert estado_documento({"Aprobada", "RequiereIntervencion"}, False) == "decision"
    assert estado_documento({"Aprobada"}, True) == "revisar"
    assert estado_documento({"Aprobada", "Pendiente"}, False) == "pendiente"
    assert estado_documento({"Aprobada"}, False) == "aprobado"
    assert estado_documento(set(), False) == "aprobado"
