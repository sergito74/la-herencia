"""Tablero de colas por etapas, foto semanal y preguntas — 036 (US7, research D13).

El tablero se calcula en vivo. La foto semanal se crea cuando se abre el tablero y todavía no existe la de la semana que empieza el lunes (no
hay proceso programado: el launcher se apaga solo) y también a pedido. Guarda un resumen, no copia las cuentas.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from src.db.connection import execute_write_transaction, fetch_all, fetch_one
from src.features.revision_cuentas import colas, fichas

ESTADOS = ("pendiente", "en-proceso", "esperando-evidencia", "esperando-sergio", "cerrada", "cerrada-con-excepcion", "reabierta")
ESTADOS_CERRADOS = ("cerrada", "cerrada-con-excepcion")


class TableroError(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


# --------------------------------------------------------------------------- funciones puras

def semana_de(dia: date) -> date:
    """El lunes de la semana de `dia`."""
    return dia - timedelta(days=dia.weekday())


def agregar(resumenes: list[dict]) -> dict:
    """Casillas por cola y etapa, totales por cola y por estado. Cada cuenta cae en una sola casilla."""
    casillas: dict[tuple[str, str], dict] = {}
    por_cola: dict[str, dict] = {}
    por_estado = {e: 0 for e in ESTADOS}
    for r in resumenes:
        c = casillas.setdefault((r["cola"], r["etapa"]), {"cola": r["cola"], "etapa": r["etapa"], "cuentas": 0, "importe": 0.0})
        c["cuentas"] += 1
        c["importe"] = round(c["importe"] + float(r.get("importeEnJuego", 0.0)), 2)
        t = por_cola.setdefault(r["cola"], {"cuentas": 0, "importe": 0.0})
        t["cuentas"] += 1
        t["importe"] = round(t["importe"] + float(r.get("importeEnJuego", 0.0)), 2)
        por_estado[r["estado"]] = por_estado.get(r["estado"], 0) + 1
    ordenadas = sorted(casillas.values(), key=lambda c: (colas.PRECEDENCIA.index(c["cola"]) if c["cola"] in colas.PRECEDENCIA else 99, c["etapa"]))
    return {"totalCuentas": len(resumenes), "porEstado": por_estado, "casillas": ordenadas,
            "totalesPorCola": {k: por_cola[k] for k in sorted(por_cola)}}


def datos_de_foto(agregado: dict) -> dict:
    """Lo que guarda la foto semanal: totales por cola, etapa y estado con su importe (no copia las cuentas)."""
    return {"totalCuentas": agregado["totalCuentas"], "porEstado": agregado["porEstado"], "casillas": agregado["casillas"],
            "totalesPorCola": agregado["totalesPorCola"]}


def comparar(actual: dict, foto_anterior: dict | None, semana_anterior: date | None) -> dict | None:
    """Cuentas cerradas desde la semana anterior y variación de la cola de excepciones (I); `None` si no hay foto anterior."""
    if foto_anterior is None or semana_anterior is None:
        return None
    cerradas_ahora = sum(actual["porEstado"].get(e, 0) for e in ESTADOS_CERRADOS)
    cerradas_antes = sum((foto_anterior.get("porEstado") or {}).get(e, 0) for e in ESTADOS_CERRADOS)
    excepciones_ahora = (actual["totalesPorCola"].get("I") or {}).get("cuentas", 0)
    excepciones_antes = ((foto_anterior.get("totalesPorCola") or {}).get("I") or {}).get("cuentas", 0)
    return {"semanaAnterior": semana_anterior, "cerradasEnLaSemana": cerradas_ahora - cerradas_antes, "variacionExcepciones": excepciones_ahora - excepciones_antes}


def preguntas_de(resumenes: list[dict]) -> list[dict]:
    """Una pregunta por cuenta que espera una decisión de Sergio, en el mismo orden de las colas (más fáciles primero)."""
    con_pregunta = [{**r, "importe": r["importe"]} for r in resumenes if r.get("pregunta")]
    return [{"idContacto": r["idContacto"], "razonSocial": r["razonSocial"], "cola": r["cola"], "etapa": r["etapa"], "pregunta": r["pregunta"], "desde": r.get("desde")}
            for r in colas.orden_de_dificultad(con_pregunta)]


# --------------------------------------------------------------------------- base de datos (fotos)

def _a_fecha(valor) -> date:
    return fichas.a_fecha(valor)


def _foto_de_semana(semana: date) -> dict | None:
    return fetch_one("SELECT IdFoto, Semana, Corte, Datos, Fecha FROM dbo.RevisionTableroFotos WHERE Semana = ?", (semana,))


def _foto_anterior(semana: date) -> dict | None:
    return fetch_one("SELECT TOP 1 IdFoto, Semana, Corte, Datos, Fecha FROM dbo.RevisionTableroFotos WHERE Semana < ? ORDER BY Semana DESC", (semana,))


def _guardar_foto(semana: date, corte: date, datos: dict, usuario: str) -> int:
    resultados = execute_write_transaction([
        ("INSERT INTO dbo.RevisionTableroFotos (Semana, Corte, Datos, Usuario) OUTPUT INSERTED.IdFoto VALUES (?, ?, ?, ?)",
         (semana, corte, json.dumps(datos, ensure_ascii=False, default=str), usuario))])
    return int(resultados[0])


def crear_foto(agregado: dict, corte: date, usuario: str, hoy: date | None = None, manual: bool = False) -> dict | None:
    """Crea la foto de la semana actual si no existe. Con `manual` y ya existente falla (409); al abrir el tablero simplemente no hace nada."""
    semana = semana_de(hoy or date.today())
    if _foto_de_semana(semana) is not None:
        if manual:
            raise TableroError(409, f"Ya existe la foto de la semana del {semana:%d/%m/%Y}")
        return None
    id_foto = _guardar_foto(semana, corte, datos_de_foto(agregado), usuario)
    return {"idFoto": id_foto, "semana": semana, "corte": corte, "fecha": datetime.now(), "totalCuentas": agregado["totalCuentas"]}


def _foto_a_respuesta(f: dict) -> dict:
    datos = json.loads(f["Datos"] or "{}")
    return {"idFoto": int(f["IdFoto"]), "semana": _a_fecha(f["Semana"]), "corte": _a_fecha(f["Corte"]), "fecha": f["Fecha"], "totalCuentas": int(datos.get("totalCuentas", 0))}


def listar_fotos(pagina: int = 1, tamano: int = 20) -> dict:
    filas = fetch_all("SELECT IdFoto, Semana, Corte, Datos, Fecha FROM dbo.RevisionTableroFotos ORDER BY Semana DESC", ())
    return {"total": len(filas), "fotos": [_foto_a_respuesta(f) for f in filas[(pagina - 1) * tamano:pagina * tamano]]}


# --------------------------------------------------------------------------- tablero

def tablero(corte: date | None = None, refrescar: bool = False, usuario: str = "sistema", hoy: date | None = None) -> dict:
    """Tablero en vivo con la comparación contra la foto anterior; crea la foto de la semana si todavía no existe."""
    corte_usado, contextos = fichas.contextos_de_todas(corte, refrescar)
    resumenes = fichas.resumenes(contextos)
    agregado = agregar(resumenes)
    semana = semana_de(hoy or date.today())
    crear_foto(agregado, corte_usado, usuario, hoy)
    anterior = _foto_anterior(semana)
    comparacion = comparar(agregado, json.loads(anterior["Datos"] or "{}") if anterior else None, _a_fecha(anterior["Semana"]) if anterior else None)
    return {"corte": corte_usado, **agregado, "comparacion": comparacion, "preguntas": len(preguntas_de(resumenes))}


def preguntas(refrescar: bool = False) -> list[dict]:
    _, contextos = fichas.contextos_de_todas(None, refrescar)
    return preguntas_de(fichas.resumenes(contextos))


def foto_manual(usuario: str, hoy: date | None = None) -> dict:
    corte_usado, contextos = fichas.contextos_de_todas()
    agregado = agregar(fichas.resumenes(contextos))
    return crear_foto(agregado, corte_usado, usuario, hoy, manual=True)
