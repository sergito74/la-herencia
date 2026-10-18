"""036 — Ricardo Criado (210), 18/10/2026: honorarios del balance 23-24 pagados en efectivo por los socios.

Sergio: los honorarios ($811.080, factura "SIN DOCUMENTO" del 12/09/2024) se pagaron en efectivo sin factura con plata
que aportaron los socios, y el 16/09/2024 se les devolvió con transferencias Galicia (sueldo o retiro) de $270.360 c/u.
La cuenta de socios ya lo tiene (migración de cajas: aporte efectivo Condominio LSC "Pago Balance Giamigli" $811.100 y
los retiros de Lucy, Ceci y Sergio del 14/09/2024). Acá se arregla la cuenta del proveedor:
- Pago efectivo de $811.080 a Ricardo Criado desde la caja "Condominio" (cuenta Blue, sin factura).
- Las 3 transferencias salen de Ricardo Criado y van al contacto del socio que las recibió:
  2100 → Virginia Giamberardini (Ceci, por nombre y CUIT); 2099 "HONORARIOS PROFESIONALES" → Albina Iglina (390, el
  destino habitual de esa leyenda) y 2098 "GASTOS REPRESENTACION" → Sergio Giamberardini (375): las dos de haberes no
  traen el nombre del beneficiario, se asignan por el patrón del resto de 2024.
El saldo de Ricardo Criado no cambia. Idempotente.

Uso (desde backend/): python -m scripts.balance_23_24_criado_socios_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

C = 210
TRANSFERENCIAS = [(2100, 564, "Virginia Giamberardini"), (2099, 390, "Albina Iglina"), (2098, 375, "Sergio Giamberardini")]
MOTIVO = ("Devolución a socios del efectivo aportado para pagar los honorarios del balance 23-24 de Ricardo Criado "
          "(confirmado por Sergio 2026-10-18); el pago a Criado fue en efectivo desde la caja Condominio")

if __name__ == "__main__":
    _assert_target_is_wc()
    if fetch_all("SELECT 1 AS x FROM dbo.[Pagos efectivo] WHERE IdContacto = ? AND Fecha = '2024-09-12' AND Caja = 'Condominio'", (C,)):
        print("Ya aplicado.")
        raise SystemExit
    print("Respaldo verificado:", backup_verificado("balance-23-24-criado-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO dbo.[Pagos efectivo] (IdContacto, IdTipoMovimiento, IdFormaPago, Fecha, Cuenta, Caja, "
                    "[Importe imputado]) VALUES (?, 1, 3, '2024-09-12', 'Blue', 'Condominio', 811080)", C)
        for mov, nuevo, nombre in TRANSFERENCIAS:
            cur.execute("UPDATE dbo.[Movimientos Galicia] SET IdContacto = ?, Contacto = ? "
                        "WHERE IdMovimiento = ? AND IdContacto = ? AND [Débitos] = 270360", nuevo, nombre, mov, C)
            assert cur.rowcount == 1, mov
            cur.execute("INSERT INTO dbo.ReasignacionesContacto (Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, "
                        "Usuario, Fecha) VALUES ('Galicia', ?, ?, ?, ?, 'Sergio (barrida 036)', SYSDATETIME())",
                        mov, C, nuevo, MOTIVO)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (C,)))
