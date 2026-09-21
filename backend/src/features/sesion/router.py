"""Estado de sesión del navegador (en memoria, sin base de datos).

El frontend manda un latido por pestaña abierta y avisa cuando se cierra;
el lanzador de escritorio (launcher/LaHerencia.ps1 -Watch) consulta
/estado para apagar el sistema al cerrarse la última pestaña o tras
inactividad. Sin lanzador nada de esto tiene efecto.
"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/sesion", tags=["sesion"])

# Una pestaña en segundo plano puede latir solo una vez por minuto
# (throttling del navegador); pasado este plazo sin latido se la da por muerta
# (navegador caído sin poder avisar el cierre).
TAB_TIMEOUT_S = 180.0


class _Estado:
    def __init__(self) -> None:
        self.reiniciar()

    def reiniciar(self) -> None:
        now = time.monotonic()
        self.tabs: dict[str, float] = {}
        self.ultima_actividad = now
        self.sin_pestanas_desde: float | None = now
        self.hubo_pestana = False

    def _purgar(self) -> None:
        now = time.monotonic()
        for tab_id in [t for t, seen in self.tabs.items() if now - seen > TAB_TIMEOUT_S]:
            del self.tabs[tab_id]
        if not self.tabs and self.sin_pestanas_desde is None:
            self.sin_pestanas_desde = now

    def latido(self, tab_id: str, activo: bool) -> None:
        now = time.monotonic()
        self.tabs[tab_id] = now
        self.sin_pestanas_desde = None
        self.hubo_pestana = True
        if activo:
            self.ultima_actividad = now

    def cierre(self, tab_id: str) -> None:
        self.tabs.pop(tab_id, None)
        if not self.tabs:
            self.sin_pestanas_desde = time.monotonic()

    def estado(self) -> dict:
        self._purgar()
        now = time.monotonic()
        return {
            "pestanasAbiertas": len(self.tabs),
            "huboPestana": self.hubo_pestana,
            "segundosSinActividad": round(now - self.ultima_actividad, 1),
            "segundosSinPestanas": (
                0.0
                if self.sin_pestanas_desde is None
                else round(now - self.sin_pestanas_desde, 1)
            ),
        }


_estado = _Estado()


async def _leer(request: Request) -> dict:
    # Se envía como text/plain (request "simple", sin preflight CORS) para que
    # navigator.sendBeacon funcione durante el cierre de la pestaña.
    try:
        data = json.loads(await request.body())
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


@router.post("/latido", status_code=204)
async def latido(request: Request) -> None:
    body = await _leer(request)
    tab_id = str(body.get("tabId") or "")
    if tab_id:
        _estado.latido(tab_id, bool(body.get("activo")))


@router.post("/cierre", status_code=204)
async def cierre(request: Request) -> None:
    body = await _leer(request)
    tab_id = str(body.get("tabId") or "")
    if tab_id:
        _estado.cierre(tab_id)


@router.post("/inicio", status_code=204)
async def inicio() -> None:
    """El lanzador lo llama justo antes de abrir el navegador: empieza de cero
    los plazos, para que un sistema que estuvo horas sin uso no se apague antes
    de que cargue la pestaña nueva."""
    _estado.reiniciar()


@router.get("/estado")
async def estado() -> dict:
    return _estado.estado()
