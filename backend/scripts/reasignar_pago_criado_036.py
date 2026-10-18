"""036 — Ricardo Criado (210), 18/10/2026.

El pago Galicia 3443 del 10/09/2026 ($1.150.754, "Trf Inmed Proveed", sin leyendas) estaba asignado a
Ricardo Criado, pero es el pago de la factura 00003-00000874 de Estudio Criado (115): misma fecha e importe exacto,
y es la cuota mensual que Estudio Criado cobra todos los meses. Se reasigna a Estudio Criado.

Uso (desde backend/): python -m scripts.reasignar_pago_criado_036
"""

from __future__ import annotations

import pyodbc

from src.db.connection import CONNECTION_STRING, _assert_target_is_wc, fetch_all
from src.features.vinculos.backup import backup_verificado

MOV, ANTES, NUEVO = 3443, 210, 115
MOTIVO = "Pago de la factura 00003-00000874 de Estudio Criado (10/09/2026, $1.150.754); estaba asignado a Ricardo Criado"

if __name__ == "__main__":
    _assert_target_is_wc()
    print("Respaldo verificado:", backup_verificado("reasignar-pago-criado-036"))
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.[Movimientos Galicia] SET IdContacto = ?, Contacto = 'Estudio Criado' "
                    "WHERE IdMovimiento = ? AND IdContacto = ? AND [Débitos] = 1150754", NUEVO, MOV, ANTES)
        if cur.rowcount == 1:
            cur.execute("INSERT INTO dbo.ReasignacionesContacto (Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Motivo, "
                        "Usuario, Fecha) VALUES ('Galicia', ?, ?, ?, ?, 'Sergio (barrida 036)', SYSDATETIME())",
                        MOV, ANTES, NUEVO, MOTIVO)
        else:
            print("Ya reasignado o no aplicable.")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    for c in (ANTES, NUEVO):
        print(c, fetch_all("SELECT SUM(ISNULL(Credito,0)-ISNULL(Deuda,0)) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto = ?", (c,)))
