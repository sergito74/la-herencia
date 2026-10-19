"""036 — FEDEA (217), 18/10/2026: imputaciones 2021-2022 (criterio C5 de la ficha).

La cuenta ya estaba en $0 y US$0 (auditoría 035). Quedaban dos errores de imputación:
- Aplicación 9129 ('automatica-exacta'): el vínculo de tarjeta 776 es de otra factura (2143513784) y estaba aplicado además
  a la ND 1003-6360 → sobrepago. Se anula.
- El FIFO 032 repartió mal los pesos de 2021-22 (pagos BNA de 2018 aplicados a la FC 10872 / NC 5019 y la ND 6375 sin
  imputar). Se rehace: la NC 5019 "Reconocimiento comercial" (US$1.384,19 x 132,42 = $183.294,65) y la transferencia
  Galicia 674 cancelan la FC 10872 y la ND 6244; la NC 5018 y el resto de la NC 5019 cancelan las ND de dif. de cambio
  6360 y 6375. No cambia ningún saldo. Idempotente.

Uso (desde backend/): python -m scripts.fedea_imputaciones_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.vinculos.backup import backup_verificado

C, U = 217, "Sergio (barrida 036)"
NC5019, NC5018, FC10872, ND6244, ND6360, ND6375 = 2143513722, 2143513723, 2143513725, 2143513712, 2143513724, 2143522624
PLAN = [("galicia", 674, FC10872, 22496.73), ("comp-compra", NC5019, FC10872, 114269.33), ("comp-compra", NC5019, ND6244, 28518.24),
        ("comp-compra", NC5018, ND6360, 2426.95), ("comp-compra", NC5019, ND6360, 3771.70), ("comp-compra", NC5019, ND6375, 36735.38)]
DOCS = (FC10872, ND6244, ND6360, ND6375)

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("fedea-imputaciones-036"))
    marca = ",".join("?" * len(DOCS))
    st = [(f"UPDATE dbo.AplicacionesPago SET Anulada = 1, MotivoAnulacion = 'Reemplazada: imputaciones 2021-22 de FEDEA (barrida 036)', "
           f"UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() WHERE Anulada = 0 AND TipoDocumento = 'CompraDeuda' AND IdDocumentoAplicado IN ({marca})",
           (U, *DOCS))]
    st += [("INSERT INTO dbo.AplicacionesPago (OrigenMovimiento, IdMovimientoOrigen, TipoDocumento, IdDocumentoAplicado, ImporteAplicado, Fecha, "
            "Usuario, Anulada, Origen, NotaConciliacion) VALUES (?, ?, 'CompraDeuda', ?, ?, SYSDATETIME(), ?, 0, 'manual', "
            "'Barrida 036: FEDEA 2021-22, NC 5019 y Galicia 674 a las FC en US$, NC 5018 y resto NC 5019 a las ND de dif. cambio')",
            (m, i, d, x, U)) for m, i, d, x in PLAN]
    execute_write_transaction(st)
    print("Imputaciones 2021-22 rehechas:", len(PLAN))
