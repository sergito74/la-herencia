"""036 — Fideicomiso La Esperanza (562), 19/10/2026: el ajuste 11 ($6.494,73) pasa a documento del arrendamiento.

Carta oferta 17/07/2024 (Dropbox/Contratos): Giamigli arrienda 111 ha al Fideicomiso por 666 qq de soja en 3 cuotas de
222 qq, cada una al equivalente en pesos a pizarra Rosario del mes de pago. La obligación es en quintales.
En agosto el Fideicomiso pagó $95.146 de más = 3,36 qq por adelantado a cuenta de la cuota 2; en noviembre esos 3,36 qq
cancelan parte de la cuota 2 (facturada a $30.511,67/qq) y valen $102.642,18. La diferencia, $6.494,73, es diferencia de
cotización del quintal de soja (como una diferencia de cambio): en quintales se cobraron los 666 qq del contrato.
Es un resultado real del arrendamiento 2024/25 → documento de alquiler negativo del mismo contrato y período (la tabla
Alquileres imputa por período, no tiene cultivo), en lugar de un AjusteCuentaCorriente. No cambia el saldo. Idempotente.

Uso (desde backend/): python -m scripts.fideicomiso_dif_cotizacion_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

C, AJUSTE, IMPORTE = 562, 11, 6494.73
DOC = "Diferencia de cotizacion qq soja cuota 2 (3,36 qq pagados en ago-2024, cancelados a pizarra nov-2024)"

if __name__ == "__main__":
    _assert_target_is_wc()
    if fetch_all("SELECT 1 AS x FROM dbo.Alquileres WHERE IdContacto = ? AND [Documento Original] = ?", (C, DOC)):
        raise SystemExit("Ya registrado.")
    print("Respaldo verificado:", backup_verificado("fideicomiso-dif-cotizacion-036"))
    execute_write_transaction([
        ("INSERT INTO dbo.Alquileres (Fecha, [Inicio del periodo], [Fin del periodo], IdContacto, [Tipo de pago], [Importe total del contrato], "
         "[Retencion Ganancias], [Cantidad de cuotas], [Superficie total], [Documento Original]) "
         "VALUES ('2024-12-05', '2024-07-17', '2025-06-30', ?, 'Contado', ?, 0, 1, 0, ?)", (C, -IMPORTE, DOC)),
        ("DELETE FROM dbo.RevisionPagosSinFactura WHERE IdContacto = ? AND Medio = 'ajuste-interno' AND IdMovimiento = ?", (C, AJUSTE)),
        ("DELETE FROM dbo.AjustesCuentaCorriente WHERE IdAjuste = ? AND IdContacto = ?", (AJUSTE, C)),
    ])
    print("Saldo:", round(sum(r["Deuda"] - r["Credito"] for r in fetch_all("SELECT Deuda, Credito FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,))), 2))
