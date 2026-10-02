"""Ejecuciones del recálculo FIFO (032): simulación, lista y detalle (US1).

Simular escribe solo en `RecalculoFifoEjecucion`, `RecalculoFifoContacto`
y `RecalculoFifoAplicacion`. Nunca toca `AplicacionesPago` (FR-009).
Aplicar y revertir (US2) se agregan después de la revisión de Sergio.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime

from src.db.connection import execute_insert_returning_id, execute_write, execute_write_transaction, fetch_all, fetch_one
from src.features.recalculo_fifo import cambio, controles, entrada, motor

ETAPA_1 = [258, 47, 48, 23, 384, 340, 249, 276, 220]
FILTROS = {"todos", "cierra", "no-cierra", "mejora", "empeora", "excepcion"}
FILAS_POR_INSERT = 100


def _insert_multi(tabla: str, columnas: list[str], filas: list[tuple]) -> list[tuple]:
    """Sentencias INSERT de varias filas (límite de 2.100 parámetros de SQL Server)."""
    stmts = []
    por_lote = max(1, min(FILAS_POR_INSERT, 2000 // len(columnas)))
    for i in range(0, len(filas), por_lote):
        lote = filas[i:i + por_lote]
        valores = ",".join("(" + ",".join("?" * len(columnas)) + ")" for _ in lote)
        stmts.append((f"INSERT INTO dbo.{tabla} ({','.join(columnas)}) VALUES {valores}",
                      tuple(v for fila in lote for v in fila)))
    return stmts


def _calcular(id_contactos: list[int], hoy: date) -> list[dict]:
    tc = cambio.funcion_tc(hoy)
    resultados = []
    for id_contacto, e in entrada.armar(id_contactos).items():
        if not e["items"]:
            continue
        res = motor.recalcular(e["items"], e["fijos"], tc, hoy)
        ev = controles.evaluar(e, res, tc)
        resultados.append({"idContacto": id_contacto, "nombre": e["nombre"], "res": res, "ev": ev})
    return resultados


def simular(alcance, usuario: str, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    if alcance == "todos":
        ids = entrada.contactos_todos()
    elif alcance == "etapa-1":
        ids = ETAPA_1
    else:
        ids = sorted({int(i) for i in alcance})
    if not ids:
        raise ValueError("El alcance no tiene contactos.")
    inicio = datetime.now()
    resultados = _calcular(ids, hoy)

    resumen = {
        "contactos": len(resultados),
        "cierranDespues": sum(r["ev"]["cierraDespues"] for r in resultados),
        "cerrabanAntes": sum(r["ev"]["cerrabaAntes"] for r in resultados),
        "mejoran": sum(r["ev"]["tendencia"] == "mejora" for r in resultados),
        "empeoran": sum(r["ev"]["tendencia"] == "empeora" for r in resultados),
        "excepciones": sum(not r["ev"]["cierraDespues"] for r in resultados),
        "aplicaciones": sum(len(r["res"]["aplicaciones"]) for r in resultados),
        "segundos": None,
    }
    id_ejecucion = execute_insert_returning_id(
        "INSERT INTO dbo.RecalculoFifoEjecucion (Tipo, Estado, Alcance, Usuario, Resumen) "
        "OUTPUT INSERTED.IdEjecucion VALUES ('simulacion', 'simulada', ?, ?, ?)",
        (json.dumps(alcance if isinstance(alcance, str) else ids), usuario, json.dumps(resumen)))

    filas_c, filas_a = [], []
    for r in resultados:
        ev = r["ev"]
        filas_c.append((id_ejecucion, r["idContacto"], None, (r["nombre"] or "")[:200], ev["moneda"],
                        ev["facturadoAntes"], ev["pagadoAntes"], ev["aplicadoAntes"], ev["aplicadoDespues"],
                        ev["anticipoAbierto"], ev["saldo"], ev["volumen"], int(ev["cerrabaAntes"]),
                        int(ev["cierraDespues"]), ev["tendencia"], json.dumps(ev["controles"], ensure_ascii=False),
                        json.dumps(ev["marcas"] + [{"codigo": "datos", "descripcion": d} for d in ev["excepcionesDatos"]],
                                   ensure_ascii=False),
                        r["res"]["huella"], "ninguna" if ev["cierraDespues"] else "pendiente"))
        for a in r["res"]["aplicaciones"]:
            filas_a.append((id_ejecucion, r["idContacto"], a["credito"][0], a["credito"][1], a["debito"][0],
                            a["debito"][1], a["debito"][2], a["importeAplicado"], a["moneda"], a["importeArs"],
                            a["tipoCambio"], a["diferenciaCambio"], a["regla"], a["fechaCredito"], a["fechaVencimiento"]))
    stmts = _insert_multi("RecalculoFifoContacto", [
        "IdEjecucion", "IdContacto", "ContactoUnificado", "Nombre", "Moneda", "FacturadoAntes", "PagadoAntes",
        "AplicadoAntes", "AplicadoDespues", "AnticipoAbierto", "Saldo", "Volumen", "CerrabaAntes", "CierraDespues",
        "Tendencia", "Controles", "Marcas", "Huella", "EstadoExcepcion"], filas_c)
    stmts += _insert_multi("RecalculoFifoAplicacion", [
        "IdEjecucion", "IdContacto", "OrigenCredito", "IdCredito", "OrigenDebito", "IdDebito", "NroCuota",
        "ImporteAplicado", "Moneda", "ImporteArs", "TipoCambio", "DiferenciaCambio", "Regla", "FechaCredito",
        "FechaVencimiento"], filas_a)
    if stmts:
        execute_write_transaction(stmts)
    resumen["segundos"] = round((datetime.now() - inicio).total_seconds(), 1)
    execute_write("UPDATE dbo.RecalculoFifoEjecucion SET FechaFin = SYSDATETIME(), Resumen = ? WHERE IdEjecucion = ?",
                  (json.dumps(resumen), id_ejecucion))
    return {"idEjecucion": id_ejecucion, "resumen": resumen}


def _ejecucion(fila: dict) -> dict:
    return {"idEjecucion": fila["IdEjecucion"], "tipo": fila["Tipo"], "estado": fila["Estado"],
            "alcance": json.loads(fila["Alcance"]), "fechaInicio": fila["FechaInicio"], "fechaFin": fila["FechaFin"],
            "usuario": fila["Usuario"], "backupArchivo": fila["BackupArchivo"],
            "resumen": json.loads(fila["Resumen"]) if fila["Resumen"] else None}


def listar() -> list[dict]:
    return [_ejecucion(f) for f in fetch_all("SELECT TOP 50 * FROM dbo.RecalculoFifoEjecucion ORDER BY IdEjecucion DESC")]


def obtener(id_ejecucion: int) -> dict:
    fila = fetch_one("SELECT * FROM dbo.RecalculoFifoEjecucion WHERE IdEjecucion = ?", (id_ejecucion,))
    if fila is None:
        raise KeyError(id_ejecucion)
    return _ejecucion(fila)


_ORDENES = {"volumen": "Volumen DESC", "nombre": "Nombre ASC", "saldo": "ABS(Saldo) DESC"}
_WHERE_FILTRO = {
    "todos": "", "cierra": " AND CierraDespues = 1", "no-cierra": " AND CierraDespues = 0",
    "mejora": " AND Tendencia = 'mejora'", "empeora": " AND Tendencia = 'empeora'",
    "excepcion": " AND EstadoExcepcion = 'pendiente'",
}


def _contacto(f: dict) -> dict:
    return {"idContacto": f["IdContacto"], "nombre": f["Nombre"], "moneda": f["Moneda"].strip(),
            "facturadoAntes": float(f["FacturadoAntes"]), "pagadoAntes": float(f["PagadoAntes"]),
            "aplicadoAntes": float(f["AplicadoAntes"]), "aplicadoDespues": float(f["AplicadoDespues"]),
            "anticipoAbierto": float(f["AnticipoAbierto"]), "saldo": float(f["Saldo"]), "volumen": float(f["Volumen"]),
            "cerrabaAntes": bool(f["CerrabaAntes"]), "cierraDespues": bool(f["CierraDespues"]),
            "tendencia": f["Tendencia"], "controles": json.loads(f["Controles"]), "marcas": json.loads(f["Marcas"]),
            "estadoExcepcion": f["EstadoExcepcion"], "notaExcepcion": f["NotaExcepcion"]}


def contactos(id_ejecucion: int, filtro: str = "todos", orden: str = "volumen", pagina: int = 1,
              tamanio: int = 50) -> dict:
    if filtro not in FILTROS:
        raise ValueError(f"Filtro desconocido: {filtro}")
    where = " WHERE IdEjecucion = ?" + _WHERE_FILTRO[filtro]
    total = fetch_one("SELECT COUNT(*) AS n FROM dbo.RecalculoFifoContacto" + where, (id_ejecucion,))["n"]
    filas = fetch_all(f"SELECT * FROM dbo.RecalculoFifoContacto{where} ORDER BY {_ORDENES.get(orden, _ORDENES['volumen'])}, "
                      "IdContacto OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", (id_ejecucion, (pagina - 1) * tamanio, tamanio))
    return {"items": [_contacto(f) for f in filas], "total": total, "pagina": pagina, "tamanio": tamanio}


def detalle(id_ejecucion: int, id_contacto: int) -> dict:
    fila = fetch_one("SELECT * FROM dbo.RecalculoFifoContacto WHERE IdEjecucion = ? AND IdContacto = ?",
                     (id_ejecucion, id_contacto))
    if fila is None:
        raise KeyError(id_contacto)
    aplic = fetch_all("SELECT OrigenCredito AS oc, IdCredito AS ic, OrigenDebito AS od, IdDebito AS id_, NroCuota AS cuota, "
                      "ImporteAplicado AS imp, Moneda AS moneda, ImporteArs AS ars, TipoCambio AS tc, "
                      "DiferenciaCambio AS dif, Regla AS regla, FechaCredito AS fc, FechaVencimiento AS fv "
                      "FROM dbo.RecalculoFifoAplicacion WHERE IdEjecucion = ? AND IdContacto = ? ORDER BY IdRenglon",
                      (id_ejecucion, id_contacto))
    e = entrada.armar([id_contacto]).get(id_contacto, {"items": []})
    aplicado: dict[tuple, float] = defaultdict(float)
    for a in aplic:
        aplicado[(a["od"], a["id_"], a["cuota"])] += float(a["imp"])
        aplicado[(a["oc"], a["ic"], None)] += float(a["imp"]) if a["moneda"] == "ARS" else float(a["ars"])
    renglones = []
    saldo = 0.0
    for i in sorted(e["items"], key=lambda i: (i["fecha"], i["lado"], i["clave"][1])):
        signo = 1 if i["lado"] == "D" else -1
        ars = i["importe"] * (i["tcDoc"] or 1.0) if i["moneda"] == "USD" else i["importe"]
        saldo += signo * ars
        renglones.append({
            "origen": i["clave"][0], "id": i["clave"][1], "cuota": i["clave"][2], "lado": i["lado"], "clase": i["clase"],
            "documento": i.get("documento"), "nro": i["nro"], "fecha": i["fecha"], "vencimiento": i["vencimiento"],
            "moneda": i["moneda"], "importe": round(i["importe"], 2), "aplicado": round(aplicado.get(i["clave"], 0.0), 2),
            "suspendido": i["suspendido"], "saldoAcumuladoArs": round(saldo, 2)})
    return {
        "contacto": _contacto(fila),
        "renglones": renglones,
        "aplicaciones": [{"credito": {"origen": a["oc"], "id": a["ic"]}, "debito": {"origen": a["od"], "id": a["id_"], "cuota": a["cuota"]},
                          "importeAplicado": float(a["imp"]), "moneda": a["moneda"].strip(), "importeArs": float(a["ars"]),
                          "tipoCambio": float(a["tc"]) if a["tc"] is not None else None,
                          "diferenciaCambio": float(a["dif"]), "regla": a["regla"], "fechaCredito": a["fc"],
                          "fechaVencimiento": a["fv"]} for a in aplic],
    }


def marcar_excepcion(id_ejecucion: int, id_contacto: int, estado: str, nota: str | None) -> None:
    if estado not in ("pendiente", "resuelta"):
        raise ValueError("Estado de excepción inválido.")
    filas = execute_write("UPDATE dbo.RecalculoFifoContacto SET EstadoExcepcion = ?, NotaExcepcion = ? "
                          "WHERE IdEjecucion = ? AND IdContacto = ?", (estado, (nota or "")[:500] or None,
                                                                      id_ejecucion, id_contacto))
    if not filas:
        raise KeyError(id_contacto)


def descartar(id_ejecucion: int) -> None:
    """Una simulación descartada queda como historial y no se puede aplicar."""
    filas = execute_write("UPDATE dbo.RecalculoFifoEjecucion SET Estado = 'descartada' "
                          "WHERE IdEjecucion = ? AND Estado = 'simulada'", (id_ejecucion,))
    if not filas:
        raise KeyError(id_ejecucion)


# --- US2: aplicar y revertir ------------------------------------------------

# Renglones de la vista que AplicacionesPago puede guardar (sus CHECK).
MOV_A_APLICACION = {"Banco Nacion": "bna", "Galicia": "galicia", "Pagos efectivo": "efectivo",
                    "Cobros Valores Recibidos": "valores-recibidos", "Pagos Valores Recibidos": "valores-recibidos",
                    "Retenciones": "retenciones", "Ret. IVA Granos": "ret-iva-granos",
                    "Ret. Ventas Hacienda": "ret-ventas-hacienda",
                    # Documento que cancela a otro (compensación o NC a su factura).
                    "Compras": "comp-compra", "Venta Granos": "comp-venta-granos",
                    "Venta Hacienda": "comp-venta-hacienda"}
DOC_A_APLICACION = {"Compras": "CompraDeuda", "Venta Granos": "VentaGranos", "Venta Hacienda": "VentaHacienda"}
# Lo que el recálculo reemplaza: las aplicaciones automáticas. Las manuales
# y las cadenas reales (tarjeta, valores propios) no se tocan (FR-004, FR-024).
ORIGENES_REEMPLAZABLES = ("automatica-exacta", "automatica-mejor-esfuerzo", "correccion-031", "fifo-032")
REGLAS_NO_ESCRITAS = ("cadena", "eleccion")


class Conflicto(Exception):
    """La ejecución no está en un estado que permita la operación (409)."""


class RequiereConfirmacion(Exception):
    """Hay contactos que empeoran y no se confirmó aplicarlos (422)."""


def _filas_a_escribir(aplic: list[dict]) -> list[tuple]:
    filas: dict[tuple, float] = defaultdict(float)
    for a in aplic:
        if a["regla"] in REGLAS_NO_ESCRITAS:
            continue
        om, td = MOV_A_APLICACION.get(a["oc"]), DOC_A_APLICACION.get(a["od"])
        if om is None or td is None:
            continue  # compensaciones, retenciones, tarjeta: viven solo en el recálculo
        # Valor del documento: a un documento en us$ pagado en pesos se le
        # aplica su equivalente al TC de la factura; la diferencia de cambio
        # queda en el recálculo y no sobreaplica la factura (FR-006).
        filas[(om, int(a["ic"]), td, int(a["id_"]), a["regla"])] += float(a["ars"]) - float(a["dif"] or 0)
    return [(om, ic, td, idd, round(imp, 2), regla) for (om, ic, td, idd, regla), imp in sorted(filas.items())
            if round(imp, 2) > 0]


def _huella_filas(filas: list[tuple]) -> str:
    claves = sorted(f"{om}|{ic}|{td}|{idd}|{imp:.2f}" for om, ic, td, idd, imp, _ in filas)
    return hashlib.sha256("\n".join(claves).encode()).hexdigest()


def _vigentes_reemplazables(id_contacto: int) -> list[dict]:
    """Aplicaciones automáticas vigentes cuyo documento o movimiento es del contacto."""
    renglones = fetch_all("SELECT Origen AS o, IdOrigen AS i FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?",
                          (id_contacto,))
    claves_doc = {(DOC_A_APLICACION[d["o"]], int(d["i"])) for d in renglones if d["o"] in DOC_A_APLICACION}
    claves_mov = {(MOV_A_APLICACION[d["o"]], int(d["i"])) for d in renglones if d["o"] in MOV_A_APLICACION}
    claves_mov |= {("tarjetas", int(f["l"])) for f in fetch_all(
        "SELECT lc.IdLineaConsumo AS l FROM dbo.Tarjetas_Resumenes_Lineas_Compras lc "
        "JOIN dbo.Compras c ON c.IdDeuda = lc.IdCompra WHERE c.IdContacto = ?", (id_contacto,))}
    marcas = ",".join("?" * len(ORIGENES_REEMPLAZABLES))
    vigentes = fetch_all(
        "SELECT IdAplicacion AS id, OrigenMovimiento AS om, IdMovimientoOrigen AS ic, TipoDocumento AS td, "
        "IdDocumentoAplicado AS idd, ImporteAplicado AS imp, Origen AS origen FROM dbo.AplicacionesPago "
        f"WHERE Anulada = 0 AND Origen IN ({marcas}) AND OrigenMovimiento <> 'valores-propios' "
        # Las copias automáticas de tarjeta se reemplazan solo si el consumo ya
        # tiene su vínculo real en Tarjetas_Resumenes_Lineas_Compras (la cadena
        # que lee el recálculo). Sin ese vínculo, la copia es el único registro.
        "AND (OrigenMovimiento <> 'tarjetas' OR EXISTS (SELECT 1 FROM dbo.Tarjetas_Resumenes_Lineas_Compras lc "
        "WHERE lc.IdLineaConsumo = AplicacionesPago.IdMovimientoOrigen))",
        ORIGENES_REEMPLAZABLES)
    return [v for v in vigentes if (v["td"], int(v["idd"])) in claves_doc or (v["om"], int(v["ic"])) in claves_mov]


def aplicar(id_ejecucion: int, contactos_pedidos: list[int] | None, confirmar_empeoran: bool, usuario: str,
            hoy: date | None = None) -> dict:
    from src.features.vinculos.backup import backup_verificado

    ej = obtener(id_ejecucion)
    if ej["estado"] != "simulada":
        raise Conflicto(f"La ejecución {id_ejecucion} está {ej['estado']}: solo se aplica una simulación vigente.")
    filas_c = {f["IdContacto"]: f for f in fetch_all(
        "SELECT IdContacto, Huella, CierraDespues, Tendencia FROM dbo.RecalculoFifoContacto WHERE IdEjecucion = ?",
        (id_ejecucion,))}
    if contactos_pedidos:
        elegidos = sorted(set(contactos_pedidos))
    else:
        elegidos = sorted(c for c, f in filas_c.items() if f["CierraDespues"])
    faltan = [c for c in elegidos if c not in filas_c]
    if faltan:
        raise ValueError(f"Contactos que no están en la simulación: {faltan}")
    empeoran = [c for c in elegidos if filas_c[c]["Tendencia"] == "empeora"]
    if empeoran and not confirmar_empeoran:
        raise RequiereConfirmacion(f"Estos contactos empeoran y requieren confirmación: {empeoran}")

    # Los datos no pueden haber cambiado desde la simulación (contrato: 409).
    actuales = {r["idContacto"]: r for r in _calcular(elegidos, hoy or date.today())}
    cambiados = [c for c in elegidos if c not in actuales or actuales[c]["res"]["huella"] != filas_c[c]["Huella"]]
    if cambiados:
        raise Conflicto(f"Los datos cambiaron desde la simulación en los contactos {cambiados}. Simulá de nuevo.")

    ruta = backup_verificado(f"032-aplicar-{id_ejecucion}")
    execute_write("UPDATE dbo.RecalculoFifoEjecucion SET BackupArchivo = ? WHERE IdEjecucion = ?", (ruta, id_ejecucion))

    motivo = f"Reemplazada por recálculo FIFO ejecución {id_ejecucion}"
    aplicados, sin_cambios = [], []
    for c in elegidos:
        aplic = fetch_all("SELECT OrigenCredito AS oc, IdCredito AS ic, OrigenDebito AS od, IdDebito AS id_, "
                          "ImporteArs AS ars, DiferenciaCambio AS dif, Regla AS regla FROM dbo.RecalculoFifoAplicacion "
                          "WHERE IdEjecucion = ? AND IdContacto = ?", (id_ejecucion, c))
        nuevas = _filas_a_escribir(aplic)
        vigentes = _vigentes_reemplazables(c)
        actuales_fifo = [(v["om"], int(v["ic"]), v["td"], int(v["idd"]), round(float(v["imp"]), 2), "")
                         for v in vigentes if v["origen"] == "fifo-032"]
        if len(actuales_fifo) == len(vigentes) and _huella_filas(actuales_fifo) == _huella_filas(nuevas):
            sin_cambios.append(c)
            continue
        stmts = [("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
                  "FechaAnulacion = SYSDATETIME() WHERE IdAplicacion = ? AND Anulada = 0",
                  (motivo, usuario[:60], v["id"])) for v in vigentes]
        stmts += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, "
                   "IdDocumentoAplicado, ImporteAplicado, Fecha, Usuario, Anulada, Origen, NotaConciliacion) "
                   "VALUES (?, ?, ?, ?, ?, SYSDATETIME(), ?, 0, 'fifo-032', ?)",
                   (om, ic, td, idd, imp, usuario[:60], f"ejecucion:{id_ejecucion} regla:{regla}"))
                  for om, ic, td, idd, imp, regla in nuevas]
        if stmts:
            execute_write_transaction(stmts)
        aplicados.append(c)

    resumen = ej["resumen"] or {}
    resumen.update({"aplicados": aplicados, "sinCambios": sin_cambios})
    execute_write("UPDATE dbo.RecalculoFifoEjecucion SET Estado = 'aplicada', Resumen = ? WHERE IdEjecucion = ?",
                  (json.dumps(resumen), id_ejecucion))
    return {"aplicados": aplicados, "sinCambios": sin_cambios,
            "omitidos": sorted(set(filas_c) - set(elegidos)), "backup": ruta}


def revertir(id_ejecucion: int, usuario: str) -> dict:
    ej = obtener(id_ejecucion)
    if ej["estado"] != "aplicada":
        raise Conflicto(f"La ejecución {id_ejecucion} está {ej['estado']}: solo se revierte una aplicada.")
    posterior = fetch_one("SELECT TOP 1 IdEjecucion AS id FROM dbo.RecalculoFifoEjecucion "
                          "WHERE IdEjecucion > ? AND Estado = 'aplicada'", (id_ejecucion,))
    if posterior:
        raise Conflicto(f"Primero hay que revertir la ejecución {posterior['id']}, que es posterior.")
    motivo = f"Reemplazada por recálculo FIFO ejecución {id_ejecucion}"
    execute_write_transaction([
        ("UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, "
         "FechaAnulacion = SYSDATETIME() WHERE Origen = 'fifo-032' AND Anulada = 0 AND NotaConciliacion LIKE ?",
         (f"Reversión de la ejecución {id_ejecucion}", usuario[:60], f"ejecucion:{id_ejecucion} %")),
        ("UPDATE dbo.AplicacionesPago SET Anulada = 0, MotivoAnulacion = NULL, UsuarioAnulacion = NULL, "
         "FechaAnulacion = NULL WHERE Anulada = 1 AND MotivoAnulacion = ?", (motivo,)),
        ("UPDATE dbo.RecalculoFifoEjecucion SET Estado = 'revertida' WHERE IdEjecucion = ?", (id_ejecucion,)),
    ])
    return {"idEjecucion": id_ejecucion, "estado": "revertida"}
