"""Ficha por cuenta y corte vigente — 036 (research D3, D4, D7).

Lee y escribe `RevisionCortes` y `RevisionFichas`. La etapa, la cola y los 7 criterios se **calculan** cada vez a partir de los datos;
solo se guarda lo que decide una persona (estado, notas, inventario, cierre). Nunca borra filas y nunca escribe en `LaHerencia`.
El historial de cada cambio va a `AuditoriaRevisionesHistorial` (existente) con `Accion` `ficha-*`, `decision`, etc.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from src.db.connection import execute_write, execute_write_transaction, fetch_all, fetch_one
from src.features.revision_cuentas import cache, colas, criterios, datos, detector, evidencia

ESTADOS_CERRADOS = ("cerrada", "cerrada-con-excepcion")
ACCIONES_DE_LA_FICHA = ("ficha-estado", "ficha-inventario", "ficha-cierre", "ficha-reapertura", "pago-sin-factura", "saldo-externo", "decision")
TOLERANCIA_REAPERTURA_PESOS = 1.0        # redondeo: un cambio menor no reabre la cuenta
TOLERANCIA_REAPERTURA_DOLARES = 0.005    # en dólares, tolerancia relativa vigente
TIPOS_DECISION = ("descartar-access", "cierre-con-excepcion", "otro")


class FichaError(Exception):
    """Error de negocio con su código HTTP (404, 409, 422) y, si hace falta, el detalle (por ejemplo los criterios que faltan)."""

    def __init__(self, codigo: int, mensaje: str, detalle: dict | None = None):
        super().__init__(mensaje)
        self.codigo, self.mensaje, self.detalle = codigo, mensaje, detalle or {}


# --------------------------------------------------------------------------- corte

def a_fecha(valor) -> date:
    """Una columna `date` puede llegar del driver como fecha, fecha y hora o texto (`2026-09-30`)."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        return date.fromisoformat(valor[:10])
    return valor


def corte_vigente() -> dict | None:
    """El corte más nuevo de `RevisionCortes` (la fila más nueva manda; las anteriores son historial)."""
    f = fetch_one("SELECT TOP 1 Corte AS corte, Motivo AS motivo, Usuario AS usuario, Fecha AS fecha "
                  "FROM dbo.RevisionCortes ORDER BY IdCorte DESC", ())
    if f is None:
        return None
    return {"corte": a_fecha(f["corte"]), "motivo": f["motivo"], "usuario": f["usuario"], "fecha": f["fecha"]}


def _insertar_corte(corte: date, motivo: str | None, usuario: str) -> None:
    execute_write("INSERT INTO dbo.RevisionCortes (Corte, Motivo, Usuario) VALUES (?, ?, ?)", (corte, motivo, usuario))


def fijar_corte(corte: date, motivo: str | None, usuario: str) -> dict:
    """Crea una fila nueva con el corte (no sobrescribe). Una fecha futura no es válida: el corte es un día ya cerrado."""
    if corte > date.today():
        raise ValueError("El corte no puede ser una fecha futura")
    _insertar_corte(corte, (motivo or "").strip() or None, usuario)
    return corte_vigente()


# --------------------------------------------------------------------------- funciones puras

def tolerancia_de_reapertura(moneda: str, saldo_al_cierre: float) -> float:
    return TOLERANCIA_REAPERTURA_PESOS if moneda != "Dolares" else max(TOLERANCIA_REAPERTURA_PESOS, TOLERANCIA_REAPERTURA_DOLARES * abs(saldo_al_cierre))


def esta_reabierta(fila: dict | None, saldo_al_corte_del_cierre: float | None) -> bool:
    """Una cuenta cerrada se reabre cuando su saldo, recalculado a la fecha de corte de su cierre, cambió más que la tolerancia (D7).

    Los movimientos posteriores a ese corte no cuentan: `saldo_al_corte_del_cierre` ya se calcula hasta esa fecha.
    """
    if not fila or fila.get("Estado") not in ESTADOS_CERRADOS or fila.get("SaldoAlCierre") is None or saldo_al_corte_del_cierre is None:
        return False
    anterior = float(fila["SaldoAlCierre"])
    return abs(float(saldo_al_corte_del_cierre) - anterior) > tolerancia_de_reapertura(fila.get("Moneda") or "Pesos", anterior)


def validar_cambio(cambio: dict) -> None:
    """Reglas de un cambio de estado que no dependen de los datos de la cuenta (FichaError 422)."""
    estado = cambio.get("estado")
    if estado == "cerrada-con-excepcion" and not (cambio.get("motivoExcepcion") or "").strip():
        raise FichaError(422, "Falta el motivo de la excepción")
    if estado == "esperando-sergio" and not (cambio.get("pregunta") or "").strip():
        raise FichaError(422, "Falta la pregunta que Sergio tiene que responder")


# --------------------------------------------------------------------------- lectura de la base

def _leer_fila(id_contacto: int) -> dict | None:
    return fetch_one("SELECT IdContacto, Estado, InventarioFuentes, Nota, PreguntaBloqueante, Corte, SaldoAlCierre, Moneda, MotivoExcepcion, "
                     "UsuarioCierre, FechaCierre, UsuarioActualiza, FechaActualiza FROM dbo.RevisionFichas WHERE IdContacto = ?", (id_contacto,))


def _inventario(fila: dict | None) -> list[dict] | None:
    if not fila or not fila.get("InventarioFuentes"):
        return None
    try:
        lista = json.loads(fila["InventarioFuentes"])
    except ValueError:
        return None
    return lista if isinstance(lista, list) and lista else None


def _cuentas_035() -> dict[int, dict]:
    """Las cuentas clasificadas por la auditoría 035, por contacto (se calculan una vez y quedan en su caché)."""
    from src.features.auditoria_cuentas import router as auditoria

    return {c["idContacto"]: c for c in auditoria._cuentas()[1]}


def _es_h(id_contacto: int) -> bool:
    from src.features.recalculo_fifo.entrada import EXCLUIDOS

    return id_contacto in EXCLUIDOS


def _en_revision_todas() -> set[int]:
    try:
        return {int(f["i"]) for f in fetch_all("SELECT IdContacto AS i FROM dbo.CuentasARevisar WHERE Resuelta = 0", ())}
    except Exception:
        return set()


def _fifo_aplicados() -> set[int]:
    from src.features.auditoria_cuentas import fifo_plan

    return set(fifo_plan.contactos_aplicados_desde(0))


def _filas_de_fichas(ids: list[int] | None) -> dict[int, dict]:
    filtro, params = ("", ()) if not ids else (" WHERE IdContacto IN (" + ",".join("?" * len(ids)) + ")", tuple(ids))
    filas = fetch_all("SELECT IdContacto, Estado, InventarioFuentes, Nota, PreguntaBloqueante, Corte, SaldoAlCierre, Moneda, MotivoExcepcion, "
                      "UsuarioCierre, FechaCierre, UsuarioActualiza, FechaActualiza FROM dbo.RevisionFichas" + filtro, params)
    return {int(f["IdContacto"]): f for f in filas}


def _con_saldos_externos() -> set[int]:
    return {int(f["i"]) for f in fetch_all("SELECT DISTINCT IdContacto AS i FROM dbo.RevisionSaldosExternos WHERE Anulado = 0", ())}


def _saldo_hasta(movimientos: list[dict], fecha: date) -> float:
    return round(sum(m["credito"] - m["deuda"] for m in movimientos if m["fecha"] <= fecha), 2)


def cargar_contextos(corte: date, ids: list[int] | None = None) -> dict[int, dict]:
    """Contexto de varias cuentas (todas las que tienen movimientos si `ids` es None) con consultas por lotes (solo lectura).

    Es lo que usan la ficha de una cuenta (con una sola) y las colas y el tablero (con todas): el mismo cálculo en los dos casos.
    """
    por_cuenta = datos.movimientos_por_cuenta(corte, ids)
    saldos = datos.saldos_al_corte(corte)   # saldo exacto de SQL (sumar filas redondeadas desvía centavos)
    cuentas035 = _cuentas_035()
    marcas = evidencia.leer_marcas_todas(ids)
    imputaciones = datos.imputaciones_de_cuentas(ids, corte)
    sin_certificado = datos.retenciones_sin_certificado()
    duplicadas = datos.tarjetas_duplicadas()
    filas = _filas_de_fichas(ids)
    con_externos = _con_saldos_externos()
    en_revision = _en_revision_todas()
    umbral = float(_umbral_pesos())
    contextos: dict[int, dict] = {}
    for id_contacto, movimientos in por_cuenta.items():
        resultado = detector.detectar(movimientos)
        marcas_cuenta = marcas.get(id_contacto, {})
        recientes = [p for p in resultado["pagos"] if not p["anteriorA2021"]]
        pendientes = [p for p in recientes if (marcas_cuenta.get((p["medio"], p["idMovimiento"])) or {}).get("estado", "pendiente") == "pendiente"]
        sentido = datos.sentido_de_cuenta(movimientos)
        cuenta = cuentas035.get(id_contacto)
        gobierna = (cuenta or {}).get("gobierna") or ("Dolares" if (cuenta or {}).get("moneda") == "Dolares" else "Pesos")
        saldo = saldos.get(id_contacto, 0.0)
        imp = imputaciones.get(id_contacto, {"facturado": 0.0, "aplicado": 0.0, "tarjeta": 0.0, "facturas": 0})
        sanas = criterios.imputaciones_sanas(sentido, gobierna, imp["facturado"], imp["aplicado"], imp["tarjeta"], saldo, imp["facturas"])
        externos = []
        if id_contacto in con_externos:
            externos = evidencia.listar_saldos_externos(id_contacto, lambda f, i=id_contacto, s=saldo: s if f == corte else datos.saldo_al_corte(i, f), umbral)
        con_saldo = next((e for e in externos if e["fuente"] != "sin-estado"), None)
        fila = filas.get(id_contacto)
        causa = (cuenta or {}).get("causa", "sin-referencia")
        hallazgos = set((cuenta or {}).get("causasExtra", ()))
        sin_cert = sin_certificado.get(id_contacto, 0)
        saldo_cierre = None
        if fila and fila.get("Estado") in ESTADOS_CERRADOS and fila.get("Corte") is not None:
            corte_cierre = a_fecha(fila["Corte"])
            saldo_cierre = saldo if corte_cierre == corte else datos.saldo_al_corte(id_contacto, corte_cierre)
        reabierta = esta_reabierta(fila, saldo_cierre)
        contextos[id_contacto] = {
            "idContacto": id_contacto, "corte": corte, "fila": fila, "saldo": saldo, "gobierna": gobierna, "sentido": sentido, "cuenta": cuenta,
            "movimientos": len(movimientos), "volumen": round(sum(m["deuda"] + m["credito"] for m in movimientos), 2),
            "pagos": resultado["pagos"], "marcas": marcas_cuenta, "consistencia": resultado["consistencia"],
            "criterios_ctx": {
                "pagos_pendientes": len(pendientes), "pagos_importe_pendiente": round(sum(p["importeEsperadoFactura"] for p in pendientes), 2),
                "pagos_antiguos": len(resultado["pagos"]) - len(recientes), "detector_cierra": resultado["consistencia"]["cierra"],
                "hallazgos": hallazgos, "retenciones_sin_certificado": sin_cert, "imputaciones": {"sanas": sanas},
                "tarjetas_duplicadas": len(duplicadas.get(id_contacto, {}).get("ids", [])),
                "referencia_access": {"tiene": cuenta is not None and cuenta.get("saldoAccess") is not None,
                                      "explica": causa in criterios.CAUSAS_ACCESS_EXPLICA, "diferencia": (cuenta or {}).get("diferencia")},
                "saldo_externo": con_saldo, "sin_estado": any(e["fuente"] == "sin-estado" for e in externos),
                "tiene_inventario": _inventario(fila) is not None, "reabierta": reabierta, "saldo": saldo,
            },
            "colas_ctx": {
                "es_h": _es_h(id_contacto), "pagos_pendientes": len(pendientes), "detector_cierra": resultado["consistencia"]["cierra"],
                "hallazgos": hallazgos, "retenciones_sin_certificado": sin_cert, "gobierna": gobierna,
                "tarjetas_duplicadas": len(duplicadas.get(id_contacto, {}).get("ids", [])),
                "saldo_revision": (cuenta or {}).get("saldoRevision", saldo), "tolerancia": (cuenta or {}).get("toleranciaRevision"),
                "causa": causa, "cuenta_a_revisar": id_contacto in en_revision, "imputaciones_sanas": sanas,
                "evidencia_externa": bool(con_saldo and con_saldo["clasificacion"] in ("cierra", "menor-al-umbral")) or any(e["fuente"] == "sin-estado" for e in externos),
            },
            "externos": externos, "reabierta": reabierta,
        }
    return contextos


def cargar_contexto(id_contacto: int, corte: date) -> dict:
    """Contexto de una sola cuenta (FichaError 404 si no tiene movimientos hasta el corte)."""
    contexto = cargar_contextos(corte, [id_contacto]).get(id_contacto)
    if contexto is None:
        raise FichaError(404, "La cuenta no existe o no tiene movimientos hasta el corte")
    return contexto


def _umbral_pesos() -> float:
    from src.features.auditoria_cuentas import parametros

    return float(parametros.obtener().get("umbralPesos", evidencia.UMBRAL_PESOS))


def _antecedente_035(id_contacto: int) -> dict | None:
    f = fetch_one("SELECT Estado AS estado, Nota AS nota, FechaRevision AS fecha FROM dbo.AuditoriaRevisiones WHERE IdContacto = ?", (id_contacto,))
    return None if f is None else {"estado": f["estado"], "nota": f["nota"], "fecha": f["fecha"]}


def _historial(id_contacto: int, limite: int = 60) -> list[dict]:
    from src.features.auditoria_cuentas import revision

    return [{"accion": h["accion"], "detalle": h["detalle"], "usuario": h["usuario"], "fecha": h["fecha"]}
            for h in revision.historial(id_contacto, limite) if h["accion"] in ACCIONES_DE_LA_FICHA]


def _registrar(id_contacto: int, accion: str, detalle, usuario: str) -> None:
    from src.features.auditoria_cuentas import revision

    revision.registrar(id_contacto, accion, detalle, usuario)


# --------------------------------------------------------------------------- ficha

def armar_ficha(ctx: dict) -> dict:
    """Arma la respuesta de la ficha a partir del contexto (pura, sin acceso a la base)."""
    crit = criterios.evaluar(ctx["criterios_ctx"])
    inventario = _inventario(ctx["fila"])
    etapa = criterios.etapa_de(crit, inventario is not None)
    cola, otros = colas.asignar_cola(ctx["colas_ctx"])
    fila = ctx["fila"] or {}
    estado = fila.get("Estado") or "pendiente"
    cierre = None
    if estado in ESTADOS_CERRADOS and fila.get("Corte") is not None:
        cierre = {"corte": a_fecha(fila["Corte"]), "saldoAlCierre": float(fila["SaldoAlCierre"] or 0), "usuario": fila.get("UsuarioCierre"),
                  "fecha": fila.get("FechaCierre"), "conExcepcion": estado == "cerrada-con-excepcion", "motivoExcepcion": fila.get("MotivoExcepcion")}
    return {
        "estado": estado, "estadoEfectivo": "reabierta" if ctx["reabierta"] else estado, "etapa": etapa, "cola": cola, "otrosProblemas": otros,
        "saldoAlCorte": ctx["saldo"], "moneda": "Dolares" if ctx["gobierna"] == "Dolares" else "Pesos", "criterios": crit,
        "inventarioFuentes": inventario, "pagosSinFactura": ctx["criterios_ctx"]["pagos_pendientes"], "saldosExternos": len(ctx["externos"]),
        "pregunta": fila.get("PreguntaBloqueante"), "cierre": cierre,
    }


def calcular_ficha(id_contacto: int, corte: date | None = None) -> dict:
    """La ficha de una cuenta: estado, etapa, cola, 7 criterios, evidencia e historial. Crea la fila `pendiente` al primer acceso."""
    if corte is None:
        vigente = corte_vigente()
        if vigente is None:
            raise FichaError(404, "Todavía no hay un corte definido")
        corte = vigente["corte"]
    ctx = cargar_contexto(id_contacto, corte)
    ficha = armar_ficha(ctx)
    cuenta = ctx["cuenta"] or {}
    ficha.update({"idContacto": id_contacto, "razonSocial": cuenta.get("razonSocial") or datos.razon_social(id_contacto), "corte": corte,
                  "saldoEsperado": _saldo_esperado(id_contacto), "antecedente035": _antecedente_035(id_contacto),
                  "fifoAplicadoAntes": id_contacto in _fifo_aplicados(), "historial": _historial(id_contacto)})
    return ficha


def _saldo_esperado(id_contacto: int) -> str | None:
    f = fetch_one("SELECT SaldoEsperado AS s FROM dbo.AuditoriaRevisiones WHERE IdContacto = ?", (id_contacto,))
    return f["s"] if f else None


def _asegurar_fila(id_contacto: int, usuario: str) -> dict:
    fila = _leer_fila(id_contacto)
    if fila is None:
        execute_write("INSERT INTO dbo.RevisionFichas (IdContacto, Estado, UsuarioActualiza) VALUES (?, 'pendiente', ?)", (id_contacto, usuario))
        fila = _leer_fila(id_contacto)
    return fila


def _guardar_estado(id_contacto: int, estado: str, nota: str | None, pregunta: str | None, motivo: str | None, usuario: str, cierre: dict | None) -> None:
    if cierre is not None:
        sql = ("UPDATE dbo.RevisionFichas SET Estado = ?, Nota = ?, PreguntaBloqueante = ?, MotivoExcepcion = ?, Corte = ?, SaldoAlCierre = ?, Moneda = ?, "
               "UsuarioCierre = ?, FechaCierre = SYSDATETIME(), UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() WHERE IdContacto = ?")
        params = (estado, nota, pregunta, motivo, cierre["corte"], cierre["saldo"], cierre["moneda"], usuario, usuario, id_contacto)
    else:
        sql = ("UPDATE dbo.RevisionFichas SET Estado = ?, Nota = ?, PreguntaBloqueante = ?, MotivoExcepcion = ?, "
               "UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() WHERE IdContacto = ?")
        params = (estado, nota, pregunta, motivo, usuario, id_contacto)
    execute_write_transaction([(sql, params)])
    cache.invalidar()


def cambiar_estado(id_contacto: int, cambio: dict, usuario: str) -> dict:
    """Cambia el estado manual de la ficha. Cerrar exige los 7 criterios al corte; cerrar con excepción exige el motivo."""
    validar_cambio(cambio)
    vigente = corte_vigente()
    if vigente is None:
        raise FichaError(404, "Todavía no hay un corte definido")
    corte = vigente["corte"]
    ctx = cargar_contexto(id_contacto, corte)
    crit = criterios.evaluar(ctx["criterios_ctx"])
    faltan = criterios.faltantes_para_cerrar(crit)
    estado = cambio["estado"]
    nota = (cambio.get("nota") or "").strip()[:500] or None
    pregunta = (cambio.get("pregunta") or "").strip()[:300] or None if estado == "esperando-sergio" else None
    motivo = (cambio.get("motivoExcepcion") or "").strip()[:500] or None if estado == "cerrada-con-excepcion" else None
    if estado == "cerrada" and faltan:
        raise FichaError(409, "No se puede cerrar: faltan criterios por cumplir", {"criterios": faltan})
    _asegurar_fila(id_contacto, usuario)
    cierre = None
    if estado in ESTADOS_CERRADOS:
        cierre = {"corte": corte, "saldo": ctx["saldo"], "moneda": "Dolares" if ctx["gobierna"] == "Dolares" else "Pesos"}
    anterior = (ctx["fila"] or {}).get("Estado") or "pendiente"
    _guardar_estado(id_contacto, estado, nota, pregunta, motivo, usuario, cierre)
    if cierre is not None:
        c3 = next(c for c in crit if c["codigo"] == "C3")
        detalle = {"estado": estado, "corte": str(corte), "saldoAlCierre": ctx["saldo"], "evidencia": c3.get("evidencia"), "nota": nota}
        ext = ctx["criterios_ctx"].get("saldo_externo")
        diferencia = float(ext["diferencia"]) if ext else (ctx["criterios_ctx"]["referencia_access"].get("diferencia"))
        if diferencia is not None and 0 < abs(float(diferencia)) < evidencia.UMBRAL_PESOS and ctx["gobierna"] != "Dolares":
            detalle["diferenciaMenorAlUmbral"] = round(float(diferencia), 2)  # FR-009: se registra la diferencia con su importe
        if estado == "cerrada-con-excepcion":
            detalle.update({"motivoExcepcion": motivo, "criteriosSinCumplir": [c["codigo"] for c in faltan]})
        _registrar(id_contacto, "ficha-cierre", detalle, usuario)
    else:
        _registrar(id_contacto, "ficha-estado", {"anterior": anterior, "nuevo": estado, "nota": nota, "pregunta": pregunta}, usuario)
    if ctx["reabierta"] and estado not in ESTADOS_CERRADOS:
        _registrar(id_contacto, "ficha-reapertura", {"saldoAlCierreAnterior": float((ctx["fila"] or {}).get("SaldoAlCierre") or 0), "saldoAhora": ctx["saldo"]}, usuario)
    return calcular_ficha(id_contacto, corte)


def confirmar_inventario(id_contacto: int, fuentes: list[dict], usuario: str) -> dict:
    """Confirma la etapa E0: qué evidencia hay para la cuenta y cuál falta."""
    if not fuentes:
        raise FichaError(422, "El inventario no puede estar vacío")
    _asegurar_fila(id_contacto, usuario)
    execute_write_transaction([("UPDATE dbo.RevisionFichas SET InventarioFuentes = ?, UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() WHERE IdContacto = ?",
                                (json.dumps(fuentes, ensure_ascii=False), usuario, id_contacto))])
    _registrar(id_contacto, "ficha-inventario", {"fuentes": fuentes}, usuario)
    cache.invalidar()
    return calcular_ficha(id_contacto)


# --------------------------------------------------------------------------- decisiones (T023a)

def registrar_decision(id_contacto: int, tipo: str, texto: str, evid: str | None, usuario: str) -> dict:
    """Registra una decisión de Sergio sobre la cuenta (se guarda en el historial con `Accion = decision`)."""
    if tipo not in TIPOS_DECISION:
        raise FichaError(422, "Tipo de decisión desconocido")
    texto = (texto or "").strip()
    if not texto:
        raise FichaError(422, "Falta el texto de la decisión")
    evid = (evid or "").strip() or None
    if tipo == "descartar-access" and evid is None:
        raise FichaError(422, "Descartar el Access exige la evidencia con el análisis que lo respalda")
    _registrar(id_contacto, "decision", {"tipo": tipo, "texto": texto, "evidencia": evid}, usuario)
    fila = fetch_one("SELECT TOP 1 IdHistorial AS id, Fecha AS fecha FROM dbo.AuditoriaRevisionesHistorial WHERE IdContacto = ? AND Accion = 'decision' "
                     "ORDER BY IdHistorial DESC", (id_contacto,))
    return {"idDecision": int(fila["id"]), "tipo": tipo, "texto": texto, "evidencia": evid, "usuario": usuario, "fecha": fila["fecha"]}


def listar_decisiones(id_contacto: int) -> list[dict]:
    filas = fetch_all("SELECT IdHistorial AS id, Detalle AS detalle, Usuario AS usuario, Fecha AS fecha FROM dbo.AuditoriaRevisionesHistorial "
                      "WHERE IdContacto = ? AND Accion = 'decision' ORDER BY IdHistorial DESC", (id_contacto,))
    salida = []
    for f in filas:
        try:
            d = json.loads(f["detalle"] or "{}")
        except ValueError:
            d = {}
        salida.append({"idDecision": int(f["id"]), "tipo": d.get("tipo", "otro"), "texto": d.get("texto", ""), "evidencia": d.get("evidencia"),
                       "usuario": f["usuario"], "fecha": f["fecha"]})
    return salida


# --------------------------------------------------------------------------- cierre en bloque (regla `aprobar-cierre`, T030)

CAMPOS_PREVIOS = ("Estado", "InventarioFuentes", "Nota", "PreguntaBloqueante", "Corte", "SaldoAlCierre", "Moneda", "MotivoExcepcion", "UsuarioCierre", "FechaCierre")


def _snapshot(fila: dict | None) -> dict | None:
    """La ficha previa de una cuenta tal como estaba (para volver atrás al revertir el lote)."""
    if fila is None:
        return None
    return {k: (None if fila.get(k) is None else (float(fila[k]) if k == "SaldoAlCierre" else str(fila[k]))) for k in CAMPOS_PREVIOS}


def cerrar_en_bloque(id_correccion: int, contextos: dict[int, dict], tildadas: list[dict], corte: date, usuario: str) -> None:
    """Cierra al corte, en una sola transacción, las cuentas tildadas de un lote. Cada cuenta debe cumplir los criterios (menos C7).

    Confirma el inventario con la fuente `access` si la cuenta no lo tenía, guarda la ficha previa en la fila del lote y deja el cierre en
    el historial con la fuente de la evidencia (FR-017b).
    """
    from src.features.revision_cuentas import lotes

    operaciones: list = []
    for c in tildadas:
        ctx = contextos.get(c["idContacto"])
        if ctx is None:
            raise FichaError(409, f"La cuenta {c['idContacto']} ya no tiene movimientos hasta el corte")
        crit = criterios.evaluar(ctx["criterios_ctx"])
        faltan = lotes.faltantes_para_cierre_en_bloque(crit)
        if faltan:
            raise FichaError(409, f"La cuenta {c['idContacto']} ya no cumple los criterios: " + "; ".join(f"{x['codigo']}: {x['medido']}" for x in faltan))
        fila = ctx["fila"]
        inventario = (fila or {}).get("InventarioFuentes")
        if not inventario or not _inventario(fila):
            inventario = json.dumps([{"tipo": "access", "disponible": True, "detalle": f"Cierre en bloque (lote {id_correccion})"}], ensure_ascii=False)
        moneda = "Dolares" if ctx["gobierna"] == "Dolares" else "Pesos"
        nota = f"Cierre en bloque (lote {id_correccion})"
        if fila is None:
            operaciones.append(("INSERT INTO dbo.RevisionFichas (IdContacto, Estado, InventarioFuentes, Nota, Corte, SaldoAlCierre, Moneda, UsuarioCierre, FechaCierre, UsuarioActualiza) "
                                "VALUES (?, 'cerrada', ?, ?, ?, ?, ?, ?, SYSDATETIME(), ?)",
                                (c["idContacto"], inventario, nota, corte, ctx["saldo"], moneda, usuario, usuario)))
        else:
            operaciones.append(("UPDATE dbo.RevisionFichas SET Estado = 'cerrada', InventarioFuentes = ?, Nota = ?, PreguntaBloqueante = NULL, MotivoExcepcion = NULL, "
                                "Corte = ?, SaldoAlCierre = ?, Moneda = ?, UsuarioCierre = ?, FechaCierre = SYSDATETIME(), UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() "
                                "WHERE IdContacto = ?", (inventario, nota, corte, ctx["saldo"], moneda, usuario, usuario, c["idContacto"])))
        extra = {**c["extra"], "previa": _snapshot(fila)}
        operaciones.append(("UPDATE dbo.AuditoriaCorreccionesCuentas SET Detalle = ? WHERE IdCorreccion = ? AND IdContacto = ?",
                            (json.dumps(extra, ensure_ascii=False, default=str), id_correccion, c["idContacto"])))
        detalle = {"estado": "cerrada", "corte": str(corte), "saldoAlCierre": ctx["saldo"], "evidencia": c["extra"].get("evidencia") or "access", "lote": id_correccion}
        operaciones.append(("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, 'ficha-cierre', ?, ?)",
                            (c["idContacto"], json.dumps(detalle, ensure_ascii=False), usuario)))
    if operaciones:
        execute_write_transaction(operaciones)
        cache.invalidar()


def revertir_cierre_en_bloque(id_correccion: int, tildadas: list[dict], usuario: str) -> None:
    """Devuelve cada cuenta del lote a su ficha previa (si no tenía ficha, vuelve a `pendiente` sin cierre)."""
    operaciones: list = []
    for c in tildadas:
        previa = c["extra"].get("previa")
        if previa is None:
            operaciones.append(("UPDATE dbo.RevisionFichas SET Estado = 'pendiente', InventarioFuentes = NULL, Nota = NULL, PreguntaBloqueante = NULL, "
                                "MotivoExcepcion = NULL, Corte = NULL, SaldoAlCierre = NULL, Moneda = NULL, UsuarioCierre = NULL, FechaCierre = NULL, "
                                "UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() WHERE IdContacto = ?", (usuario, c["idContacto"])))
        else:
            operaciones.append(("UPDATE dbo.RevisionFichas SET Estado = ?, InventarioFuentes = ?, Nota = ?, PreguntaBloqueante = ?, MotivoExcepcion = ?, Corte = ?, "
                                "SaldoAlCierre = ?, Moneda = ?, UsuarioCierre = ?, FechaCierre = ?, UsuarioActualiza = ?, FechaActualiza = SYSDATETIME() WHERE IdContacto = ?",
                                (previa["Estado"], previa["InventarioFuentes"], previa["Nota"], previa["PreguntaBloqueante"], previa["MotivoExcepcion"], previa["Corte"],
                                 previa["SaldoAlCierre"], previa["Moneda"], previa["UsuarioCierre"], previa["FechaCierre"], usuario, c["idContacto"])))
        operaciones.append(("INSERT INTO dbo.AuditoriaRevisionesHistorial (IdContacto, Accion, Detalle, Usuario) VALUES (?, 'ficha-estado', ?, ?)",
                            (c["idContacto"], json.dumps({"nuevo": (previa or {}).get("Estado", "pendiente"), "motivo": f"Reversión del lote {id_correccion}"}, ensure_ascii=False), usuario)))
    if operaciones:
        execute_write_transaction(operaciones)


def contextos_de_todas(corte: date | None = None, refrescar: bool = False) -> tuple[date, dict[int, dict]]:
    """Contextos de todas las cuentas con movimientos (en caché); devuelve también el corte usado."""
    if corte is None:
        vigente = corte_vigente()
        if vigente is None:
            raise FichaError(404, "Todavía no hay un corte definido")
        corte = vigente["corte"]
    return corte, cache.contextos(corte, cargar_contextos, refrescar)


def resumenes(contextos: dict[int, dict]) -> list[dict]:
    """Una línea por cuenta para las colas y el tablero: cola, etapa, estado efectivo, movimientos, importe y saldo."""
    salida = []
    for id_contacto, ctx in contextos.items():
        ficha = armar_ficha(ctx)
        salida.append({"idContacto": id_contacto, "razonSocial": (ctx.get("cuenta") or {}).get("razonSocial"), "movimientos": ctx["movimientos"],
                       "importe": ctx["volumen"], "saldo": ctx["saldo"], "moneda": ficha["moneda"], "etapa": ficha["etapa"], "estado": ficha["estadoEfectivo"],
                       "cola": ficha["cola"], "otrosProblemas": ficha["otrosProblemas"], "pregunta": ficha["pregunta"],
                       # lo que está en juego en la cuenta: el mayor entre su saldo y los pagos sin factura que faltan respaldar
                       "importeEnJuego": round(max(abs(ctx["saldo"]), float(ctx["criterios_ctx"]["pagos_importe_pendiente"])), 2),
                       "desde": (ctx.get("fila") or {}).get("FechaActualiza")})
    return salida


# --------------------------------------------------------------------------- puerta del FIFO (US5, FR-007)

def _resultado_de_puerta(ctx: dict | None) -> dict:
    """Una cuenta sin movimientos hasta el corte no tiene nada que revisar antes del FIFO: la puerta se abre."""
    if ctx is None:
        return {"puede": True, "etapaPendiente": None, "criterios": []}
    puede, etapa, faltan = criterios.previos_al_fifo(criterios.evaluar(ctx["criterios_ctx"]))
    return {"puede": puede, "etapaPendiente": etapa, "criterios": faltan}


def puerta_fifo(id_contacto: int, corte: date | None = None) -> dict:
    """¿La cuenta completó E1 a E4 (documentos, movimientos, tarjetas y conciliación)? Solo lectura."""
    corte = corte or (corte_vigente() or {}).get("corte")
    if corte is None:
        return {"puede": True, "etapaPendiente": None, "criterios": []}
    return _resultado_de_puerta(cargar_contextos(corte, [id_contacto]).get(id_contacto))


def puerta_fifo_varias(ids: list[int], corte: date | None = None) -> dict[int, dict]:
    """La puerta de varias cuentas con consultas por lotes (para las tandas del FIFO)."""
    corte = corte or (corte_vigente() or {}).get("corte")
    if corte is None:
        return {i: {"puede": True, "etapaPendiente": None, "criterios": []} for i in ids}
    contextos = cargar_contextos(corte, ids) if ids else {}
    return {i: _resultado_de_puerta(contextos.get(i)) for i in ids}


def mensaje_de_puerta(puerta: dict) -> str:
    c = puerta["criterios"][0] if puerta["criterios"] else None
    resto = f" Falta: {c['codigo']}: {c['medido']}." if c else ""
    return f"Todavía no se puede aplicar el FIFO: la cuenta no completó la etapa {puerta['etapaPendiente']}.{resto}"
