"""036 — Syngenta (398), 18/10/2026: valuación en dólares para que la cuenta cierre en $0 y US$0.

La única factura en dólares (FC 0272-67088, US$785,90 a TC 69,26) se pagó exacta con la tarjeta ($54.431,43, vínculo 5612).
El resto son documentos y pagos en pesos (regalías ND 2567 y S/D, ND 25845 de dif. de cambio y su pago/NC) que cierran en pesos
y no mueven dólares; sin esto el motor daba US$5,46 por valuar las regalías de 2017 y su pago de 2021 a cotizaciones distintas.
Syngenta confirmó la cuenta en $0 por mail (Anabella Aquaro, 15/09/2020). Idempotente.

Uso (desde backend/): python -m scripts.syngenta_valuacion_036
"""

from __future__ import annotations

from src.db.connection import _assert_target_is_wc, execute_write_transaction
from src.features.auditoria_cuentas import bimonetaria
from src.features.vinculos.backup import backup_verificado

C, U = 398, "Sergio (barrida 036)"
VALUACION = {("Tarjetas", 5612): 785.90, ("Tarjetas", 5671): 0.0, ("Banco Nacion", 18563): 0.0, ("Banco Nacion", 18548): 0.0,
             ("Compras", 2143522612): 0.0, ("Compras", 2143512706): 0.0, ("Compras", 2143513033): 0.0, ("Compras", 2143512865): 0.0}

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("syngenta-036"))
    st = [("DELETE FROM dbo.ValuacionProveedor WHERE IdContacto = ?", (C,))]
    st += [("INSERT INTO dbo.ValuacionProveedor (Origen, IdOrigen, IdContacto, Dolares, Fuente, Nota, Usuario, Fecha) VALUES "
            "(?, ?, ?, ?, 'FC 67088 pagada exacta con tarjeta, lo demás es en pesos (Syngenta confirmó $0, mail 15/09/2020)', NULL, ?, SYSDATETIME())",
            (o, i, C, d, U)) for (o, i), d in VALUACION.items()]
    execute_write_transaction(st)
    bimonetaria.invalidar()
    r = bimonetaria.cargar_cuenta(C, refrescar=True)
    print("Saldo: pesos", r["saldoPesos"], " US$", r["saldoDolares"], r["gobierna"])
