"""Colas de trabajo y orden de dificultad — 036 (research D5 y D6; decisiones de Sergio del 09/10/2026). Funciones puras.

Cada cuenta va a la primera cola que le corresponde según este orden de precedencia (el de las etapas: primero lo que cambia
el saldo y al final las imputaciones): H, D, E, C, G, F, I, B, A. Los demás problemas de la cuenta se devuelven como
`otrosProblemas`.
"""

from __future__ import annotations

PRECEDENCIA = ("H", "D", "E", "C", "G", "F", "I", "B", "A")
COLAS = {
    "A": "Ya sanas",
    "B": "Solo imputación",
    "C": "Doble conteo con tarjeta",
    "D": "Pago sin factura",
    "E": "Contacto duplicado o movimiento sin contacto",
    "F": "Dólares y mixtas",
    "G": "Retenciones e impuestos",
    "H": "Socios, entidades y compras particulares",
    "I": "Excepciones",
}
# Etapa en la que se resuelve cada cola (para el tablero)
ETAPA_DE_COLA = {"H": "E2", "D": "E1", "E": "E2", "C": "E3", "G": "E4", "F": "E4", "I": "E4", "B": "E5", "A": "E6"}


def problemas_de_cuenta(ctx: dict) -> dict[str, str]:
    """Colas en las que cae la cuenta, con el motivo (en el orden de precedencia). `A` no es un problema."""
    hallazgos = set(ctx.get("hallazgos", ()))
    p: dict[str, str] = {}
    if ctx.get("es_h"):
        p["H"] = "Es un socio, una entidad o tiene compras particulares"
    if int(ctx.get("pagos_pendientes", 0)) > 0 or not ctx.get("detector_cierra", True):
        p["D"] = "Tiene pagos sin factura que los respalde"
    if hallazgos & {"contacto-duplicado", "movimiento-sin-contacto"}:
        p["E"] = "Hay un contacto duplicado o movimientos sin contacto"
    if "doble-descuento-tarjeta" in hallazgos or int(ctx.get("tarjetas_duplicadas", 0)) > 0:
        p["C"] = "Hay doble conteo entre la tarjeta y el banco, o imputaciones de tarjeta duplicadas"
    if int(ctx.get("retenciones_sin_certificado", 0)) > 0 or "impuesto-sin-boleta" in hallazgos:
        p["G"] = "Hay retenciones sin certificado o impuestos sin boleta"
    gobierna, tolerancia = ctx.get("gobierna"), float(ctx.get("tolerancia") or 1.0)
    if gobierna == "Mixta" or (gobierna == "Dolares" and abs(float(ctx.get("saldo_revision", 0))) >= tolerancia):
        p["F"] = "La cuenta es en dólares o mixta y no cierra"
    # La diferencia contra el Access deja de ser una excepción cuando la evidencia externa (el proveedor con documento) respalda el saldo
    if (ctx.get("causa") == "otros" and not ctx.get("evidencia_externa")) or ctx.get("cuenta_a_revisar"):
        p["I"] = "Queda una diferencia sin explicar o la cuenta está marcada para revisar"
    if hallazgos & {"aplicacion-fuera-de-plazo", "sobrepago", "nota-sin-imputar"} or ctx.get("imputaciones_sanas") is False:
        p["B"] = "El saldo no cambia pero hay imputaciones por recalcular"
    return p


def asignar_cola(ctx: dict) -> tuple[str, list[str]]:
    """La cola de la cuenta y los demás problemas (lista de códigos de cola, en orden de precedencia)."""
    problemas = problemas_de_cuenta(ctx)
    orden = [c for c in PRECEDENCIA if c in problemas]
    if not orden:
        return "A", []
    return orden[0], orden[1:]


def orden_de_dificultad(cuentas: list[dict]) -> list[dict]:
    """De las más fáciles a las más complejas: menos movimientos primero y, a igual cantidad, menor importe (research D6)."""
    return sorted(cuentas, key=lambda c: (int(c["movimientos"]), abs(float(c["importe"])), (c.get("razonSocial") or "").casefold(), c["idContacto"]))
