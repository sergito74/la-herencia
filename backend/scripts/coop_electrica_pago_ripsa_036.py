"""036, 30/10/2026: Cooperativa Eléctrica (23) - el "dinero a favor" de $125.553,71 que muestra su portal.
La FC 0003-00205294 (31/07/2025, $125.553,71) se pagó dos veces: con Visa Galicia el 25/08/2025 (línea 673) y por
Mercado Libre el 28/08/2025 con QR de RIPSA (mov. 49, fondeado ese día con $130.000 desde Galicia, mov. 48).
El pago de Mercado Libre había quedado sin contacto; se imputa a la Cooperativa como pago a cuenta (crédito a favor),
igual que lo informa el portal. Ficha 23 actualizada al nuevo saldo al 30/09/2026.
Uso (desde backend/): python -m scripts.coop_electrica_pago_ripsa_036 [--aplicar]
"""
import json
import sys

from scripts.inventario_cuentas_externas_036 import saldo_a
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_one
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

COOP, MOV, IMPORTE = 23, 49, 125553.71

if __name__ == "__main__":
    _assert_target_is_wc()
    m = fetch_one("SELECT Importe, IdContacto FROM dbo.[Movimientos Mercado Libre] WHERE IdMovimiento = ?", (MOV,))
    assert abs(m["Importe"] + IMPORTE) < 0.005 and m["IdContacto"] is None, m
    assert not fetch_one("SELECT 1 x FROM dbo.ConciliacionesTesoreria WHERE Medio = 'mercado-libre' AND IdMovimiento = ?", (MOV,))
    antes = saldo_a(COOP, "2026-09-30")
    print("antes", antes)
    if "--aplicar" not in sys.argv:
        raise SystemExit("Simulación: usar --aplicar para grabar.")
    respaldo = backup_verificado("coop-electrica-pago-ripsa-036")
    execute_write_transaction([
        ("UPDATE dbo.[Movimientos Mercado Libre] SET IdContacto = ? WHERE IdMovimiento = ?", (COOP, MOV)),
        ("INSERT INTO dbo.ConciliacionesTesoreria (Medio, IdMovimiento, IdContacto, Importe, Usuario, Fecha) "
         "VALUES ('mercado-libre', ?, ?, ?, 'Claude036 (pago duplicado RIPSA 28/08/2025)', SYSDATETIME())", (MOV, COOP, IMPORTE)),
        ("INSERT INTO dbo.AuditoriaCorrecciones (Regla,Estado,Parametros,Usuario,Fecha,UsuarioAplicacion,FechaAplicacion,Respaldo,Resumen) "
         "VALUES ('coop-electrica-pago-ripsa-036','aplicada',?,'Claude036',SYSDATETIME(),'Claude036',SYSDATETIME(),?,?)",
         (json.dumps({"movML": MOV, "contacto": COOP, "importe": IMPORTE, "factura": "0003-00205294"}), respaldo,
          "Pago QR RIPSA por Mercado Libre del 28/08/2025 imputado a la Cooperativa Eléctrica: pago duplicado de la FC "
          "0003-00205294 (también pagada con Visa), es el dinero a favor que informa el portal.")),
    ])
    bimonetaria.invalidar()
    despues = saldo_a(COOP, "2026-09-30")
    execute_write_transaction([("UPDATE dbo.RevisionFichas SET SaldoAlCierre = ? WHERE IdContacto = ?", (round(despues[0], 2), COOP))])
    print("despues", despues)
