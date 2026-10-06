"""Débito indebido del Banco Nación contra la Mastercard BNA dada de baja (034, T053).

El 05/06/2024 el banco debitó $15.180,50 contra la tarjeta Mastercard BNA, que ya
estaba dada de baja (último resumen cargado: 05/2023). Sergio reclamó y nunca tuvo una
respuesta positiva: decisión del 2026-10-06 de registrarlo como pérdida y gasto bancario.

Se hace con los dos mecanismos que ya usa el sistema:
  * reasignación del movimiento del contacto "Mastercard BNA" (372) al contacto
    "Banco Nacion" (369), como el resto de los gastos bancarios;
  * estado `SinDocumento`/`Otro` en Tesorería con la explicación, si Tesorería lo admite
    (con el movimiento ya asignado al banco lo da por resuelto; entonces la explicación
    queda en el motivo de la reasignación).

Uso (desde backend/):  python -m scripts.registrar_debito_indebido_mastercard_bna [--verificar]
"""

from __future__ import annotations

import sys

from src.db.connection import fetch_one
from src.features.conciliacion_tesoreria.repository import marcar_sin_documento
from src.features.reasignacion_contacto.repository import reasignar
from src.features.vinculos.backup import backup_verificado

ID_MOVIMIENTO = 18020
ID_MASTERCARD, ID_BANCO_NACION = 372, 369
USUARIO = "preparacion-034"
MOTIVO = ("Débito indebido del banco contra la Mastercard BNA ya dada de baja; reclamo sin respuesta favorable. "
          "Se registra como pérdida y gasto bancario (decisión de Sergio, 2026-10-06).")
DETALLE = ("Débito del 05/06/2024 por $15.180,50 contra la tarjeta Mastercard BNA que ya estaba dada de baja. "
           "Reclamado al banco sin respuesta positiva: pérdida y gasto bancario.")


def main(solo_verificar: bool) -> None:
    mov = fetch_one(
        "SELECT IdMovimientoBNA AS id, Importe AS importe, IdContacto AS contacto, Concepto AS concepto, "
        "CONVERT(varchar(10), [Fecha / Hora Mov#], 23) AS fecha FROM dbo.[Movimientos BNA] WHERE IdMovimientoBNA = ?",
        (ID_MOVIMIENTO,))
    assert mov and abs(float(mov["importe"]) + 15180.50) < 0.005 and mov["fecha"] == "2024-06-05", mov
    reasignado = fetch_one(
        "SELECT TOP 1 IdContactoNuevo AS c FROM dbo.ReasignacionesContacto WHERE Origen = 'Banco Nacion' AND IdOrigen = ? "
        "ORDER BY IdReasignacion DESC", (ID_MOVIMIENTO,))
    contacto_vigente = reasignado["c"] if reasignado else mov["contacto"]
    estado = fetch_one(
        "SELECT TOP 1 Estado AS e FROM dbo.ConciliacionesTesoreriaEstado WHERE Medio = 'bna' AND IdMovimiento = ? "
        "ORDER BY IdEstado DESC", (ID_MOVIMIENTO,))
    print(f"Movimiento {mov['id']}: {mov['concepto']} {mov['importe']} del {mov['fecha']}; contacto vigente {contacto_vigente}; "
          f"estado en Tesorería: {estado['e'] if estado else 'sin estado'}")
    if solo_verificar:
        print("Solo verificación: no se escribió nada.")
        return
    print(f"Respaldo verificado: {backup_verificado('debito-indebido-mastercard')}")
    if contacto_vigente != ID_BANCO_NACION:
        reasignar("Banco Nacion", ID_MOVIMIENTO, ID_BANCO_NACION, USUARIO, MOTIVO)
        print("Reasignado a Banco Nacion (369).")
    if not estado or estado["e"] == "EstadoQuitado":
        try:
            marcar_sin_documento("bna", ID_MOVIMIENTO, "Otro", DETALLE, USUARIO)
            print("Marcado en Tesorería como SinDocumento/Otro con la explicación.")
        except ValueError as e:
            # Con el movimiento ya asignado al contacto del banco, Tesorería lo da por resuelto
            # y no admite un estado aparte: la explicación queda en el motivo de la reasignación.
            print(f"Tesorería no admite un estado aparte ({e}); la explicación queda en el motivo de la reasignación.")


if __name__ == "__main__":
    main("--verificar" in sys.argv)
