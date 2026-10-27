"""Conectores de los 4 portales de peaje (042, T030).

Envuelven el código de 037 (`descarga_peajes/portales.py` y `lectores.py`) sin
reescribirlo: el ingreso y el listado siguen siendo los de 037, ahora con la
credencial que viene de la bóveda. Todos los documentos se cargan como
Factura A en Compras (también el resumen de Telepeaje, por el sello), con la
clasificación de 037 (rubro Viáticos, centro de costo 3) y la regla de cierre
al centavo de la bóveda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.features.boveda.conectores import (
    Credencial, CredencialesRechazadas, DatosCompra, DocumentoPortal, MapeoProveedor, PortalCambio, registrar,
)
from src.features.descarga_peajes import carga as carga_037
from src.features.descarga_peajes import lectores, portales


@dataclass
class _Sesion:
    pw: object
    credencial: Credencial = field(repr=False)
    ctx: object = None


class ConectorPeaje:
    tiene_estado_cuenta = False
    tiene_carga_compras = True

    def __init__(self, codigo: str, nombre: str, listar):
        self.codigo = codigo
        self.nombre = nombre
        self._listar = listar
        self.mapeo_proveedores = {
            p: MapeoProveedor(id_contacto=c, rubro=str(carga_037.RUBRO_VIATICOS), centro_costo=str(carga_037.CENTRO_COSTO))
            for p, c in portales.CONTACTOS.items()
        }

    def ingresar(self, pw, credencial: Credencial) -> _Sesion:
        # El ingreso de 037 va junto con el listado (mismo navegador).
        return _Sesion(pw=pw, credencial=credencial)

    def listar_documentos(self, sesion: _Sesion) -> list[DocumentoPortal]:
        try:
            c = sesion.credencial
            docs, ctx, _avisos = self._listar(sesion.pw, (c.usuario or "", c.clave.valor() if c.clave else ""))
        except portales.ErrorIngreso as e:
            # 037 no distingue clave rechazada de captcha: se trata como rechazo (suspende y no reintenta,
            # para no bloquear la cuenta). Se reanuda al cambiar la clave o al volver a guardar la programación.
            raise CredencialesRechazadas(str(e)) from None
        except portales.ErrorPortal as e:
            raise PortalCambio(str(e)) from None
        sesion.ctx = ctx
        return [
            DocumentoPortal(
                clave=d["clave"], fecha=d["fecha"], tipo="factura", proveedor=d["proveedor"], bajar=d["bajar"],
                detalle=d["detalle"], id_contacto=d["idContacto"], moneda="ARS",
                equivalentes=list(d.get("equivalentes", [])),
            )
            for d in docs
        ]

    def estado_cuenta(self, sesion: _Sesion):
        return []

    def leer_comprobante(self, documento: DocumentoPortal, pdf: bytes) -> DatosCompra | None:
        try:
            leido = lectores.leer(documento.proveedor, lectores.texto_pdf(pdf))
        except lectores.NoReconocido:
            return None
        if not documento.id_contacto:
            cabecera, lineas = carga_037.armar_compra(leido, 0, "")
            cabecera["idContacto"] = None
        else:
            cabecera, lineas = carga_037.armar_compra(leido, documento.id_contacto, "")
        return DatosCompra(cabecera=cabecera, lineas=lineas, numero=leido.numero,
                           total_impreso=Decimal(str(leido.total_impreso)))

    def cerrar(self, sesion: _Sesion) -> None:
        if sesion.ctx is not None:
            sesion.ctx.browser.close()


for _codigo, _nombre, _listar in (
    ("telepeajeplus", "TelepeajePlus", portales.listar_telepeajeplus),
    ("telepase", "TelePASE", portales.listar_telepase),
    ("ceamse", "CEAMSE", portales.listar_ceamse),
    ("aubasa", "AUBASA", portales.listar_aubasa),
):
    registrar(ConectorPeaje(_codigo, _nombre, _listar))
