import os

from fastapi.testclient import TestClient

from src.features.documentos import router as documentos
from src.main import app

client = TestClient(app)


def _crear(base, rel, contenido=b"x", mtime=None):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(contenido)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def test_ubicar_encuentra_por_nombre_y_tamano(tmp_path, monkeypatch):
    monkeypatch.setenv("LA_HERENCIA_RAICES_DOCUMENTOS", str(tmp_path))
    esperado = _crear(tmp_path, "a/b/resumen.pdf", b"12345")
    _crear(tmp_path, "c/resumen.pdf", b"otro-tamano")
    r = client.get("/api/documentos/ubicar", params={"nombre": "RESUMEN.pdf", "tamano": 5})
    assert r.status_code == 200 and r.json()["ruta"] == str(esperado)


def test_ubicar_prefiere_misma_fecha_de_modificacion(tmp_path, monkeypatch):
    monkeypatch.setenv("LA_HERENCIA_RAICES_DOCUMENTOS", str(tmp_path))
    _crear(tmp_path, "a/resumen.pdf", b"123", mtime=1_700_000_000)
    buscado = _crear(tmp_path, "z/resumen.pdf", b"123", mtime=1_600_000_000)
    r = client.get(
        "/api/documentos/ubicar",
        params={"nombre": "resumen.pdf", "tamano": 3, "modificado": 1_600_000_000_000},
    )
    assert r.json()["ruta"] == str(buscado)


def test_ubicar_sin_coincidencia_devuelve_null(tmp_path, monkeypatch):
    monkeypatch.setenv("LA_HERENCIA_RAICES_DOCUMENTOS", str(tmp_path))
    r = client.get("/api/documentos/ubicar", params={"nombre": "nada.pdf", "tamano": 1})
    assert r.status_code == 200 and r.json()["ruta"] is None


def test_ubicar_rechaza_nombre_con_carpeta():
    r = client.get("/api/documentos/ubicar", params={"nombre": "..\\secreto.pdf", "tamano": 1})
    assert r.status_code == 400


def test_seleccionar_exige_encabezado_del_cliente():
    r = client.post("/api/documentos/seleccionar", json={})
    assert r.status_code == 403


def test_seleccionar_devuelve_ruta_y_null_al_cancelar(monkeypatch):
    monkeypatch.setattr(documentos, "_abrir_selector", lambda titulo, inicial: r"C:\x\a.pdf")
    r = client.post("/api/documentos/seleccionar", json={}, headers={"X-La-Herencia": "1"})
    assert r.json() == {"ruta": r"C:\x\a.pdf"}
    monkeypatch.setattr(documentos, "_abrir_selector", lambda titulo, inicial: None)
    r = client.post("/api/documentos/seleccionar", json={}, headers={"X-La-Herencia": "1"})
    assert r.json() == {"ruta": None}
