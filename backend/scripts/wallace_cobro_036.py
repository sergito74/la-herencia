"""036, 19/10/2026: cobro Wallace identificado por banco, antes asignado a J y M.

Galicia 2656, 10/07/2025, crédito $1.833.341,86, CUIT 30692071898.
La cuenta suma $1.833.341,8819: diferencia de redondeo $0,0219.
"""
from src.db.connection import fetch_all, execute_write_transaction, _assert_target_is_wc
from src.features.vinculos.backup import backup_verificado


def main():
    _assert_target_is_wc()
    fila = fetch_all("SELECT IdContacto, [Créditos] AS importe, [Descripción] AS descripcion FROM dbo.[Movimientos Galicia] WHERE IdMovimiento = ?", (2656,))[0]
    if fila["IdContacto"] == 47:
        if round(float(fila["importe"]), 2) != 1833341.86 or "30692071898" not in fila["descripcion"]:
            raise RuntimeError("El banco no coincide con la evidencia revisada")
        if fetch_all("SELECT Estado FROM dbo.RevisionFichas WHERE IdContacto IN (?,?) AND Estado IN ('cerrada','cerrada-con-excepcion')", (47,600)):
            raise RuntimeError("Una de las cuentas está cerrada: revisar antes de reasignar")
        print("Respaldo verificado:", backup_verificado("wallace-cobro-036"))
        execute_write_transaction([(
            "INSERT INTO dbo.ReasignacionesContacto (Origen,IdOrigen,IdContactoAnterior,IdContactoNuevo,Motivo,Usuario,Fecha) "
            "SELECT 'Galicia',2656,47,600,?, ?,SYSDATETIME() FROM dbo.[Movimientos Galicia] WITH (UPDLOCK,HOLDLOCK) "
            "WHERE IdMovimiento = 2656 AND IdContacto = 47 AND [Créditos] = 1833341.86",
            ("Cobro Wallace: el extracto identifica WALLACE HERMANOS SA CUIT 30692071898; $1.833.341,86 coincide con liquidacion 24837 + NC bonificacion 1355, salvo $0,02 de redondeo. Antes asignado a J y M de la Serna.", "Sergio (continuidad 036, 19/10/2026)"),
        ), ("UPDATE dbo.[Movimientos Galicia] SET IdContacto = 600, Contacto = 'Wallace Hnos.' WHERE IdMovimiento = 2656 AND IdContacto = 47 AND [Créditos] = 1833341.86", ())])
    elif fila["IdContacto"] != 600:
        raise RuntimeError("Movimiento asignado a un tercero; no modificar")
    for contacto in (600,47):
        print(contacto, fetch_all("SELECT SUM(Credito)-SUM(Deuda) AS saldo FROM dbo.vw_MovimientosCuenta_Base WHERE IdContacto = ?", (contacto,)))


if __name__ == "__main__":
    main()
