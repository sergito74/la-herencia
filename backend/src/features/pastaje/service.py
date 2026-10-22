"""039: reglas de pastaje (contratos, bitácora, liquidaciones, comprobantes, resumen mensual)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from src.features.pastaje import calculo, inmag, repository as repo
from src.features.pastaje.calculo import Movimiento, SinIndice, Tarifa
from src.features.pastaje.repository import Conflicto, NoExiste  # noqa: F401 (re-export para el router)

EMPRESA_GIAMIGLI = 386  # Contacto "Giamigli de Bolivar" (CUIT 30712114602)
CUIT_GIAMIGLI = "30712114602"
LA_HERENCIA = 1  # dbo.Establecimientos
CARPETA_DEFECTO = r"C:\Users\Sergio\Documents\La Herencia\Ganaderia\Pastaje - La Herencia"
TIPOS_MOV = ("ingreso", "egreso", "muerte", "faltante", "nacimiento", "destete", "recuento")


def _d(x) -> Decimal:
    return Decimal(str(x)) if x not in (None, "") else Decimal(0)


def _mes(d: date) -> date:
    return d.replace(day=1)


def _fin_mes(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _siguiente(d: date) -> date:
    return (_fin_mes(d) + timedelta(days=1))


# --- Insumos del cálculo -----------------------------------------------------

def _movs(id_contrato: int) -> list[Movimiento]:
    return [Movimiento(date.fromisoformat(m["fecha"]), m["tipo"], m["idTipoHacienda"], m["cabezas"])
            for m in repo.bitacora(id_contrato) if m["estado"] == "vigente"]


def _tarifas(id_contrato: int) -> list[Tarifa]:
    return [Tarifa(t["idTipoHacienda"], t["tipoTarifa"], _d(t["valor"]), date.fromisoformat(t["vigenteDesde"]))
            for t in repo.tarifas(id_contrato)]


def calcular(id_contrato: int, periodo: date, hasta: date | None = None) -> calculo.Liquidacion:
    c = repo.contrato(id_contrato)
    ini = _mes(periodo)
    return calculo.liquidar(ini, _movs(id_contrato), _tarifas(id_contrato), inmag.indices(ini, _fin_mes(ini)),
                            _d(c["alicuotaIva"]), hasta)


def _serializar(liq: calculo.Liquidacion, nombres: dict[int, str]) -> dict:
    return {
        "periodo": liq.periodo.isoformat(), "diasMes": liq.dias_mes, "moneda": liq.moneda,
        "precioPromedio": str(liq.precio) if liq.precio is not None else None, "kg": str(round(liq.kg, 4)),
        "neto": str(liq.neto), "iva": str(liq.iva), "total": str(liq.total),
        "tramos": [{"idTipoHacienda": t.categoria, "categoria": nombres.get(t.categoria, str(t.categoria)),
                    "desde": t.desde.isoformat(), "hasta": t.hasta.isoformat(), "cabezas": t.cabezas, "dias": t.dias,
                    "tipoTarifa": t.tipo, "valorMes": str(t.valor_mes), "kg": str(round(t.kg, 4)),
                    "importe": str(round(t.importe, 2))} for t in liq.tramos],
        "indices": [{"fecha": f.isoformat(), "indice": str(v)} for f, v in liq.indices],
    }


def preview(id_contrato: int, periodo: date) -> dict:
    nombres = repo.categorias()
    try:
        out = _serializar(calcular(id_contrato, periodo), nombres)
        out["bloqueo"] = None
    except SinIndice as exc:
        out = {"periodo": _mes(periodo).isoformat(), "bloqueo": str(exc), "tramos": [], "indices": []}
    out["textoFactura"] = texto_sugerido(out, nombres) if not out["bloqueo"] else []
    out["liquidacion"] = repo.mensual_vigente(id_contrato, _mes(periodo))
    return out


def texto_sugerido(liq: dict, nombres: dict[int, str] | None = None) -> list[str]:
    tramos = [calculo.Tramo(t["idTipoHacienda"], date.fromisoformat(t["desde"]), date.fromisoformat(t["hasta"]),
                            t["cabezas"], t["dias"], _d(t["valorMes"]), t["tipoTarifa"]) for t in liq["tramos"]]
    l = calculo.Liquidacion(date.fromisoformat(liq["periodo"]), 0, tramos)
    return calculo.texto_factura(l, nombres or repo.categorias())


# --- Contratos ---------------------------------------------------------------

def _validar_tarifas(tarifas: list[dict]) -> None:
    for t in tarifas:
        if t["tipoTarifa"] not in ("kg_novillo", "fijo_ars", "fijo_usd"):
            raise ValueError("Tipo de tarifa inválido.")
        if _d(t["valor"]) <= 0:
            raise ValueError("La tarifa debe ser mayor que cero.")


def crear_contrato(d: dict, usuario: str) -> dict:
    if not repo.contacto(d["idContacto"]):
        raise ValueError("El cliente no existe. Dalo de alta en Contactos.")
    if not d.get("tarifas"):
        raise ValueError("El contrato necesita al menos una categoría con tarifa.")
    _validar_tarifas(d["tarifas"])
    d.setdefault("carpetaDocumentos", CARPETA_DEFECTO)
    for t in d["tarifas"]:
        t.setdefault("vigenteDesde", d["fechaInicio"])
    nuevo = repo.insertar_contrato(d, d["tarifas"], usuario, EMPRESA_GIAMIGLI, LA_HERENCIA)
    return ficha(nuevo)


def _ultimo_confirmado(id_contrato: int) -> date | None:
    conf = [date.fromisoformat(l["periodo"]) for l in repo.liquidaciones(id_contrato) if l["estado"] == "confirmada"]
    return _fin_mes(max(conf)) if conf else None


def actualizar_contrato(id_contrato: int, d: dict, usuario: str) -> dict:
    actual = repo.contrato(id_contrato)
    if actual["estado"] != "vigente":
        raise Conflicto("Solo se puede editar un contrato vigente.")
    nuevas = d.get("tarifasNuevas") or []
    _validar_tarifas(nuevas)
    limite = _ultimo_confirmado(id_contrato)
    if limite and str(d["fechaInicio"]) != actual["fechaInicio"]:
        raise Conflicto("No se puede cambiar la fecha de inicio: hay meses liquidados.")
    for t in nuevas:
        if not t.get("vigenteDesde"):
            raise ValueError("Una tarifa nueva necesita fecha de vigencia.")
        if limite and date.fromisoformat(str(t["vigenteDesde"])) <= limite:
            raise Conflicto(f"Una tarifa nueva debe regir después del último mes liquidado ({limite:%d/%m/%Y}).")
    repo.actualizar_contrato(id_contrato, d, nuevas, d["version"], usuario)
    return ficha(id_contrato)


def finalizar(id_contrato: int, fecha_fin: date, motivo: str, version: int, usuario: str) -> dict:
    cab = calculo.cabezas_por_dia(_movs(id_contrato), fecha_fin)
    if cab:
        raise Conflicto(f"Al {fecha_fin:%d/%m/%Y} todavía hay hacienda en el campo: registrá el egreso total antes de finalizar.")
    repo.cambiar_estado(id_contrato, "finalizado", motivo, fecha_fin, version, usuario)
    return ficha(id_contrato)


def anular(id_contrato: int, motivo: str, version: int, usuario: str) -> dict:
    if not (motivo or "").strip():
        raise ValueError("La anulación requiere un motivo.")
    if any(l["estado"] == "confirmada" for l in repo.liquidaciones(id_contrato)):
        raise Conflicto("El contrato tiene liquidaciones confirmadas: no se puede anular, finalizalo.")
    repo.cambiar_estado(id_contrato, "anulado", motivo, None, version, usuario)
    return ficha(id_contrato)


def ficha(id_contrato: int) -> dict:
    c = repo.contrato(id_contrato)
    c["tarifas"] = repo.tarifas(id_contrato)
    c["meses"] = resumen(id_contrato)
    return c


# --- Bitácora ----------------------------------------------------------------

def registrar_movimiento(id_contrato: int, m: dict, usuario: str) -> dict:
    c = repo.contrato(id_contrato)
    if c["estado"] != "vigente":
        raise Conflicto("El contrato no está vigente.")
    if m["tipo"] not in TIPOS_MOV:
        raise ValueError("Tipo de movimiento inválido.")
    if int(m["cabezas"]) <= 0:
        raise ValueError("Las cabezas deben ser mayores que cero.")
    fecha = date.fromisoformat(str(m["fecha"]))
    if fecha < date.fromisoformat(c["fechaInicio"]):
        raise ValueError("La fecha es anterior al inicio del contrato.")
    movs = _movs(id_contrato)
    sistema = None
    diferencia = None
    if m["tipo"] == "recuento":
        sistema = calculo.cabezas_por_dia(movs, fecha).get(m["idTipoHacienda"], 0)
        diferencia = int(m["cabezas"]) - sistema
    else:
        calculo.validar_bitacora(movs + [Movimiento(fecha, m["tipo"], m["idTipoHacienda"], int(m["cabezas"]))])
    nuevo = repo.insertar_movimiento(id_contrato, m, sistema, usuario)
    return {"id": nuevo, "cabezasSistema": sistema, "diferencia": diferencia, "afectaLiquidado": _afecta_liquidado(id_contrato, fecha)}


def _afecta_liquidado(id_contrato: int, fecha: date) -> bool:
    limite = _ultimo_confirmado(id_contrato)
    return bool(limite and fecha <= limite)


def anular_movimiento(id_mov: int, motivo: str, version: int, usuario: str) -> dict:
    if not (motivo or "").strip():
        raise ValueError("La anulación requiere un motivo.")
    mov = repo.movimiento(id_mov)
    restantes = [x for x in repo.bitacora(mov["idContrato"]) if x["estado"] == "vigente" and x["id"] != id_mov]
    calculo.validar_bitacora([Movimiento(date.fromisoformat(x["fecha"]), x["tipo"], x["idTipoHacienda"], x["cabezas"])
                              for x in restantes])
    repo.anular_movimiento(id_mov, motivo, version, usuario)
    return {"id": id_mov, "afectaLiquidado": _afecta_liquidado(mov["idContrato"], date.fromisoformat(mov["fecha"]))}


def bitacora(id_contrato: int) -> dict:
    movs = repo.bitacora(id_contrato)
    hoy = date.today()
    nombres = repo.categorias()
    vig = calculo.cabezas_por_dia(_movs(id_contrato), hoy)
    return {"movimientos": movs, "cabezasActuales": [{"idTipoHacienda": k, "categoria": nombres.get(k, str(k)), "cabezas": v}
                                                     for k, v in sorted(vig.items())]}


# --- Liquidaciones -----------------------------------------------------------

def crear_borrador(id_contrato: int, periodo: date, usuario: str) -> dict:
    ini = _mes(periodo)
    if ini >= _mes(date.today()):
        raise ValueError("La liquidación es a mes vencido: solo meses ya terminados.")
    existente = repo.mensual_vigente(id_contrato, ini)
    liq = calcular(id_contrato, ini)
    if not liq.tramos:
        raise ValueError(f"No hubo hacienda en el campo en {ini:%m/%Y}.")
    lid = repo.guardar_borrador(id_contrato, liq, usuario, existente=existente)
    return repo.liquidacion(lid)


def generar_mes(periodo: date, usuario: str) -> list[dict]:
    out = []
    for c in repo.contratos("vigente") + repo.contratos("finalizado"):
        ini = _mes(periodo)
        if date.fromisoformat(c["fechaInicio"]) > _fin_mes(ini) or (c["fechaFin"] and date.fromisoformat(c["fechaFin"]) < ini):
            continue
        existente = repo.mensual_vigente(c["id"], ini)
        if existente and existente["estado"] == "confirmada":
            out.append({"contrato": c["id"], "estado": "ya confirmada"})
            continue
        try:
            liq = crear_borrador(c["id"], ini, usuario)
            out.append({"contrato": c["id"], "estado": "borrador", "id": liq["id"], "total": liq["total"]})
        except SinIndice as exc:
            out.append({"contrato": c["id"], "estado": "bloqueada", "motivo": str(exc)})
        except ValueError as exc:
            out.append({"contrato": c["id"], "estado": "sin hacienda", "motivo": str(exc)})
    return out


def _pdf(id_liq: int, original: dict | None = None) -> str:
    from src.features.pastaje import liquidacion_pdf

    liq = repo.liquidacion(id_liq)
    c = repo.contrato(liq["idContrato"])
    liq["alicuotaIva"] = c["alicuotaIva"]
    contenido = liquidacion_pdf.generar(liq, c, repo.tarifas(c["id"]), original)
    carpeta = Path(c["carpetaDocumentos"] or CARPETA_DEFECTO)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / liquidacion_pdf.nombre_archivo(liq, c["cliente"])
    ruta.write_bytes(contenido)
    repo.guardar_pdf_liquidacion(id_liq, str(ruta))
    return str(ruta)


def confirmar(id_liq: int, version: int, usuario: str) -> dict:
    liq = repo.liquidacion(id_liq)
    if liq["estado"] != "borrador":
        raise Conflicto("Solo se confirma un borrador.")
    if liq["tipo"] == "mensual":
        # Se confirma con el cálculo vigente al momento de confirmar (bitácora e índices actuales).
        if liq["version"] != version:
            raise Conflicto("La liquidación fue modificada. Volvé a cargarla.")
        nuevo = calcular(liq["idContrato"], date.fromisoformat(liq["periodo"]))
        repo.guardar_borrador(liq["idContrato"], nuevo, usuario, existente=liq)
        version = repo.liquidacion(id_liq)["version"]
    repo.confirmar_liquidacion(id_liq, version, usuario)
    original = repo.liquidacion(liq["idLiquidacionOriginal"]) if liq["tipo"] == "ajuste" else None
    _pdf(id_liq, original)
    return repo.liquidacion(id_liq)


def anular_liquidacion(id_liq: int, version: int, usuario: str) -> dict:
    repo.anular_liquidacion(id_liq, version, usuario)
    return repo.liquidacion(id_liq)


def diferencia(id_liq: int) -> dict | None:
    """Recalculado − (original + ajustes confirmados). None si no hay diferencia."""
    liq = repo.liquidacion(id_liq)
    if liq["estado"] != "confirmada" or liq["tipo"] != "mensual":
        return None
    try:
        nuevo = calcular(liq["idContrato"], date.fromisoformat(liq["periodo"]))
    except SinIndice:
        return None
    ajustes = [l for l in repo.liquidaciones(liq["idContrato"]) if l["idLiquidacionOriginal"] == id_liq and l["estado"] == "confirmada"]
    liquidado = _d(liq["neto"]) + sum(_d(a["neto"]) for a in ajustes)
    iva_liq = _d(liq["iva"]) + sum(_d(a["iva"]) for a in ajustes)
    dif = nuevo.neto - liquidado
    return {"neto": dif, "iva": nuevo.iva - iva_liq, "recalculado": nuevo, "liquidado": liquidado} if dif else None


def crear_ajuste(id_liq: int, usuario: str) -> dict:
    d = diferencia(id_liq)
    if not d:
        raise Conflicto("No hay diferencia entre lo liquidado y el recálculo.")
    liq = repo.liquidacion(id_liq)
    lid = repo.guardar_borrador(liq["idContrato"], d["recalculado"], usuario, tipo="ajuste", original=id_liq,
                                importes=(d["neto"], d["iva"], d["neto"] + d["iva"]))
    return repo.liquidacion(lid)


# --- Comprobantes ------------------------------------------------------------

def leer_comprobante(contenido: bytes) -> dict:
    from src.features.pastaje import lector_factura

    datos = lector_factura.leer_pdf(contenido)
    datos["advertencias"] = []
    if datos["cuitEmisor"] != CUIT_GIAMIGLI:
        datos["advertencias"].append(f"El emisor ({datos['cuitEmisor']}) no es Giamigli de Bolívar S.A.")
    return datos


def _comparar(c: dict, contrato: dict, liq: dict | None) -> list[str]:
    adv = []
    cuit = (contrato.get("cuit") or "").replace("-", "")
    if c.get("cuitCliente") and cuit and c["cuitCliente"] != cuit:
        adv.append(f"El CUIT del comprobante ({c['cuitCliente']}) no es el del cliente del contrato ({cuit}).")
    if liq:
        signo = Decimal(-1) if c["tipo"] == "nota_credito" else Decimal(1)
        for k in ("neto", "iva", "total"):
            esperado = _d(liq[k]) * signo if liq["tipo"] == "ajuste" else _d(liq[k])
            if _d(c[k]) != abs(esperado):
                adv.append(f"{k.capitalize()} del comprobante {_d(c[k])} distinto de la liquidación {abs(esperado)}.")
    if _d(c["neto"]) + _d(c["iva"]) + _d(c.get("otrosTributos")) != _d(c["total"]):
        adv.append("Neto + IVA + otros tributos no coincide con el total.")
    return adv


def previsualizar_comprobante(c: dict) -> dict:
    contrato = repo.contrato(c["idContrato"])
    liq = repo.liquidacion(c["idLiquidacion"]) if c.get("idLiquidacion") else None
    return {"advertencias": _comparar(c, contrato, liq)}


def registrar_comprobante(c: dict, usuario: str) -> dict:
    contrato = repo.contrato(c["idContrato"])
    if repo.existe_numero(c["tipo"], c["letra"], c["puntoVenta"], c["numero"]):
        raise Conflicto("Ese comprobante ya está cargado.")
    liq = None
    if c["tipo"] == "factura":
        if not c.get("idLiquidacion"):
            raise ValueError("La factura debe vincularse a la liquidación del mes.")
        liq = repo.liquidacion(c["idLiquidacion"])
        if liq["idContrato"] != contrato["id"] or liq["estado"] != "confirmada" or liq["tipo"] != "mensual":
            raise ValueError("La factura se vincula a una liquidación mensual confirmada del mismo contrato.")
        if any(x["idLiquidacion"] == liq["id"] and x["tipo"] == "factura" and x["estado"] == "vigente"
               for x in repo.comprobantes(contrato["id"])):
            raise Conflicto("Esa liquidación ya tiene factura.")
        c["idComprobanteAsociado"] = None
    else:
        if not c.get("idComprobanteAsociado"):
            raise ValueError("La ND/NC debe vincularse a la factura original.")
        orig = repo.comprobante(c["idComprobanteAsociado"])
        if orig["tipo"] != "factura" or orig["idContrato"] != contrato["id"] or orig["estado"] != "vigente":
            raise ValueError("La ND/NC se vincula a una factura vigente del mismo contrato.")
        if c.get("idLiquidacion"):
            liq = repo.liquidacion(c["idLiquidacion"])
            if liq["tipo"] != "ajuste" or liq["estado"] != "confirmada" or liq["idLiquidacionOriginal"] != orig["idLiquidacion"]:
                raise ValueError("La ND/NC se respalda con una liquidación de ajuste confirmada de esa factura.")
            if (_d(liq["neto"]) > 0) != (c["tipo"] == "nota_debito"):
                raise ValueError("El ajuste es a favor del " + ("campo: corresponde nota de débito." if _d(liq["neto"]) > 0
                                                                 else "cliente: corresponde nota de crédito."))
    if _comparar(c, contrato, liq) and not c.get("aceptarAdvertencias"):
        raise Conflicto("Hay diferencias con la liquidación o el contrato: revisalas y aceptalas para guardar.")
    if c["tipo"] == "factura" or liq:
        c["idCampania"] = repo.id_campania(calculo.campania(date.fromisoformat(liq["periodo"])))
    else:
        c["idCampania"] = orig["idCampania"]  # La ND/NC corrige el mes de su factura.
    c["idEstablecimiento"] = LA_HERENCIA
    nuevo = repo.insertar_comprobante(c, usuario)
    return repo.comprobante(nuevo)


def anular_comprobante(id_comp: int, motivo: str, version: int, usuario: str) -> dict:
    if not (motivo or "").strip():
        raise ValueError("La anulación requiere un motivo.")
    try:
        repo.anular_comprobante(id_comp, motivo, version, usuario)
    except Conflicto as exc:
        raise Conflicto("No se puede anular: tiene cobros aplicados o fue modificado.") from exc
    return repo.comprobante(id_comp)


def comprobantes(id_contrato: int) -> list[dict]:
    comps = repo.comprobantes(id_contrato)
    cob = repo.cobrado([x["id"] for x in comps if x["estado"] == "vigente" and x["tipo"] != "nota_credito"])
    for x in comps:
        nc = sum(_d(n["total"]) for n in comps if n["idComprobanteAsociado"] == x["id"] and n["tipo"] == "nota_credito"
                 and n["estado"] == "vigente")
        x["cobrado"] = str(cob.get(x["id"], Decimal(0)))
        x["saldo"] = str(_d(x["total"]) - nc - cob[x["id"]]) if x["id"] in cob else "0"
    return comps


# --- Resumen mensual y tarjetas ------------------------------------------------

def resumen(id_contrato: int) -> list[dict]:
    c = repo.contrato(id_contrato)
    if c["estado"] == "anulado":
        return []
    hoy = date.today()
    ini = _mes(date.fromisoformat(c["fechaInicio"]))
    fin = _mes(min(hoy, date.fromisoformat(c["fechaFin"]))) if c["fechaFin"] else _mes(hoy)
    liqs = repo.liquidaciones(id_contrato)
    comps = comprobantes(id_contrato)
    out = []
    p = ini
    while p <= fin:
        en_curso = p == _mes(hoy)
        fila = {"periodo": p.isoformat(), "devengado": None, "liquidado": None, "facturado": "0", "cobrado": "0",
                "saldo": "0", "estado": "", "diferencia": None, "alertas": [], "idLiquidacion": None}
        try:
            dev = calcular(id_contrato, p, hoy if en_curso else None)
            fila["devengado"] = str(dev.neto)
        except SinIndice as exc:
            fila["alertas"].append(str(exc))
        mensual = next((l for l in liqs if l["periodo"] == p.isoformat() and l["tipo"] == "mensual" and l["estado"] != "anulada"), None)
        if mensual:
            fila["idLiquidacion"] = mensual["id"]
            ids = {mensual["id"]} | {l["id"] for l in liqs if l["idLiquidacionOriginal"] == mensual["id"] and l["estado"] == "confirmada"}
            if mensual["estado"] == "confirmada":
                fila["liquidado"] = str(sum(_d(l["neto"]) for l in liqs if l["id"] in ids and l["estado"] == "confirmada"))
                d = diferencia(mensual["id"])
                if d:
                    fila["diferencia"] = str(d["neto"])
                    fila["alertas"].append(f"Diferencia de {d['neto']} entre lo liquidado y el recálculo: emitir ajuste.")
            fac = [x for x in comps if x["estado"] == "vigente" and (x["idLiquidacion"] in ids or
                   any(f["id"] == x["idComprobanteAsociado"] and f["idLiquidacion"] in ids for f in comps))]
            neto = sum((-_d(x["neto"]) if x["tipo"] == "nota_credito" else _d(x["neto"])) for x in fac)
            fila["facturado"] = str(neto)
            fila["cobrado"] = str(sum(_d(x["cobrado"]) for x in fac))
            fila["saldo"] = str(sum(_d(x["saldo"]) for x in fac if x["tipo"] != "nota_credito"))
        sin_hacienda = fila["devengado"] in (None, "0", "0.00") and not mensual
        if en_curso:
            fila["estado"] = "En curso"
        elif sin_hacienda:
            fila["estado"] = "Sin hacienda"
        elif not mensual:
            fila["estado"] = "Sin liquidar"
            fila["alertas"].append("Mes cerrado sin liquidación.")
        elif mensual["estado"] == "borrador":
            fila["estado"] = "Liquidación en borrador"
        elif _d(fila["facturado"]) == 0:
            fila["estado"] = "Liquidado sin factura"
            if hoy > _fin_mes(_siguiente(p)):
                fila["alertas"].append("Mes liquidado sin factura dentro del mes siguiente.")
        elif _d(fila["saldo"]) <= Decimal("0.005"):
            fila["estado"] = "Cobrado"
        elif _d(fila["cobrado"]) > 0:
            fila["estado"] = "Cobrado parcial"
        else:
            fila["estado"] = "Facturado — pendiente de cobro"
        out.append(fila)
        p = _siguiente(p)
    return list(reversed(out))


def tarjetas(estado: str | None = None) -> list[dict]:
    hoy = date.today()
    nombres = repo.categorias()
    ultimo = inmag.listar(hoy - timedelta(days=15), hoy)
    out = []
    for c in repo.contratos(estado):
        cab = calculo.cabezas_por_dia(_movs(c["id"]), hoy)
        meses = resumen(c["id"]) if c["estado"] != "anulado" else []
        curso = meses[0] if meses and meses[0]["estado"] == "En curso" else None
        promedio = None
        try:
            liq = calcular(c["id"], hoy, hoy)
            promedio = str(liq.precio) if liq.precio is not None else None
        except SinIndice:
            pass
        pendiente = next((m for m in reversed(meses) if m["estado"] in ("Sin liquidar", "Liquidación en borrador",
                                                                         "Liquidado sin factura", "Facturado — pendiente de cobro",
                                                                         "Cobrado parcial")), None)
        proximo = None
        if pendiente:
            p = date.fromisoformat(pendiente["periodo"])
            mes = f"{calculo.MESES[p.month - 1]} {p.year}"
            proximo = {"Sin liquidar": f"Liquidar {mes}", "Liquidación en borrador": f"Confirmar liquidación de {mes}",
                       "Liquidado sin factura": f"Cargar factura de {mes}"}.get(pendiente["estado"], f"Cobro pendiente de {mes}")
        out.append({**c, "cabezasActuales": [{"categoria": nombres.get(k, str(k)), "cabezas": v} for k, v in sorted(cab.items())],
                    "tarifas": repo.tarifas(c["id"]), "inmagUltimo": ultimo[-1] if ultimo else None,
                    "promedioMesCurso": promedio, "estimadoMesCurso": curso["devengado"] if curso else None,
                    "proximoPaso": proximo, "alertas": [a for m in meses for a in m["alertas"]][:5]})
    return out


def ingresos_por_campania(campania: str) -> list[dict]:
    """Neto facturado de pastaje (facturas + ND − NC vigentes) por establecimiento de una campaña."""
    from src.db.connection import fetch_all

    return fetch_all(
        "SELECT e.Establecimiento establecimiento, CAST(SUM(CASE WHEN c.Tipo='nota_credito' THEN -c.Neto ELSE c.Neto END) "
        "AS varchar(30)) neto FROM dbo.PastajeComprobantes c JOIN dbo.Campañas k ON k.IdCampaña=c.IdCampania "
        "LEFT JOIN dbo.Establecimientos e ON e.Id=c.IdEstablecimiento WHERE c.Estado='vigente' AND k.Campaña=? "
        "GROUP BY e.Establecimiento", (campania,))
