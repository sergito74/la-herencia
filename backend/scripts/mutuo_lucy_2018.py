"""Mutuo en dólares de Lucy (Albina Lucila Iglina) a Giamigli de Bolívar, 01/02/2018 (Sergio 22/10/2026).

Contrato "Mutuo Lucy 2018 - Compra hacienda.pdf": US$ 27.000 en efectivo; 5 cuotas anuales de capital de US$ 5.400 con
vencimiento 20/08/2019-2023; interés compensatorio 9% anual sobre el capital adeudado, pagadero con cada cuota (Anexo 1).
Uso: pagó la compra de hacienda a Yanquelen FC 0003-00000005 (08/02/2018, $541.450; Pagos efectivo 1224, caja Particular L).
No se devolvió ninguna cuota ni estaba registrado (no figura en "Cuenta Lucy").
Decisión de Sergio: deuda de Giamigli con Lucy asociada a su cuenta de socio, SOLO en dólares (respetar el acuerdo); solo el 9%
compensatorio (sin punitorio). Se registra en MovimientosCuentaSocio (socio 2) como Devolución (a favor de Lucy) con Importe 0 y
ImporteUSD: capital US$ 27.000 al 01/02/2018 y el interés de cada aniversario (20/08) = 9% del capital adeudado (US$ 2.430,
capital sin amortizar). Idempotente; correr de nuevo después de cada 20/08 agrega el interés del año.
"""
from datetime import date

from src.db.connection import _assert_target_is_wc, execute_write_transaction, fetch_all, reconciliation_transaction
from src.features.vinculos.backup import backup_verificado

LUCY = 2
USUARIO = 'Sergio (mutuo 2018, 22/10/2026)'
CAPITAL = 27000.0
TASA = 0.09


def main():
    _assert_target_is_wc()
    hoy = date.today()
    movs = [(date(2018, 2, 1), CAPITAL, 'Mutuo US$ 27.000 (01/02/2018): préstamo de Lucy a Giamigli para la compra de hacienda a Yanquelen '
                                        '(FC 0003-00000005); deuda de Giamigli con Lucy, solo en dólares')]
    for anio in range(2019, hoy.year + 1):
        venc = date(anio, 8, 20)
        if venc <= hoy:
            movs.append((venc, round(CAPITAL * TASA, 2), f'Mutuo 2018: interés compensatorio 9% anual al 20/08/{anio} sobre capital adeudado US$ 27.000'))
    st = []
    for f, usd, motivo in movs:
        if not fetch_all("SELECT 1 x FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Origen='Mutuo2018' AND Fecha=? AND Anulada=0", (LUCY, f.isoformat())):
            st.append(("INSERT INTO dbo.MovimientosCuentaSocio (IdSocio,Tipo,Importe,ImporteUSD,ImporteKgCarne,Fecha,Origen,IdOrigen,Medio,Motivo,Usuario,Anulada) "
                       "VALUES (?, 'Devolucion', 0, ?, 0, ?, 'Mutuo2018', NULL, 'Dolares', ?, ?, 0)", (LUCY, usd, f.isoformat(), motivo, USUARIO)))
    if st:
        print(backup_verificado('mutuo-lucy-2018'))
        with reconciliation_transaction():
            execute_write_transaction(st)
    r = fetch_all("SELECT SUM(ImporteUSD) u, COUNT(*) n FROM dbo.MovimientosCuentaSocio WHERE IdSocio=? AND Origen='Mutuo2018' AND Anulada=0", (LUCY,))[0]
    print(f"Mutuo registrado: {r['n']} movimientos, US$ {r['u']:,.2f} a favor de Lucy")


if __name__ == '__main__': main()
