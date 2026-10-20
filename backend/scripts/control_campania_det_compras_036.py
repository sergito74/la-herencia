"""Control 036: ningún renglón de compra puede tener campaña escrita sin su IdCampaña del catálogo.

1. Completa IdCampaña 'No Aplica' en los renglones con texto 'No Aplica' e id vacío (no cambia
   resultados por campaña: ambos quedan fuera de las campañas productivas).
2. Crea el trigger dbo.trg_Det_Compras_Campania (AFTER INSERT, UPDATE): rechaza la operación si un
   renglón insertado/modificado tiene texto de campaña y su IdCampaña falta o es de otra campaña.
   Frena también a scripts y cargas directas; la app ya valida antes (compras/repository.validar_compra).

Idempotente. Uso (desde backend/): python -m scripts.control_campania_det_compras_036
"""
from src.db.connection import _assert_target_is_wc, _reconciliation_connection, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

TRIGGER = """
CREATE OR ALTER TRIGGER dbo.trg_Det_Compras_Campania ON dbo.Det_Compras AFTER INSERT, UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1 FROM inserted i
        LEFT JOIN dbo.Campañas c ON c.IdCampaña = i.IdCampaña
        WHERE NULLIF(LTRIM(RTRIM(i.Campaña)), '') IS NOT NULL
          AND (c.IdCampaña IS NULL OR LTRIM(RTRIM(c.Campaña)) <> LTRIM(RTRIM(i.Campaña))))
        THROW 50036, 'Det_Compras: la campaña escrita no tiene el IdCampaña del catálogo que le corresponde (control 036). Elegí una campaña existente o creala primero.', 1;
END
"""
SIN_ID = ("SELECT IdDetalleCompra FROM dbo.Det_Compras WHERE NULLIF(LTRIM(RTRIM(Campaña)),'') IS NOT NULL AND IdCampaña IS NULL")
DISCORDANTES = ("SELECT d.IdDetalleCompra FROM dbo.Det_Compras d JOIN dbo.Campañas c ON c.IdCampaña = d.IdCampaña "
                "WHERE NULLIF(LTRIM(RTRIM(d.Campaña)),'') IS NOT NULL AND LTRIM(RTRIM(c.Campaña)) <> LTRIM(RTRIM(d.Campaña))")


def main():
    _assert_target_is_wc()
    no_aplica = fetch_all("SELECT IdCampaña AS id FROM dbo.Campañas WHERE LTRIM(RTRIM(Campaña)) = 'No Aplica'")
    assert len(no_aplica) == 1
    pendientes = fetch_all("SELECT IdDetalleCompra FROM dbo.Det_Compras WHERE LTRIM(RTRIM(Campaña)) = 'No Aplica' AND IdCampaña IS NULL")
    print('Respaldo verificado:', backup_verificado('control-campania-036'))
    with reconciliation_transaction():
        if pendientes:
            execute_write_transaction([("UPDATE dbo.Det_Compras SET IdCampaña = ? WHERE LTRIM(RTRIM(Campaña)) = 'No Aplica' AND IdCampaña IS NULL",
                                        (no_aplica[0]['id'],))])
        restantes, discordantes = fetch_all(SIN_ID), fetch_all(DISCORDANTES)
        assert not restantes and not discordantes, (restantes[:5], discordantes[:5])
        _reconciliation_connection.get().cursor().execute(TRIGGER)
    print(f"No Aplica completados: {len(pendientes)}; trigger trg_Det_Compras_Campania activo.")


if __name__ == '__main__': main()
