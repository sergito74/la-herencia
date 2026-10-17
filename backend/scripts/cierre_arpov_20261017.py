"""036 — Cierre de ArPov (454), 17/10/2026.

Factura 0004-00047416 (01/08/2021) en dólares (U$S 216,70 cargados a TC 96,69, con la diferencia de cambio
facturada en un renglón) pagada el 17/08/2021 por Galicia con exactamente $20.952,45 = U$S 216,70 x 96,69.
En pesos la cuenta ya está en 0; en dólares quedaba −U$S 0,94 porque el pago se pasaba al dólar BNA del día.
Regla `tc-pactado` (el pago se toma al TC de la factura), marca del pago con su factura, inventario y cierre.
"""

from __future__ import annotations

from src.features.auditoria_cuentas import bimonetaria, conocidos
from src.features.revision_cuentas import evidencia, fichas

U = "Sergio (036, ArPov 2026-10-17)"
C = 454

if __name__ == "__main__":
    conocidos.crear("tc-pactado", str(C), "ArPov facturó U$S 216,70 a TC 96,69 (renglón de diferencia de cambio incluido) "
                    "y se pagó exactamente $20.952,45 a ese TC: sin diferencia de cambio.", None, U)
    bimonetaria.invalidar()
    evidencia.guardar_marca(C, "galicia", 136, "factura-cargada", 2143513283, None,
                            "Transferencia 'ARPOV REGALIA EXTENDIDA - FACTURAS' de la factura 0004-00047416", U)
    fichas.confirmar_inventario(C, [{"tipo": "dropbox", "disponible": True, "detalle": "Factura 0004-00047416 (PDF)"},
                                    {"tipo": "extracto", "disponible": True, "detalle": "Galicia 17/08/2021"}], U)
    print(bimonetaria.cargar_cuenta(C, refrescar=True)["saldoGobierna"])
    print(fichas.cambiar_estado(C, {"estado": "cerrada", "nota": "Factura en dólares pagada al TC de la factura (tc-pactado). Decisión de Sergio 17/10/2026."}, U)["estado"])
