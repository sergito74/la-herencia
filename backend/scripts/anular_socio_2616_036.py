"""036 — Cuenta de socios, 18/10/2026: anula el movimiento 2616 de Lucy ($24.594, 03/01/2024, "Sancor Seguros – Seg. Accidentes Irma").

Venía de la planilla "Cajas Giamigli.xlsx", hoja "Cuenta Lucy", fila 346. No existe: en el extracto de la caja de ahorro en pesos
de Galicia de Lucy (DDJJ Físicas 2024, resumen al 19/04/2024) el único pago a Sancor de esas semanas es el del 08/01/2024 por
$6.017 (movimiento 2620, cuota con vencimiento 02/01/2024); $24.594 no aparece en ningún extracto de Lucy de 2024. Es el importe
del pago de Sergio del 07/02/2025 (hoja "Cuenta Sergio", fila 302): fila copiada con la fecha equivocada. Decisión de Sergio.

Uso (desde backend/): python -m scripts.anular_socio_2616_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all
from src.features.vinculos.backup import backup_verificado

if __name__ == "__main__":
    _assert_target_is_wc()
    if fetch_all("SELECT 1 AS x FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = 2616 AND Anulada = 0 AND Importe = 24594"):
        print("Respaldo verificado:", backup_verificado("anular-socio-2616-036"))
        execute_write_transaction([(
            "UPDATE dbo.MovimientosCuentaSocio SET Anulada = 1, MotivoAnulacion = ?, UsuarioAnulacion = ?, FechaAnulacion = SYSDATETIME() "
            "WHERE IdMovimiento = 2616",
            ("No existe en el extracto de Galicia de Lucy (el único pago a Sancor de ene-2024 es el del 08/01 por $6.017, mov. 2620); "
             "es una fila copiada del pago de Sergio del 07/02/2025 ($24.594). Planilla 'Cuenta Lucy' fila 346.", "Sergio (barrida 036)"))])
    print(fetch_all("SELECT IdMovimiento, Importe, Anulada, MotivoAnulacion FROM dbo.MovimientosCuentaSocio WHERE IdMovimiento = 2616"))
