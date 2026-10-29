"""`/api/documentos-nuevos` (043, contracts/api.md).

Lectura: cualquier usuario con sesión (los de solo lectura ven los avisos).
Escritura (revisado, módulo): solo Administrador. Todo en palabras de negocio.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.features.boveda.router import exigir_admin, iso, usuario_actual
from src.features.documentos_nuevos import repository
from src.features.documentos_nuevos.schemas import CambioModulo, EstadoRutina, Item, Lista, Resumen

router = APIRouter(prefix="/api/documentos-nuevos", tags=["documentos-nuevos"])

TIPOS = {
    "recibos_sueldo": "Recibos de sueldo", "resumen_sueldos": "Resumen de sueldos",
    "factura": "Factura", "nota_credito": "Nota de crédito", "nota_debito": "Nota de débito", "boleta": "Boleta",
    "retencion": "Certificado de retención", "liquidacion": "Liquidación", "recibo": "Recibo",
    "resumen_banco": "Resumen de banco", "resumen_tarjeta": "Resumen de tarjeta",
    "resumen_proveedor": "Resumen de cuenta", "contrato": "Contrato", "otro": "Comprobante",
}


def _fecha_hora(valor) -> str:
    v = iso(valor) or ""
    return f"{v[8:10]}/{v[5:7]}/{v[0:4]} {v[11:16]}".strip() if len(v) >= 10 else ""


def _enlace(d: dict) -> str | None:
    if d["tipo"] in ("recibos_sueldo", "resumen_sueldos"):
        return "/personal/remuneraciones"
    if d["modulo"] == "compras" and d["idRegistro"]:
        return f"/compras/{d['idRegistro']}/editar"
    if d["modulo"] == "impuestos" and d["idRegistro"]:
        return f"/finanzas/impuestos/{d['idRegistro']}"
    if d["modulo"] == "cuentas_corrientes" and d["idContacto"]:
        return f"/finanzas/cuentas-corrientes?idContacto={d['idContacto']}"
    if d["modulo"] == "tesoreria":
        return "/finanzas/tesoreria"
    return None


def _item(d: dict, renglones: list[dict]) -> dict:
    if d["origen"] == "mail":
        origen = f"Mail de {d['mailRemitente'] or 'remitente desconocido'}"
        detalle = " · ".join(x for x in (d["mailAsunto"], f"Llegó el {_fecha_hora(d['mailRecibido'])}") if x)
    else:
        origen = f"Portal {d['portal']}" if d["portal"] else "Portal"
        detalle = f"Llegó el {_fecha_hora(d['creado'])}"
    item = {
        "idDocumentoNuevo": d["idDocumentoNuevo"], "origen": origen, "origenDetalle": detalle,
        "tipo": TIPOS.get(d["tipo"], d["tipo"].replace("_", " ").capitalize()), "modulo": d["modulo"],
        "estado": d["estado"], "motivo": d["motivo"], "contacto": ("Sueldos de Giamigli" if d["tipo"] in ("recibos_sueldo", "resumen_sueldos") else d["contacto"]), "idContacto": d["idContacto"],
        "fecha": (iso(d["fecha"]) or "")[:10] or None, "numero": d["numero"],
        "total": float(d["total"]) if d["total"] is not None else None,
        "archivo": Path(d["ruta"]).name, "ruta": d["ruta"], "idRegistro": d["idRegistro"], "enlace": _enlace(d),
        "renglones": None,
    }
    if d["modulo"] == "compras" and d["idRegistro"]:
        item["renglones"] = [{
            "detalle": r["detalle"], "rubro": r["rubro"], "centroCosto": r["centroCosto"],
            "importe": round(float(r["cantidad"] or 1) * float(r["precioUnitario"] or 0), 2),
            "iva": float(r["iva"]) if r["iva"] is not None else None,
        } for r in renglones if r["idCompra"] == d["idRegistro"]]
    return item


@router.get("/resumen", response_model=Resumen)
def resumen() -> dict:
    n = repository.resumen_pendientes()
    datos = {"compras": n.get("compras", 0), "impuestos": n.get("impuestos", 0), "ventas": n.get("ventas", 0),
             "tesoreria": n.get("tesoreria", 0), "cuentasCorrientes": n.get("cuentas_corrientes", 0),
             "sinClasificar": n.get("sin_clasificar", 0)}
    datos["total"] = sum(datos.values())
    return datos


@router.get("/rutina", response_model=EstadoRutina, dependencies=[Depends(exigir_admin)])
def estado_rutina() -> dict:
    prog = repository.programacion() or {}
    ultima = repository.ultima_corrida()
    if ultima:
        ultima = {**ultima, "inicio": iso(ultima["inicio"]), "fin": iso(ultima["fin"])}
    return {"proxima": iso(prog.get("proxima")), "activa": bool(prog.get("activa", True)), "ultima": ultima}


@router.get("/", response_model=Lista)
def listar(modulo: str = Query(...), limite: int = Query(50, ge=1, le=100), desde: int = Query(0, ge=0)) -> dict:
    if modulo not in repository.MODULOS:
        raise HTTPException(status_code=400, detail="Módulo inválido")
    filas, total = repository.listar_pendientes(modulo, limite, desde)
    renglones = repository.renglones_compras([d["idRegistro"] for d in filas if d["modulo"] == "compras" and d["idRegistro"]])
    return {"items": [_item(d, renglones) for d in filas], "total": total}


@router.post("/{id_documento}/revisado", dependencies=[Depends(exigir_admin)])
def marcar_revisado(id_documento: int, request: Request) -> dict:
    if not repository.marcar_revisado(id_documento, usuario_actual(request)):
        raise HTTPException(status_code=404, detail="No está pendiente de revisión")
    return {"ok": True}


@router.post("/{id_documento}/modulo", response_model=Item, dependencies=[Depends(exigir_admin)])
def cambiar_modulo(id_documento: int, body: CambioModulo, request: Request) -> dict:
    if not repository.cambiar_modulo(id_documento, body.modulo, usuario_actual(request)):
        raise HTTPException(status_code=409, detail="No se pudo mover: ya no está pendiente o ya figura en ese módulo")
    d = repository.obtener(id_documento)
    renglones = repository.renglones_compras([d["idRegistro"]]) if d["modulo"] == "compras" and d["idRegistro"] else []
    return _item(d, renglones)
