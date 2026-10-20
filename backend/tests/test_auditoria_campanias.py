import pytest
from src.features.revision_cuentas.auditoria_campanias import clasificar

CATALOGO = [{'IdCampaña': 17, 'Campaña': '2022/2023'}, {'IdCampaña': 18, 'Campaña': '2023'}, {'IdCampaña': 20, 'Campaña': 'No Aplica'}]


@pytest.mark.parametrize('texto,identificador,tipo,candidatos', [
    (' 2022/2023 ', None, 'falta_vinculo', [17]),
    ('2022/2023', 17, None, [17]),
    ('2022/2023', 18, 'texto_vinculo_discordantes', [17]),
    ('2022/2023', 999, 'identificador_inexistente', [17]),
    ('2022', None, 'texto_desconocido', []),
    ('', 17, 'sin_texto', []),
    (None, None, 'sin_asignacion', []),
    ('NO APLICA', None, 'no_aplica_sin_vinculo', [20]),
])
def test_clasificacion(texto, identificador, tipo, candidatos):
    assert clasificar(texto, identificador, CATALOGO) == (tipo, candidatos)


def test_catalogo_ambiguo_no_sugiere_correccion_univoca():
    catalogo = CATALOGO + [{'IdCampaña': 99, 'Campaña': '2022/2023'}]
    assert clasificar('2022/2023', None, catalogo) == ('texto_ambiguo', [17, 99])
