"""Lista positiva documental del libro histórico: no inferir vínculos por nombre de socio."""

from decimal import Decimal

CONCEPTOS_RELACIONADOS = frozenset(
    {
        "aporte efectivo giamigli",
        "retiro giamigli",
        "retiro giamigli (prestamo)",
        "gastos bancarios giamigli",
        "cobro motosierra giamigli cta 1/6",
        "cobro motosierra giamigli cta 2/6",
        "pago balance giamigli",
    }
)


def evidencia_relacion(concepto, fecha=None, importe=None, fila=None):
    normalized = " ".join(str(concepto or "").lower().split())
    if normalized in CONCEPTOS_RELACIONADOS:
        return "Relación explícita con Giamigli en concepto de Caja Efectivo."
    if (
        normalized == "pago honorarios criado"
        and str(fecha)[:10] == "2016-04-20"
        and importe is not None
        and Decimal(str(importe)) == Decimal("-3818")
        and fila == 15
    ):
        return "Abr 16!A41:F41: Honorarios Criado (dev. Giamigli) 3 2016; -3818; Caja Efectivo fila 15."
    return None
