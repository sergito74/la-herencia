"""Controles por contacto y comparación antes/después (032, T010).

"Antes" son los vínculos actuales leídos por la fuente unificada de 031
(`vinculos.fuente.pagado_de_documentos`). "Después" es el resultado del
motor. La tolerancia es 0,5% (aclaración del 2026-10-01).

Antes y después se mide con el mismo balance (FR-010, ver `evaluar`):
ningún documento sobreaplicado, y lo aplicado igual al menor entre los
totales de los lados Deuda y Crédito. El
"después" además falla si queda un pago de más sin explicar (FR-037) o
una excepción de datos. El motor recorta siempre, así que un documento
sobreaplicado después no puede ocurrir.
"""

from __future__ import annotations

from collections import defaultdict

from src.features.recalculo_fifo.entrada import TIPO_DOC_VISTA
from src.features.vinculos import fuente

TOLERANCIA = 0.005
VISTA_A_TIPO_DOC = {v: k for k, v in TIPO_DOC_VISTA.items()}

CONTROLES_QUE_FALLAN = ("pago-de-mas",)
DESCRIPCION = {
    "pago-de-mas": "Hay pagos o cobros de hace más de 60 días que no tienen documento al que aplicarse.",
    "documento-sobreaplicado-antes": "Antes del recálculo había documentos con más aplicado que su total.",
    "datos": "Hay renglones sin fecha en la cuenta.",
    "anticipo-largo": "Hay anticipos de más de 60 días (se aplicaron, quedan para revisar).",
    "manual-ajustado": "Una elección manual sobreaplicaba y el exceso se reasignó por FIFO.",
    "tc-implicito": "Falta cotización BNA para alguna fecha: se usó el tipo de cambio de la factura.",
    "factura-suspendida": "Tiene facturas suspendidas que el FIFO salteó.",
    "aplicado-distinto": "Quedan a la vez documentos pendientes y créditos sin aplicar (FR-010).",
    "reintegro": "Hay dinero cruzado contra dinero (reintegros): revisar.",
}


def _cerca(a: float, b: float) -> bool:
    return abs(a - b) <= max(1.0, max(abs(a), abs(b)) * TOLERANCIA)


def totales_documentos(items: list[dict], tc) -> dict[tuple, float]:
    """Total en pesos de cada documento (suma de sus cuotas)."""
    totales: dict[tuple, float] = defaultdict(float)
    for i in items:
        if i["clase"] != "doc":
            continue
        importe = float(i["importe"])
        if i["moneda"] == "USD":
            importe *= float(i.get("tcDoc") or tc(i["fecha"]) or 1.0)
        totales[i["clave"][:2]] += importe
    return dict(totales)


def pagado_antes(totales: dict[tuple, float]) -> dict[tuple, float]:
    claves = [(VISTA_A_TIPO_DOC[o], i) for (o, i) in totales if o in VISTA_A_TIPO_DOC]
    pagado = fuente.pagado_de_documentos(claves) if claves else {}
    return {(TIPO_DOC_VISTA[t], i): v for (t, i), v in pagado.items()}


PROVEEDOR = {"Compras", "Impuestos", "Remuneraciones"}
CLIENTE = {"Venta Granos", "Venta Hacienda", "Alquileres", "Cobro Seguro"}


def _grupo(origen: str) -> str:
    return "cliente" if origen in CLIENTE else "proveedor"


def evaluar(entrada_contacto: dict, resultado: dict, tc) -> dict:
    """Mismo balance antes y después (FR-010). Con SD y SC como los totales de
    los lados Deuda y Crédito, y A como lo aplicado (cada par cuenta una
    vez), lo aplicado tiene que ser el menor entre SD y SC. Eso equivale a
    que no queden a la vez documentos pendientes y créditos sin aplicar.
    Los documentos en us$ se valúan al TC de la factura."""
    items = entrada_contacto["items"]
    totales = totales_documentos(items, tc)
    antes = pagado_antes(totales)

    def ars(i, campo="importe"):
        v = float(i[campo])
        if i["moneda"] == "USD":
            v *= float(i.get("tcDoc") or tc(i["fecha"]) or 1.0)
        return v

    sd = sum(ars(i) for i in items if i["lado"] == "D")
    sc = sum(ars(i) for i in items if i["lado"] == "C")
    objetivo = min(sd, sc)

    sobre_antes = [k for k, tot in totales.items() if antes.get(k, 0) > tot * (1 + TOLERANCIA) + 1]
    aplicado_antes = round(sum(min(antes.get(k, 0), tot) for k, tot in totales.items()), 2)

    # Después: lo que queda sin aplicar en cada lado, según el motor.
    pend_d = sum(ars(i, "rem") for i in resultado["items"] if i["lado"] == "D")
    pend_c = sum(ars(i, "rem") for i in resultado["items"] if i["lado"] == "C")
    aplicado_despues = round(sum(a["importeArs"] - a["diferenciaCambio"] for a in resultado["aplicaciones"]), 2)

    f_prov = sum(ars(i) * (1 if i["lado"] == "D" else -1) for i in items
                 if i["clase"] == "doc" and _grupo(i["clave"][0]) == "proveedor")
    f_cli = sum(ars(i) * (1 if i["lado"] == "C" else -1) for i in items
                if i["clase"] == "doc" and _grupo(i["clave"][0]) == "cliente")
    pagado = sum(ars(i) for i in items if i["clase"] == "dinero")

    controles = [c for c in resultado["marcas"] if c in CONTROLES_QUE_FALLAN]
    if min(pend_d, pend_c) > max(1.0, objetivo * TOLERANCIA):
        controles.append("aplicado-distinto")
    if entrada_contacto.get("excepcionesDatos"):
        controles.append("datos")
    marcas = [m for m in resultado["marcas"] if m not in CONTROLES_QUE_FALLAN]
    if sobre_antes:
        marcas.append("documento-sobreaplicado-antes")

    # Un pago de más sin documento, o una excepción de datos, ya existían antes.
    cerraba = (not sobre_antes and _cerca(aplicado_antes, objetivo)
               and "pago-de-mas" not in controles and "datos" not in controles)
    cierra = not controles
    tendencia = "igual" if cerraba == cierra else ("mejora" if cierra else "empeora")
    return {
        "moneda": "USD" if any(i["moneda"] == "USD" for i in items if i["clase"] == "doc") else "ARS",
        "facturadoAntes": round(max(0.0, f_prov) + max(0.0, f_cli), 2),
        "pagadoAntes": round(pagado, 2),
        "aplicadoAntes": aplicado_antes,
        "aplicadoDespues": aplicado_despues,
        "aplicadoEsperado": round(objetivo, 2),
        "anticipoAbierto": resultado["anticipoAbierto"],
        "saldo": round(sd - sc, 2),
        "volumen": round(sd + sc, 2),
        "cerrabaAntes": cerraba,
        "cierraDespues": cierra,
        "tendencia": tendencia,
        "controles": [{"codigo": c, "descripcion": DESCRIPCION.get(c, c)} for c in controles],
        "marcas": [{"codigo": m, "descripcion": DESCRIPCION.get(m, m)} for m in marcas],
        "documentosSobreaplicadosAntes": len(sobre_antes),
        "excepcionesDatos": entrada_contacto.get("excepcionesDatos", []),
    }
