"""Revisión de una cuenta: estado, saldo esperado, orden de trabajo y avisos — 035 (Historia 0, FR-020 a FR-023).

Las funciones puras (`dificultad`, `avisos_de_cuenta`, `estado_de_revision`, `orden_de_revision`) no leen la base;
las de abajo leen y escriben `dbo.AuditoriaRevisiones` y su historial (nunca se borra nada).
"""

from __future__ import annotations

import json
from datetime import datetime

from src.db.connection import execute_write, fetch_all, fetch_one

TOLERANCIA_REDONDEO = 1.0  # una diferencia de redondeo no preocupa
EXCEPCIONES_EXTRA = {
    "aplicacion-fuera-de-plazo", "doble-descuento-tarjeta", "nota-sin-imputar", "impuesto-sin-boleta",
    "movimiento-sin-contacto", "sobrepago", "contacto-duplicado", "falta-documento",
}
NOMBRES_AVISO = {
    "aplicacion-fuera-de-plazo": "Hay pagos aplicados a facturas de hace mucho tiempo",
    "doble-descuento-tarjeta": "Hay pagos que podrían estar descontados dos veces (tarjeta y banco)",
    "nota-sin-imputar": "Hay notas de débito sin imputar",
    "impuesto-sin-boleta": "Se pagó más de lo que hay en boletas cargadas",
    "sobrepago": "Hay facturas con más pagos aplicados que su importe",
    "contacto-duplicado": "Hay otro contacto con el mismo CUIT",
    "fuera-de-plazo-decidido": "Hay pagos fuera de plazo que se aplicaron a mano o por FIFO",
}


def dificultad(cuenta: dict, saldo_esperado: str | None = None) -> int:
    """0 = sin avisos (fácil), 1 = diferencia explicada o menor, 2 = con excepciones o saldo inesperado."""
    extras = set(cuenta.get("causasExtra", []))
    if cuenta["causa"] in ("otros",) or extras & EXCEPCIONES_EXTRA:
        return 2
    if saldo_esperado == "cero" and abs(cuenta["saldoSistema"]) >= TOLERANCIA_REDONDEO:
        return 2
    if cuenta["causa"] != "coincide" or extras:
        return 1
    return 0


def avisos_de_cuenta(cuenta: dict, saldo_esperado: str | None) -> list[dict]:
    avisos = []
    if saldo_esperado == "cero" and abs(cuenta["saldoSistema"]) >= TOLERANCIA_REDONDEO:
        avisos.append({"tipo": "saldo-esperado", "motivo": "Marcaste que esta cuenta debe estar en cero y no lo está",
                       "importe": cuenta["saldoSistema"]})
    if cuenta["causa"] == "otros":
        avisos.append({"tipo": "diferencia-sin-explicar", "motivo": "Hay una diferencia con el Access que nadie explicó (solo es una referencia)",
                       "importe": cuenta["sinExplicar"]})
    if cuenta.get("documentada"):
        avisos.append({"tipo": "diferencia-documentada", "motivo": f"Diferencia ya documentada: {cuenta['documentada']}", "importe": None})
    for causa in cuenta.get("causasExtra", []):
        if causa in NOMBRES_AVISO:
            avisos.append({"tipo": causa, "motivo": NOMBRES_AVISO[causa], "importe": None})
    return avisos


def estado_de_revision(fila: dict | None, saldo_actual: float) -> str:
    """`pendiente`, `revisada` o `revision-vieja` (el saldo cambió después de revisarla)."""
    if not fila or fila["Estado"] != "revisada":
        return "pendiente"
    anterior = float(fila["SaldoAlRevisar"] or 0)
    return "revisada" if abs(saldo_actual - anterior) < TOLERANCIA_REDONDEO else "revision-vieja"


def orden_de_revision(cuentas: list[dict], esperados: dict[int, str | None]) -> list[dict]:
    """Alfabético, de las más fáciles a las más complicadas."""
    return sorted(cuentas, key=lambda c: (dificultad(c, esperados.get(c["idContacto"])), (c["razonSocial"] or "").lower(), c["idContacto"]))


def siguiente_sin_revisar(orden: list[dict], estados: dict[int, str], despues_de: int | None = None) -> dict | None:
    """La próxima cuenta pendiente después de `despues_de` en el orden de trabajo (y luego, desde el principio)."""
    ids = [c["idContacto"] for c in orden]
    inicio = ids.index(despues_de) + 1 if despues_de in ids else 0
    for c in orden[inicio:] + orden[:inicio]:
        if c["idContacto"] != despues_de and estados.get(c["idContacto"], "pendiente") != "revisada":
            return c
    return None


# --------------------------------------------------------------------------- base de datos

def leer_todas() -> dict[int, dict]:
    try:
        return {f["IdContacto"]: f for f in fetch_all("SELECT IdContacto, SaldoEsperado, Estado, FechaRevision, Usuario, Nota, SaldoAlRevisar "
                                                       "FROM dbo.AuditoriaRevisiones", ())}
    except Exception:
        return {}


def historial(id_contacto: int, limite: int = 50) -> list[dict]:
    try:
        return fetch_all("SELECT TOP (?) IdHistorial AS id, Accion AS accion, Detalle AS detalle, Usuario AS usuario, Fecha AS fecha "
                         "FROM dbo.AuditoriaRevisionesHistorial WHERE IdContacto = ? ORDER BY IdHistorial DESC", (limite, id_contacto))
    except Exception:
        return []


def registrar(id_contacto: int, accion: str, detalle: dict | str | None, usuario: str) -> None:
    execute_write("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, ?, ?, ?)",
                  (id_contacto, accion, detalle if isinstance(detalle, str) or detalle is None else json.dumps(detalle, ensure_ascii=False, default=str), usuario))


def guardar(id_contacto: int, saldo_actual: float, usuario: str, estado: str | None, nota: str | None, saldo_esperado: str | None,
            quitar_esperado: bool = False) -> None:
    if estado is not None and estado not in ("pendiente", "revisada"):
        raise ValueError("Estado desconocido")
    if saldo_esperado is not None and saldo_esperado not in ("cero", "puede-tener-saldo"):
        raise ValueError("Saldo esperado desconocido")
    existe = fetch_one("SELECT 1 AS x FROM dbo.AuditoriaRevisiones WHERE IdContacto = ?", (id_contacto,))
    if not existe:
        execute_write("INSERT INTO dbo.AuditoriaRevisiones (IdContacto, Estado) VALUES (?, 'pendiente')", (id_contacto,))
    if saldo_esperado is not None or quitar_esperado:
        execute_write("UPDATE dbo.AuditoriaRevisiones SET SaldoEsperado = ? WHERE IdContacto = ?", (saldo_esperado, id_contacto))
        registrar(id_contacto, "saldo-esperado", saldo_esperado or "sin definir", usuario)
    if estado is not None:
        if estado == "revisada":
            execute_write("UPDATE dbo.AuditoriaRevisiones SET Estado = 'revisada', FechaRevision = SYSDATETIME(), Usuario = ?, Nota = ?, "
                          "SaldoAlRevisar = ? WHERE IdContacto = ?", (usuario, (nota or "")[:500] or None, round(saldo_actual, 2), id_contacto))
        else:
            execute_write("UPDATE dbo.AuditoriaRevisiones SET Estado = 'pendiente' WHERE IdContacto = ?", (id_contacto,))
        registrar(id_contacto, estado, {"nota": nota, "saldo": round(saldo_actual, 2)}, usuario)
    elif nota is not None:
        execute_write("UPDATE dbo.AuditoriaRevisiones SET Nota = ? WHERE IdContacto = ?", ((nota or "")[:500] or None, id_contacto))
        registrar(id_contacto, "nota", nota, usuario)
