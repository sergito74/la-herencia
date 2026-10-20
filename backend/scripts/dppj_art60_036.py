"""Dirección Provincial de Personas Jurídicas: inscripción Art. 60 (Directorio) $275.500, exento de IVA, 12/09/2024.

Evidencia: mail de Florencia García Ullan (Estudio Criado) del 12/09/2024 "Te paso el importe de la inscripción
del Art. 60 (Directorio) $275.500.-". Se pagó con la transferencia Galicia 2104 (16/09/2024) a Criado Ricardo
Marcos, que gestionó el trámite: el pago pasa de Ricardo Criado (210) a la cuenta nueva. Indicado por Sergio 20/10/2026.
Idempotente.
"""
from datetime import date
from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.compras import repository as compras
from src.features.contactos import repository as contactos
from src.features.vinculos.backup import backup_verificado

NOMBRE = 'Dirección Provincial de Personas Jurídicas'


def main():
    _assert_target_is_wc()
    print(backup_verificado('dppj-art60-036'))
    fila = fetch_all('SELECT IdContacto FROM dbo.Contactos WHERE [Razon Social]=?', (NOMBRE,))
    id_c = fila[0]['IdContacto'] if fila else contactos.create_contacto(NOMBRE, 'Organismo', None, False)
    if not fetch_all("SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND Fecha='2024-09-12'", (id_c,)):
        compras.create_compra(
            {'idContacto': id_c, 'fecha': date(2024, 9, 12), 'tipoDocumento': 'Factura', 'tipo': 'X',
             'numeroDocumento': 'SIN DOCUMENTO', 'moneda': 'Pesos',
             'documentoOriginal': 'Mail Florencia García Ullan 12/09/2024: Inscripción Art. 60 Directorio $275.500'},
            [{'productoServicio': 'Inscripción Art. 60 Directorio', 'cantidad': 1, 'precioUnitario': 275500, 'iva': 0,
              'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 14, 'campaña': 'No Aplica'}],
            [{'fechaVencimiento': date(2024, 9, 12)}])
    with reconciliation_transaction():
        execute_write_transaction([('UPDATE dbo.[Movimientos Galicia] SET IdContacto=?, Contacto=? WHERE IdMovimiento=2104 AND IdContacto IN (210, ?)',
                                    (id_c, NOMBRE, id_c))])
    for c in (id_c, 210):
        print(c, fetch_all('SELECT SUM(Deuda-Credito) s FROM dbo.vw_MovimientosCuenta_Saldo WHERE IdContacto=?', (c,)))


if __name__ == '__main__': main()
