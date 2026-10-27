"""API de la Bóveda de portales (042, contracts/api.md).

Todo el router exige rol `Administrador` (FR-001), además de la sesión del
middleware global. Ninguna respuesta lleva secretos salvo `revelar`, que va
con `Cache-Control: no-store` y queda auditado.
"""

from __future__ import annotations

import ntpath
from datetime import datetime, time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from src.features.auth.repository import get_usuario_por_id
from src.features.boveda import cifrado, planificador, repository, servicio
from src.features.boveda.conectores import cargar_conectores
from src.features.boveda.schemas import (
    Autorizacion, AutorizacionEntrada, ClaveNueva, ConectorInfo, CorridaResumen, CredencialEdicion, CredencialNueva,
    CredencialResumen, CredencialSalida, FotoResumen, FotoRevision, Lista, PedidoRevelar, PedidoSincronizar,
    PortalEdicion, PortalEntrada, PortalSalida, Programacion, ProgramacionEntrada, Progreso, Revelado,
)

ESTADOS_CARGA = {"cargado_auto", "ya_cargado", "pendiente", "no_aplica", "historico"}


def exigir_admin(request: Request) -> None:
    payload = getattr(request.state, "usuario", None) or {}
    if payload.get("rol") != "Administrador":
        raise HTTPException(status_code=403, detail="Solo el administrador accede a la bóveda")


router = APIRouter(prefix="/api/boveda", tags=["boveda"], dependencies=[Depends(exigir_admin)])


def usuario_actual(request: Request) -> str | None:
    payload = getattr(request.state, "usuario", None) or {}
    try:
        u = get_usuario_por_id(payload.get("idUsuario"))
        return (u or {}).get("NombreUsuario")
    except Exception:
        return None


def iso(valor) -> str | None:
    """`datetime2` llega del driver ODBC como texto ("2026-11-02 09:00:00.0000000"): se normaliza a ISO."""
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor.replace(" ", "T", 1).split(".")[0]
    return valor.isoformat()


def _conector_info(codigo: str | None) -> ConectorInfo:
    con = cargar_conectores().get(codigo) if codigo else None
    if con is None:
        return ConectorInfo(codigo=codigo, disponible=False)
    return ConectorInfo(codigo=codigo, nombre=con.nombre, disponible=True,
                        estadoCuenta=con.tiene_estado_cuenta, cargaCompras=con.tiene_carga_compras)


PROXIMAMENTE = "Próximamente"

# Portales que piden una verificación humana en cada ingreso (relevamientos 042): no se pueden automatizar.
SIN_AUTOMATIZAR = {
    "tributaria.hacienda.bolivar.gob.ar": "No se puede automatizar: pide un código de verificación en cada consulta",
    "auth.allianz.com.ar": "No se puede automatizar: manda un código por mail en cada ingreso",
    "www.lartirigoyen.com.ar": "No se puede automatizar: pide marcar \"No soy un robot\" en cada ingreso",
    "extranet.lartirigoyen.com.ar": "No se puede automatizar: pide marcar \"No soy un robot\" en cada ingreso",
}


# Portales sin automatizar que facturan todos los meses: se recuerda bajar a mano la factura que falte en Compras.
RECORDATORIO_MENSUAL = {"auth.allianz.com.ar"}
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre")


def recordatorio(f: dict) -> str | None:
    if f["codigoConector"] or not f["idContacto"] or urlparse(f.get("url") or "").hostname not in RECORDATORIO_MENSUAL:
        return None
    faltan = repository.meses_sin_factura(f["idContacto"], datetime.now().date())
    if not faltan:
        return None
    meses = " y ".join(f"{_MESES[m.month - 1]} {m.year}" for m in faltan)
    return f"Falta la factura de {meses}: entrá al portal y bajala"


def motivo_no_sincroniza(f: dict) -> str | None:
    # Primero lo que el usuario puede resolver; lo que falta del lado del sistema se muestra como "Próximamente".
    if not f["codigoConector"]:
        host = urlparse(f.get("url") or "").hostname or ""
        if host in SIN_AUTOMATIZAR:
            return SIN_AUTOMATIZAR[host]
    if f["autFecha"] is None:
        return "Falta tu autorización"
    if not f["idCredencial"] or not f["claveConfigurada"]:
        return "Falta cargar usuario y contraseña"
    if f["credencialRechazada"]:
        return "El portal rechazó la contraseña: actualizala"
    if not f["codigoConector"] or f["codigoConector"] not in cargar_conectores():
        return PROXIMAMENTE
    return None


def portal_salida(f: dict, cola: list[int] | None = None) -> PortalSalida:
    credencial = None
    if f["idCredencial"]:
        estado = "rechazada" if f["credencialRechazada"] else ("ok" if f["claveConfigurada"] else "faltante")
        credencial = CredencialResumen(idCredencial=f["idCredencial"], nombre=f["credencialNombre"],
                                       usuario=f["credencialUsuario"], claveConfigurada=bool(f["claveConfigurada"]),
                                       estado=estado)
    programacion = None
    if f["frecuencia"]:
        programacion = Programacion(
            frecuencia=f["frecuencia"], diaSemana=f["diaSemana"], diaMes=f["diaMes"], hora=f["hora"],
            proximaCorrida=iso(f["proximaCorrida"]),
            suspendida=bool(f["suspendida"]), motivoSuspension=f["motivoSuspension"],
        )
    corrida = None
    if f["ucId"]:
        corrida = CorridaResumen(idCorrida=f["ucId"], inicio=iso(f["ucInicio"]), fin=iso(f["ucFin"]), estado=f["ucEstado"],
                                 nuevos=f["ucNuevos"], existentes=f["ucExistentes"], cargados=f["ucCargados"],
                                 pendientes=f["ucPendientes"], mensaje=f["ucMensaje"])
    foto = None
    if f["ufFechaCorte"]:
        foto = FotoResumen(fechaCorte=f["ufFechaCorte"], moneda=f["ufMoneda"], saldoPortal=f["ufSaldoPortal"],
                           saldoSistema=f["ufSaldoSistema"], diferencia=f["ufDiferencia"])
    return PortalSalida(
        idPortal=f["idPortal"], nombre=f["nombre"], url=f["url"], tipo=f["tipo"], idContacto=f["idContacto"],
        contacto=f["contacto"], notas=f["notas"], credencial=credencial, conector=_conector_info(f["codigoConector"]),
        autorizacion=Autorizacion(vigente=f["autFecha"] is not None, fecha=f["autFecha"], autorizadoPor=f["autPor"],
                                  fuente=f["autFuente"]),
        programacion=programacion, ultimaCorrida=corrida, ultimaFoto=foto,
        enCurso=f["ucEstado"] == "en_curso",
        enCola=f["idPortal"] in (cola if cola is not None else servicio.en_cola()) and f["ucEstado"] != "en_curso",
        progreso=Progreso(paso=f["ucPaso"], hecho=f["ucHecho"], total=f["ucTotal"]) if f["ucEstado"] == "en_curso" else None,
        motivoNoSincroniza=motivo_no_sincroniza(f),
        recordatorio=recordatorio(f),
    )


def _portal_o_404(id_portal: int) -> dict:
    fila = repository.obtener_portal(id_portal)
    if fila is None:
        raise HTTPException(status_code=404, detail="Portal inexistente")
    return fila


def _validar_portal(nombre: str | None, codigo: str | None, id_contacto: int | None, id_credencial: int | None,
                    excepto: int | None = None) -> None:
    if nombre is not None and repository.existe_nombre_portal(nombre, excepto):
        raise HTTPException(status_code=400, detail="Ya existe un portal con ese nombre")
    if codigo and codigo not in cargar_conectores():
        raise HTTPException(status_code=400, detail="Conector desconocido")
    if id_contacto is not None and not repository.existe_contacto(id_contacto):
        raise HTTPException(status_code=400, detail="Contacto inexistente")
    if id_credencial is not None and repository.obtener_credencial(id_credencial) is None:
        raise HTTPException(status_code=400, detail="Credencial inexistente")


# --- Conectores ---------------------------------------------------------------

@router.get("/conectores")
def conectores() -> list[ConectorInfo]:
    return [_conector_info(c) for c in sorted(cargar_conectores())]


# --- Portales -----------------------------------------------------------------

@router.get("/portales", response_model=Lista)
def listar_portales() -> Lista:
    cola = servicio.en_cola()
    return Lista(items=[portal_salida(f, cola) for f in repository.listar_portales()])


@router.get("/portales/{id_portal}", response_model=PortalSalida)
def obtener_portal(id_portal: int) -> PortalSalida:
    return portal_salida(_portal_o_404(id_portal))


@router.post("/portales", status_code=201)
def crear_portal(body: PortalEntrada, request: Request) -> dict:
    usuario = usuario_actual(request)
    if body.idCredencial and body.credencialNueva:
        raise HTTPException(status_code=400, detail="Elegir una credencial existente o una nueva, no ambas")
    _validar_portal(body.nombre, body.codigoConector, body.idContacto, body.idCredencial)
    id_credencial = body.idCredencial
    if body.credencialNueva:
        id_credencial = _crear_credencial(body.credencialNueva, usuario)
    try:
        id_portal = repository.crear_portal(body.nombre, body.url, body.tipo, body.idContacto, id_credencial,
                                            body.codigoConector, body.notas)
    except Exception:
        if body.credencialNueva and id_credencial:
            repository.borrar_credencial(id_credencial)
        raise
    repository.auditar("alta_portal", usuario, id_portal=id_portal, id_credencial=id_credencial, detalle=body.nombre)
    return {"idPortal": id_portal}


@router.patch("/portales/{id_portal}", response_model=PortalSalida)
def editar_portal(id_portal: int, body: PortalEdicion, request: Request) -> PortalSalida:
    _portal_o_404(id_portal)
    cambios = body.model_dump(exclude_unset=True)
    _validar_portal(cambios.get("nombre"), cambios.get("codigoConector"), cambios.get("idContacto"),
                    cambios.get("idCredencial"), excepto=id_portal)
    repository.editar_portal(id_portal, cambios)
    repository.auditar("edicion_portal", usuario_actual(request), id_portal=id_portal,
                       detalle=", ".join(sorted(cambios)))
    return portal_salida(_portal_o_404(id_portal))


# --- Credenciales -------------------------------------------------------------

def _crear_credencial(body: CredencialNueva, usuario: str | None) -> int:
    if body.titular == "socio" and body.idSocio is None:
        raise HTTPException(status_code=400, detail="Indicar el socio titular")
    try:
        id_credencial = repository.crear_credencial(
            body.nombre, body.titular, body.idSocio, body.usuario, body.clave,
            [d.model_dump() for d in body.datos if d.valor],
        )
    except cifrado.ClaveMaestraNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    repository.auditar("alta_credencial", usuario, id_credencial=id_credencial, detalle=body.nombre)
    return id_credencial


@router.get("/credenciales")
def listar_credenciales() -> list[CredencialSalida]:
    return [CredencialSalida(**c) for c in repository.listar_credenciales()]


@router.post("/credenciales", status_code=201)
def crear_credencial(body: CredencialNueva, request: Request) -> dict:
    return {"idCredencial": _crear_credencial(body, usuario_actual(request))}


@router.patch("/credenciales/{id_credencial}", status_code=204)
def editar_credencial(id_credencial: int, body: CredencialEdicion, request: Request) -> Response:
    if repository.obtener_credencial(id_credencial) is None:
        raise HTTPException(status_code=404, detail="Credencial inexistente")
    datos = [d.model_dump() for d in body.datos] if body.datos is not None else None
    try:
        repository.editar_credencial(id_credencial, body.nombre, body.usuario, datos)
    except cifrado.ClaveMaestraNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    repository.auditar("edicion_credencial", usuario_actual(request), id_credencial=id_credencial)
    return Response(status_code=204)


@router.put("/credenciales/{id_credencial}/clave", status_code=204)
def cambiar_clave(id_credencial: int, body: ClaveNueva, request: Request) -> Response:
    try:
        cambiadas = repository.cambiar_clave(id_credencial, body.clave)
    except cifrado.ClaveMaestraNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if not cambiadas:
        raise HTTPException(status_code=404, detail="Credencial inexistente")
    repository.auditar("cambio_clave", usuario_actual(request), id_credencial=id_credencial)
    for id_portal in repository.levantar_suspension_credencial(id_credencial):
        planificador.reprogramar(id_portal)
    return Response(status_code=204)


@router.post("/credenciales/{id_credencial}/revelar", response_model=Revelado)
def revelar(id_credencial: int, body: PedidoRevelar, request: Request, response: Response) -> Revelado:
    response.headers["Cache-Control"] = "no-store"
    try:
        if body.campo == "clave":
            blob = repository.leer_clave_cifrada(id_credencial)
            if not blob:
                raise HTTPException(status_code=404, detail="La credencial no tiene contraseña guardada")
            secreto = cifrado.descifrar(blob, cifrado.aad_clave(id_credencial))
        else:
            nombre = body.campo.split(":", 1)[1]
            dato = next((d for d in repository.leer_datos(id_credencial) if d["nombre"] == nombre and d["secreto"]), None)
            if dato is None:
                raise HTTPException(status_code=404, detail="Dato secreto inexistente")
            secreto = cifrado.descifrar(dato["valorCifrado"], cifrado.aad_dato(id_credencial, nombre))
    except cifrado.ClaveMaestraNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="No se pudo descifrar: la clave maestra no corresponde") from None
    repository.auditar("revelar", usuario_actual(request), id_credencial=id_credencial, detalle=body.campo)
    return Revelado(valor=secreto.valor())


# --- Autorización -------------------------------------------------------------

@router.post("/portales/{id_portal}/autorizacion", status_code=201)
def autorizar(id_portal: int, body: AutorizacionEntrada, request: Request) -> dict:
    _portal_o_404(id_portal)
    usuario = usuario_actual(request)
    id_aut = repository.autorizar(id_portal, body.fecha, body.autorizadoPor, body.fuente, usuario)
    repository.auditar("autorizar", usuario, id_portal=id_portal,
                       detalle=f"{body.fecha.isoformat()} {body.autorizadoPor}; {body.fuente or ''}")
    return {"idAutorizacion": id_aut}


@router.delete("/portales/{id_portal}/autorizacion", status_code=204)
def revocar(id_portal: int, request: Request) -> Response:
    _portal_o_404(id_portal)
    usuario = usuario_actual(request)
    if repository.revocar(id_portal, usuario):
        repository.auditar("revocar", usuario, id_portal=id_portal)
    return Response(status_code=204)


# --- Programación y corridas -------------------------------------------------------

def _exigir_conector(fila: dict) -> None:
    if not fila["codigoConector"] or fila["codigoConector"] not in cargar_conectores():
        raise HTTPException(status_code=400, detail="Esta cuenta todavía no tiene sincronización automática")


@router.put("/portales/{id_portal}/programacion", response_model=PortalSalida)
def programar(id_portal: int, body: ProgramacionEntrada, request: Request) -> PortalSalida:
    fila = _portal_o_404(id_portal)
    _exigir_conector(fila)
    hora = time.fromisoformat(body.hora)
    dia_semana = body.diaSemana if body.frecuencia == "semanal" else None
    dia_mes = body.diaMes if body.frecuencia == "mensual" else None
    try:
        proxima = planificador.proxima_corrida(body.frecuencia, dia_semana, dia_mes, hora, datetime.now())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    repository.guardar_programacion(id_portal, body.frecuencia, dia_semana, dia_mes, hora, proxima)
    repository.auditar("programar", usuario_actual(request), id_portal=id_portal,
                       detalle=f"{body.frecuencia} {dia_semana or dia_mes or ''} {body.hora}")
    return portal_salida(_portal_o_404(id_portal))


@router.post("/portales/{id_portal}/corridas", status_code=202)
def correr_ahora(id_portal: int, request: Request):
    """Sincroniza un portal; pasa por la misma cola que las tandas (nunca dos navegadores a la vez)."""
    fila = _portal_o_404(id_portal)
    _exigir_conector(fila)
    motivo = motivo_no_sincroniza(fila)
    if motivo:
        raise HTTPException(status_code=409, detail=motivo)
    if not servicio.correr_varios_en_segundo_plano([id_portal], usuario_actual(request)):
        return JSONResponse(status_code=409, content={"detail": "Ya se está sincronizando"})
    return {"encolados": [id_portal]}


@router.post("/corridas", status_code=202)
def sincronizar(request: Request, body: PedidoSincronizar | None = None) -> dict:
    """Sincroniza ahora los portales elegidos (o todos los que se pueden), uno por vez.
    Devuelve los encolados y, por cada omitido, el motivo en palabras."""
    pedidos = set(body.idsPortales) if body and body.idsPortales else None
    cola = servicio.en_cola()
    candidatos, omitidos = [], []
    for f in repository.listar_portales():
        if pedidos is not None and f["idPortal"] not in pedidos:
            continue
        motivo = motivo_no_sincroniza(f)
        if motivo is None and (f["ucEstado"] == "en_curso" or f["idPortal"] in cola):
            motivo = "Ya se está sincronizando"
        if motivo:
            omitidos.append({"idPortal": f["idPortal"], "nombre": f["nombre"], "motivo": motivo})
        else:
            candidatos.append(f["idPortal"])
    encolados = servicio.correr_varios_en_segundo_plano(candidatos, usuario_actual(request))
    return {"encolados": encolados, "omitidos": omitidos}


@router.get("/corridas")
def listar_corridas(idPortal: int | None = None, limite: int = Query(20, ge=1, le=100),
                    desde: int = Query(0, ge=0)) -> dict:
    filas, total = repository.listar_corridas(idPortal, limite, desde)
    return {"items": [corrida_iso(c) for c in filas], "total": total}


def corrida_iso(c: dict) -> dict:
    return {**c, "inicio": iso(c["inicio"]), "fin": iso(c["fin"])}


@router.get("/corridas/{id_corrida}")
def detalle_corrida(id_corrida: int) -> dict:
    corrida = repository.obtener_corrida(id_corrida)
    if corrida is None:
        raise HTTPException(status_code=404, detail="Corrida inexistente")
    return {**corrida_iso(corrida), "documentos": [con_nombre(d) for d in repository.documentos_de_corrida(id_corrida)],
            "fotos": [f for f in repository.listar_fotos(corrida["idPortal"]) if f["idCorrida"] == id_corrida]}


# --- Documentos y estado de cuenta --------------------------------------------------

def con_nombre(doc: dict) -> dict:
    return {**doc, "nombreArchivo": ntpath.basename(doc["ruta"]) if doc.get("ruta") else None}


@router.get("/documentos")
def listar_documentos(idPortal: int | None = None, estado: str | None = None,
                      limite: int = Query(50, ge=1, le=100), desde: int = Query(0, ge=0)) -> dict:
    if estado and estado not in ESTADOS_CARGA:
        raise HTTPException(status_code=400, detail="Estado inválido")
    repository.revalidar_pendientes()
    filas, total = repository.listar_documentos(idPortal, estado, limite, desde)
    return {"items": [con_nombre(d) for d in filas], "total": total}


@router.get("/estado-cuenta")
def listar_fotos(idPortal: int | None = None) -> list[dict]:
    return [{**f, "creado": iso(f["creado"])} for f in repository.listar_fotos(idPortal)]


@router.get("/estado-cuenta/{id_foto}")
def detalle_foto(id_foto: int) -> dict:
    foto = repository.obtener_foto(id_foto)
    if foto is None:
        raise HTTPException(status_code=404, detail="Foto inexistente")
    return {**foto, "creado": iso(foto["creado"])}


@router.patch("/estado-cuenta/{id_foto}", status_code=204)
def revisar_foto(id_foto: int, body: FotoRevision, request: Request) -> Response:
    if not repository.marcar_foto_revisada(id_foto, body.revisada):
        raise HTTPException(status_code=404, detail="Foto inexistente")
    repository.auditar("revisar_foto", usuario_actual(request), detalle=f"foto {id_foto}: {body.revisada}")
    return Response(status_code=204)


@router.get("/resumen")
def resumen() -> dict:
    datos = repository.resumen()
    datos["facturasAMano"] = sum(1 for f in repository.listar_portales() if recordatorio(f))
    datos["total"] += datos["facturasAMano"]
    return datos
