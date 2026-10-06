"""Aplicación informativa de créditos anteriores, sin crear pagos ni deuda.

Cada resumen conserva sus cargos y pagos reales. El excedente de un período
puede cubrir el faltante de uno posterior de la misma tarjeta, una sola vez.
"""
from decimal import Decimal, ROUND_HALF_UP

from src.db.connection import fetch_all


ESTADO_HISTORICO = "Cerrado"


def calcular_compensaciones(resumenes: list[dict]) -> dict[int, dict]:
    centavo = Decimal("0.01")
    disponibles: list[dict] = []
    resultado = {}
    for r in sorted(resumenes, key=lambda r: (r["fechaCierre"], r["idResumen"])):
        if r.get("estado") == ESTADO_HISTORICO:
            # Saldo inicial de una administración anterior: no se concilia ni genera créditos.
            resultado[r["idResumen"]] = {"creditoAplicado": 0.0, "saldoPendiente": 0.0,
                                         "creditoDisponible": 0.0, "compensaciones": []}
            continue
        diferencia = (Decimal(str(r["total"])) - Decimal(str(r["pagado"]))).quantize(
            centavo, rounding=ROUND_HALF_UP
        )
        pendiente = max(diferencia, Decimal(0))
        aplicaciones = []
        for credito in disponibles:
            aplicado = min(pendiente, credito["resto"])
            if aplicado > 0:
                aplicaciones.append({"idResumen": credito["id"], "codigo": credito["codigo"],
                                     "importe": float(aplicado)})
                credito["resto"] -= aplicado
                pendiente -= aplicado
        resultado[r["idResumen"]] = {
            "creditoAplicado": float(max(diferencia, Decimal(0)) - pendiente),
            "saldoPendiente": float(pendiente),
            "creditoDisponible": 0.0,
            "compensaciones": aplicaciones,
        }
        if diferencia < 0:
            disponibles.append({"id": r["idResumen"], "codigo": r["codigo"], "resto": -diferencia})
    for credito in disponibles:
        resultado[credito["id"]]["creditoDisponible"] = float(credito["resto"])
    return resultado


def get_compensaciones(id_tarjeta: int) -> dict[int, dict]:
    rows = fetch_all("""
        SELECT r.IdResumen AS idResumen, r.ResumenCodigo AS codigo,
               r.FechaCierre AS fechaCierre, r.EstadoResumen AS estado,
               COALESCE((SELECT SUM(l.Importe) FROM dbo.Tarjetas_Resumenes_Lineas l
                         WHERE l.IdResumen=r.IdResumen),0)
               +COALESCE(r.ImpuestoSellos,0)+COALESCE(r.GastosAdmin,0)
               +COALESCE(r.MantCuenta,0)+COALESCE(r.RenovAnual,0)
               +COALESCE(r.PromocionBNA,0)+COALESCE(r.CreditoContingente,0)
               +COALESCE(r.IntFinanc,0)+COALESCE(r.IntCompens,0)
               +COALESCE(r.IVA105,0)+COALESCE(r.PercepIVA105,0)
               +COALESCE(r.IVA21,0)+COALESCE(r.PercepIVA21,0)
               +COALESCE(r.PercepIIBB,0)+COALESCE(r.AjusteResAnterior,0) AS total,
               COALESCE((SELECT SUM(p.Importe) FROM dbo.Tarjetas_Resumenes_Pagos p
                         WHERE p.IdResumen=r.IdResumen),0) AS pagado
        FROM dbo.Tarjetas_Resumenes r WHERE r.IdTarjeta=?
    """, (id_tarjeta,))
    return calcular_compensaciones(rows)
