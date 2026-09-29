"""Test de integración contra `WC` real (022-reasignacion-contacto,
Foundational, T008): confirma que `vw_MovimientosCuenta_Base` aplica el
override de `dbo.ReasignacionesContacto` (research.md §3). Inserta una
fila de prueba sobre un movimiento real conocido y la borra al final —
no debe quedar dato de prueba permanente."""

from __future__ import annotations

from src.db.connection import execute_insert_returning_id, execute_write, fetch_one


def test_override_de_reasignacion_se_refleja_en_la_vista():
    # Movimiento real conocido (ver historial de la conversación):
    # Movimientos Galicia IdMovimiento=2712, hoy con IdContacto=1652
    # (Encode S.A., ya corregido manualmente antes de esta feature).
    origen, id_origen = "Galicia", 2712

    antes = fetch_one(
        "SELECT IdContacto FROM dbo.vw_MovimientosCuenta_Base WHERE Origen = ? AND IdOrigen = ?",
        (origen, id_origen),
    )
    assert antes is not None
    contacto_original = antes["IdContacto"]

    # Un contacto real distinto, cualquiera, para el override de prueba.
    otro_contacto = fetch_one(
        "SELECT TOP 1 IdContacto FROM dbo.Contactos WHERE IdContacto <> ?",
        (contacto_original,),
    )["IdContacto"]

    id_reasignacion = execute_insert_returning_id(
        "INSERT INTO dbo.ReasignacionesContacto "
        "(Origen, IdOrigen, IdContactoAnterior, IdContactoNuevo, Usuario) "
        "OUTPUT INSERTED.IdReasignacion VALUES (?, ?, ?, ?, ?)",
        (origen, id_origen, contacto_original, otro_contacto, "test-integracion-022"),
    )
    try:
        despues = fetch_one(
            "SELECT IdContacto FROM dbo.vw_MovimientosCuenta_Base WHERE Origen = ? AND IdOrigen = ?",
            (origen, id_origen),
        )
        assert despues["IdContacto"] == otro_contacto
    finally:
        execute_write("DELETE FROM dbo.ReasignacionesContacto WHERE IdReasignacion = ?", (id_reasignacion,))

    restaurado = fetch_one(
        "SELECT IdContacto FROM dbo.vw_MovimientosCuenta_Base WHERE Origen = ? AND IdOrigen = ?",
        (origen, id_origen),
    )
    assert restaurado["IdContacto"] == contacto_original
