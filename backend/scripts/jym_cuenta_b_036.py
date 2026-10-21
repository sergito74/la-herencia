"""J y M de la Serna (47): parte B de las ventas de hacienda (Sergio 21/10/2026: "el complemento es un eufemismo para la
cuenta B; tiene que cerrar en cero, no hay cobros pendientes").

La vista suma A neto + TotalB (precio B) + Complemento, y cobra comisión sobre A+B: con precio B y complemento cargados la
parte B se contaba dos veces. Regla: la parte B va SOLO en Complemento = efectivo cobrado (planilla "Cajas Giamigli.xlsx",
Caja Efectivo Pesos); precio B = 0 (así la comisión queda sobre A y el neto A = total del PDF de la liquidación).
- mar-2025 (0003-15132/15103): complementos 262.599,06 + 719.400,94 = cobro 22/04/2025 $982.000 (fila 1785).
- oct-2025: 0003-16178 y 0003-16182 son la misma liquidación ($474.641,25) y la NC 0003-16181 anula una; el complemento
  queda solo en 16182 = cobro 18/11/2025 $403.000 (fila 1809).
- mar-2026 (0003-16822): complemento = cobro 08/04/2026 $1.137.200 (fila 1823).
Cobros B: Pagos efectivo tipo 3 (cobro), caja La Herencia, cuenta Blue, importe negativo; marca [Nro Mov] = 90360000 +
10000 + fila. Idempotente.
"""
import openpyxl

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.auditoria_cuentas.bimonetaria import cargar_cuenta, invalidar
from src.features.vinculos.backup import backup_verificado

C = 47
PLANILLA = r'C:\Users\Sergio\Documents\La Herencia\Administracion y gestion\Cuentas a pagar\Cajas Giamigli.xlsx'
SIN_PRECIO_B = (135, 136, 142, 147)
COMPLEMENTO = {142: 0, 143: 403000, 144: 0, 147: 1137200}
COBROS = {1785: 982000, 1809: 403000, 1823: 1137200}  # fila de Caja Efectivo Pesos -> importe


def main():
    _assert_target_is_wc()
    ws = openpyxl.load_workbook(PLANILLA, data_only=True, read_only=True)['Caja Efectivo Pesos']
    filas = {n: r for n, r in enumerate(ws.iter_rows(min_row=1, values_only=True), start=1) if n in COBROS}
    for n, imp in COBROS.items():
        assert 'serna' in str(filas[n][3]).lower() and abs(filas[n][6] - imp) < 0.01, (n, filas[n])
    print(backup_verificado('jym-cuenta-b-036'))
    st = [('UPDATE dbo.[Det_Ventas Hacienda] SET [Precio unitario (B)]=0 WHERE IdVenta=? AND ISNULL([Precio unitario (B)],0)<>0', (v,)) for v in SIN_PRECIO_B]
    st += [('UPDATE dbo.[Venta Hacienda] SET Complemento=? WHERE IdVenta=? AND IdConsignatario=?', (c, v, C)) for v, c in COMPLEMENTO.items()]
    for n, imp in COBROS.items():
        marca = 90360000 + 10000 + n
        if not fetch_all('SELECT 1 x FROM dbo.[Pagos efectivo] WHERE IdContacto=? AND [Nro Mov]=?', (C, marca)):
            st.append(("INSERT INTO dbo.[Pagos efectivo] (IdContacto,IdTipoMovimiento,IdFormaPago,Fecha,Cuenta,Caja,[Importe imputado],[Nro Mov]) "
                       "VALUES (?,3,3,?,'Blue','La Herencia',?,?)", (C, filas[n][0], -imp, marca)))
    with reconciliation_transaction():
        execute_write_transaction(st)
    invalidar()
    print('saldo', round(cargar_cuenta(C, refrescar=True)['saldoPesos'], 2))


if __name__ == '__main__': main()
