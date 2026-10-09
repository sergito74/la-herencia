"""Los 7 criterios de cierre de una cuenta y su etapa — 036 (data-model.md, research D3). Funciones puras: no leen la base.

Cada criterio devuelve `cumple` (True, False, o None si no aplica), el número medido, el texto en español simple y la etapa a la
que pertenece. La etapa de una cuenta es la primera cuyo criterio no se cumple (se calcula, no se guarda).
"""

from __future__ import annotations

SALDO_CERO = 2.0  # hasta este saldo (en la moneda de la cuenta) se da por cero: redondeo
UMBRAL_PESOS = 300.0  # una diferencia menor se da por cerrada (en dólares rige la tolerancia relativa de la cuenta)

ETAPA_DE_CRITERIO = {"C1": "E1", "C2": "E2", "C3": "E4", "C4": "E3", "C5": "E5", "C6": "E4", "C7": "E6"}
# Criterios que tienen que cumplirse antes de aplicar el FIFO de una cuenta (E1 a E4, FR-007)
CRITERIOS_PREVIOS_AL_FIFO = ("C1", "C2", "C4", "C3", "C6")
# Origen de las causas de hallazgo de la 035 que usa cada criterio
CAUSAS_ACCESS_EXPLICA = ("coincide", "coincide-causa-conocida", "diferencia-menor-umbral")
# Hallazgos que afectan el saldo: invalidan la evidencia del Access. Los de imputación (plazo, sobrepago, notas sin imputar, doble conteo)
# no cambian el saldo y se arreglan en E3 y E5; si bloquearan la evidencia del saldo, el FIFO nunca podría aplicarse (sería un círculo).
HALLAZGOS_DE_SALDO = frozenset({"contacto-duplicado", "movimiento-sin-contacto", "impuesto-sin-boleta"})


def _dinero(valor: float) -> str:
    """Importe con miles '.' y decimales ',' (regla del proyecto: nunca `toLocaleString`)."""
    texto = f"{abs(valor):,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return ("-" if valor < 0 else "") + "$ " + texto


def _criterio(codigo: str, cumple: bool | None, medido: str, texto: str, evidencia: str | None = None) -> dict:
    return {"codigo": codigo, "etapa": ETAPA_DE_CRITERIO[codigo], "cumple": cumple, "medido": medido, "texto": texto, "evidencia": evidencia}


def _c1(ctx: dict) -> dict:
    pendientes, antiguos = int(ctx.get("pagos_pendientes", 0)), int(ctx.get("pagos_antiguos", 0))
    texto = "Todos los pagos tienen una factura que los respalde"
    nota = f"; {antiguos} anteriores a 2021 quedan anotados como excepción" if antiguos else ""
    if not ctx.get("detector_cierra", True):
        return _criterio("C1", False, "El detector no cierra con el saldo de la cuenta" + nota, "Hay que explicar la diferencia del detector antes de dar por completos los documentos")
    if pendientes:
        return _criterio("C1", False, f"{pendientes} pagos sin factura por {_dinero(float(ctx.get('pagos_importe_pendiente', 0)))}" + nota,
                         "Hay pagos sin factura que los respalde")
    return _criterio("C1", True, "0 pagos sin factura desde 2021" + nota, texto)


def _c2(ctx: dict) -> dict:
    hallazgos = set(ctx.get("hallazgos", ()))
    problemas = [n for c, n in (("contacto-duplicado", "contacto duplicado por CUIT"), ("movimiento-sin-contacto", "movimientos sin contacto")) if c in hallazgos]
    if problemas:
        return _criterio("C2", False, ", ".join(problemas), "Hay movimientos o contactos por corregir")
    return _criterio("C2", True, "Sin contactos duplicados ni movimientos sin contacto", "Los movimientos y contactos están bien asignados")


def _c3(ctx: dict) -> dict:
    ext, ref = ctx.get("saldo_externo"), ctx.get("referencia_access") or {}
    discrepa = ""
    if ext and ref.get("tiene") and not ref.get("explica"):
        discrepa = ". El Access discrepa: gana el proveedor con documento"
    if ext:
        diferencia = float(ext["diferencia"])
        if ext["clasificacion"] in ("cierra", "menor-al-umbral"):
            return _criterio("C3", True, f"Diferencia contra el saldo del proveedor: {_dinero(diferencia)} ({ext['clasificacion']})" + discrepa,
                             "El saldo está respaldado por evidencia externa", ext["fuente"])
        return _criterio("C3", False, f"Diferencia contra el saldo externo: {_dinero(diferencia)}" + discrepa, "El saldo no coincide con la evidencia externa")
    if ctx.get("sin_estado"):
        return _criterio("C3", True, "Se decidió no pedir estado de cuenta", "Cierra con la evidencia disponible, anotado como excepción", "sin-estado")
    sin_problemas = not (set(ctx.get("hallazgos", ())) & HALLAZGOS_DE_SALDO) and int(ctx.get("pagos_pendientes", 0)) == 0
    saldo = abs(float(ctx.get("saldo") or 0))
    if ref.get("tiene") and ref.get("explica") and sin_problemas and saldo > SALDO_CERO:
        # Regla de Sergio (09/10/2026): coincidir con el Access no alcanza si hay saldo; hace falta evidencia externa o explicar por qué queda (no venció, falta el resumen del proveedor)
        return _criterio("C3", False, f"Coincide con el Access, pero el saldo no es cero ({_dinero(saldo)})",
                         "Con saldo, hace falta saldo externo o explicar por qué queda pendiente (no venció, falta el resumen)")
    if ref.get("tiene") and ref.get("explica") and sin_problemas:
        return _criterio("C3", True, "El saldo coincide con la referencia del Access al corte, sin hallazgos de saldo ni pagos sin factura",
                         "Respaldado por la referencia del Access (cierre en bloque)", "access")
    if ref.get("tiene") and ref.get("explica"):
        return _criterio("C3", False, "Coincide con el Access pero la cuenta tiene hallazgos de saldo o pagos sin factura", "Falta evidencia externa del saldo")
    return _criterio("C3", False, "Sin saldo externo y sin coincidencia con el Access", "Falta evidencia del saldo")


def _c4(ctx: dict) -> dict:
    duplicadas = int(ctx.get("tarjetas_duplicadas", 0))
    if "doble-descuento-tarjeta" in set(ctx.get("hallazgos", ())):
        return _criterio("C4", False, "Hay pagos del banco imputados a facturas que la tarjeta ya cubrió", "La tarjeta tiene doble conteo con el banco")
    if duplicadas:
        return _criterio("C4", False, f"Hay {duplicadas} imputaciones de tarjeta que sobran: la factura ya estaba cubierta por los otros pagos",
                         "La tarjeta tiene imputaciones duplicadas que el FIFO no reemplaza")
    return _criterio("C4", True, "0 casos de doble conteo con tarjeta", "La tarjeta no se cuenta dos veces")


def _c5(ctx: dict) -> dict:
    hallazgos = set(ctx.get("hallazgos", ()))
    faltan = [n for c, n in (("aplicacion-fuera-de-plazo", "pagos aplicados a facturas muy viejas"), ("sobrepago", "facturas con más pagos que su importe"),
                             ("nota-sin-imputar", "notas de débito sin imputar")) if c in hallazgos]
    sanas = (ctx.get("imputaciones") or {}).get("sanas")
    if sanas is False:
        faltan.append("imputaciones incompletas o sobrantes")
    if faltan:
        return _criterio("C5", False, ", ".join(faltan), "Hay imputaciones por recalcular")
    if sanas is None:
        return _criterio("C5", None, "No aplica a cuentas de clientes ni en dólares", "Las imputaciones se revisan en la cola que corresponde")
    return _criterio("C5", True, "Imputaciones completas y sin sobrantes", "Las imputaciones están sanas")


def _c6(ctx: dict) -> dict:
    hallazgos = set(ctx.get("hallazgos", ()))
    sin_cert = int(ctx.get("retenciones_sin_certificado", 0))
    problemas = [n for c, n in (("impuesto-sin-boleta", "impuestos sin boleta"),) if c in hallazgos]
    if sin_cert:
        problemas.append(f"{sin_cert} retenciones sin certificado")
    if problemas:
        return _criterio("C6", False, ", ".join(problemas), "Hay pendientes por tipificar")
    return _criterio("C6", True, "Sin impuestos sin boleta ni retenciones sin certificado", "Los pendientes están tipificados")


def _c7(ctx: dict) -> dict:
    if ctx.get("reabierta"):
        return _criterio("C7", False, "El saldo al corte cambió desde el cierre", "La cuenta se reabrió: hay que revisarla de nuevo")
    if not ctx.get("tiene_inventario"):
        return _criterio("C7", False, "No se confirmó el inventario de fuentes", "Falta registrar qué evidencia hay para esta cuenta")
    return _criterio("C7", True, "Inventario de fuentes confirmado y saldo estable al corte", "La cuenta tiene trazabilidad")


def evaluar(ctx: dict) -> list[dict]:
    """Los 7 criterios de la cuenta, en orden C1 a C7."""
    return [_c1(ctx), _c2(ctx), _c3(ctx), _c4(ctx), _c5(ctx), _c6(ctx), _c7(ctx)]


def etapa_de(criterios: list[dict], tiene_inventario: bool) -> str:
    """E0 si no hay inventario de fuentes; luego la primera etapa (E1 a E5) con un criterio sin cumplir; E6 si todo cumple."""
    if not tiene_inventario:
        return "E0"
    por_codigo = {c["codigo"]: c for c in criterios}
    for etapa, codigos in (("E1", ("C1",)), ("E2", ("C2",)), ("E3", ("C4",)), ("E4", ("C3", "C6")), ("E5", ("C5",))):
        if any(por_codigo[c]["cumple"] is False for c in codigos):
            return etapa
    return "E6"


def faltantes_para_cerrar(criterios: list[dict]) -> list[dict]:
    """Criterios que impiden cerrar la cuenta (los que no se cumplen; los que no aplican no cuentan)."""
    return [c for c in criterios if c["cumple"] is False]


def previos_al_fifo(criterios: list[dict]) -> tuple[bool, str | None, list[dict]]:
    """¿Completó E1 a E4? Devuelve (puede, etapa pendiente, criterios que faltan). No exige E0 ni E5."""
    por_codigo = {c["codigo"]: c for c in criterios}
    faltan = [por_codigo[c] for c in CRITERIOS_PREVIOS_AL_FIFO if por_codigo[c]["cumple"] is False]
    if not faltan:
        return True, None, []
    orden = {"E1": 1, "E2": 2, "E3": 3, "E4": 4}
    return False, min((c["etapa"] for c in faltan), key=lambda e: orden[e]), faltan


def imputaciones_sanas(sentido: str, gobierna: str | None, facturado: float, aplicado: float, tarjeta: float, saldo: float, facturas: int) -> bool | None:
    """¿Hay facturas sin imputar (con pagos o con tarjeta) que el saldo no justifica?

    Compara lo facturado y no imputado con lo que el saldo dice que se debe. Solo mide las facturas **sin imputar de más**:
    el exceso de imputación es el hallazgo `sobrepago`, que ya tiene su propio criterio. `None` si no aplica (clientes, cuentas
    mixtas o en dólares). Tolerancia de $1 más un centavo por factura (redondeos).
    """
    if sentido != "proveedor" or gobierna in ("Dolares", "Mixta"):
        return None
    deuda_abierta = max(-saldo, 0.0)
    sin_imputar = facturado - aplicado - tarjeta
    return (sin_imputar - deuda_abierta) <= 1.0 + 0.01 * facturas
