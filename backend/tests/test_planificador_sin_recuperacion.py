"""04/11/2026: al iniciar el sistema no se corre nada vencido; pasa al próximo horario."""

from datetime import datetime

from src.features.boveda import planificador
from src.features.boveda import repository as boveda_repo
from src.features.documentos_nuevos import repository as rutina_repo


def test_al_arrancar_lo_vencido_se_reprograma_sin_correr(monkeypatch):
    fijada, reprogramados = [], []
    monkeypatch.setattr(rutina_repo, "programacion",
                        lambda: {"activa": True, "horarios": "07:00,14:00", "proxima": datetime(2026, 11, 4, 7, 0)})
    monkeypatch.setattr(rutina_repo, "fijar_proxima", fijada.append)
    monkeypatch.setattr(boveda_repo, "portales_vencidos", lambda _a: [{"idPortal": 7}])
    monkeypatch.setattr(planificador, "reprogramar", lambda i, desde=None: reprogramados.append(i))
    monkeypatch.setattr("src.features.boveda.servicio.correr_portal",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe correr")))

    planificador.saltear_vencidas(datetime(2026, 11, 4, 9, 30))

    assert fijada == [datetime(2026, 11, 4, 14, 0)]
    assert reprogramados == [7]
