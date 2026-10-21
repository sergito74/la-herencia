"""Mario Piccirilli (plomero): arreglo de bomba de agua en el campo, $280.000 pagados por Sergio desde su ICBC el 08/05/2026
(Sergio 21/10/2026). Piccirilli iba a mandar facturas de terceros para justificar el gasto; una fue la de Breccia (FC C
00002-00000023, $120.000, "Gacela"), que no completó el total. Decisión de Sergio: eliminar la factura de Breccia y cargar el
gasto de mantenimiento sin factura a nombre de Mario Piccirilli.
- Contacto nuevo "Piccirilli, Mario" (Proveedor).
- Compra tipo X "SIN COMPROBANTE" $280.000, clasificación de la factura de Breccia (centro 3, destino 1, rubro 5
  Mantenimiento Construcciones).
- Pago: movimiento de socio 2257 (Sergio, Devolucion, ICBC, migrado de "Cuenta Sergio") vinculado al contacto (PagosSocioProveedor).
- Se borra la factura de Breccia (Compras 2143522639, renglones y vencimiento).
Idempotente.
"""
from datetime import datetime

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.compras import repository as compras
from src.features.vinculos.backup import backup_verificado

BRECCIA = 2143522639
MOV_SOCIO = 2257


def main():
    _assert_target_is_wc()
    print(backup_verificado('piccirilli-mantenimiento-036'))
    with reconciliation_transaction():
        c = fetch_all("SELECT IdContacto i FROM dbo.Contactos WHERE [Razon Social]='Piccirilli, Mario'")
        if c:
            c = c[0]['i']
        else:
            c = execute_write_transaction([("INSERT INTO dbo.Contactos ([Tipo Contacto],[Razon Social],EsContratistaLabores) "
                                            "OUTPUT INSERTED.IdContacto VALUES ('Proveedor','Piccirilli, Mario',0)", ())])[0]
        f = datetime(2026, 5, 8)
        if not fetch_all("SELECT 1 x FROM dbo.Compras WHERE IdContacto=? AND [Nro Documento]='SIN COMPROBANTE'", (c,)):
            cab = {'idContacto': c, 'fecha': f, 'tipoDocumento': 'Factura', 'tipo': 'X', 'numeroDocumento': 'SIN COMPROBANTE',
                   'moneda': 'Pesos', 'tipoDeCambio': 1, 'ajustaTipoCambio': False}
            lin = {'productoServicio': 'Arreglo bomba de agua - mano de obra', 'cantidad': 1, 'precioUnitario': 280000, 'iva': 0,
                   'ajusteFinanciero': False, 'idCentroCosto': 3, 'idDestino': 1, 'idRubro': 5, 'campaña': 'No Aplica', 'idCampania': 20}
            execute_write_transaction([compras._cabecera_insert_statement(cab), compras._linea_insert_statement(lin),
                                       compras._vencimiento_insert_statement({'fechaVencimiento': f})])
        if not fetch_all('SELECT 1 x FROM dbo.PagosSocioProveedor WHERE IdMovimientoSocio=?', (MOV_SOCIO,)):
            execute_write_transaction([("INSERT INTO dbo.PagosSocioProveedor (IdMovimientoSocio,IdContacto,Criterio,FechaAlta) "
                                        "VALUES (?,?,'revision-036',SYSDATETIME())", (MOV_SOCIO, c))])
        if fetch_all('SELECT 1 x FROM dbo.Compras WHERE IdDeuda=?', (BRECCIA,)):
            execute_write_transaction([('DELETE FROM dbo.Det_Compras WHERE IdCompra=?', (BRECCIA,)),
                                       ('DELETE FROM dbo.[Vencimiento Compras] WHERE IdCompra=?', (BRECCIA,)),
                                       ('DELETE FROM dbo.Compras WHERE IdDeuda=? AND IdContacto=5665', (BRECCIA,))])
    invalidar()
    for x in (c, 5665):
        print(x, round(cargar_cuenta(x, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
