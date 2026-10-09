"""Contract tests de GET /api/revision-cuentas/archivos/incompletos (036, T045). Raíz temporal: nunca la real de Dropbox; no modifica archivos."""

from __future__ import annotations

import httpx
import pytest

from src.features.revision_cuentas import archivos
from src.main import app

URL = "/api/revision-cuentas/archivos/incompletos"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def raiz(monkeypatch, tmp_path):
    p = tmp_path / "04 2025 - 03 2026"
    p.mkdir()
    (p / "20250923_JaureguiYMorales.crdownload").write_bytes(b"%PDF-legible")
    (p / "20251212_JaureguiYMorales.crdownload").write_bytes(b"")
    (p / "20250103_JaureguiYMorales.jpg").write_bytes(b"\xff\xd8\xff")
    monkeypatch.setenv("COMPRAS_RAIZ", str(tmp_path))
    monkeypatch.setattr(archivos, "_cargadas", lambda: ({"900077393": 2143522625}, []))
    monkeypatch.setattr(archivos, "_texto_pdf", lambda ruta: "Asiento 0 A 0009-00077393\n23/09/2025\nFACTURA\nGIAMIGLI DE BOLIVAR S.A.\nTOTAL 30017,03")
    return tmp_path


async def _get(**params) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(URL, params=params or None)


@pytest.mark.anyio
async def test_lista_los_archivos_incompletos_con_la_forma_del_contrato(raiz):
    r = await _get(periodo="04 2025 - 03 2026")
    assert r.status_code == 200
    b = r.json()
    assert b["raiz"] == str(raiz) and b["total"] == 3
    legible = next(a for a in b["archivos"] if a["estado"] == "comprobante-legible-extension-incorrecta")
    assert legible["numero"] == "0009-00077393" and legible["importe"] == 30017.03 and legible["cargado"] is True and legible["idCompra"] == 2143522625
    assert legible["proveedor"] == "JaureguiYMorales" and legible["fecha"] == "2025-09-23" and legible["periodo"] == "04 2025 - 03 2026"
    assert {a["estado"] for a in b["archivos"]} == {"comprobante-legible-extension-incorrecta", "vacio", "imagen-revisar"}


@pytest.mark.anyio
async def test_filtra_por_estado(raiz):
    b = (await _get(estado="vacio")).json()
    assert b["total"] == 1 and b["archivos"][0]["ruta"].endswith("20251212_JaureguiYMorales.crdownload")


@pytest.mark.anyio
async def test_sin_periodo_recorre_todas_las_carpetas_de_periodo(raiz):
    assert (await _get()).json()["total"] == 3


@pytest.mark.anyio
async def test_un_periodo_con_formato_incorrecto_devuelve_422(raiz):
    for periodo in ("2025", "..", "04 2025 - 03 2027", "../otros"):
        assert (await _get(periodo=periodo)).status_code == 422


@pytest.mark.anyio
async def test_un_estado_desconocido_o_un_tamano_excesivo_devuelven_422(raiz):
    assert (await _get(estado="inventado")).status_code == 422
    assert (await _get(tamano=201)).status_code == 422


@pytest.mark.anyio
async def test_el_cliente_no_puede_elegir_la_raiz(raiz):
    """Un parámetro `raiz` o una ruta mandada por el cliente se ignora: la raíz es la del backend."""
    b = (await _get(raiz="C:\\Windows", ruta="C:\\Windows")).json()
    assert b["raiz"] == str(raiz)


@pytest.mark.anyio
async def test_la_consulta_no_modifica_los_archivos(raiz):
    antes = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in raiz.rglob("*") if p.is_file()}
    await _get(periodo="04 2025 - 03 2026")
    assert {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in raiz.rglob("*") if p.is_file()} == antes
