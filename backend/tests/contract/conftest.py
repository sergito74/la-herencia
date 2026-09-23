"""016-autenticacion: la API ahora exige sesión (AuthMiddleware, FR-001).

Los contract tests preexistentes construyen su propio `httpx.AsyncClient`
contra un `ASGITransport(app=app)`, sin conocer la cookie de sesión. Para
no editar cada archivo uno por uno, se parchea `httpx.AsyncClient` para
que agregue una cookie de sesión `Administrador` por defecto cuando el
test no especifica `cookies` explícitamente — preserva el comportamiento
existente (SC-003) sin ocultar los tests que sí ejercitan la auth
directamente (le alcanza con pasar `cookies=...` para tomar el control).
"""

from __future__ import annotations

import httpx

from src.auth.tokens import crear_token
from src.features.auth.router import COOKIE_NAME

_ADMIN_COOKIES = {COOKIE_NAME: crear_token(id_usuario=0, rol="Administrador")}

_original_init = httpx.AsyncClient.__init__


def _init_with_default_admin_cookie(self, *args, **kwargs):
    kwargs.setdefault("cookies", _ADMIN_COOKIES)
    _original_init(self, *args, **kwargs)


httpx.AsyncClient.__init__ = _init_with_default_admin_cookie
