"""Ayudas para vincular archivos del disco local a un registro.

El backend corre en la misma PC que los archivos, así que puede hacer lo que
un navegador no puede: mostrar el selector nativo de Windows y ubicar en el
disco un archivo arrastrado (el navegador solo entrega nombre, tamaño y fecha,
nunca la ruta completa). No toca ninguna base de datos ni modifica archivos.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/api/documentos", tags=["documentos"])

_TIEMPO_MAX_BUSQUEDA_S = 8.0
_TOLERANCIA_MTIME_S = 2.0
_DIRS_IGNORADOS = {"node_modules", "$recycle.bin", "system volume information", ".dropbox.cache"}

_SCRIPT_SELECTOR = r"""
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true; $owner.Opacity = 0; $owner.ShowInTaskbar = $false
$owner.StartPosition = 'CenterScreen'; $owner.Show(); $owner.Activate()
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Title = $env:LH_TITULO
$d.Filter = 'PDF (*.pdf)|*.pdf|Todos los archivos (*.*)|*.*'
if ($env:LH_INICIAL -and (Test-Path -LiteralPath $env:LH_INICIAL -PathType Container)) { $d.InitialDirectory = $env:LH_INICIAL }
if ($d.ShowDialog($owner) -eq 'OK') { [Console]::Out.Write($d.FileName) }
$owner.Dispose()
"""


class RutaResponse(BaseModel):
    ruta: str | None = None


def _raices() -> list[Path]:
    """Carpetas donde se busca un archivo arrastrado, por orden de prioridad.
    Configurable con LA_HERENCIA_RAICES_DOCUMENTOS (separadas por `;`)."""
    env = os.environ.get("LA_HERENCIA_RAICES_DOCUMENTOS")
    if env:
        candidatas = [Path(p) for p in env.split(";") if p.strip()]
    else:
        home = Path.home()
        # Las carpetas chicas y de uso habitual primero (cortan la búsqueda antes);
        # Dropbox, que es enorme, al final.
        candidatas = [
            home / "Downloads",
            home / "Desktop",
            home / "Documents",
            home / "Dropbox" / "Giamigli de Bolivar SA",
            home / "Dropbox",
        ]
    return [p for p in candidatas if p.is_dir()]


def ubicar_archivo(nombre: str, tamano: int, modificado_ms: float | None) -> str | None:
    """Busca `nombre` con ese tamaño en las carpetas habituales. Ante varias
    coincidencias prefiere la de misma fecha de modificación y luego la de la
    carpeta de mayor prioridad."""
    nombre_l = nombre.lower()
    mtime_esperado = modificado_ms / 1000.0 if modificado_ms else None
    limite = time.monotonic() + _TIEMPO_MAX_BUSQUEDA_S
    vistos: set[str] = set()
    raices_recorridas: set[str] = set()
    candidatos: list[tuple[int, int, str]] = []  # coincidencias sin fecha igual: (1, orden_raiz, ruta)

    for orden, raiz in enumerate(_raices()):
        for dirpath, dirnames, filenames in os.walk(raiz):
            if time.monotonic() > limite:
                break
            # No re-recorrer una carpeta que ya fue una raíz anterior (Dropbox
            # contiene a la carpeta de la empresa).
            dirnames[:] = [
                d
                for d in dirnames
                if d.lower() not in _DIRS_IGNORADOS
                and os.path.normcase(os.path.realpath(os.path.join(dirpath, d))) not in raices_recorridas
            ]
            for f in filenames:
                if f.lower() != nombre_l:
                    continue
                ruta = os.path.join(dirpath, f)
                clave = os.path.normcase(os.path.realpath(ruta))
                if clave in vistos:
                    continue
                try:
                    st = os.stat(ruta)
                except OSError:
                    continue
                if st.st_size != tamano:
                    continue
                vistos.add(clave)
                misma_fecha = (
                    mtime_esperado is not None
                    and abs(st.st_mtime - mtime_esperado) <= _TOLERANCIA_MTIME_S
                )
                if misma_fecha:
                    return ruta
                candidatos.append((1, orden, ruta))
        raices_recorridas.add(os.path.normcase(os.path.realpath(raiz)))

    if not candidatos:
        return None
    candidatos.sort()
    return candidatos[0][2]


def _abrir_selector(titulo: str, inicial: str | None) -> str | None:
    env = {**os.environ, "LH_TITULO": titulo, "LH_INICIAL": inicial or ""}
    try:
        proc = subprocess.run(
            ["powershell.exe", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_SELECTOR],
            capture_output=True,
            env=env,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo abrir el selector de archivos: {exc}") from exc
    ruta = proc.stdout.decode("utf-8", errors="replace").strip()
    return ruta or None


def _exigir_cliente(valor: str | None) -> None:
    # Encabezado propio: fuerza un preflight CORS, así ninguna otra página web
    # puede abrir ventanas en esta PC.
    if valor != "1":
        raise HTTPException(status_code=403, detail="Solicitud no permitida.")


class SeleccionarRequest(BaseModel):
    titulo: str = "Seleccionar archivo"
    # Ruta actual (archivo o carpeta) para abrir el selector cerca de ella.
    inicial: str | None = None


@router.post("/seleccionar", response_model=RutaResponse)
async def seleccionar(
    body: SeleccionarRequest, x_la_herencia: str | None = Header(default=None)
) -> RutaResponse:
    """Abre el selector de archivos de Windows en esta PC y devuelve la ruta
    elegida (`ruta: null` si el usuario cancela)."""
    _exigir_cliente(x_la_herencia)
    inicial = None
    if body.inicial:
        p = Path(body.inicial.strip().strip('"'))
        inicial = str(p if p.is_dir() else p.parent)
    ruta = await run_in_threadpool(_abrir_selector, body.titulo, inicial)
    return RutaResponse(ruta=ruta)


@router.get("/ubicar", response_model=RutaResponse)
async def ubicar(
    nombre: str = Query(min_length=1),
    tamano: int = Query(ge=0),
    modificado: float | None = Query(default=None, description="lastModified del File, en ms"),
) -> RutaResponse:
    """Ruta completa de un archivo arrastrado al navegador, buscándolo en
    disco por nombre, tamaño y fecha (`ruta: null` si no se encuentra)."""
    if any(sep in nombre for sep in ("\\", "/")):
        raise HTTPException(status_code=400, detail="Solo se admite el nombre del archivo, sin carpeta.")
    ruta = await run_in_threadpool(ubicar_archivo, nombre, tamano, modificado)
    return RutaResponse(ruta=ruta)
