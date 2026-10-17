"""036 — Cierre de Lemos, Rubén Luján (3655), 17/10/2026 (decisiones de Sergio).

- Factura 00003-1040 (25/08/2026, $62.678): la cancela la transferencia Galicia del 21/08 de $64.000; la
  factura se hizo por un monto menor → renglón "Ajuste" de $1.322 (sin IVA) para que cierre con la transferencia.
- Factura 00003-1042 (03/09/2026, $21.780): pagada en efectivo desde la caja chica del campo (la maneja el
  encargado): movimiento en la caja CampoChica + Pago efectivo con caja CampoChica (mismo patrón que Extragas).
- Marca del pago con su factura, inventario y cierre de la ficha.

Uso (desde backend/): python -m scripts.cierre_lemos_20261017
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc
from src.features.revision_cuentas import evidencia, fichas
from src.features.revision_cuentas.router import _corte_o_404, _detectar_cuenta
from src.features.vinculos.backup import backup_verificado

U = "Sergio (036, Lemos 2026-10-17)"
C, F1040, F1042 = 3655, 2143522640, 2143522641

if __name__ == "__main__":
    print("Respaldo verificado:", backup_verificado("cierre-lemos-036"))
    _assert_target_is_wc()
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO dbo.Det_Compras (IdCompra, Cantidad, Unidad, [Producto/Servicio], IdCentroCostos, IdDestino, IdRubro, "
                    "Campaña, [Precio Unitario], IVA, [Ajuste financiero]) "
                    "SELECT TOP 1 IdCompra, 1, 'UNIDAD', 'Ajuste (factura por monto menor a lo transferido)', IdCentroCostos, IdDestino, "
                    "IdRubro, Campaña, 1322.00, 0, 0 FROM dbo.Det_Compras WHERE IdCompra = ?", F1040)
        cur.execute("INSERT INTO dbo.MovimientosCajaEfectivo (Caja, Fecha, Concepto, Detalle, Importe, FormaPago, IdContactoRelacionado, Usuario) "
                    "VALUES ('CampoChica', '2026-09-03', 'Factura 00003-00001042', 'Maderas varias (Lemos)', -21780.00, 'Efectivo', ?, ?)", C, U)
        cur.execute("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, [Importe imputado]) "
                    "VALUES (?, 1, 3, '2026-09-03', 'White', 'CampoChica', 21780.00)", C)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    corte = _corte_o_404()
    _, resultado, _ = _detectar_cuenta(C, corte)
    for p in resultado["pagos"]:
        if not p.get("marca"):
            factura = F1040 if p["medio"] == "galicia" else F1042
            evidencia.guardar_marca(C, p["medio"], p["idMovimiento"], "factura-cargada", factura, None,
                                    "Pago de la factura (decisión de Sergio 17/10/2026)", U)
            print("marcado", p["medio"], p["idMovimiento"], p["importe"])
    fichas.confirmar_inventario(C, [{"tipo": "dropbox", "disponible": True, "detalle": "Facturas 1040 y 1042 (PDF)"},
                                    {"tipo": "extracto", "disponible": True, "detalle": "Galicia 21/08/2026 y caja chica del campo"}], U)
    f = fichas.cambiar_estado(C, {"estado": "cerrada", "nota": "1040 cancelada por la transferencia de $64.000 (ajuste $1.322); "
                                  "1042 pagada en efectivo con la caja chica del campo. Decisión de Sergio 17/10/2026."}, U)
    print(f["estado"], f.get("saldoAlCorte"))
